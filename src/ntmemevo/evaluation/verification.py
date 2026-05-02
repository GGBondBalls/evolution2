from __future__ import annotations

import math
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from ntmemevo.agents.react_agent import ReActToolAgent
from ntmemevo.envs.base import AgentEnv
from ntmemevo.evaluation.replay import (
    NullTraceLogger,
    ReplayResult,
    _build_comparison_result,
    _execution_id,
)
from ntmemevo.memory.retriever import tokenize
from ntmemevo.memory.schema import CandidateMemory
from ntmemevo.types import RetrievedMemory, Task


@dataclass(frozen=True)
class VerificationConfig:
    enabled: bool = False
    support_split_file: Path | None = None
    max_support_tasks: int = 2
    min_support_tasks: int = 2
    min_support_similarity: float = 0.0
    require_intent_match: bool = True
    require_domain_match: bool = False
    min_helpful_before_verify: int = 2
    disable_immediate_promotion: bool = True
    delta_threshold: float = 0.0
    min_delta_mean: float = 0.0
    min_lcb_delta_reward: float = 0.0
    max_negative_transfer_rate: float = 0.0
    quarantine_on_negative_transfer: bool = True
    retire_on_verification_failure: bool = False
    prompt_token_cost_weight: float = 0.0
    tool_call_cost_weight: float = 0.0
    log_support_selection: bool = True
    max_verifications_per_run: int | None = None
    max_support_replay_records_per_run: int | None = None
    enable_scope_refinement: bool = False
    min_refinement_helpful: int = 1
    refined_memory_status: str = "candidate"
    quarantine_parent_on_refinement: bool = True

    @classmethod
    def from_config(cls, data: dict[str, Any] | None) -> "VerificationConfig":
        data = data or {}
        budget = data.get("budget", {}) or {}
        refinement = data.get("refinement", {}) or {}
        support_split_file = data.get("support_split_file")
        return cls(
            enabled=bool(data.get("enabled", False)),
            support_split_file=(
                Path(str(support_split_file)) if support_split_file is not None else None
            ),
            max_support_tasks=int(data.get("max_support_tasks", 2)),
            min_support_tasks=int(data.get("min_support_tasks", 2)),
            min_support_similarity=float(data.get("min_support_similarity", 0.0)),
            require_intent_match=bool(data.get("require_intent_match", True)),
            require_domain_match=bool(data.get("require_domain_match", False)),
            min_helpful_before_verify=int(data.get("min_helpful_before_verify", 2)),
            disable_immediate_promotion=bool(data.get("disable_immediate_promotion", True)),
            delta_threshold=float(data.get("delta_threshold", 0.0)),
            min_delta_mean=float(data.get("min_delta_mean", 0.0)),
            min_lcb_delta_reward=float(data.get("min_lcb_delta_reward", 0.0)),
            max_negative_transfer_rate=float(data.get("max_negative_transfer_rate", 0.0)),
            quarantine_on_negative_transfer=bool(
                data.get("quarantine_on_negative_transfer", True)
            ),
            retire_on_verification_failure=bool(
                data.get("retire_on_verification_failure", False)
            ),
            prompt_token_cost_weight=float(data.get("prompt_token_cost_weight", 0.0)),
            tool_call_cost_weight=float(data.get("tool_call_cost_weight", 0.0)),
            log_support_selection=bool(data.get("log_support_selection", True)),
            max_verifications_per_run=_optional_int(
                data.get(
                    "max_verifications_per_run",
                    budget.get("max_verifications_per_run"),
                )
            ),
            max_support_replay_records_per_run=_optional_int(
                data.get(
                    "max_support_replay_records_per_run",
                    budget.get("max_support_replay_records_per_run"),
                )
            ),
            enable_scope_refinement=bool(
                data.get("enable_scope_refinement", refinement.get("enabled", False))
            ),
            min_refinement_helpful=int(
                data.get("min_refinement_helpful", refinement.get("min_helpful", 1))
            ),
            refined_memory_status=str(
                data.get(
                    "refined_memory_status",
                    refinement.get("refined_status", "candidate"),
                )
            ),
            quarantine_parent_on_refinement=bool(
                data.get(
                    "quarantine_parent_on_refinement",
                    refinement.get("quarantine_parent", True),
                )
            ),
        )


