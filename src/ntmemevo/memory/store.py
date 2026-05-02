from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

from ntmemevo.memory.extractor import CandidateExtractionContext, CandidateMemoryExtractor
from ntmemevo.memory.schema import (
    CandidateMemory,
    MemoryLifecycle,
    MemoryScope,
    MemorySource,
    MemoryUtility,
    canonical_json_hash_payload,
)
from ntmemevo.types import AgentResult, Task


UtilityOutcome = Literal["helpful", "harmful", "neutral"]
UtilityCreditSource = Literal["online_proxy", "leave_one_memory_out"]


@dataclass(frozen=True)
class UtilityUpdate:
    memory: CandidateMemory
    outcome: UtilityOutcome
    credit_source: UtilityCreditSource
    baseline_reward: float
    delta_reward: float
    utility_before: MemoryUtility
    utility_after: MemoryUtility
    lifecycle_before: MemoryLifecycle
    lifecycle_after: MemoryLifecycle
    replay_id: str | None = None
    source_run_id: str | None = None

    def to_json(self) -> dict[str, object]:
        return {
            "memory_id": self.memory.memory_id,
            "outcome": self.outcome,
            "credit_source": self.credit_source,
            "baseline_reward": self.baseline_reward,
            "delta_reward": self.delta_reward,
            "utility_before": self.utility_before.to_json(),
            "utility_after": self.utility_after.to_json(),
            "lifecycle_before": self.lifecycle_before.to_json(),
            "lifecycle_after": self.lifecycle_after.to_json(),
            "positive_evidence": list(self.memory.positive_evidence),
            "negative_evidence": list(self.memory.negative_evidence),
            "replay_id": self.replay_id,
            "source_run_id": self.source_run_id,
        }


@dataclass(frozen=True)
class VerificationUpdate:
    memory: CandidateMemory
    verification_id: str
    source_run_id: str
    verification_passed: bool
    failure_reason: str | None
    support_task_ids: tuple[str, ...]
    support_delta_mean: float
    support_lcb_delta_reward: float
    support_negative_transfer_rate: float
    support_replay_count: int
    support_replay_helpful_count: int
    support_replay_harmful_count: int
    support_replay_neutral_count: int
    utility_before: MemoryUtility
    utility_after: MemoryUtility
    lifecycle_before: MemoryLifecycle
    lifecycle_after: MemoryLifecycle

    def to_json(self) -> dict[str, object]:
        return {
            "memory_id": self.memory.memory_id,
            "verification_id": self.verification_id,
            "source_run_id": self.source_run_id,
            "verification_passed": self.verification_passed,
            "failure_reason": self.failure_reason,
            "support_task_ids": list(self.support_task_ids),
            "support_delta_mean": self.support_delta_mean,
            "support_lcb_delta_reward": self.support_lcb_delta_reward,
            "support_negative_transfer_rate": self.support_negative_transfer_rate,
            "support_replay_count": self.support_replay_count,
            "support_replay_helpful_count": self.support_replay_helpful_count,
            "support_replay_harmful_count": self.support_replay_harmful_count,
            "support_replay_neutral_count": self.support_replay_neutral_count,
            "utility_before": self.utility_before.to_json(),
            "utility_after": self.utility_after.to_json(),
            "lifecycle_before": self.lifecycle_before.to_json(),
            "lifecycle_after": self.lifecycle_after.to_json(),
            "positive_evidence": list(self.memory.positive_evidence),
            "negative_evidence": list(self.memory.negative_evidence),
        }


