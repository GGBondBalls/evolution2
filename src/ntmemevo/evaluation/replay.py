from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable, Literal

from ntmemevo.agents.react_agent import ReActToolAgent
from ntmemevo.envs.base import AgentEnv
from ntmemevo.types import AgentResult, RetrievedMemory, Task


AttributionLabel = Literal["helpful", "harmful", "neutral", "context"]
ReplayScope = Literal["source_task_replay", "support_task_replay"]
ReplayMode = Literal[
    "with_selected_memory",
    "without_selected_memory",
    "leave_one_memory_out",
    "support_task_replay",
]


@dataclass(frozen=True)
class ReplayConfig:
    enabled: bool = False
    delta_threshold: float = 0.0
    max_memories: int | None = None
    log_context_modes: bool = True
    promote_requires_positive_lcb: bool = True
    prompt_token_cost_weight: float = 0.0
    tool_call_cost_weight: float = 0.0

    @classmethod
    def from_config(cls, data: dict[str, Any] | None) -> "ReplayConfig":
        data = data or {}
        max_memories = data.get("max_memories")
        return cls(
            enabled=bool(data.get("enabled", False)),
            delta_threshold=float(data.get("delta_threshold", 0.0)),
            max_memories=int(max_memories) if max_memories is not None else None,
            log_context_modes=bool(data.get("log_context_modes", True)),
            promote_requires_positive_lcb=bool(
                data.get("promote_requires_positive_lcb", True)
            ),
            prompt_token_cost_weight=float(data.get("prompt_token_cost_weight", 0.0)),
            tool_call_cost_weight=float(data.get("tool_call_cost_weight", 0.0)),
        )


@dataclass(frozen=True)
class ReplayResult:
    replay_id: str
    source_run_id: str
    task_id: str
    memory_id: str | None
    mode: ReplayMode
    with_reward: float | None
    without_reward: float | None
    delta_reward: float | None
    cost_adjusted_delta_reward: float | None
    with_success: bool | None
    without_success: bool | None
    attribution_label: AttributionLabel
    with_used_memory_ids: tuple[str, ...]
    without_used_memory_ids: tuple[str, ...]
    replay_scope: ReplayScope = "source_task_replay"
    with_prompt_tokens: int | None = None
    without_prompt_tokens: int | None = None
    delta_prompt_tokens: int | None = None
    with_completion_tokens: int | None = None
    without_completion_tokens: int | None = None
    delta_completion_tokens: int | None = None
    with_tool_calls: int | None = None
    without_tool_calls: int | None = None
    delta_tool_calls: int | None = None
    with_execution_id: str | None = None
    without_execution_id: str | None = None

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["with_used_memory_ids"] = list(self.with_used_memory_ids)
        data["without_used_memory_ids"] = list(self.without_used_memory_ids)
        return data


