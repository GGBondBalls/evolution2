from __future__ import annotations

import math
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any

from ntmemevo.llm.cost import estimate_tokens
from ntmemevo.memory.retriever import tokenize
from ntmemevo.memory.schema import CandidateMemory
from ntmemevo.types import RetrievedMemory, Task


@dataclass(frozen=True)
class RetrieverGateConfig:
    top_k: int = 2
    min_score: float = 0.30
    min_similarity: float = 0.02
    min_precondition: float = 0.25
    max_risk: float = 0.65
    max_memory_tokens: int = 220
    allowed_statuses: tuple[str, ...] = ("candidate", "active")
    reject_negative_evidence: bool = True
    weight_similarity: float = 1.0
    weight_precondition: float = 0.50
    weight_utility: float = 0.25
    weight_risk: float = 0.80
    weight_age: float = 0.10
    weight_cost: float = 0.05

    @classmethod
    def from_config(cls, data: dict[str, Any], top_k: int) -> "RetrieverGateConfig":
        gate = data.get("gate", {}) or {}
        allowed_statuses = gate.get("allowed_statuses", ("candidate", "active"))
        return cls(
            top_k=int(gate.get("top_k", top_k)),
            min_score=float(gate.get("min_score", 0.30)),
            min_similarity=float(gate.get("min_similarity", 0.02)),
            min_precondition=float(gate.get("min_precondition", 0.25)),
            max_risk=float(gate.get("max_risk", 0.65)),
            max_memory_tokens=int(gate.get("max_memory_tokens", 220)),
            allowed_statuses=tuple(str(item) for item in allowed_statuses),
            reject_negative_evidence=bool(gate.get("reject_negative_evidence", True)),
            weight_similarity=float(gate.get("weight_similarity", 1.0)),
            weight_precondition=float(gate.get("weight_precondition", 0.50)),
            weight_utility=float(gate.get("weight_utility", 0.25)),
            weight_risk=float(gate.get("weight_risk", 0.80)),
            weight_age=float(gate.get("weight_age", 0.10)),
            weight_cost=float(gate.get("weight_cost", 0.05)),
        )


@dataclass(frozen=True)
class GateDecision:
    task_id: str
    memory_id: str
    candidate_type: str
    lifecycle_status: str
    similarity_score: float
    precondition_score: float
    utility_score: float
    risk_score: float
    age_penalty: float
    cost_penalty: float
    final_gate_score: float
    gate_decision: str
    rejection_reason: str | None = None
    selected_rank: int | None = None

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