@dataclass(frozen=True)
class SupportTaskMatch:
    task: Task
    intent_score: float
    domain_score: float
    tool_score: float
    lexical_score: float
    final_score: float

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["task_id"] = self.task.task_id
        data["task_intent"] = _task_intent(self.task)
        data["task_domain"] = str(self.task.metadata.get("domain", ""))
        data["task_tool_names"] = [
            str(item) for item in self.task.metadata.get("tool_names", ())
        ]
        data["support_match_score"] = self.final_score
        data.pop("task", None)
        return data


@dataclass(frozen=True)
class VerificationResult:
    verification_id: str
    source_run_id: str
    memory_id: str
    support_task_ids: tuple[str, ...]
    support_delta_mean: float
    support_lcb_delta_reward: float
    support_negative_transfer_rate: float
    support_replay_count: int
    support_replay_helpful_count: int
    support_replay_harmful_count: int
    support_replay_neutral_count: int
    verification_passed: bool
    failure_reason: str | None
    replay_ids: tuple[str, ...]
    positive_evidence_ids: tuple[str, ...]
    negative_evidence_ids: tuple[str, ...]
    support_match_details: tuple[dict[str, Any], ...] = ()

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["support_task_ids"] = list(self.support_task_ids)
        data["replay_ids"] = list(self.replay_ids)
        data["positive_evidence_ids"] = list(self.positive_evidence_ids)
        data["negative_evidence_ids"] = list(self.negative_evidence_ids)
        data["support_match_details"] = list(self.support_match_details)
        return data


class SupportTaskSelector:
    def __init__(
        self,
        tasks: list[Task],
        config: VerificationConfig,
    ) -> None:
        self.tasks = list(tasks)
        self.config = config

    def select(self, memory: CandidateMemory) -> list[SupportTaskMatch]:
        matches = [self._score(memory=memory, task=task) for task in self.tasks]
        filtered = [
            match
            for match in matches
            if match.final_score >= self.config.min_support_similarity
        ]
        filtered.sort(
            key=lambda match: (
                -match.final_score,
                match.task.task_id,
            )
        )
        return filtered[: self.config.max_support_tasks]

    def _score(self, memory: CandidateMemory, task: Task) -> SupportTaskMatch:
        task_intent = _task_intent(task)
        if task_intent == memory.scope.intent:
            intent_score = 1.0
        elif self.config.require_intent_match:
            intent_score = 0.0
        else:
            intent_score = _token_overlap_score(
                task_intent.replace("_", " "),
                memory.scope.intent.replace("_", " "),
            )

        task_domain = str(task.metadata.get("domain", memory.scope.domain))
        domain_score = 1.0 if task_domain == memory.scope.domain else 0.0
        if self.config.require_domain_match and domain_score == 0.0:
            final_score = 0.0
        elif self.config.require_intent_match and intent_score == 0.0:
            final_score = 0.0
        else:
            task_tools = tuple(str(item) for item in task.metadata.get("tool_names", ()))
            tool_score = _tool_overlap_score(memory.scope.tool_names, task_tools)
            lexical_score = _cosine_similarity(memory.text, task.instruction)
            final_score = _clamp(
                0.55 * intent_score
                + 0.15 * domain_score
                + 0.20 * tool_score
                + 0.10 * lexical_score
            )
            return SupportTaskMatch(
                task=task,
                intent_score=round(intent_score, 6),
                domain_score=round(domain_score, 6),
                tool_score=round(tool_score, 6),
                lexical_score=round(lexical_score, 6),
                final_score=round(final_score, 6),
            )

        return SupportTaskMatch(
            task=task,
            intent_score=round(intent_score, 6),
            domain_score=round(domain_score, 6),
            tool_score=0.0,
            lexical_score=0.0,
            final_score=round(final_score, 6),
        )


