from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


MessageRole = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True)
class ChatMessage:
    role: MessageRole
    content: str


@dataclass(frozen=True)
class LLMUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str
    usage: LLMUsage = field(default_factory=LLMUsage)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Task:
    task_id: str
    instruction: str
    expected_answer_contains: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    args: dict[str, Any]
    observation: str
    ok: bool = True


@dataclass(frozen=True)
class AgentResult:
    task_id: str
    success: bool
    reward: float
    final_answer: str
    num_steps: int
    prompt_tokens: int
    completion_tokens: int
    tool_calls: int
    used_memory_ids: tuple[str, ...] = ()
    trace_summary: tuple[str, ...] = ()
    error_type: str | None = None
    evaluation_details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievedMemory:
    memory_id: str
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
