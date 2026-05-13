from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from ntmemevo.agents.base import Agent
from ntmemevo.envs.base import AgentEnv
from ntmemevo.llm.client import LLMClient
from ntmemevo.logging.trace_logger import TraceLogger
from ntmemevo.types import AgentResult, ChatMessage, RetrievedMemory, Task


REACT_TOOL_DECISION_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "thought": {
            "type": "string",
            "maxLength": 80,
            "description": "A very short audit label. Leave empty when possible.",
        },
        "action": {"type": "string", "enum": ["tool", "final"]},
        "tool_name": {"type": "string"},
        "args": {"type": "object", "additionalProperties": True},
        "answer": {"type": "string"},
    },
    "required": ["action"],
    "additionalProperties": True,
}


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
        prompt_observations: list[tuple[str, str]] = []
        repeat_guardrails: list[tuple[str, str]] = []
        trace_summary: list[str] = []
        memories = memories or []
        prompt_tokens = 0
        completion_tokens = 0
        tool_calls = 0
        final_answer = ""
        error_type: str | None = None
        last_tool_repeat_key: str | None = None
        last_tool_observation: str | None = None
        repeated_run_start_step: int | None = None

        for step in range(1, self.max_steps + 1):
            messages = self._build_messages(
                task,
                env,
                [item[1] for item in prompt_observations],
                memories,
                [item[1] for item in repeat_guardrails[-3:]],
            )
            max_tokens = int(self.model_config.get("max_tokens", 1024))
            response = self.llm.complete(
                messages=messages,
                temperature=float(self.model_config.get("temperature", 0.0)),
                max_tokens=max_tokens,
                response_format=self._response_format(),
            )
            prompt_tokens += response.usage.prompt_tokens
            completion_tokens += response.usage.completion_tokens

            raw_response = response.content
            try:
                parsed_decision = json.loads(raw_response)
            except json.JSONDecodeError as exc:
                parse_detail = _classify_json_parse_error(
                    raw_response=raw_response,
                    exc=exc,
                    max_tokens=max_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    finish_reason=_extract_finish_reason(response.raw),
                )
                final_answer = response.content
                error_type = str(parse_detail["error_type"])
                trace_logger.log_event(
                    task_id=task.task_id,
                    step=step,
                    event_type="model_parse_error",
                    payload={"raw_response": raw_response, **parse_detail},
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
            _upsert_prompt_observation(
                prompt_observations,
                key=_prompt_observation_key(result),
                text=_compact_tool_observation_for_prompt(result),
            )
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
            repeat_key = _repeat_tool_call_key(result)
            if repeat_key == last_tool_repeat_key and result.observation == last_tool_observation:
                if repeated_run_start_step is None:
                    repeated_run_start_step = max(1, step - 1)
                same_call_run_length = step - repeated_run_start_step + 1
                guardrail_message = _repeat_guardrail_message(
                    result=result,
                    same_call_run_length=same_call_run_length,
                )
                _upsert_prompt_observation(
                    repeat_guardrails,
                    key=repeat_key,
                    text=guardrail_message,
                )
                trace_logger.log_event(
                    task_id=task.task_id,
                    step=step,
                    event_type="repeated_tool_call_loop",
                    payload={
                        "repeat_key": repeat_key,
                        "tool_name": result.tool_name,
                        "tool_args": result.args,
                        "first_step": repeated_run_start_step,
                        "current_step": step,
                        "same_call_run_length": same_call_run_length,
                        "consecutive_repeat_count": same_call_run_length - 1,
                        "observation_hash": _stable_text_hash(result.observation),
                        "observation_excerpt": _truncate_text(result.observation, 240),
                        "guardrail_message": guardrail_message,
                    },
                )
            else:
                last_tool_repeat_key = repeat_key
                last_tool_observation = result.observation
                repeated_run_start_step = step
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
        repeat_guardrails: list[str] | None = None,
    ) -> list[ChatMessage]:
        observation_block = "\n".join(f"Observation: {item}" for item in observations)
        repeat_guardrails = repeat_guardrails or []
        user_lines = [
            f"Task id: {task.task_id}",
            f"Instruction: {task.instruction}",
        ]
        if memories:
            user_lines.append(self._format_memories(memories))
        if repeat_guardrails:
            user_lines.append("Repeat guardrails:")
            user_lines.extend(f"- {item}" for item in repeat_guardrails)
        user_lines.extend(
            [
                "Available tools:",
                env.tool_descriptions(),
                observation_block,
                "Output contract:",
                "Return exactly one JSON object and no markdown or extra text.",
                'For a tool call, prefer {"thought":"","action":"tool","tool_name":"name","args":{...}}.',
                'For a final answer, prefer {"thought":"","action":"final","answer":"..."}.',
                'Do not return only a thought. Do not omit "action".',
                'When action is "tool", do not omit "tool_name" or "args".',
                "Keep thought empty or under 8 words. Never copy observations, product variants, IDs lists, or long reasoning into thought.",
                "If you need more information, call exactly one next tool instead of writing a long analysis.",
                "Retail tool-use guardrails:",
                "Do not repeat an identical read-only tool call after it returned the same observation; use the existing observation to choose a different next step.",
                "For exchange requests involving multiple ordered items, inspect each relevant product once, then call the exchange tool with the selected replacement item ids.",
                "Use get_product_details(product_id) to inspect product variants; count available variants from the observation without copying the list.",
                "Use get_item_details(item_id) only for a concrete item id, not for a product id.",
                "Use list_all_product_types at most once; it returns a product-name to product-id map for product discovery.",
                "After get_user_details returns a user, use its order ids with get_order_details; do not repeat the same get_user_details call.",
            ]
        )
        user = "\n".join(user_lines)
        return [
            ChatMessage(
                role="system",
                content=(
                    "You are a careful tool-using agent. "
                    "Call tools when needed and answer only when observations are sufficient. "
                    "Every assistant response must be exactly one compact JSON object with an action field. "
                    "Use an empty or very short thought field; do not expose chain-of-thought."
                ),
            ),
            ChatMessage(role="user", content=user),
        ]

    def _response_format(self) -> dict[str, Any] | None:
        configured = self.model_config.get("response_format")
        if configured is None:
            return {"type": "json_object"}
        if isinstance(configured, bool):
            return {"type": "json_object"} if configured else None
        if isinstance(configured, dict):
            return dict(configured)
        mode = str(configured).strip().lower()
        if mode in {"", "none", "false", "disabled"}:
            return None
        if mode in {"json_object", "object"}:
            return {"type": "json_object"}
        if mode in {"json_schema", "schema"}:
            return {
                "type": "json_schema",
                "json_schema": {
                    "name": "react_tool_decision",
                    "schema": REACT_TOOL_DECISION_JSON_SCHEMA,
                    "strict": False,
                },
            }
        raise ValueError(f"Unsupported models.actor.response_format: {configured!r}")

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