class NullTraceLogger:
    def log_event(
        self,
        task_id: str,
        step: int,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        return None


def run_memory_replays(
    task: Task,
    agent: ReActToolAgent,
    env_factory: Callable[[], AgentEnv],
    source_run_id: str,
    selected_memories: list[RetrievedMemory],
    config: ReplayConfig,
) -> list[ReplayResult]:
    if not config.enabled or not selected_memories:
        return []

    max_memories = config.max_memories
    memories_for_attribution = (
        selected_memories[:max_memories] if max_memories is not None else selected_memories
    )
    replay_results: list[ReplayResult] = []
    replay_cache: dict[tuple[str, ...], AgentResult] = {}

    def next_replay_id() -> str:
        return f"{source_run_id}_replay_{len(replay_results) + 1:03d}"

    selected_ids = tuple(memory.memory_id for memory in selected_memories)
    with_all_execution_id = _execution_id(
        source_run_id=source_run_id,
        task_id=task.task_id,
        replay_scope="source_task_replay",
        memory_ids=selected_ids,
    )
    without_all_execution_id = _execution_id(
        source_run_id=source_run_id,
        task_id=task.task_id,
        replay_scope="source_task_replay",
        memory_ids=(),
    )
    with_all_result = _run_replay(
        task=task,
        agent=agent,
        env_factory=env_factory,
        memories=selected_memories,
    )
    replay_cache[selected_ids] = with_all_result
    without_all_result = _run_replay(
        task=task,
        agent=agent,
        env_factory=env_factory,
        memories=[],
    )
    replay_cache[()] = without_all_result

    if config.log_context_modes:
        replay_results.append(
            ReplayResult(
                replay_id=next_replay_id(),
                source_run_id=source_run_id,
                task_id=task.task_id,
                memory_id=None,
                mode="with_selected_memory",
                replay_scope="source_task_replay",
                with_reward=_round_reward(with_all_result.reward),
                without_reward=None,
                delta_reward=None,
                cost_adjusted_delta_reward=None,
                with_success=with_all_result.success,
                without_success=None,
                attribution_label="context",
                with_used_memory_ids=with_all_result.used_memory_ids,
                without_used_memory_ids=(),
                with_prompt_tokens=with_all_result.prompt_tokens,
                with_completion_tokens=with_all_result.completion_tokens,
                with_tool_calls=with_all_result.tool_calls,
                with_execution_id=with_all_execution_id,
            )
        )
        replay_results.append(
            _build_comparison_result(
                replay_id=next_replay_id(),
                source_run_id=source_run_id,
                task=task,
                memory_id=None,
                mode="without_selected_memory",
                with_result=with_all_result,
                without_result=without_all_result,
                threshold=config.delta_threshold,
                prompt_token_cost_weight=config.prompt_token_cost_weight,
                tool_call_cost_weight=config.tool_call_cost_weight,
                with_execution_id=with_all_execution_id,
                without_execution_id=without_all_execution_id,
            )
        )

    for memory in memories_for_attribution:
        leave_one_memories = [
            candidate
            for candidate in selected_memories
            if candidate.memory_id != memory.memory_id
        ]
        leave_one_ids = tuple(candidate.memory_id for candidate in leave_one_memories)
        leave_one_execution_id = _execution_id(
            source_run_id=source_run_id,
            task_id=task.task_id,
            replay_scope="source_task_replay",
            memory_ids=leave_one_ids,
        )
        without_result = replay_cache.get(leave_one_ids)
        if without_result is None:
            without_result = _run_replay(
                task=task,
                agent=agent,
                env_factory=env_factory,
                memories=leave_one_memories,
            )
            replay_cache[leave_one_ids] = without_result
        replay_results.append(
            _build_comparison_result(
                replay_id=next_replay_id(),
                source_run_id=source_run_id,
                task=task,
                memory_id=memory.memory_id,
                mode="leave_one_memory_out",
                with_result=with_all_result,
                without_result=without_result,
                threshold=config.delta_threshold,
                prompt_token_cost_weight=config.prompt_token_cost_weight,
                tool_call_cost_weight=config.tool_call_cost_weight,
                with_execution_id=with_all_execution_id,
                without_execution_id=leave_one_execution_id,
            )
        )

    return replay_results


def _run_replay(
    task: Task,
    agent: ReActToolAgent,
    env_factory: Callable[[], AgentEnv],
    memories: list[RetrievedMemory],
) -> AgentResult:
    return agent.run(
        task=task,
        env=env_factory(),
        trace_logger=NullTraceLogger(),  # type: ignore[arg-type]
        memories=memories,
    )


def _build_comparison_result(
    replay_id: str,
    source_run_id: str,
    task: Task,
    memory_id: str | None,
    mode: ReplayMode,
    with_result: AgentResult,
    without_result: AgentResult,
    threshold: float,
    replay_scope: ReplayScope = "source_task_replay",
    prompt_token_cost_weight: float = 0.0,
    tool_call_cost_weight: float = 0.0,
    with_execution_id: str | None = None,
    without_execution_id: str | None = None,
) -> ReplayResult:
    delta_reward = _round_reward(with_result.reward - without_result.reward)
    delta_prompt_tokens = with_result.prompt_tokens - without_result.prompt_tokens
    delta_completion_tokens = (
        with_result.completion_tokens - without_result.completion_tokens
    )
    delta_tool_calls = with_result.tool_calls - without_result.tool_calls
    cost_adjusted_delta_reward = _cost_adjusted_delta_reward(
        delta_reward=delta_reward,
        delta_prompt_tokens=delta_prompt_tokens,
        delta_tool_calls=delta_tool_calls,
        prompt_token_cost_weight=prompt_token_cost_weight,
        tool_call_cost_weight=tool_call_cost_weight,
    )
    return ReplayResult(
        replay_id=replay_id,
        source_run_id=source_run_id,
        task_id=task.task_id,
        memory_id=memory_id,
        mode=mode,
        replay_scope=replay_scope,
        with_reward=_round_reward(with_result.reward),
        without_reward=_round_reward(without_result.reward),
        delta_reward=delta_reward,
        cost_adjusted_delta_reward=cost_adjusted_delta_reward,
        with_success=with_result.success,
        without_success=without_result.success,
        attribution_label=_attribution_label(delta_reward, threshold),
        with_used_memory_ids=with_result.used_memory_ids,
        without_used_memory_ids=without_result.used_memory_ids,
        with_prompt_tokens=with_result.prompt_tokens,
        without_prompt_tokens=without_result.prompt_tokens,
        delta_prompt_tokens=delta_prompt_tokens,
        with_completion_tokens=with_result.completion_tokens,
        without_completion_tokens=without_result.completion_tokens,
        delta_completion_tokens=delta_completion_tokens,
        with_tool_calls=with_result.tool_calls,
        without_tool_calls=without_result.tool_calls,
        delta_tool_calls=delta_tool_calls,
        with_execution_id=with_execution_id,
        without_execution_id=without_execution_id,
    )


def _execution_id(
    source_run_id: str,
    task_id: str,
    replay_scope: ReplayScope,
    memory_ids: tuple[str, ...],
) -> str:
    memory_suffix = ",".join(memory_ids) if memory_ids else "no_memory"
    return f"{source_run_id}:{replay_scope}:{task_id}:{memory_suffix}"


def _attribution_label(delta_reward: float, threshold: float) -> AttributionLabel:
    if delta_reward > threshold:
        return "helpful"
    if delta_reward < -threshold:
        return "harmful"
    return "neutral"


def _round_reward(value: float) -> float:
    return round(max(-1.0, min(1.0, float(value))), 6)


def _cost_adjusted_delta_reward(
    delta_reward: float,
    delta_prompt_tokens: int,
    delta_tool_calls: int,
    prompt_token_cost_weight: float,
    tool_call_cost_weight: float,
) -> float:
    prompt_penalty = prompt_token_cost_weight * max(0, delta_prompt_tokens) / 1000.0
    tool_penalty = tool_call_cost_weight * max(0, delta_tool_calls)
    return _round_reward(delta_reward - prompt_penalty - tool_penalty)
