from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ntmemevo.types import AgentResult, Task


@dataclass(frozen=True)
class ReflectionMemory:
    memory_id: str
    task_id: str
    instruction: str
    reflection: str
    reflection_type: str
    final_answer: str
    trace_summary: tuple[str, ...]
    reward: float
    success: bool
    error_type: str | None
    created_iter: int

    @property
    def text(self) -> str:
        trace = " | ".join(self.trace_summary) if self.trace_summary else "no tool trace"
        outcome = "success" if self.success else "failure"
        return (
            f"Reflection from prior {outcome} task. "
            f"Instruction: {self.instruction} "
            f"Lesson: {self.reflection} "
            f"Trace evidence: {trace}. "
            f"Final answer: {self.final_answer}"
        )

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["trace_summary"] = list(self.trace_summary)
        data["text"] = self.text
        return data

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "ReflectionMemory":
        return cls(
            memory_id=str(data["memory_id"]),
            task_id=str(data["task_id"]),
            instruction=str(data["instruction"]),
            reflection=str(data["reflection"]),
            reflection_type=str(data.get("reflection_type", "strategy")),
            final_answer=str(data.get("final_answer", "")),
            trace_summary=tuple(data.get("trace_summary", [])),
            reward=float(data.get("reward", 0.0)),
            success=bool(data.get("success", False)),
            error_type=data.get("error_type"),
            created_iter=int(data.get("created_iter", 0)),
        )


class ReflectionExtractor:
    def __init__(self, max_reflection_chars: int = 700) -> None:
        self.max_reflection_chars = max_reflection_chars

    def extract(self, task: Task, result: AgentResult, iteration: int) -> ReflectionMemory:
        reflection_type = "strategy" if result.success else "warning"
        reflection = self._build_reflection(task=task, result=result)
        if len(reflection) > self.max_reflection_chars:
            reflection = reflection[: self.max_reflection_chars - 3].rstrip() + "..."
        return ReflectionMemory(
            memory_id=f"refl_{iteration:06d}_{task.task_id}",
            task_id=task.task_id,
            instruction=task.instruction,
            reflection=reflection,
            reflection_type=reflection_type,
            final_answer=result.final_answer,
            trace_summary=result.trace_summary,
            reward=result.reward,
            success=result.success,
            error_type=result.error_type,
            created_iter=iteration,
        )

    def _build_reflection(self, task: Task, result: AgentResult) -> str:
        tool_sequence = self._tool_sequence(result.trace_summary)
        trace = " | ".join(result.trace_summary) if result.trace_summary else "no tool was called"
        expected = ", ".join(task.expected_answer_contains) if task.expected_answer_contains else "the evaluator target"

        if result.success:
            return (
                f"For similar tasks, map the instruction to the needed tool evidence, "
                f"use the tool sequence {tool_sequence}, and ground the final response in the observation. "
                f"This run satisfied expected answer signal(s): {expected}. "
                f"Do not add unsupported details beyond the observed result. Evidence: {trace}."
            )

        error = result.error_type or "unknown_error"
        return (
            f"A similar attempt failed with {error}. Before finalizing, verify that the answer contains "
            f"the expected signal(s): {expected}. If the trace is insufficient, call the relevant tool "
            f"instead of guessing. Failed trace evidence: {trace}."
        )

    def _tool_sequence(self, trace_summary: tuple[str, ...]) -> str:
        tool_names = []
        for item in trace_summary:
            name = item.split("(", maxsplit=1)[0].strip()
            if name:
                tool_names.append(name)
        return " -> ".join(tool_names) if tool_names else "no tool"


class ReflectionMemoryStore:
    def __init__(
        self,
        path: str | Path,
        save_successes: bool = True,
        save_failures: bool = True,
        extractor: ReflectionExtractor | None = None,
    ) -> None:
        self.path = Path(path)
        self.save_successes = save_successes
        self.save_failures = save_failures
        self.extractor = extractor or ReflectionExtractor()
        self.memories: list[ReflectionMemory] = []
        if self.path.exists() and self.path.stat().st_size > 0:
            self.load()

    def load(self) -> None:
        self.memories = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                self.memories.append(ReflectionMemory.from_json(json.loads(line)))

    def add_from_result(self, task: Task, result: AgentResult, iteration: int) -> ReflectionMemory | None:
        if result.success and not self.save_successes:
            return None
        if not result.success and not self.save_failures:
            return None
        memory = self.extractor.extract(task=task, result=result, iteration=iteration)
        self.memories.append(memory)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(memory.to_json(), ensure_ascii=False) + "\n")
        return memory

    def all(self) -> list[ReflectionMemory]:
        return list(self.memories)
