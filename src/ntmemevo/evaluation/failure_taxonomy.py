from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


TRACE_EVENT_KEYS = (
    "model_decision",
    "model_action_repair",
    "model_parse_error",
    "expected_actions_complete",
    "tool_call",
    "scripted_action",
)


def summarize_failure_taxonomy(output_dir: str | Path) -> dict[str, Any]:
    output_path = Path(output_dir)
    run_records = _read_jsonl(output_path / "runs.jsonl")
    trace_records = _read_jsonl(output_path / "trace_events.jsonl")

    event_counts_by_task: dict[str, Counter[str]] = defaultdict(Counter)
    last_model_decision_by_task: dict[str, dict[str, Any]] = {}
    first_model_parse_error_by_task: dict[str, dict[str, Any]] = {}
    for record in trace_records:
        task_id = str(record.get("task_id") or "")
        event_type = str(record.get("event_type") or "")
        if not task_id or not event_type:
            continue
        event_counts_by_task[task_id][event_type] += 1
        if event_type == "model_decision":
            last_model_decision_by_task[task_id] = record
        elif event_type == "model_parse_error" and task_id not in first_model_parse_error_by_task:
            first_model_parse_error_by_task[task_id] = record

    task_summaries = []
    primary_failure_counts: Counter[str] = Counter()
    error_type_counts: Counter[str] = Counter()
    trace_event_counts: Counter[str] = Counter()
    success_count = 0

    for record in run_records:
        task_id = str(record.get("task_id") or "")
        success = bool(record.get("success"))
        if success:
            success_count += 1
        error_type = _optional_str(record.get("error_type"))
        if error_type:
            error_type_counts[error_type] += 1

        details = record.get("evaluation_details") or {}
        if not isinstance(details, dict):
            details = {}
        event_counts = event_counts_by_task.get(task_id, Counter())
        trace_event_counts.update(event_counts)
        primary_failure = _primary_failure_type(
            success=success,
            error_type=error_type,
            details=details,
            event_counts=event_counts,
        )
        primary_failure_counts[primary_failure] += 1

        task_summaries.append(
            _task_summary(
                record=record,
                details=details,
                primary_failure=primary_failure,
                event_counts=event_counts,
                last_model_decision=last_model_decision_by_task.get(task_id),
                first_model_parse_error=first_model_parse_error_by_task.get(task_id),
            )
        )

    return {
        "num_tasks": len(run_records),
        "success_count": success_count,
        "failure_count": len(run_records) - success_count,
        "success_rate": success_count / len(run_records) if run_records else 0.0,
        "primary_failure_types": dict(sorted(primary_failure_counts.items())),
        "error_types": dict(sorted(error_type_counts.items())),
        "trace_event_counts": dict(sorted(trace_event_counts.items())),
        "tasks": task_summaries,
    }


def write_failure_taxonomy(output_dir: str | Path) -> dict[str, Any]:
    summary = summarize_failure_taxonomy(output_dir)
    path = Path(output_dir) / "failure_taxonomy.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def failure_taxonomy_metric_summary(summary: dict[str, Any]) -> dict[str, Any]:
    trace_counts = summary.get("trace_event_counts") or {}
    primary_counts = summary.get("primary_failure_types") or {}
    if not isinstance(trace_counts, dict):
        trace_counts = {}
    if not isinstance(primary_counts, dict):
        primary_counts = {}
    return {
        "failure_taxonomy_task_count": int(summary.get("num_tasks") or 0),
        "failure_taxonomy_failure_count": int(summary.get("failure_count") or 0),
        "failure_taxonomy_primary_types": dict(sorted(primary_counts.items())),
        "expected_actions_complete_count": int(
            trace_counts.get("expected_actions_complete") or 0
        ),
        "model_action_repair_count": int(trace_counts.get("model_action_repair") or 0),
        "model_parse_error_count": int(trace_counts.get("model_parse_error") or 0),
        "truncated_json_response_count": int(
            primary_counts.get("truncated_json_response") or 0
        ),
    }


