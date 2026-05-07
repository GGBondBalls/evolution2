from __future__ import annotations

import ast
import json
import os
import re
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Any

from ntmemevo.llm.cost import estimate_tokens
from ntmemevo.types import ChatMessage, LLMResponse, LLMUsage


class LLMClient(ABC):
    @abstractmethod
    def complete(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.0,
        max_tokens: int = 1024,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        raise NotImplementedError


class MockLLMClient(LLMClient):
    """Deterministic tool-use model for offline smoke tests."""

    def __init__(self, model: str = "mock-tool-agent", follow_memory_hints: bool = False) -> None:
        self.model = model
        self.follow_memory_hints = follow_memory_hints

    def complete(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.0,
        max_tokens: int = 1024,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        prompt = "\n".join(message.content for message in messages)
        content = json.dumps(self._decide(prompt), ensure_ascii=False)
        prompt_tokens = sum(estimate_tokens(message.content) for message in messages)
        completion_tokens = estimate_tokens(content)
        return LLMResponse(
            content=content,
            model=self.model,
            usage=LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            raw={"provider": "mock"},
        )

    def _decide(self, prompt: str) -> dict[str, Any]:
        lower_prompt = prompt.lower()
        observations = re.findall(r"observation:\s*(.+)", prompt, flags=re.IGNORECASE)
        if observations:
            last = observations[-1].strip()
            return {
                "thought": "The latest tool observation is sufficient to answer.",
                "action": "final",
                "answer": last,
            }

        instruction_match = re.search(r"^instruction:\s*(.+)$", prompt, flags=re.IGNORECASE | re.MULTILINE)
        task_text = instruction_match.group(1) if instruction_match else prompt
        lower_task = task_text.lower()

        if self.follow_memory_hints:
            memory_decision = self._decide_from_retrieved_memory(prompt)
            if memory_decision:
                return memory_decision

        if "ord-1001" in lower_task:
            return {
                "thought": "The task asks for order status.",
                "action": "tool",
                "tool_name": "get_order_status",
                "args": {"order_id": "ORD-1001"},
            }
        if "ord-1002" in lower_task:
            return {
                "thought": "Refund eligibility depends on order status.",
                "action": "tool",
                "tool_name": "get_order_status",
                "args": {"order_id": "ORD-1002"},
            }
        if "ord-1003" in lower_task and "sku-blue-s" in lower_task:
            return {
                "thought": "Exchange eligibility depends on replacement stock.",
                "action": "tool",
                "tool_name": "check_exchange_eligibility",
                "args": {"order_id": "ORD-1003", "replacement_sku": "SKU-BLUE-S"},
            }
        if "sku-red-m" in lower_task:
            return {
                "thought": "The task asks for inventory status.",
                "action": "tool",
                "tool_name": "check_inventory",
                "args": {"sku": "SKU-RED-M"},
            }
        if "return window" in lower_task:
            return {
                "thought": "The task asks for a policy lookup.",
                "action": "tool",
                "tool_name": "lookup_policy",
                "args": {"policy_name": "return_window"},
            }
        tau_retail_decision = self._decide_tau_retail_task(task_text)
        if tau_retail_decision is not None:
            return tau_retail_decision

        return {
            "thought": "No matching tool-use pattern was found.",
            "action": "final",
            "answer": "Unable to determine the answer from the available tools.",
        }

    def _decide_from_retrieved_memory(self, prompt: str) -> dict[str, Any] | None:
        block_match = re.search(
            r"retrieved memories:\s*(.*?)\navailable tools:",
            prompt,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not block_match:
            return None
        memory_block = block_match.group(1)
        tool_names = (
            "get_order_status",
            "check_inventory",
            "check_exchange_eligibility",
            "lookup_policy",
            "find_user_id_by_name_zip",
            "find_user_id_by_email",
            "get_user_details",
            "get_order_details",
            "get_product_details",
            "get_item_details",
            "list_all_product_types",
            "modify_user_address",
            "modify_pending_order_address",
            "modify_pending_order_payment",
            "modify_pending_order_items",
            "cancel_pending_order",
            "return_delivered_order_items",
            "exchange_delivered_order_items",
        )
        tool_match = re.search(
            r"\b(" + "|".join(re.escape(name) for name in tool_names) + r")"
            r"\((\{.*?\})\)",
            memory_block,
            flags=re.DOTALL,
        )
        if not tool_match:
            return None
        tool_name = tool_match.group(1)
        try:
            args = ast.literal_eval(tool_match.group(2))
        except (SyntaxError, ValueError):
            args = {}
        if not isinstance(args, dict):
            args = {}
        return {
            "thought": "Following the highest-ranked retrieved memory tool hint.",
            "action": "tool",
            "tool_name": tool_name,
            "args": args,
        }

    def _decide_tau_retail_task(self, task_text: str) -> dict[str, Any] | None:
        lower_task = task_text.lower()
        if "user id" in lower_task and ("zip" in lower_task or "postal" in lower_task):
            name_match = re.search(
                r"(?:for|named)\s+([A-Z][A-Za-z'-]+)\s+([A-Z][A-Za-z'-]+)",
                task_text,
            )
            zip_match = re.search(r"\b(\d{5})(?:-\d{4})?\b", task_text)
            if name_match and zip_match:
                return {
                    "thought": "The task asks for a customer id by name and zip code.",
                    "action": "tool",
                    "tool_name": "find_user_id_by_name_zip",
                    "args": {
                        "first_name": name_match.group(1),
                        "last_name": name_match.group(2),
                        "zip": zip_match.group(1),
                    },
                }

        email_match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", task_text)
        if email_match and ("user" in lower_task or "customer" in lower_task):
            return {
                "thought": "The task asks for a customer id by email.",
                "action": "tool",
                "tool_name": "find_user_id_by_email",
                "args": {"email": email_match.group(0)},
            }

        order_match = re.search(
            r"\border\s+#?([A-Z][A-Z0-9_-]{3,}\d[A-Z0-9_-]*)",
            task_text,
            flags=re.IGNORECASE,
        ) or re.search(
            r"#?([A-Z][A-Z0-9_-]{3,}\d[A-Z0-9_-]*)",
            task_text,
            flags=re.IGNORECASE,
        )
        if order_match and "cancel" in lower_task:
            return {
                "thought": "The task asks to cancel a pending retail order.",
                "action": "tool",
                "tool_name": "cancel_pending_order",
                "args": {
                    "order_id": order_match.group(1).upper(),
                    "reason": "customer_request",
                },
            }

        if order_match and "return" in lower_task:
            item_match = re.search(r"\b(item[_-][A-Za-z0-9_-]+|item\d+)\b", task_text, flags=re.IGNORECASE)
            item_ids = [item_match.group(1)] if item_match else []
            return {
                "thought": "The task asks to return delivered order items.",
                "action": "tool",
                "tool_name": "return_delivered_order_items",
                "args": {
                    "order_id": order_match.group(1).upper(),
                    "item_ids": item_ids,
                },
            }

        if order_match and "exchange" in lower_task:
            item_match = re.search(r"\b(item[_-][A-Za-z0-9_-]+|item\d+)\b", task_text, flags=re.IGNORECASE)
            product_match_for_exchange = re.search(
                r"(?:product|item)\s+(?:id\s+)?#?([A-Z0-9][A-Za-z0-9_-]{4,})\b",
                task_text,
                flags=re.IGNORECASE,
            )
            return {
                "thought": "The task asks to exchange delivered order items.",
                "action": "tool",
                "tool_name": "exchange_delivered_order_items",
                "args": {
                    "order_id": order_match.group(1).upper(),
                    "item_ids": [item_match.group(1)] if item_match else [],
                    "new_item_ids": (
                        [product_match_for_exchange.group(1)]
                        if product_match_for_exchange
                        else []
                    ),
                },
            }

        if order_match and "order" in lower_task:
            return {
                "thought": "The task asks for order details.",
                "action": "tool",
                "tool_name": "get_order_details",
                "args": {"order_id": order_match.group(1).upper()},
            }

        product_match = re.search(
            r"(?:product|item)\s+(?:id\s+)?#?([A-Z0-9][A-Za-z0-9_-]{4,})\b",
            task_text,
            flags=re.IGNORECASE,
        )
        if product_match and product_match.group(1).lower() in {"detail", "details"}:
            product_match = re.search(
                r"(?:for|about)\s+(?:product|item)\s+(?:id\s+)?#?([A-Z0-9][A-Za-z0-9_-]{4,})\b",
                task_text,
                flags=re.IGNORECASE,
            )
        if product_match and "item" in lower_task and "product" not in lower_task:
            return {
                "thought": "The task asks for item variant details.",
                "action": "tool",
                "tool_name": "get_item_details",
                "args": {"item_id": product_match.group(1)},
            }

        if product_match and ("product" in lower_task or "item" in lower_task):
            return {
                "thought": "The task asks for product details.",
                "action": "tool",
                "tool_name": "get_product_details",
                "args": {"product_id": product_match.group(1)},
            }

        if "list" in lower_task and "product type" in lower_task:
            return {
                "thought": "The task asks for product type enumeration.",
                "action": "tool",
                "tool_name": "list_all_product_types",
                "args": {},
            }

        if "policy" in lower_task:
            policy_name = "return_window"
            if "exchange" in lower_task:
                policy_name = "exchange_policy"
            elif "cancel" in lower_task:
                policy_name = "cancellation_policy"
            return {
                "thought": "The task asks for a retail policy lookup.",
                "action": "tool",
                "tool_name": "lookup_policy",
                "args": {"policy_name": policy_name},
            }

        if "human agent" in lower_task or "human support" in lower_task:
            return {
                "thought": "The task asks to transfer the user to a human agent.",
                "action": "tool",
                "tool_name": "transfer_to_human_agents",
                "args": {"summary": task_text[:200]},
            }

        return None


class OpenAIChatClient(LLMClient):
    def __init__(self, model: str) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI provider requires `pip install -e .[openai]`."
            ) from exc
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is required for the OpenAI provider.")
        self.model = model
        self.client = OpenAI()

    def complete(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.0,
        max_tokens: int = 1024,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [message.__dict__ for message in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format
        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        usage = response.usage
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        return LLMResponse(
            content=content,
            model=self.model,
            usage=LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            raw=response.model_dump() if hasattr(response, "model_dump") else {},
        )


class OpenAICompatibleChatClient(LLMClient):
    """HTTP client for vLLM and other OpenAI-compatible chat servers.

    The project uses this path for local Qwen/vLLM actors so experiments do not
    require the OpenAI Python SDK or a hosted API key.
    """

    def __init__(
        self,
        model: str,
        base_url: str = "http://127.0.0.1:8000/v1",
        api_key: str = "EMPTY",
        timeout_seconds: float = 120.0,
        request_retries: int = 1,
        retry_sleep_seconds: float = 1.0,
        provider_name: str = "openai_compatible",
        healthcheck: bool = True,
        disable_response_format: bool = False,
        extract_json_object: bool = False,
        strip_thinking: bool = False,
        extra_body: dict[str, Any] | None = None,
        context_overflow_margin_tokens: int = 64,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.request_retries = max(0, request_retries)
        self.retry_sleep_seconds = max(0.0, retry_sleep_seconds)
        self.provider_name = provider_name
        self.disable_response_format = disable_response_format
        self.extract_json_object = extract_json_object
        self.strip_thinking = strip_thinking
        self.extra_body = dict(extra_body or {})
        self.context_overflow_margin_tokens = max(0, context_overflow_margin_tokens)
        if healthcheck:
            self._healthcheck()

    def complete(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.0,
        max_tokens: int = 1024,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [message.__dict__ for message in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format and not self.disable_response_format:
            payload["response_format"] = response_format
        payload.update(self.extra_body)

        response = self._request_json(
            method="POST",
            path="/chat/completions",
            payload=payload,
        )
        choices = response.get("choices") or []
        if not choices:
            raise RuntimeError(
                f"{self.provider_name} chat completion returned no choices."
            )
        message = choices[0].get("message") if isinstance(choices[0], dict) else {}
        if not isinstance(message, dict):
            message = {}
        content = str(message.get("content") or "")
        if self.strip_thinking:
            content = _strip_thinking_blocks(content)
        if self.extract_json_object and response_format:
            content = _extract_first_json_object(content)

        usage = response.get("usage") or {}
        if not isinstance(usage, dict):
            usage = {}
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))
        return LLMResponse(
            content=content,
            model=str(response.get("model") or self.model),
            usage=LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
            raw={
                "provider": self.provider_name,
                "base_url": self.base_url,
                "response": response,
            },
        )

    def _healthcheck(self) -> None:
        try:
            self._request_json(method="GET", path="/models", payload=None)
        except RuntimeError as exc:
            raise RuntimeError(
                f"Cannot reach {self.provider_name} server at {self.base_url}. "
                "Start the local vLLM OpenAI-compatible service first, for example "
                "`bash scripts/start_vllm_qwen35_9b.sh`, or set "
                "`models.actor.healthcheck: false` for dry config construction."
            ) from exc

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        body = None
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        attempts = self.request_retries + 1
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            request = urllib.request.Request(
                url=url,
                data=body,
                headers=headers,
                method=method,
            )
            try:
                with urllib.request.urlopen(
                    request,
                    timeout=self.timeout_seconds,
                ) as handle:
                    raw_body = handle.read().decode("utf-8")
            except urllib.error.HTTPError as exc:
                error_body = exc.read().decode("utf-8", errors="replace")
                last_error = RuntimeError(
                    f"{self.provider_name} HTTP {exc.code} from {url}: {error_body}"
                )
                adjusted_payload = _reduce_max_tokens_for_context_overflow(
                    payload=payload,
                    error_body=error_body,
                    margin_tokens=self.context_overflow_margin_tokens,
                )
                if adjusted_payload is not None and attempt < attempts:
                    payload = adjusted_payload
                    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                    continue
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
            else:
                try:
                    data = json.loads(raw_body)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        f"{self.provider_name} returned non-JSON response from {url}: "
                        f"{raw_body[:500]}"
                    ) from exc
                if not isinstance(data, dict):
                    raise RuntimeError(
                        f"{self.provider_name} returned unexpected JSON type from {url}."
                    )
                return data
            if attempt < attempts and self.retry_sleep_seconds:
                time.sleep(self.retry_sleep_seconds)
        raise RuntimeError(
            f"{self.provider_name} request failed after {attempts} attempt(s): {last_error}"
        )


def _strip_thinking_blocks(text: str) -> str:
    stripped = re.sub(r"(?is)<think>.*?</think>", "", text).strip()
    if "</think>" in stripped.lower():
        stripped = re.split(r"(?i)</think>", stripped, maxsplit=1)[-1].strip()
    return stripped


def _extract_first_json_object(text: str) -> str:
    candidate = text.strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        return json.dumps(parsed, ensure_ascii=False)

    cleaned = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).replace("```", "")
    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return json.dumps(parsed, ensure_ascii=False)
    return candidate


def create_llm_client(config: dict[str, Any]) -> LLMClient:
    provider = str(config.get("provider", "mock")).lower()
    model = str(config.get("model", "mock-tool-agent"))
    if provider == "mock":
        return MockLLMClient(
            model=model,
            follow_memory_hints=bool(config.get("follow_memory_hints", False)),
        )
    if provider == "openai":
        return OpenAIChatClient(model=model)
    if provider in {"vllm", "local_vllm", "openai_compatible"}:
        base_url_env = str(config.get("base_url_env", "VLLM_BASE_URL"))
        base_url = str(
            os.getenv(base_url_env)
            or config.get("base_url")
            or os.getenv("OPENAI_BASE_URL")
            or "http://127.0.0.1:8000/v1"
        )
        api_key = str(
            _resolve_secret_config_value(
                config.get("api_key"),
                env_name=str(config.get("api_key_env", "VLLM_API_KEY")),
                default="EMPTY",
            )
        )
        raw_extra_body = config.get("extra_body") or config.get("request_body") or {}
        if not isinstance(raw_extra_body, dict):
            raise ValueError("models.actor.extra_body must be a mapping when provided.")
        extra_body = dict(raw_extra_body)
        for key in [
            "top_p",
            "top_k",
            "min_p",
            "repetition_penalty",
            "presence_penalty",
            "frequency_penalty",
            "seed",
            "stop",
        ]:
            if key in config:
                extra_body[key] = config[key]
        return OpenAICompatibleChatClient(
            model=model,
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=float(config.get("timeout_seconds", 120.0)),
            request_retries=int(config.get("request_retries", 1)),
            retry_sleep_seconds=float(config.get("retry_sleep_seconds", 1.0)),
            provider_name=provider,
            healthcheck=bool(config.get("healthcheck", True)),
            disable_response_format=bool(config.get("disable_response_format", False)),
            extract_json_object=bool(config.get("extract_json_object", True)),
            strip_thinking=bool(config.get("strip_thinking", True)),
            extra_body=extra_body,
            context_overflow_margin_tokens=int(
                config.get("context_overflow_margin_tokens", 64)
            ),
        )
    raise ValueError(f"Unsupported LLM provider: {provider}")


def _resolve_secret_config_value(
    value: Any,
    env_name: str,
    default: str,
) -> str:
    if value is None:
        return os.getenv(env_name, default)
    if isinstance(value, str) and value.startswith("env:"):
        return os.getenv(value.removeprefix("env:"), default)
    return str(value)


def _reduce_max_tokens_for_context_overflow(
    payload: dict[str, Any] | None,
    error_body: str,
    margin_tokens: int = 64,
) -> dict[str, Any] | None:
    if payload is None or "max_tokens" not in payload:
        return None
    try:
        current_max_tokens = int(payload.get("max_tokens") or 0)
    except (TypeError, ValueError):
        return None
    if current_max_tokens <= 1:
        return None

    match = re.search(
        r"maximum context length is\s+(\d+)\s+tokens.*?"
        r"requested\s+(\d+)\s+output tokens.*?"
        r"prompt contains at least\s+(\d+)\s+input tokens",
        error_body,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None

    context_window = int(match.group(1))
    prompt_tokens = int(match.group(3))
    adjusted_max_tokens = context_window - prompt_tokens - margin_tokens
    if adjusted_max_tokens < 1 and margin_tokens > 0:
        adjusted_max_tokens = context_window - prompt_tokens - 1
    if adjusted_max_tokens < 1 or adjusted_max_tokens >= current_max_tokens:
        return None

    adjusted = dict(payload)
    adjusted["max_tokens"] = adjusted_max_tokens
    return adjusted
