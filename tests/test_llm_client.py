from __future__ import annotations

import json
import urllib.error
from unittest.mock import patch

from ntmemevo.llm.client import create_llm_client
from ntmemevo.types import ChatMessage


class _FakeHTTPResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class _FakeHTTPErrorBody:
    def __init__(self, body: str) -> None:
        self.body = body

    def read(self) -> bytes:
        return self.body.encode("utf-8")

    def close(self) -> None:
        return None


def test_vllm_openai_compatible_client_uses_local_http_endpoint() -> None:
    requests: list[dict[str, object]] = []

    def fake_urlopen(request: object, timeout: float) -> _FakeHTTPResponse:
        del timeout
        url = getattr(request, "full_url")
        method = request.get_method()
        if method == "GET" and url == "http://127.0.0.1:8000/v1/models":
            return _FakeHTTPResponse(
                {"object": "list", "data": [{"id": "qwen3.5-9b"}]}
            )
        if method == "POST" and url == "http://127.0.0.1:8000/v1/chat/completions":
            data = getattr(request, "data")
            payload = json.loads(data.decode("utf-8"))
            requests.append(payload)
            return _FakeHTTPResponse(
                {
                    "id": "chatcmpl-test",
                    "object": "chat.completion",
                    "model": payload["model"],
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": (
                                    "<think>reasoning omitted</think>\n"
                                    "```json\n"
                                    '{"action":"final","answer":"ok"}\n'
                                    "```"
                                ),
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 7,
                        "completion_tokens": 5,
                        "total_tokens": 12,
                    },
                }
            )
        raise AssertionError(f"Unexpected request: {method} {url}")

    with patch.dict(
        "os.environ",
        {"VLLM_TEST_BASE_URL": "http://127.0.0.1:8000/v1"},
    ), patch("urllib.request.urlopen", side_effect=fake_urlopen):
        client = create_llm_client(
            {
                "provider": "vllm",
                "model": "qwen3.5-9b",
                "base_url_env": "VLLM_TEST_BASE_URL",
                "base_url": "http://127.0.0.1:9999/v1",
                "api_key": "EMPTY",
                "healthcheck": True,
                "extract_json_object": True,
                "strip_thinking": True,
                "request_retries": 0,
            }
        )

        response = client.complete(
            messages=[
                ChatMessage(role="system", content="Return JSON."),
                ChatMessage(role="user", content="Say ok."),
            ],
            response_format={"type": "json_object"},
        )

    assert json.loads(response.content) == {"action": "final", "answer": "ok"}
    assert response.model == "qwen3.5-9b"
    assert response.usage.total_tokens == 12
    assert requests
    request_payload = requests[-1]
    assert request_payload["model"] == "qwen3.5-9b"
    assert request_payload["response_format"] == {"type": "json_object"}


def test_vllm_client_reduces_max_tokens_after_context_overflow() -> None:
    requests: list[dict[str, object]] = []

    def fake_urlopen(request: object, timeout: float) -> _FakeHTTPResponse:
        del timeout
        payload = json.loads(getattr(request, "data").decode("utf-8"))
        requests.append(payload)
        if len(requests) == 1:
            error_body = json.dumps(
                {
                    "error": {
                        "message": (
                            "This model's maximum context length is 4096 tokens. "
                            "However, you requested 1536 output tokens and your prompt "
                            "contains at least 2561 input tokens, for a total of at least "
                            "4097 tokens."
                        ),
                        "type": "BadRequestError",
                        "param": "input_tokens",
                    }
                }
            )
            raise urllib.error.HTTPError(
                url="http://127.0.0.1:8000/v1/chat/completions",
                code=400,
                msg="Bad Request",
                hdrs=None,
                fp=_FakeHTTPErrorBody(error_body),
            )
        return _FakeHTTPResponse(
            {
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "model": payload["model"],
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": '{"action":"final","answer":"ok"}',
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 2561,
                    "completion_tokens": 12,
                    "total_tokens": 2573,
                },
            }
        )

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        client = create_llm_client(
            {
                "provider": "vllm",
                "model": "qwen3.5-9b",
                "base_url": "http://127.0.0.1:8000/v1",
                "api_key": "EMPTY",
                "healthcheck": False,
                "request_retries": 1,
                "retry_sleep_seconds": 0,
                "context_overflow_margin_tokens": 128,
            }
        )

        response = client.complete(
            messages=[ChatMessage(role="user", content="Return JSON.")],
            max_tokens=1536,
            response_format={"type": "json_object"},
        )

    assert json.loads(response.content) == {"action": "final", "answer": "ok"}
    assert len(requests) == 2
    assert requests[0]["max_tokens"] == 1536
    assert requests[1]["max_tokens"] == 1407


def test_vllm_client_reduces_max_tokens_when_margin_is_too_large() -> None:
    requests: list[dict[str, object]] = []

    def fake_urlopen(request: object, timeout: float) -> _FakeHTTPResponse:
        del timeout
        payload = json.loads(getattr(request, "data").decode("utf-8"))
        requests.append(payload)
        if len(requests) == 1:
            error_body = json.dumps(
                {
                    "error": {
                        "message": (
                            "This model's maximum context length is 4096 tokens. "
                            "However, you requested 255 output tokens and your prompt "
                            "contains at least 3842 input tokens, for a total of at least "
                            "4097 tokens."
                        ),
                        "type": "BadRequestError",
                        "param": "input_tokens",
                    }
                }
            )
            raise urllib.error.HTTPError(
                url="http://127.0.0.1:8000/v1/chat/completions",
                code=400,
                msg="Bad Request",
                hdrs=None,
                fp=_FakeHTTPErrorBody(error_body),
            )
        return _FakeHTTPResponse(
            {
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "model": payload["model"],
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": '{"action":"final","answer":"ok"}',
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 3842,
                    "completion_tokens": 12,
                    "total_tokens": 3854,
                },
            }
        )

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        client = create_llm_client(
            {
                "provider": "vllm",
                "model": "qwen3.5-9b",
                "base_url": "http://127.0.0.1:8000/v1",
                "api_key": "EMPTY",
                "healthcheck": False,
                "request_retries": 1,
                "retry_sleep_seconds": 0,
                "context_overflow_margin_tokens": 256,
            }
        )

        response = client.complete(
            messages=[ChatMessage(role="user", content="Return JSON.")],
            max_tokens=255,
            response_format={"type": "json_object"},
        )

    assert json.loads(response.content) == {"action": "final", "answer": "ok"}
    assert len(requests) == 2
    assert requests[0]["max_tokens"] == 255
    assert requests[1]["max_tokens"] == 253