def _classify_json_parse_error(
    raw_response: str,
    exc: json.JSONDecodeError,
    max_tokens: int,
    completion_tokens: int,
    finish_reason: str | None,
) -> dict[str, Any]:
    stripped = raw_response.strip()
    unclosed_json_object = _looks_like_unclosed_json_object(stripped)
    token_budget_hit = _token_budget_hit(
        completion_tokens=completion_tokens,
        max_tokens=max_tokens,
        finish_reason=finish_reason,
    )
    error_type = (
        "truncated_json_response"
        if stripped.startswith("{") and unclosed_json_object and token_budget_hit
        else "invalid_json_response"
    )
    parse_error = (
        "truncated_json_response"
        if error_type == "truncated_json_response"
        else "json_decode_error"
    )
    return {
        "error_type": error_type,
        "parse_error": parse_error,
        "json_error": exc.msg,
        "json_error_pos": exc.pos,
        "raw_response_chars": len(raw_response),
        "starts_with_json_object": stripped.startswith("{"),
        "unclosed_json_object": unclosed_json_object,
        "completion_tokens": completion_tokens,
        "max_tokens": max_tokens,
        "finish_reason": finish_reason,
        "token_budget_hit": token_budget_hit,
    }


def _looks_like_unclosed_json_object(text: str) -> bool:
    if not text.startswith("{"):
        return False
    depth = 0
    in_string = False
    escape = False
    for char in text:
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
    return in_string or depth > 0


def _token_budget_hit(
    completion_tokens: int,
    max_tokens: int,
    finish_reason: str | None,
) -> bool:
    if finish_reason and finish_reason.lower() in {"length", "max_tokens"}:
        return True
    if max_tokens <= 0 or completion_tokens <= 0:
        return False
    return completion_tokens >= max(1, int(max_tokens * 0.95))


def _extract_finish_reason(raw: dict[str, Any]) -> str | None:
    response = raw.get("response") if isinstance(raw, dict) else None
    if not isinstance(response, dict):
        response = raw if isinstance(raw, dict) else {}
    choices = response.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            reason = first.get("finish_reason")
            if reason is not None:
                return str(reason)
    return None