class RetrieverGate:
    def __init__(
        self,
        memories: list[CandidateMemory],
        config: RetrieverGateConfig | None = None,
    ) -> None:
        self.memories = list(memories)
        self.config = config or RetrieverGateConfig()

    def retrieve(
        self,
        task: Task,
        iteration: int,
        top_k: int | None = None,
    ) -> tuple[list[RetrievedMemory], list[GateDecision]]:
        limit = self.config.top_k if top_k is None else top_k
        if limit <= 0 or not self.memories:
            return [], []

        scored: list[tuple[GateDecision, CandidateMemory]] = [
            (self._score_memory(task=task, memory=memory, iteration=iteration), memory)
            for memory in self.memories
        ]
        preselected = [
            (decision, memory)
            for decision, memory in scored
            if decision.gate_decision == "accept"
        ]
        preselected.sort(
            key=lambda item: (
                -item[0].final_gate_score,
                item[1].lifecycle.created_iter,
                item[1].memory_id,
            )
        )
        selected_ids = {
            memory.memory_id: rank
            for rank, (_decision, memory) in enumerate(preselected[:limit], start=1)
        }

        final_decisions: list[GateDecision] = []
        selected: list[RetrievedMemory] = []
        for decision, memory in scored:
            rank = selected_ids.get(memory.memory_id)
            if decision.gate_decision == "accept" and rank is None:
                decision = GateDecision(
                    **{
                        **decision.to_json(),
                        "gate_decision": "reject",
                        "rejection_reason": "top_k_pruned",
                    }
                )
            elif rank is not None:
                decision = GateDecision(
                    **{
                        **decision.to_json(),
                        "selected_rank": rank,
                    }
                )
                selected.append(self._to_retrieved_memory(memory=memory, decision=decision))
            final_decisions.append(decision)

        selected.sort(key=lambda item: int(item.metadata.get("selected_rank", 0)))
        final_decisions.sort(
            key=lambda item: (
                item.selected_rank is None,
                item.selected_rank or 999_999,
                -item.final_gate_score,
                item.memory_id,
            )
        )
        return selected, final_decisions

    def _score_memory(
        self,
        task: Task,
        memory: CandidateMemory,
        iteration: int,
    ) -> GateDecision:
        similarity_score = _cosine_similarity(task.instruction, memory.text)
        precondition_score = self._precondition_score(task=task, memory=memory)
        utility_score = self._utility_score(memory)
        risk_score = self._risk_score(memory)
        age_penalty = self._age_penalty(memory=memory, iteration=iteration)
        cost_penalty = self._cost_penalty(memory)
        final_score = (
            self.config.weight_similarity * similarity_score
            + self.config.weight_precondition * precondition_score
            + self.config.weight_utility * utility_score
            - self.config.weight_risk * risk_score
            - self.config.weight_age * age_penalty
            - self.config.weight_cost * cost_penalty
        )
        reason = self._rejection_reason(
            memory=memory,
            similarity_score=similarity_score,
            precondition_score=precondition_score,
            risk_score=risk_score,
            final_score=final_score,
        )
        return GateDecision(
            task_id=task.task_id,
            memory_id=memory.memory_id,
            candidate_type=memory.type,
            lifecycle_status=memory.lifecycle.status,
            similarity_score=round(similarity_score, 6),
            precondition_score=round(precondition_score, 6),
            utility_score=round(utility_score, 6),
            risk_score=round(risk_score, 6),
            age_penalty=round(age_penalty, 6),
            cost_penalty=round(cost_penalty, 6),
            final_gate_score=round(final_score, 6),
            gate_decision="reject" if reason else "accept",
            rejection_reason=reason,
        )

    def _precondition_score(self, task: Task, memory: CandidateMemory) -> float:
        task_intent = _task_intent(task)
        if task_intent == memory.scope.intent:
            intent_score = 1.0
        elif "general_tool_use" in {task_intent, memory.scope.intent}:
            intent_score = _token_overlap_score(
                task_intent.replace("_", " "),
                memory.scope.intent.replace("_", " "),
            )
        else:
            intent_score = 0.0

        task_domain = str(task.metadata.get("domain", memory.scope.domain))
        domain_score = 1.0 if task_domain == memory.scope.domain else 0.0
        preconditions = " ".join(memory.scope.preconditions)
        precondition_overlap = _token_overlap_score(task.instruction, preconditions)
        return _clamp(0.75 * intent_score + 0.15 * domain_score + 0.10 * precondition_overlap)

    def _utility_score(self, memory: CandidateMemory) -> float:
        utility = memory.utility
        total = utility.alpha + utility.beta
        beta_mean = utility.alpha / total if total > 0 else 0.5
        delta_score = _clamp(0.5 + 0.5 * utility.mean_delta_reward)
        lcb_bonus = 0.1 if utility.lcb_delta_reward > 0.0 else 0.0
        return _clamp(0.70 * beta_mean + 0.30 * delta_score + lcb_bonus)

    def _risk_score(self, memory: CandidateMemory) -> float:
        utility = memory.utility
        evidence_total = len(memory.positive_evidence) + len(memory.negative_evidence)
        negative_evidence_rate = (
            len(memory.negative_evidence) / evidence_total
            if evidence_total
            else 0.0
        )
        harmful_rate = utility.num_harmful / utility.num_used if utility.num_used else 0.0
        status_risk = 1.0 if memory.lifecycle.status in {"quarantined", "retired"} else 0.0
        uncertainty = 1.0 / (1.0 + utility.alpha + utility.beta)
        lcb_risk = 1.0 if utility.lcb_delta_reward < 0.0 else 0.0
        overbroad_risk = 1.0 if memory.scope.intent == "general_tool_use" else 0.0
        return _clamp(
            0.45 * negative_evidence_rate
            + 0.30 * harmful_rate
            + 0.10 * status_risk
            + 0.05 * uncertainty
            + 0.05 * lcb_risk
            + 0.05 * overbroad_risk
        )

    def _age_penalty(self, memory: CandidateMemory, iteration: int) -> float:
        age = max(0, iteration - memory.lifecycle.created_iter)
        ttl = max(1, memory.lifecycle.ttl)
        return _clamp(age / ttl)

    def _cost_penalty(self, memory: CandidateMemory) -> float:
        max_tokens = max(1, self.config.max_memory_tokens)
        return _clamp(estimate_tokens(memory.text) / max_tokens)

    def _rejection_reason(
        self,
        memory: CandidateMemory,
        similarity_score: float,
        precondition_score: float,
        risk_score: float,
        final_score: float,
    ) -> str | None:
        if memory.lifecycle.status not in self.config.allowed_statuses:
            return f"lifecycle_status_{memory.lifecycle.status}"
        if self.config.reject_negative_evidence and memory.negative_evidence:
            return "negative_evidence_present"
        if risk_score > self.config.max_risk:
            return "risk_above_threshold"
        if similarity_score < self.config.min_similarity:
            return "similarity_below_threshold"
        if precondition_score < self.config.min_precondition:
            return "precondition_below_threshold"
        if final_score < self.config.min_score:
            return "score_below_threshold"
        return None

    def _to_retrieved_memory(
        self,
        memory: CandidateMemory,
        decision: GateDecision,
    ) -> RetrievedMemory:
        return RetrievedMemory(
            memory_id=memory.memory_id,
            text=memory.text,
            score=decision.final_gate_score,
            metadata={
                "memory_kind": memory.__class__.__name__,
                "candidate_type": memory.type,
                "lifecycle_status": memory.lifecycle.status,
                "created_iter": memory.lifecycle.created_iter,
                "selected_rank": decision.selected_rank,
                "similarity_score": decision.similarity_score,
                "precondition_score": decision.precondition_score,
                "utility_score": decision.utility_score,
                "risk_score": decision.risk_score,
                "age_penalty": decision.age_penalty,
                "cost_penalty": decision.cost_penalty,
                "final_gate_score": decision.final_gate_score,
                "positive_evidence": list(memory.positive_evidence),
                "negative_evidence": list(memory.negative_evidence),
            },
        )


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


def _task_intent(task: Task) -> str:
    metadata_intent = task.metadata.get("intent")
    if isinstance(metadata_intent, str) and metadata_intent.strip():
        return metadata_intent.strip()
    return _infer_intent(task.instruction)


def _infer_intent(instruction: str) -> str:
    text = instruction.lower()
    if "exchange" in text:
        return "exchange_eligibility"
    if "policy" in text or "return window" in text:
        return "policy_lookup"
    if "refund" in text or "return" in text:
        return "refund_eligibility"
    if "customer" in text or "user id" in text or "email" in text or "zip code" in text:
        return "customer_lookup"
    if "product" in text or "item" in text:
        return "product_lookup"
    if "inventory" in text or "in stock" in text or "sku-" in text:
        return "inventory_check"
    if "order" in text or "delivery status" in text:
        return "order_status"
    return "general_tool_use"


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))
