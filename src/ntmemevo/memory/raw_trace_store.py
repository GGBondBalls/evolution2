from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ntmemevo.types import AgentResult, Task


@dataclass(frozen=True)
class RawTraceMemory:
    memory_id: str
    task_id: str
    instruction: str
    final_answer: str
    trace_summary: tuple[str, ...]
    reward: float
    success: bool
    created_iter: int

    @property
    def text(self) -> str:
        trace = " | ".join(self.trace_summary) if self.trace_summary else "no tool trace"
        outcome = "success" if self.success else "failure"
        return (
            f"Past task: {self.instruction} "
            f"Outcome: {outcome}, reward={self.reward:.1f}. "
            f"Trace: {trace}. "
            f"Final answer: {self.final_answer}"
        )

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["trace_summary"] = list(self.trace_summary)
        data["text"] = self.text
        return data

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "RawTraceMemory":
        return cls(
            memory_id=str(data["memory_id"]),
            task_id=str(data["task_id"]),
            instruction=str(data["instruction"]),
            final_answer=str(data.get("final_answer", "")),
            trace_summary=tuple(data.get("trace_summary", [])),
            reward=float(data.get("reward", 0.0)),
            success=bool(data.get("success", False)),
            created_iter=int(data.get("created_iter", 0)),
        )


class RawTraceMemoryStore:
    def __init__(self, path: str | Path, save_failures: bool = True) -> None:
        self.path = Path(path)
        self.save_failures = save_failures
        self.memories: list[RawTraceMemory] = []
        if self.path.exists() and self.path.stat().st_size > 0:
            self.load()

    def load(self) -> None:
        self.memories = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                self.memories.append(RawTraceMemory.from_json(json.loads(line)))

    def add_from_result(self, task: Task, result: AgentResult, iteration: int) -> RawTraceMemory | None:
        if not result.success and not self.save_failures:
            return None
        memory = RawTraceMemory(
            memory_id=f"raw_{iteration:06d}_{task.task_id}",
            task_id=task.task_id,
            instruction=task.instruction,
            final_answer=result.final_answer,
            trace_summary=result.trace_summary,
            reward=result.reward,
            success=result.success,
            created_iter=iteration,
        )
        self.memories.append(memory)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(memory.to_json(), ensure_ascii=False) + "\n")
        return memory

    def all(self) -> list[RawTraceMemory]:
        return list(self.memories)