def _prompt_observation_key(result: Any) -> str:
    return json.dumps(
        {
            "tool_name": getattr(result, "tool_name", ""),
            "args": getattr(result, "args", {}),
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _repeat_tool_call_key(result: Any) -> str:
    return _prompt_observation_key(result)


def _stable_text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _repeat_guardrail_message(result: Any, same_call_run_length: int) -> str:
    tool_name = str(getattr(result, "tool_name", "") or "")
    args = getattr(result, "args", {})
    args_text = json.dumps(args, ensure_ascii=False, sort_keys=True)
    return (
        f"{tool_name}({args_text}) returned the same observation "
        f"{same_call_run_length} consecutive times. Do not call it again with "
        "identical args; use the existing result, call a different required lookup, "
        "finish with a final answer, or make a safe write call if all required data is known."
    )


def _upsert_prompt_observation(
    observations: list[tuple[str, str]],
    key: str,
    text: str,
) -> None:
    for index, (existing_key, _) in enumerate(observations):
        if existing_key == key:
            observations[index] = (key, text)
            return
    observations.append((key, text))


def _compact_tool_observation_for_prompt(result: Any) -> str:
    tool_name = str(getattr(result, "tool_name", "") or "")
    args = getattr(result, "args", {})
    observation = str(getattr(result, "observation", "") or "")
    prefix = f"{tool_name}({json.dumps(args, ensure_ascii=False, sort_keys=True)}) -> "
    if not observation.strip().startswith("{"):
        return prefix + _truncate_text(observation, 900)

    try:
        record = json.loads(observation)
    except json.JSONDecodeError:
        return prefix + _truncate_text(observation, 900)
    if not isinstance(record, dict):
        return prefix + _truncate_text(observation, 900)

    if tool_name == "get_product_details":
        compact = _compact_product_record(record)
    elif tool_name == "get_order_details":
        compact = _compact_order_record(record)
    elif tool_name == "get_user_details":
        compact = _compact_user_record(record)
    elif tool_name == "list_all_product_types":
        compact = _compact_product_type_index(record)
    else:
        compact = _truncate_text(
            json.dumps(record, ensure_ascii=False, sort_keys=True),
            900,
        )
    return prefix + compact


def _compact_product_record(record: dict[str, Any]) -> str:
    variants = record.get("variants")
    if not isinstance(variants, dict):
        return _truncate_text(json.dumps(record, ensure_ascii=False, sort_keys=True), 900)

    available = []
    unavailable = []
    unavailable_count = 0
    for item_id, raw_variant in sorted(variants.items()):
        if not isinstance(raw_variant, dict):
            continue
        variant = dict(raw_variant)
        variant.setdefault("item_id", item_id)
        entry = _compact_variant_entry(variant)
        if bool(variant.get("available")):
            available.append(entry)
        else:
            unavailable.append(entry)
            unavailable_count += 1

    return (
        f"product_id={record.get('product_id')}; name={record.get('name')}; "
        f"variants_total={len(variants)}; available_count={len(available)}; "
        f"available_variants=[{_format_variant_entries(available)}]; "
        f"unavailable_count={unavailable_count}; "
        f"unavailable_variants=[{_format_variant_entries(unavailable)}]"
    )


def _compact_order_record(record: dict[str, Any]) -> str:
    items = record.get("items")
    compact_items = []
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            compact_items.append(
                (
                    f"item_id={item.get('item_id')}; name={item.get('name')}; "
                    f"product_id={item.get('product_id')}; options={_compact_options(item.get('options'))}; "
                    f"price={item.get('price')}"
                )
            )
    payment_ids = []
    payment_history = record.get("payment_history")
    if isinstance(payment_history, list):
        for payment in payment_history:
            if isinstance(payment, dict) and payment.get("payment_method_id") is not None:
                payment_ids.append(str(payment.get("payment_method_id")))
    return (
        f"order_id={record.get('order_id')}; status={record.get('status')}; "
        f"user_id={record.get('user_id')}; payment_method_ids={payment_ids}; "
        f"items=[{'; '.join(compact_items)}]"
    )


def _compact_user_record(record: dict[str, Any]) -> str:
    order_ids = record.get("orders") or record.get("order_ids")
    if isinstance(order_ids, dict):
        order_ids = list(order_ids)
    if not isinstance(order_ids, list):
        order_ids = []
    payment_methods = record.get("payment_methods")
    payment_ids = list(payment_methods) if isinstance(payment_methods, dict) else []
    return (
        f"user_id={record.get('user_id') or record.get('id')}; "
        f"name={record.get('name')}; email={record.get('email')}; "
        f"order_ids={order_ids}; payment_method_ids={payment_ids}"
    )


def _compact_product_type_index(record: dict[str, Any]) -> str:
    entries = []
    for name, product_id in sorted(record.items(), key=lambda item: str(item[0]).lower()):
        entries.append(f"{name}={product_id}")
    return "product_type_ids={" + "; ".join(entries) + "}"


def _compact_variant_entry(variant: dict[str, Any]) -> str:
    return (
        f"item_id={variant.get('item_id')}; "
        f"options={_compact_options(variant.get('options'))}; "
        f"price={variant.get('price')}"
    )


def _compact_options(value: Any) -> str:
    if isinstance(value, dict):
        return ",".join(f"{key}={value[key]}" for key in sorted(value))
    return str(value or "")


def _format_variant_entries(entries: list[str], max_entries: int = 12) -> str:
    if len(entries) <= max_entries:
        return "; ".join(entries)
    visible = entries[:max_entries]
    visible.append(f"... +{len(entries) - max_entries} more")
    return "; ".join(visible)


def _truncate_text(text: str, max_chars: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3] + "..."
