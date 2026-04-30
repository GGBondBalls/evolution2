from __future__ import annotations

from typing import Any

from ntmemevo.envs.base import AgentEnv
from ntmemevo.types import Task, ToolResult


class TauBenchEnv(AgentEnv):
    """Placeholder adapter for the real tau-bench integration."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def load_tasks(self, max_tasks: int | None = None) -> list[Task]:
        raise NotImplementedError(
            "tau-bench is not wired in this first coding round. "
            "Use configs/tiny_nomem.yaml for the offline smoke test, then install tau-bench "
            "and implement this adapter against its task and tool APIs."
        )

    def tool_descriptions(self) -> str:
        raise NotImplementedError("tau-bench tool descriptions are not implemented yet.")

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> ToolResult:
        raise NotImplementedError("tau-bench tool calls are not implemented yet.")

    def evaluate(self, task: Task, final_answer: str) -> tuple[bool, float, str | None]:
        raise NotImplementedError("tau-bench evaluation is not implemented yet.")
