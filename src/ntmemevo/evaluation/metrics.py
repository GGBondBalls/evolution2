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