def _task_summary(
    record: dict[str, Any],
    details: dict[str, Any],
    primary_failure: str,
    event_counts: Counter[str],
    last_model_decision: dict[str, Any] | None,
    first_model_parse_error: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "task_id": str(record.get("task_id") or ""),
        "run_id": str(record.get("run_id") or ""),
        "success": bool(record.get("success")),
        "reward": float(record.get("reward") or 0.0),
        "primary_failure_type": primary_failure,
        "error_type": _optional_str(record.get("error_type")),
        "num_steps": int(record.get("num_steps") or 0),
        "tool_calls": int(record.get("tool_calls") or 0),
        "prompt_tokens": int(record.get("prompt_tokens") or 0),
        "completion_tokens": int(record.get("completion_tokens") or 0),
        "memory_policy": str(record.get("memory_policy") or ""),
        "expected_actions_matched": details.get("expected_actions_matched"),
        "expected_action_count": int(details.get("expected_action_count") or 0),
        "actual_action_count": int(details.get("actual_action_count") or 0),
        "state_diff_passed": details.get("state_diff_passed"),
        "communicate_info_passed": details.get("communicate_info_passed"),
        "nl_assertions_passed": details.get("nl_assertions_passed"),
        "policy_violation_count": int(details.get("policy_violation_count") or 0),
        "tool_observation_error_count": int(
            details.get("tool_observation_error_count") or 0
        ),
        "expected_negative_observation_count": int(
            details.get("expected_negative_observation_count") or 0
        ),
        "tool_semantic_error_count": int(details.get("tool_semantic_error_count") or 0),
        "unsupported_official_criteria_count": int(
            details.get("unsupported_official_criteria_count") or 0
        ),
        "event_counts": _selected_event_counts(event_counts),
        "expected_actions_complete": event_counts.get("expected_actions_complete", 0) > 0,
        "first_action_mismatch": _first_item(details.get("action_mismatches")),
        "first_policy_violation": _first_item(details.get("policy_violations")),
        "first_tool_semantic_error": _first_item(details.get("tool_semantic_errors")),
        "first_tool_observation_error": _first_item(
            details.get("tool_observation_errors")
        ),
        "last_model_decision": _model_decision_summary(last_model_decision),
        "first_model_parse_error": _model_parse_error_summary(first_model_parse_error),
    }


def _primary_failure_type(
    success: bool,
    error_type: str | None,
    details: dict[str, Any],
    event_counts: Counter[str],
) -> str:
    if success:
        return "success"
    if event_counts.get("model_parse_error", 0) > 0:
        if error_type == "truncated_json_response":
            return "truncated_json_response"
        return "model_parse_error"
    if error_type:
        return error_type
    if int(details.get("policy_violation_count") or 0) > 0:
        return "policy_violation"
    if int(details.get("tool_semantic_error_count") or 0) > 0:
        return "tool_semantic_error"
    if details.get("expected_actions_matched") is False:
        return "expected_action_sequence_mismatch"
    if details.get("state_diff_passed") is False:
        return "state_diff_mismatch"
    if details.get("communicate_info_passed") is False:
        return "communicate_info_mismatch"
    if details.get("nl_assertions_passed") is False:
        return "natural_language_assertion_mismatch"
    if int(details.get("unsupported_official_criteria_count") or 0) > 0:
        return "unsupported_official_criterion"
    return "unknown_failure"


def _model_decision_summary(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if not record:
        return None
    raw_response = record.get("raw_response")
    raw_response_text = raw_response if isinstance(raw_response, str) else None
    return {
        "step": record.get("step"),
        "action": record.get("action"),
        "tool_name": record.get("tool_name"),
        "repair_status": record.get("repair_status"),
        "repair_reason": record.get("repair_reason"),
        "raw_response_available": raw_response_text is not None,
        "raw_response_chars": len(raw_response_text) if raw_response_text is not None else 0,
        "raw_response_excerpt": _excerpt(raw_response_text),
    }


def _model_parse_error_summary(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if not record:
        return None
    raw_response = record.get("raw_response")
    raw_response_text = raw_response if isinstance(raw_response, str) else None
    return {
        "step": record.get("step"),
        "error_type": record.get("error_type"),
        "parse_error": record.get("parse_error"),
        "json_error": record.get("json_error"),
        "json_error_pos": record.get("json_error_pos"),
        "raw_response_available": raw_response_text is not None,
        "raw_response_chars": len(raw_response_text) if raw_response_text is not None else 0,
        "raw_response_excerpt": _excerpt(raw_response_text),
        "starts_with_json_object": record.get("starts_with_json_object"),
        "unclosed_json_object": record.get("unclosed_json_object"),
        "completion_tokens": record.get("completion_tokens"),
        "max_tokens": record.get("max_tokens"),
        "finish_reason": record.get("finish_reason"),
        "token_budget_hit": record.get("token_budget_hit"),
    }


def _selected_event_counts(event_counts: Counter[str]) -> dict[str, int]:
    return {
        key: int(event_counts.get(key, 0))
        for key in TRACE_EVENT_KEYS
        if event_counts.get(key, 0)
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if isinstance(record, dict):
            records.append(record)
    return records


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _first_item(value: Any) -> Any:
    if isinstance(value, list) and value:
        return value[0]
    return None


def _excerpt(value: str | None, max_chars: int = 240) -> str | None:
    if value is None:
        return None
    compact = " ".join(value.split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3] + "..."
