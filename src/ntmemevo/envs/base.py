from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ntmemevo.types import Task, ToolResult


class AgentEnv(ABC):
    @abstractmethod
    def load_tasks(self, max_tasks: int | None = None) -> list[Task]:
        raise NotImplementedError

    @abstractmethod
    def tool_descriptions(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def call_tool(self, tool_name: str, args: dict[str, Any]) -> ToolResult:
        raise NotImplementedError

    @abstractmethod
    def evaluate(self, task: Task, final_answer: str) -> tuple[bool, float, str | None]:
        raise NotImplementedError