@dataclass(frozen=True)
class ScopeRefinementUpdate:
    parent_memory: CandidateMemory
    child_memory: CandidateMemory
    verification_id: str
    source_run_id: str
    trigger_reason: str
    parent_scope_before: MemoryScope
    child_scope: MemoryScope
    parent_lifecycle_before: MemoryLifecycle
    parent_lifecycle_after: MemoryLifecycle
    helpful_support_task_ids: tuple[str, ...]
    harmful_support_task_ids: tuple[str, ...]
    neutral_support_task_ids: tuple[str, ...]
    support_match_details: tuple[dict[str, Any], ...]

    def to_json(self) -> dict[str, object]:
        return {
            "parent_memory_id": self.parent_memory.memory_id,
            "child_memory_id": self.child_memory.memory_id,
            "verification_id": self.verification_id,
            "source_run_id": self.source_run_id,
            "trigger_reason": self.trigger_reason,
            "parent_scope_before": self.parent_scope_before.to_json(),
            "child_scope": self.child_scope.to_json(),
            "parent_lifecycle_before": self.parent_lifecycle_before.to_json(),
            "parent_lifecycle_after": self.parent_lifecycle_after.to_json(),
            "child_lifecycle": self.child_memory.lifecycle.to_json(),
            "child_utility": self.child_memory.utility.to_json(),
            "helpful_support_task_ids": list(self.helpful_support_task_ids),
            "harmful_support_task_ids": list(self.harmful_support_task_ids),
            "neutral_support_task_ids": list(self.neutral_support_task_ids),
            "positive_evidence": list(self.child_memory.positive_evidence),
            "negative_evidence": list(self.child_memory.negative_evidence),
            "support_match_details": list(self.support_match_details),
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
        allow_promotion: bool = True,
    ) -> UtilityUpdate:
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
        return self._apply_utility_update(
            memory_id=memory_id,
            run_id=run_id,
            iteration=iteration,
            observed_reward=observed_reward,
            baseline_reward=baseline_reward,
            delta_reward=delta_reward,
            outcome=outcome,
            credit_source="online_proxy",
            promote_after_helpful=promote_after_helpful,
            quarantine_after_harmful=quarantine_after_harmful,
            promote_requires_positive_lcb=False,
            allow_promotion=allow_promotion,
        )

    def update_utility_from_replay(
        self,
        memory_id: str,
        source_run_id: str,
        replay_id: str,
        iteration: int,
        with_reward: float,
        without_reward: float,
        delta_reward: float,
        attribution_label: str,
        promote_after_helpful: int = 2,
        quarantine_after_harmful: int = 1,
        promote_requires_positive_lcb: bool = True,
        allow_promotion: bool = True,
    ) -> UtilityUpdate:
        outcome: UtilityOutcome
        if attribution_label == "helpful":
            outcome = "helpful"
        elif attribution_label == "harmful":
            outcome = "harmful"
        else:
            outcome = "neutral"
        return self._apply_utility_update(
            memory_id=memory_id,
            run_id=source_run_id,
            iteration=iteration,
            observed_reward=_clamp(float(with_reward), 0.0, 1.0),
            baseline_reward=_clamp(float(without_reward), 0.0, 1.0),
            delta_reward=_clamp(float(delta_reward), -1.0, 1.0),
            outcome=outcome,
            credit_source="leave_one_memory_out",
            promote_after_helpful=promote_after_helpful,
            quarantine_after_harmful=quarantine_after_harmful,
            promote_requires_positive_lcb=promote_requires_positive_lcb,
            allow_promotion=allow_promotion,
            replay_id=replay_id,
            source_run_id=source_run_id,
        )

    def _apply_utility_update(
        self,
        memory_id: str,
        run_id: str,
        iteration: int,
        observed_reward: float,
        baseline_reward: float,
        delta_reward: float,
        outcome: UtilityOutcome,
        credit_source: UtilityCreditSource,
        promote_after_helpful: int,
        quarantine_after_harmful: int,
        promote_requires_positive_lcb: bool,
        allow_promotion: bool,
        replay_id: str | None = None,
        source_run_id: str | None = None,
    ) -> UtilityUpdate:
        index, memory = self._find(memory_id)
        utility_before = memory.utility
        lifecycle_before = memory.lifecycle

        old_used = utility_before.num_used
        new_used = old_used + 1
        new_helpful = utility_before.num_helpful + (1 if outcome == "helpful" else 0)
        new_harmful = utility_before.num_harmful + (1 if outcome == "harmful" else 0)
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
        if credit_source == "online_proxy":
            alpha_increment = observed_reward
            beta_increment = 1.0 - observed_reward
        else:
            alpha_increment = 1.0 if outcome == "helpful" else 0.0
            beta_increment = 1.0 if outcome == "harmful" else 0.0
        utility_after = MemoryUtility(
            alpha=round(utility_before.alpha + alpha_increment, 6),
            beta=round(utility_before.beta + beta_increment, 6),
            mean_delta_reward=round(mean_delta_reward, 6),
            lcb_delta_reward=round(lcb_delta_reward, 6),
            num_used=new_used,
            num_helpful=new_helpful,
            num_harmful=new_harmful,
        )

        positive_evidence = tuple(
            dict.fromkeys(
                memory.positive_evidence + ((run_id,) if outcome == "helpful" else ())
            )
        )
        negative_evidence = tuple(
            dict.fromkeys(
                memory.negative_evidence + ((run_id,) if outcome == "harmful" else ())
            )
        )
        status = self._next_status(
            current_status=memory.lifecycle.status,
            num_helpful=new_helpful,
            num_harmful=new_harmful,
            negative_evidence=negative_evidence,
            lcb_delta_reward=utility_after.lcb_delta_reward,
            promote_after_helpful=promote_after_helpful,
            quarantine_after_harmful=quarantine_after_harmful,
            promote_requires_positive_lcb=promote_requires_positive_lcb,
            allow_promotion=allow_promotion,
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
            credit_source=credit_source,
            baseline_reward=round(baseline_reward, 6),
            delta_reward=round(delta_reward, 6),
            utility_before=utility_before,
            utility_after=utility_after,
            lifecycle_before=lifecycle_before,
            lifecycle_after=lifecycle_after,
            replay_id=replay_id,
            source_run_id=source_run_id,
        )

    def apply_verification_result(
        self,
        memory_id: str,
        verification_id: str,
        source_run_id: str,
        support_task_ids: tuple[str, ...],
        support_delta_mean: float,
        support_lcb_delta_reward: float,
        support_negative_transfer_rate: float,
        support_replay_count: int,
        support_replay_helpful_count: int,
        support_replay_harmful_count: int,
        support_replay_neutral_count: int,
        verification_passed: bool,
        failure_reason: str | None,
        positive_evidence_ids: tuple[str, ...] = (),
        negative_evidence_ids: tuple[str, ...] = (),
        quarantine_on_negative_transfer: bool = True,
        retire_on_verification_failure: bool = False,
    ) -> VerificationUpdate:
        index, memory = self._find(memory_id)
        utility_before = memory.utility
        lifecycle_before = memory.lifecycle
        utility_after = replace(
            memory.utility,
            mean_delta_reward=round(float(support_delta_mean), 6),
            lcb_delta_reward=round(float(support_lcb_delta_reward), 6),
        )
        positive_evidence = tuple(
            dict.fromkeys(memory.positive_evidence + positive_evidence_ids)
        )
        negative_evidence = tuple(
            dict.fromkeys(memory.negative_evidence + negative_evidence_ids)
        )
        status = self._verification_status(
            current_status=memory.lifecycle.status,
            verification_passed=verification_passed,
            support_negative_transfer_rate=support_negative_transfer_rate,
            quarantine_on_negative_transfer=quarantine_on_negative_transfer,
            retire_on_verification_failure=retire_on_verification_failure,
        )
        lifecycle_after = replace(memory.lifecycle, status=status)
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
        return VerificationUpdate(
            memory=updated,
            verification_id=verification_id,
            source_run_id=source_run_id,
            verification_passed=verification_passed,
            failure_reason=failure_reason,
            support_task_ids=support_task_ids,
            support_delta_mean=round(float(support_delta_mean), 6),
            support_lcb_delta_reward=round(float(support_lcb_delta_reward), 6),
            support_negative_transfer_rate=round(float(support_negative_transfer_rate), 6),
            support_replay_count=support_replay_count,
            support_replay_helpful_count=support_replay_helpful_count,
            support_replay_harmful_count=support_replay_harmful_count,
            support_replay_neutral_count=support_replay_neutral_count,
            utility_before=utility_before,
            utility_after=utility_after,
            lifecycle_before=lifecycle_before,
            lifecycle_after=lifecycle_after,
        )

    def refine_scope_from_verification(
        self,
        memory_id: str,
        verification_id: str,
        source_run_id: str,
        iteration: int,
        support_match_details: tuple[dict[str, Any], ...],
        min_helpful: int = 1,
        refined_status: str = "candidate",
        quarantine_parent: bool = True,
    ) -> ScopeRefinementUpdate | None:
        helpful_details = _support_details_by_label(support_match_details, "helpful")
        harmful_details = _support_details_by_label(support_match_details, "harmful")
        neutral_details = _support_details_by_label(support_match_details, "neutral")
        if len(helpful_details) < min_helpful:
            return None
        if not harmful_details and not neutral_details:
            return None

        index, parent = self._find(memory_id)
        parent_scope_before = parent.scope
        parent_lifecycle_before = parent.lifecycle
        parent_lifecycle_after = (
            replace(parent.lifecycle, status="quarantined")
            if quarantine_parent and parent.lifecycle.status != "retired"
            else parent.lifecycle
        )
        parent_after = replace(parent, lifecycle=parent_lifecycle_after)

        refined_intent = _most_common_value(helpful_details, "task_intent", parent.scope.intent)
        refined_tools = _most_common_tools(helpful_details) or parent.scope.tool_names
        helpful_task_ids = _task_ids(helpful_details)
        harmful_task_ids = _task_ids(harmful_details)
        neutral_task_ids = _task_ids(neutral_details)
        positive_evidence = tuple(
            dict.fromkeys(
                str(detail["replay_id"])
                for detail in helpful_details
                if detail.get("replay_id")
            )
        )
        if not positive_evidence:
            positive_evidence = parent.positive_evidence

        child_id = self._next_refined_memory_id(parent.memory_id)
        child_scope = MemoryScope(
            benchmark=parent.scope.benchmark,
            domain=parent.scope.domain,
            intent=refined_intent,
            tool_names=refined_tools,
            preconditions=_refined_preconditions(
                parent=parent,
                refined_intent=refined_intent,
                verification_id=verification_id,
                helpful_task_ids=helpful_task_ids,
            ),
        )
        delta_values = [
            float(detail.get("delta_reward", 0.0) or 0.0)
            for detail in helpful_details
        ]
        mean_delta = sum(delta_values) / len(delta_values) if delta_values else 0.0
        lcb_delta = _clamp(mean_delta - (1.0 / math.sqrt(len(delta_values))), -1.0, 1.0)
        child_utility = MemoryUtility(
            alpha=round(1.0 + len(helpful_details), 6),
            beta=1.0,
            mean_delta_reward=round(mean_delta, 6),
            lcb_delta_reward=round(lcb_delta, 6),
            num_used=len(helpful_details),
            num_helpful=len(helpful_details),
            num_harmful=0,
        )
        source_payload = {
            "parent_memory_id": parent.memory_id,
            "child_memory_id": child_id,
            "verification_id": verification_id,
            "source_run_id": source_run_id,
            "support_match_details": list(support_match_details),
        }
        child = CandidateMemory(
            memory_id=child_id,
            type=parent.type,
            claim=(
                f"{parent.claim} Refined scope: apply only when the current task "
                f"matches {refined_intent} support evidence."
            ),
            scope=child_scope,
            action_hint=parent.action_hint,
            avoid_hint=(
                f"{parent.avoid_hint} Do not apply the parent memory outside this "
                "refined support-verified scope without another verification pass."
            ),
            positive_evidence=positive_evidence,
            negative_evidence=(),
            utility=child_utility,
            lifecycle=MemoryLifecycle(
                status=refined_status,
                created_iter=iteration,
                last_used_iter=None,
                ttl=parent.lifecycle.ttl,
            ),
            source=MemorySource(
                created_from=tuple(
                    dict.fromkeys(parent.source.created_from + (verification_id,))
                ),
                extractor_model=f"{parent.source.extractor_model}+scope_refiner_v1",
                prompt_hash=hashlib.sha256(
                    canonical_json_hash_payload(source_payload).encode("utf-8")
                ).hexdigest(),
            ),
        )
        parent_after.validate()
        child.validate()
        self.memories[index] = parent_after
        self.memories.append(child)
        self._write_all()
        trigger_reason = (
            "mixed_support_harmful"
            if harmful_details
            else "mixed_support_neutral"
        )
        return ScopeRefinementUpdate(
            parent_memory=parent_after,
            child_memory=child,
            verification_id=verification_id,
            source_run_id=source_run_id,
            trigger_reason=trigger_reason,
            parent_scope_before=parent_scope_before,
            child_scope=child_scope,
            parent_lifecycle_before=parent_lifecycle_before,
            parent_lifecycle_after=parent_lifecycle_after,
            helpful_support_task_ids=helpful_task_ids,
            harmful_support_task_ids=harmful_task_ids,
            neutral_support_task_ids=neutral_task_ids,
            support_match_details=support_match_details,
        )

    def all(self) -> list[CandidateMemory]:
        return list(self.memories)

    def get(self, memory_id: str) -> CandidateMemory:
        return self._find(memory_id)[1]

    def _find(self, memory_id: str) -> tuple[int, CandidateMemory]:
        for index, memory in enumerate(self.memories):
            if memory.memory_id == memory_id:
                return index, memory
        raise KeyError(f"Candidate memory not found: {memory_id}")

    def _next_refined_memory_id(self, parent_memory_id: str) -> str:
        prefix = f"{parent_memory_id}__refined_"
        existing = [
            memory.memory_id
            for memory in self.memories
            if memory.memory_id.startswith(prefix)
        ]
        return f"{prefix}{len(existing) + 1:03d}"

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
        lcb_delta_reward: float,
        promote_after_helpful: int,
        quarantine_after_harmful: int,
        promote_requires_positive_lcb: bool,
        allow_promotion: bool,
    ) -> str:
        if current_status == "retired":
            return "retired"
        if num_harmful >= quarantine_after_harmful or negative_evidence:
            return "quarantined"
        if (
            allow_promotion
            and current_status == "candidate"
            and num_helpful >= promote_after_helpful
            and num_harmful == 0
            and (not promote_requires_positive_lcb or lcb_delta_reward > 0.0)
        ):
            return "active"
        return current_status

    def _verification_status(
        self,
        current_status: str,
        verification_passed: bool,
        support_negative_transfer_rate: float,
        quarantine_on_negative_transfer: bool,
        retire_on_verification_failure: bool,
    ) -> str:
        if current_status == "retired":
            return "retired"
        if verification_passed:
            return "active"
        if quarantine_on_negative_transfer and support_negative_transfer_rate > 0.0:
            return "quarantined"
        if retire_on_verification_failure:
            return "retired"
        return current_status


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _support_details_by_label(
    support_match_details: tuple[dict[str, Any], ...],
    label: str,
) -> list[dict[str, Any]]:
    return [
        detail
        for detail in support_match_details
        if detail.get("attribution_label") == label
    ]