class MemoryVerifier:
    def __init__(
        self,
        agent: ReActToolAgent,
        env_factory: Callable[[], AgentEnv],
        support_tasks: list[Task],
        config: VerificationConfig,
    ) -> None:
        self.agent = agent
        self.env_factory = env_factory
        self.support_tasks = list(support_tasks)
        self.config = config

    def verify(
        self,
        memory: CandidateMemory,
        source_run_id: str,
    ) -> tuple[VerificationResult, list[ReplayResult]]:
        matches = SupportTaskSelector(self.support_tasks, self.config).select(memory)
        selected_tasks = [match.task for match in matches]
        replay_results: list[ReplayResult] = []
        retrieved_memory = _candidate_to_retrieved_memory(memory)
        verification_id = f"{source_run_id}_verify_{memory.memory_id}"

        for index, task in enumerate(selected_tasks, start=1):
            with_execution_id = _execution_id(
                source_run_id=source_run_id,
                task_id=task.task_id,
                replay_scope="support_task_replay",
                memory_ids=(memory.memory_id,),
            )
            without_execution_id = _execution_id(
                source_run_id=source_run_id,
                task_id=task.task_id,
                replay_scope="support_task_replay",
                memory_ids=(),
            )
            with_result = self.agent.run(
                task=task,
                env=self.env_factory(),
                trace_logger=NullTraceLogger(),  # type: ignore[arg-type]
                memories=[retrieved_memory],
            )
            without_result = self.agent.run(
                task=task,
                env=self.env_factory(),
                trace_logger=NullTraceLogger(),  # type: ignore[arg-type]
                memories=[],
            )
            replay_results.append(
                _build_comparison_result(
                    replay_id=f"{verification_id}_support_{index:03d}",
                    source_run_id=source_run_id,
                    task=task,
                    memory_id=memory.memory_id,
                    mode="support_task_replay",
                    with_result=with_result,
                    without_result=without_result,
                    threshold=self.config.delta_threshold,
                    replay_scope="support_task_replay",
                    prompt_token_cost_weight=self.config.prompt_token_cost_weight,
                    tool_call_cost_weight=self.config.tool_call_cost_weight,
                    with_execution_id=with_execution_id,
                    without_execution_id=without_execution_id,
                )
            )

        verification_result = self._summarize(
            verification_id=verification_id,
            source_run_id=source_run_id,
            memory_id=memory.memory_id,
            replay_results=replay_results,
            support_matches=matches,
        )
        return verification_result, replay_results

    def _summarize(
        self,
        verification_id: str,
        source_run_id: str,
        memory_id: str,
        replay_results: list[ReplayResult],
        support_matches: list[SupportTaskMatch],
    ) -> VerificationResult:
        support_task_ids = tuple(result.task_id for result in replay_results)
        deltas = [
            float(result.delta_reward)
            for result in replay_results
            if result.delta_reward is not None
        ]
        mean_delta = sum(deltas) / len(deltas) if deltas else 0.0
        lcb_delta = _lcb(mean_delta=mean_delta, n=len(deltas))
        label_counts = Counter(result.attribution_label for result in replay_results)
        harmful_count = label_counts.get("harmful", 0)
        negative_transfer_rate = harmful_count / len(replay_results) if replay_results else 0.0
        failure_reason = self._failure_reason(
            support_replay_count=len(replay_results),
            mean_delta=mean_delta,
            lcb_delta=lcb_delta,
            negative_transfer_rate=negative_transfer_rate,
        )
        positive_evidence_ids = tuple(
            result.replay_id
            for result in replay_results
            if result.attribution_label == "helpful"
        )
        negative_evidence_ids = tuple(
            result.replay_id
            for result in replay_results
            if result.attribution_label == "harmful"
        )
        return VerificationResult(
            verification_id=verification_id,
            source_run_id=source_run_id,
            memory_id=memory_id,
            support_task_ids=support_task_ids,
            support_delta_mean=round(mean_delta, 6),
            support_lcb_delta_reward=round(lcb_delta, 6),
            support_negative_transfer_rate=round(negative_transfer_rate, 6),
            support_replay_count=len(replay_results),
            support_replay_helpful_count=label_counts.get("helpful", 0),
            support_replay_harmful_count=harmful_count,
            support_replay_neutral_count=label_counts.get("neutral", 0),
            verification_passed=failure_reason is None,
            failure_reason=failure_reason,
            replay_ids=tuple(result.replay_id for result in replay_results),
            positive_evidence_ids=positive_evidence_ids,
            negative_evidence_ids=negative_evidence_ids,
            support_match_details=_support_match_details(
                support_matches=support_matches,
                replay_results=replay_results,
            ),
        )

    def _failure_reason(
        self,
        support_replay_count: int,
        mean_delta: float,
        lcb_delta: float,
        negative_transfer_rate: float,
    ) -> str | None:
        if support_replay_count < self.config.min_support_tasks:
            return "insufficient_support_tasks"
        if negative_transfer_rate > self.config.max_negative_transfer_rate:
            return "support_negative_transfer_rate_above_threshold"
        if mean_delta <= self.config.min_delta_mean:
            return "support_delta_mean_below_threshold"
        if lcb_delta <= self.config.min_lcb_delta_reward:
            return "support_lcb_delta_reward_below_threshold"
        return None


