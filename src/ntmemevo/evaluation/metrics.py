from __future__ import annotations

from ntmemevo.types import AgentResult


def aggregate_results(results: list[AgentResult]) -> dict[str, float | int]:
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