def _task_ids(details: list[dict[str, Any]]) -> tuple[str, ...]:
    return tuple(str(detail["task_id"]) for detail in details if detail.get("task_id"))


def _most_common_value(
    details: list[dict[str, Any]],
    key: str,
    fallback: str,
) -> str:
    values = [str(detail.get(key, "")) for detail in details if detail.get(key)]
    if not values:
        return fallback
    return Counter(values).most_common(1)[0][0]


def _most_common_tools(details: list[dict[str, Any]]) -> tuple[str, ...]:
    tool_counts: Counter[str] = Counter()
    for detail in details:
        for tool_name in detail.get("task_tool_names", ()) or ():
            tool_counts[str(tool_name)] += 1
    return tuple(tool for tool, _ in tool_counts.most_common())


def _refined_preconditions(
    parent: CandidateMemory,
    refined_intent: str,
    verification_id: str,
    helpful_task_ids: tuple[str, ...],
) -> tuple[str, ...]:
    retained = [
        item
        for item in parent.scope.preconditions
        if not item.startswith("instruction intent is ")
    ]
    return tuple(
        dict.fromkeys(
            (
                f"instruction intent is {refined_intent}",
                *retained,
                f"scope refined from parent memory {parent.memory_id}",
                f"verification id is {verification_id}",
                "helpful support task ids: " + ", ".join(helpful_task_ids),
            )
        )
    )
