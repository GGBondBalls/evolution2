from __future__ import annotations

import ast
import json
import os
import re
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
        tool_match = re.search(
            r"\b(get_order_status|check_inventory|check_exchange_eligibility|lookup_policy)"
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
    raise ValueError(f"Unsupported LLM provider: {provider}")
