from __future__ import annotations

from collections import Counter

from ntmemevo.types import AgentResult


def aggregate_results(results: list[AgentResult]) -> dict[str, object]:
    if not results:
        return {
            "num_tasks": 0,
            "success_rate": 0.0,
            "avg_reward": 0.0,
            "avg_steps": 0.0,
            "avg_prompt_tokens": 0.0,
            "avg_completion_tokens": 0.0,
            "avg_tool_calls": 0.0,
        }
    n = len(results)
    return {
        "num_tasks": n,
        "success_rate": sum(1 for result in results if result.success) / n,
        "avg_reward": sum(result.reward for result in results) / n,
        "avg_steps": sum(result.num_steps for result in results) / n,
        "avg_prompt_tokens": sum(result.prompt_tokens for result in results) / n,
        "avg_completion_tokens": sum(result.completion_tokens for result in results) / n,
        "avg_tool_calls": sum(result.tool_calls for result in results) / n,
        **aggregate_evaluation_details(results),
    }


def aggregate_evaluation_details(results: list[AgentResult]) -> dict[str, object]:
    details = [result.evaluation_details for result in results if result.evaluation_details]
    modes = Counter(str(detail.get("evaluation_mode")) for detail in details if detail.get("evaluation_mode"))
    error_types = Counter(result.error_type for result in results if result.error_type)

    state_diff_evaluated = [
        detail for detail in details if detail.get("state_diff_passed") is not None
    ]
    action_evaluated = [
        detail for detail in details if detail.get("expected_actions_matched") is not None
    ]
    communicate_evaluated = [
        detail for detail in details if detail.get("communicate_info_passed") is not None
    ]
    nl_assertion_evaluated = [
        detail for detail in details if detail.get("nl_assertions_passed") is not None
    ]
    return {
        "evaluation_modes": dict(sorted(modes.items())),
        "state_diff_evaluated_count": len(state_diff_evaluated),
        "state_diff_passed_count": sum(
            1 for detail in state_diff_evaluated if detail.get("state_diff_passed") is True
        ),
        "state_diff_failed_count": sum(
            1 for detail in state_diff_evaluated if detail.get("state_diff_passed") is False
        ),
        "expected_actions_evaluated_count": len(action_evaluated),
        "expected_actions_matched_count": sum(
            1 for detail in action_evaluated if detail.get("expected_actions_matched") is True
        ),
        "expected_actions_failed_count": sum(
            1 for detail in action_evaluated if detail.get("expected_actions_matched") is False
        ),
        "policy_violation_count": sum(
            int(detail.get("policy_violation_count") or 0) for detail in details
        ),
        "tool_observation_error_count": sum(
            int(detail.get("tool_observation_error_count") or 0) for detail in details
        ),
        "expected_negative_observation_count": sum(
            int(detail.get("expected_negative_observation_count") or 0) for detail in details
        ),
        "tool_semantic_error_count": sum(
            int(detail.get("tool_semantic_error_count") or 0) for detail in details
        ),
        "communicate_info_evaluated_count": len(communicate_evaluated),
        "communicate_info_passed_count": sum(
            1 for detail in communicate_evaluated if detail.get("communicate_info_passed") is True
        ),
        "communicate_info_failed_count": sum(
            1 for detail in communicate_evaluated if detail.get("communicate_info_passed") is False
        ),
        "nl_assertion_evaluated_count": len(nl_assertion_evaluated),
        "nl_assertion_passed_count": sum(
            1 for detail in nl_assertion_evaluated if detail.get("nl_assertions_passed") is True
        ),
        "nl_assertion_failed_count": sum(
            1 for detail in nl_assertion_evaluated if detail.get("nl_assertions_passed") is False
        ),
        "unsupported_official_criteria_count": sum(
            int(detail.get("unsupported_official_criteria_count") or 0) for detail in details
        ),
        "evaluator_error_types": dict(sorted(error_types.items())),
    }


def aggregate_negative_transfer(
    results: list[AgentResult],
    no_memory_success_by_task: dict[str, bool] | None = None,
) -> dict[str, int | float | list[str] | list[dict[str, object]]]:
    no_memory_success_by_task = no_memory_success_by_task or {}
    attributed_failures: list[dict[str, object]] = []
    harmful_memory_ids: set[str] = set()

    for result in results:
        baseline_success = no_memory_success_by_task.get(result.task_id, True)
        if result.used_memory_ids and not result.success and baseline_success:
            harmful_memory_ids.update(result.used_memory_ids)
            attributed_failures.append(
                {
                    "task_id": result.task_id,
                    "used_memory_ids": list(result.used_memory_ids),
                    "reward": result.reward,
                    "error_type": result.error_type,
                }
            )

    denominator = len(results) if results else 1
    return {
        "with_memory_fail_no_memory_success": len(attributed_failures),
        "memory_attributed_failures": len(attributed_failures),
        "negative_transfer_rate": len(attributed_failures) / denominator,
        "harmful_memory_ids": sorted(harmful_memory_ids),
        "negative_transfer_failure_examples": attributed_failures,
    }