def _candidate_to_retrieved_memory(memory: CandidateMemory) -> RetrievedMemory:
    return RetrievedMemory(
        memory_id=memory.memory_id,
        text=memory.text,
        score=1.0,
        metadata={
            "memory_kind": memory.__class__.__name__,
            "candidate_type": memory.type,
            "lifecycle_status": memory.lifecycle.status,
            "verification_replay": True,
        },
    )


def _task_intent(task: Task) -> str:
    metadata_intent = task.metadata.get("intent") or task.metadata.get("support_intent")
    if metadata_intent:
        return str(metadata_intent)
    text = task.instruction.lower()
    if "exchange" in text:
        return "exchange_eligibility"
    if "refund" in text:
        return "refund_eligibility"
    if "inventory" in text or "in stock" in text or "sku-" in text:
        return "inventory_check"
    if "policy" in text or "return window" in text:
        return "policy_lookup"
    if "order" in text or "delivery status" in text:
        return "order_status"
    return "general_tool_use"


def _tool_overlap_score(memory_tools: tuple[str, ...], task_tools: tuple[str, ...]) -> float:
    if not memory_tools or not task_tools:
        return 0.0
    memory_set = set(memory_tools)
    task_set = set(task_tools)
    return len(memory_set & task_set) / len(memory_set)


def _cosine_similarity(left: str, right: str) -> float:
    left_terms = Counter(tokenize(left))
    right_terms = Counter(tokenize(right))
    if not left_terms or not right_terms:
        return 0.0
    overlap = set(left_terms) & set(right_terms)
    if not overlap:
        return 0.0
    dot = sum(left_terms[token] * right_terms[token] for token in overlap)
    left_norm = math.sqrt(sum(value * value for value in left_terms.values()))
    right_norm = math.sqrt(sum(value * value for value in right_terms.values()))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _token_overlap_score(left: str, right: str) -> float:
    left_tokens = set(tokenize(left))
    right_tokens = set(tokenize(right))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens)


def _lcb(mean_delta: float, n: int) -> float:
    if n <= 0:
        return 0.0
    return _clamp(mean_delta - (1.0 / math.sqrt(n)), -1.0, 1.0)


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _support_match_details(
    support_matches: list[SupportTaskMatch],
    replay_results: list[ReplayResult],
) -> tuple[dict[str, Any], ...]:
    result_by_task_id = {result.task_id: result for result in replay_results}
    details: list[dict[str, Any]] = []
    for rank, match in enumerate(support_matches[: len(replay_results)], start=1):
        record = match.to_json()
        result = result_by_task_id.get(match.task.task_id)
        record["selected_rank"] = rank
        if result is not None:
            record.update(
                {
                    "replay_id": result.replay_id,
                    "attribution_label": result.attribution_label,
                    "delta_reward": result.delta_reward,
                    "cost_adjusted_delta_reward": result.cost_adjusted_delta_reward,
                    "with_success": result.with_success,
                    "without_success": result.without_success,
                }
            )
        details.append(record)
    return tuple(details)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)
