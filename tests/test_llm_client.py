from __future__ import annotations

import json
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
