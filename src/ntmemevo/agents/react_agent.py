from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ntmemevo.agents.base import Agent
from ntmemevo.envs.base import AgentEnv
from ntmemevo.llm.client import LLMClient
from ntmemevo.logging.trace_logger import TraceLogger
from ntmemevo.types import AgentResult, ChatMessage, RetrievedMemory, Task


class ReActToolAgent(Agent):
    def __init__(
        self,
        llm: LLMClient,
        model_config: dict[str, Any],
        max_steps: int,
        memory_top_k: int = 0,
        log_raw_model_io: bool = False,
        stop_after_expected_actions: bool = False,
    ) -> None:
        self.llm = llm
        self.model_config = model_config
        self.max_steps = max_steps
        self.memory_top_k = memory_top_k
        self.log_raw_model_io = log_raw_model_io
        self.stop_after_expected_actions = stop_after_expected_actions

    def run(
        self,
        task: Task,
        env: AgentEnv,
        trace_logger: TraceLogger,
        memories: list[RetrievedMemory] | None = None,
    ) -> AgentResult:
        start_task = getattr(env, "start_task", None)
        if callable(start_task):
            start_task(task)

        observations: list[str] = []
        trace_summary: list[str] = []
        memories = memories or []
        prompt_tokens = 0
        completion_tokens = 0
        tool_calls = 0
        final_answer = ""
        error_type: str | None = None

        for step in range(1, self.max_steps + 1):
            messages = self._build_messages(task, env, observations, memories)
            response = self.llm.complete(
                messages=messages,
                temperature=float(self.model_config.get("temperature", 0.0)),
                max_tokens=int(self.model_config.get("max_tokens", 1024)),
                response_format={"type": "json_object"},
            )
            prompt_tokens += response.usage.prompt_tokens
            completion_tokens += response.usage.completion_tokens

            raw_response = response.content
            try:
                parsed_decision = json.loads(raw_response)
            except json.JSONDecodeError:
                final_answer = response.content
                error_type = "invalid_json_response"
                trace_logger.log_event(
                    task_id=task.task_id,
                    step=step,
                    event_type="model_parse_error",
                    payload={"raw_response": raw_response, "parse_error": "json_decode_error"},
                )
                break
            if not isinstance(parsed_decision, dict):
                final_answer = response.content
                error_type = "invalid_decision_object"
                trace_logger.log_event(
                    task_id=task.task_id,
                    step=step,
                    event_type="model_parse_error",
                    payload={
                        "raw_response": raw_response,
                        "parse_error": "json_root_not_object",
                        "parsed_decision": parsed_decision,
                    },
                )
                break

            normalized = _normalize_decision(parsed_decision)
            if normalized.repair_status == "repaired":
                trace_logger.log_event(
                    task_id=task.task_id,
                    step=step,
                    event_type="model_action_repair",
                    payload={
                        "repair_reason": normalized.repair_reason,
                        "raw_response": raw_response,
                        "parsed_decision": parsed_decision,
                        "repaired_decision": normalized.decision,
                        "action_before": normalized.action_before,
                        "action_after": normalized.action,
                        "tool_name": normalized.tool_name or None,
                        "args": normalized.args,
                    },
                )

            action = normalized.action
            decision_payload: dict[str, Any] = {
                "thought_summary": normalized.decision.get("thought", ""),
                "action": action,
                "tool_name": normalized.tool_name or None,
                "used_memory_ids": [memory.memory_id for memory in memories],
                "repair_status": normalized.repair_status,
                "repair_reason": normalized.repair_reason,
            }
            if (
                self.log_raw_model_io
                or normalized.repair_status != "not_needed"
                or action not in {"tool", "final"}
            ):
                decision_payload["raw_response"] = raw_response
                decision_payload["parsed_decision"] = parsed_decision
            trace_logger.log_event(
                task_id=task.task_id,
                step=step,
                event_type="model_decision",
                payload=decision_payload,
            )

            if action == "final":
                final_answer = str(normalized.decision.get("answer", ""))
                break

            if action != "tool":
                final_answer = f"Unsupported action: {action}"
                error_type = "unsupported_action"
                break

            tool_name = normalized.tool_name
            args = normalized.args
            result = env.call_tool(tool_name, args)
            tool_calls += 1
            observations.append(result.observation)
            trace_summary.append(f"{result.tool_name}({result.args}) -> {result.observation}")
            trace_logger.log_event(
                task_id=task.task_id,
                step=step,
                event_type="tool_call",
                payload={
                    "tool_name": result.tool_name,
                    "tool_args": result.args,
                    "observation_summary": result.observation,
                    "ok": result.ok,
                },
            )
            expected_actions_completed = getattr(env, "expected_actions_completed", None)
            if (
                self.stop_after_expected_actions
                and callable(expected_actions_completed)
                and expected_actions_completed(task)
            ):
                final_answer = result.observation
                trace_logger.log_event(
                    task_id=task.task_id,
                    step=step,
                    event_type="expected_actions_complete",
                    payload={
                        "tool_calls": tool_calls,
                        "final_answer": final_answer,
                    },
                )
                break
        else:
            error_type = "max_steps_exceeded"
            final_answer = observations[-1] if observations else "No final answer."

        success, reward, eval_error = env.evaluate(task, final_answer)
        evaluation_details = getattr(env, "last_evaluation_detail", {})
        if not isinstance(evaluation_details, dict):
            evaluation_details = {}
        error_type = error_type or eval_error
        return AgentResult(
            task_id=task.task_id,
            success=success,
            reward=reward,
            final_answer=final_answer,
            num_steps=min(self.max_steps, len(observations) + 1),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            tool_calls=tool_calls,
            used_memory_ids=tuple(memory.memory_id for memory in memories),
            trace_summary=tuple(trace_summary),
            error_type=error_type,
            evaluation_details=dict(evaluation_details),
        )

    def _build_messages(
        self,
        task: Task,
        env: AgentEnv,
        observations: list[str],
        memories: list[RetrievedMemory],
    ) -> list[ChatMessage]:
        observation_block = "\n".join(f"Observation: {item}" for item in observations)
        user_lines = [
            f"Task id: {task.task_id}",
            f"Instruction: {task.instruction}",
        ]
        if memories:
            user_lines.append(self._format_memories(memories))
        user_lines.extend(
            [
                "Available tools:",
                env.tool_descriptions(),
                observation_block,
                "Output contract:",
                "Return exactly one JSON object and no markdown or extra text.",
                'For a tool call, use {"thought":"...","action":"tool","tool_name":"name","args":{...}}.',
                'For a final answer, use {"thought":"...","action":"final","answer":"..."}.',
                'Do not return only a thought. Do not omit "action".',
                'When action is "tool", do not omit "tool_name" or "args".',
            ]
        )
        user = "\n".join(user_lines)
        return [
            ChatMessage(
                role="system",
                content=(
                    "You are a careful tool-using agent. "
                    "Call tools when needed and answer only when observations are sufficient. "
                    "Every assistant response must be exactly one JSON object with an action field."
                ),
            ),
            ChatMessage(role="user", content=user),
        ]

    def _format_memories(self, memories: list[RetrievedMemory]) -> str:
        lines = ["Retrieved memories:"]
        for memory in memories:
            memory_kind = str(memory.metadata.get("memory_kind") or "memory")
            reflection_type = memory.metadata.get("reflection_type")
            label = memory_kind
            if reflection_type:
                label = f"{memory_kind}:{reflection_type}"
            lines.append(f"[{memory.memory_id} | {label} | score={memory.score:.3f}] {memory.text}")
        return "\n".join(lines)


