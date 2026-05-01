from __future__ import annotations

import json
import math
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from ntmemevo.memory.extractor import CandidateExtractionContext, CandidateMemoryExtractor
from ntmemevo.memory.schema import CandidateMemory, MemoryLifecycle, MemoryUtility
from ntmemevo.types import AgentResult, Task


UtilityOutcome = Literal["helpful", "harmful", "neutral"]


@dataclass(frozen=True)
class UtilityUpdate:
    memory: CandidateMemory
    outcome: UtilityOutcome
    baseline_reward: float
    delta_reward: float
    utility_before: MemoryUtility
    utility_after: MemoryUtility
    lifecycle_before: MemoryLifecycle
    lifecycle_after: MemoryLifecycle

    def to_json(self) -> dict[str, object]:
        return {
            "memory_id": self.memory.memory_id,
            "outcome": self.outcome,
            "baseline_reward": self.baseline_reward,
            "delta_reward": self.delta_reward,
            "utility_before": self.utility_before.to_json(),
            "utility_after": self.utility_after.to_json(),
            "lifecycle_before": self.lifecycle_before.to_json(),
            "lifecycle_after": self.lifecycle_after.to_json(),
            "positive_evidence": list(self.memory.positive_evidence),
            "negative_evidence": list(self.memory.negative_evidence),
        }


class CandidateMemoryStore:
    def __init__(
        self,
        path: str | Path,
        benchmark: str,
        experiment_id: str,
        save_successes: bool = True,
        save_failures: bool = True,
        extractor: CandidateMemoryExtractor | None = None,
    ) -> None:
        self.path = Path(path)
        self.benchmark = benchmark
        self.experiment_id = experiment_id
        self.save_successes = save_successes
        self.save_failures = save_failures
        self.extractor = extractor or CandidateMemoryExtractor()
        self.memories: list[CandidateMemory] = []
        if self.path.exists() and self.path.stat().st_size > 0:
            self.load()

    def load(self) -> None:
        self.memories = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                self.memories.append(CandidateMemory.from_json(json.loads(line)))

    def add_from_result(
        self,
        task: Task,
        result: AgentResult,
        iteration: int,
        run_id: str | None = None,
    ) -> CandidateMemory | None:
        if result.success and not self.save_successes:
            return None
        if not result.success and not self.save_failures:
            return None
        source_run_id = run_id or f"{self.experiment_id}_{task.task_id}"
        memory = self.extractor.extract(
            task=task,
            result=result,
            context=CandidateExtractionContext(
                benchmark=self.benchmark,
                experiment_id=self.experiment_id,
                run_id=source_run_id,
                iteration=iteration,
            ),
        )
        self.memories.append(memory)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(memory.to_json(), ensure_ascii=False) + "\n")
        return memory

    def import_jsonl(self, path: str | Path, append_to_store_file: bool = True) -> list[CandidateMemory]:
        source_path = Path(path)
        imported: list[CandidateMemory] = []
        if not source_path.exists():
            raise FileNotFoundError(f"Candidate memory bootstrap file not found: {source_path}")

        existing_ids = {memory.memory_id for memory in self.memories}
        with source_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                memory = CandidateMemory.from_json(json.loads(line))
                if memory.memory_id in existing_ids:
                    raise ValueError(f"Duplicate candidate memory id: {memory.memory_id}")
                existing_ids.add(memory.memory_id)
                imported.append(memory)

        self.memories.extend(imported)
        if append_to_store_file and imported:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                for memory in imported:
                    handle.write(json.dumps(memory.to_json(), ensure_ascii=False) + "\n")
        return imported

    def update_utility(
        self,
        memory_id: str,
        result: AgentResult,
        iteration: int,
        run_id: str,
        no_memory_success: bool = True,
        no_memory_reward: float | None = None,
        promote_after_helpful: int = 2,
        quarantine_after_harmful: int = 1,
    ) -> UtilityUpdate:
        index, memory = self._find(memory_id)
        utility_before = memory.utility
        lifecycle_before = memory.lifecycle
        baseline_reward = (
            float(no_memory_reward)
            if no_memory_reward is not None
            else (1.0 if no_memory_success else 0.0)
        )
        observed_reward = _clamp(float(result.reward), 0.0, 1.0)
        delta_reward = _clamp(observed_reward - baseline_reward, -1.0, 1.0)
        harmful = bool((not result.success) and no_memory_success)
        helpful = bool(result.success)
        outcome: UtilityOutcome = "helpful" if helpful else "harmful" if harmful else "neutral"

        old_used = utility_before.num_used
        new_used = old_used + 1
        new_helpful = utility_before.num_helpful + (1 if helpful else 0)
        new_harmful = utility_before.num_harmful + (1 if harmful else 0)
        mean_delta_reward = (
            (utility_before.mean_delta_reward * old_used + delta_reward) / new_used
            if new_used
            else 0.0
        )
        lcb_delta_reward = _clamp(
            mean_delta_reward - (1.0 / math.sqrt(new_used)),
            -1.0,
            1.0,
        )
        utility_after = MemoryUtility(
            alpha=round(utility_before.alpha + observed_reward, 6),
            beta=round(utility_before.beta + (1.0 - observed_reward), 6),
            mean_delta_reward=round(mean_delta_reward, 6),
            lcb_delta_reward=round(lcb_delta_reward, 6),
            num_used=new_used,
            num_helpful=new_helpful,
            num_harmful=new_harmful,
        )

        positive_evidence = tuple(
            dict.fromkeys(memory.positive_evidence + ((run_id,) if helpful else ()))
        )
        negative_evidence = tuple(
            dict.fromkeys(memory.negative_evidence + ((run_id,) if harmful else ()))
        )
        status = self._next_status(
            current_status=memory.lifecycle.status,
            num_helpful=new_helpful,
            num_harmful=new_harmful,
            negative_evidence=negative_evidence,
            promote_after_helpful=promote_after_helpful,
            quarantine_after_harmful=quarantine_after_harmful,
        )
        lifecycle_after = replace(
            memory.lifecycle,
            status=status,
            last_used_iter=iteration,
        )
        updated = replace(
            memory,
            positive_evidence=positive_evidence,
            negative_evidence=negative_evidence,
            utility=utility_after,
            lifecycle=lifecycle_after,
        )
        updated.validate()
        self.memories[index] = updated
        self._write_all()
        return UtilityUpdate(
            memory=updated,
            outcome=outcome,
            baseline_reward=round(baseline_reward, 6),
            delta_reward=round(delta_reward, 6),
            utility_before=utility_before,
            utility_after=utility_after,
            lifecycle_before=lifecycle_before,
            lifecycle_after=lifecycle_after,
        )

    def all(self) -> list[CandidateMemory]:
        return list(self.memories)

    def _find(self, memory_id: str) -> tuple[int, CandidateMemory]:
        for index, memory in enumerate(self.memories):
            if memory.memory_id == memory_id:
                return index, memory
        raise KeyError(f"Candidate memory not found: {memory_id}")

    def _write_all(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            for memory in self.memories:
                handle.write(json.dumps(memory.to_json(), ensure_ascii=False) + "\n")

    def _next_status(
        self,
        current_status: str,
        num_helpful: int,
        num_harmful: int,
        negative_evidence: tuple[str, ...],
        promote_after_helpful: int,
        quarantine_after_harmful: int,
    ) -> str:
        if current_status == "retired":
            return "retired"
        if num_harmful >= quarantine_after_harmful or negative_evidence:
            return "quarantined"
        if (
            current_status == "candidate"
            and num_helpful >= promote_after_helpful
            and num_harmful == 0
        ):
            return "active"
        return current_status


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))
