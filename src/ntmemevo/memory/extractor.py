from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from ntmemevo.memory.schema import (
    CandidateMemory,
    MemoryLifecycle,
    MemoryScope,
    MemorySource,
    MemoryUtility,
    canonical_json_hash_payload,
)
from ntmemevo.types import AgentResult, Task


TOOL_NAME_RE = re.compile(r"^([A-Za-z0-9_-]+)\(")


@dataclass(frozen=True)
class CandidateExtractionContext:
    benchmark: str
    experiment_id: str
    run_id: str
    iteration: int


class CandidateMemoryExtractor:
    def __init__(
        self,
        extractor_model: str = "deterministic_candidate_extractor_v1",
        domain: str = "retail",
        ttl: int = 50,
        max_claim_chars: int = 700,
    ) -> None:
        self.extractor_model = extractor_model
        self.domain = domain
        self.ttl = ttl
        self.max_claim_chars = max_claim_chars

    def extract(
        self,
        task: Task,
        result: AgentResult,
        context: CandidateExtractionContext,
    ) -> CandidateMemory:
        memory_type = self._memory_type(task=task, result=result)
        intent = self._intent(task.instruction)
        tool_names = self._tool_names(result.trace_summary)
        positive_evidence = (context.run_id,) if result.success else ()
        negative_evidence = () if result.success else (context.run_id,)
        claim = self._truncate(
            self._claim(
                task=task,
                result=result,
                intent=intent,
                tool_names=tool_names,
            )
        )
        action_hint = self._action_hint(result.trace_summary)
        avoid_hint = self._avoid_hint(result=result)
        source_payload = {
            "task_id": task.task_id,
            "instruction": task.instruction,
            "trace_summary": list(result.trace_summary),
            "final_answer": result.final_answer,
            "reward": result.reward,
            "success": result.success,
            "extractor_model": self.extractor_model,
        }
        prompt_hash = hashlib.sha256(
            canonical_json_hash_payload(source_payload).encode("utf-8")
        ).hexdigest()

        memory = CandidateMemory(
            memory_id=f"cand_{context.iteration:06d}_{task.task_id}",
            type=memory_type,
            claim=claim,
            scope=MemoryScope(
                benchmark=context.benchmark,
                domain=str(task.metadata.get("domain", self.domain)),
                intent=intent,
                tool_names=tool_names,
                preconditions=self._preconditions(
                    task=task,
                    intent=intent,
                    tool_names=tool_names,
                ),
            ),
            action_hint=action_hint,
            avoid_hint=avoid_hint,
            positive_evidence=positive_evidence,
            negative_evidence=negative_evidence,
            utility=MemoryUtility(),
            lifecycle=MemoryLifecycle(
                status="candidate",
                created_iter=context.iteration,
                last_used_iter=None,
                ttl=self.ttl,
            ),
            source=MemorySource(
                created_from=(context.run_id,),
                extractor_model=self.extractor_model,
                prompt_hash=prompt_hash,
            ),
        )
        memory.validate()
        return memory

    def _memory_type(self, task: Task, result: AgentResult) -> str:
        if not result.success:
            return "warning"
        intent = self._intent(task.instruction)
        if intent == "policy_lookup":
            return "user_policy"
        if intent in {"exchange_eligibility", "refund_eligibility"}:
            return "constraint"
        return "tool_usage"

    def _claim(
        self,
        task: Task,
        result: AgentResult,
        intent: str,
        tool_names: tuple[str, ...],
    ) -> str:
        tools = " -> ".join(tool_names) if tool_names else "no tool"
        expected = ", ".join(task.expected_answer_contains) if task.expected_answer_contains else "target answer"
        if result.success:
            return (
                f"For {intent} tasks like '{task.instruction}', collect tool evidence with "
                f"{tools} and make the final answer include the evaluator signal(s): {expected}."
            )
        error = result.error_type or "unknown_error"
        return (
            f"A prior {intent} attempt failed with {error}. Do not rely on this pattern "
            f"unless the tool evidence supports the expected signal(s): {expected}."
        )

    def _action_hint(self, trace_summary: tuple[str, ...]) -> str:
        if not trace_summary:
            return "Call the relevant tool before answering; do not guess without an observation."
        return "Follow the observed tool evidence path: " + " | ".join(trace_summary)

    def _avoid_hint(self, result: AgentResult) -> str:
        if result.success:
            return "Do not answer from memory alone; verify the current task with the matching tool output."
        error = result.error_type or "unknown_error"
        return f"Avoid repeating runs that end with {error}; obtain missing evidence first."

    def _preconditions(
        self,
        task: Task,
        intent: str,
        tool_names: tuple[str, ...],
    ) -> tuple[str, ...]:
        preconditions = [
            f"instruction intent is {intent}",
            "current task asks for tool-grounded retail evidence",
        ]
        ids = self._identifiers(task.instruction)
        if ids:
            preconditions.append("instruction contains identifier(s): " + ", ".join(ids))
        if tool_names:
            preconditions.append("available tools include: " + ", ".join(tool_names))
        return tuple(preconditions)

    def _intent(self, instruction: str) -> str:
        text = instruction.lower()
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

    def _tool_names(self, trace_summary: tuple[str, ...]) -> tuple[str, ...]:
        names = []
        for item in trace_summary:
            match = TOOL_NAME_RE.search(item.strip())
            if match:
                names.append(match.group(1))
        return tuple(dict.fromkeys(names))

    def _identifiers(self, instruction: str) -> tuple[str, ...]:
        matches = re.findall(r"\b(?:ORD|SKU)-[A-Z0-9-]+\b", instruction.upper())
        return tuple(dict.fromkeys(matches))

    def _truncate(self, value: str) -> str:
        if len(value) <= self.max_claim_chars:
            return value
        return value[: self.max_claim_chars - 3].rstrip() + "..."