@dataclass(frozen=True)
class _NormalizedDecision:
    decision: dict[str, Any]
    action: str
    tool_name: str
    args: dict[str, Any]
    action_before: str
    repair_status: str
    repair_reason: str | None = None


def _normalize_decision(decision: dict[str, Any]) -> _NormalizedDecision:
    normalized = dict(decision)
    action_before = _normalize_action(decision.get("action"))
    action = action_before
    tool_name = _first_string(decision.get("tool_name"), decision.get("tool"))
    args, args_key = _extract_args(decision)
    repair_status = "not_needed"
    repair_reason: str | None = None

    if action == "tool":
        if "tool_name" not in normalized and tool_name:
            normalized["tool_name"] = tool_name
            repair_status = "repaired"
            repair_reason = "normalized_tool_field"
        if args_key == "arguments" and "args" not in normalized:
            normalized["args"] = args
            repair_status = "repaired"
            repair_reason = (
                "normalized_tool_arguments"
                if repair_reason is None
                else f"{repair_reason}+normalized_tool_arguments"
            )
        if not isinstance(normalized.get("args"), dict):
            normalized["args"] = args
        return _NormalizedDecision(
            decision=normalized,
            action=action,
            tool_name=tool_name,
            args=args,
            action_before=action_before,
            repair_status=repair_status,
            repair_reason=repair_reason,
        )

    if action == "final":
        return _NormalizedDecision(
            decision=normalized,
            action=action,
            tool_name=tool_name,
            args=args,
            action_before=action_before,
            repair_status=repair_status,
            repair_reason=repair_reason,
        )

    if not action and tool_name and args_key is not None:
        normalized["action"] = "tool"
        normalized["tool_name"] = tool_name
        normalized["args"] = args
        return _NormalizedDecision(
            decision=normalized,
            action="tool",
            tool_name=tool_name,
            args=args,
            action_before=action_before,
            repair_status="repaired",
            repair_reason=f"missing_action_with_{args_key}",
        )

    if not action:
        repair_status = "unrepairable"
        repair_reason = "missing_action_without_tool_fields"

    return _NormalizedDecision(
        decision=normalized,
        action=action,
        tool_name=tool_name,
        args=args,
        action_before=action_before,
        repair_status=repair_status,
        repair_reason=repair_reason,
    )


def _normalize_action(value: Any) -> str:
    return str(value or "").strip().lower()


def _first_string(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_args(decision: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    for key in ("args", "arguments"):
        value = decision.get(key)
        if isinstance(value, dict):
            return dict(value), key
    return {}, None
