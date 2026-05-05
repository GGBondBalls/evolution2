from __future__ import annotations

from typing import Any

from ntmemevo.agents.base import Agent
from ntmemevo.envs.base import AgentEnv
from ntmemevo.logging.trace_logger import TraceLogger
from ntmemevo.types import AgentResult, RetrievedMemory, Task


class ActionReplayAgent(Agent):
    """Scripted oracle that replays a task's expected tool actions.

    This agent is for adapter/evaluator alignment only. It executes
    ``Task.metadata["expected_actions"]`` exactly as loaded from a tau2 task,
    so failures can be attributed to tool semantics, state mutation, or
    evaluator support rather than to a weak mock actor.
    """

    def __init__(self, max_steps: int = 32) -> None:
        self.max_steps = max_steps

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

        expected_actions = task.metadata.get("expected_actions") or []
        if not isinstance(expected_actions, list):
            expected_actions = []

        trace_summary: list[str] = []
        observations: list[str] = []
        tool_calls = 0
        error_type: str | None = None

        for step, action in enumerate(expected_actions[: self.max_steps], start=1):
            if not isinstance(action, dict):
                continue
            tool_name = str(action.get("name") or action.get("tool_name") or action.get("action") or "")
            args = action.get("args") or action.get("arguments") or action.get("kwargs") or {}
            if not isinstance(args, dict):
                args = {}
            trace_logger.log_event(
                task_id=task.task_id,
                step=step,
                event_type="scripted_action",
                payload={
                    "tool_name": tool_name,
                    "tool_args": args,
                    "expected_action_id": action.get("action_id"),
                    "action_source": "metadata.expected_actions",
                    "used_memory_ids": [memory.memory_id for memory in memories or []],
                },
            )
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
                    "expected_action_id": action.get("action_id"),
                    "action_source": "metadata.expected_actions",
                },
            )

        if len(expected_actions) > self.max_steps:
            error_type = "max_steps_exceeded"

        final_answer = self._final_answer(task=task, observations=observations)
        success, reward, eval_error = env.evaluate(task, final_answer)
        evaluation_details = getattr(env, "last_evaluation_detail", {})
        if not isinstance(evaluation_details, dict):
            evaluation_details = {}

        return AgentResult(
            task_id=task.task_id,
            success=success,
            reward=reward,
            final_answer=final_answer,
            num_steps=min(len(expected_actions), self.max_steps) + 1,
            prompt_tokens=0,
            completion_tokens=0,
            tool_calls=tool_calls,
            used_memory_ids=tuple(memory.memory_id for memory in memories or []),
            trace_summary=tuple(trace_summary),
            error_type=error_type or eval_error,
            evaluation_details=dict(evaluation_details),
        )

    def _final_answer(self, task: Task, observations: list[str]) -> str:
        communicate_info = _string_list(task.metadata.get("communicate_info"))
        nl_assertions = _string_list(task.metadata.get("nl_assertions"))
        if communicate_info:
            joined = "; ".join(communicate_info)
            if nl_assertions:
                return f"Communicated required information: {joined}. {self._nl_hint(nl_assertions)}"
            return f"Communicated required information: {joined}."
        if nl_assertions:
            return self._nl_hint(nl_assertions)
        if observations:
            return observations[-1]
        return "Completed scripted expected actions."

    def _nl_hint(self, nl_assertions: list[str]) -> str:
        # Keep the answer deterministic and auditable; do not try to solve
        # arbitrary natural-language assertions with a hidden judge.
        return " ".join(assertion.rstrip(".") + "." for assertion in nl_assertions)


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]
