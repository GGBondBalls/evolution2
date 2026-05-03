from __future__ import annotations

import json
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
    ) -> None:
        self.llm = llm
        self.model_config = model_config
        self.max_steps = max_steps
        self.memory_top_k = memory_top_k

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

            try:
                decision = json.loads(response.content)
            except json.JSONDecodeError:
                final_answer = response.content
                error_type = "invalid_json_response"
                trace_logger.log_event(
                    task_id=task.task_id,
                    step=step,
                    event_type="model_parse_error",
                    payload={"raw_response": response.content},
                )
                break

            action = str(decision.get("action", "")).lower()
            trace_logger.log_event(
                task_id=task.task_id,
                step=step,
                event_type="model_decision",
                payload={
                    "thought_summary": decision.get("thought", ""),
                    "action": action,
                    "tool_name": decision.get("tool_name"),
                    "used_memory_ids": [memory.memory_id for memory in memories],
                },
            )

            if action == "final":
                final_answer = str(decision.get("answer", ""))
                break

            if action != "tool":
                final_answer = f"Unsupported action: {action}"
                error_type = "unsupported_action"
                break

            tool_name = str(decision.get("tool_name", ""))
            args = decision.get("args", {})
            if not isinstance(args, dict):
                args = {}
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
                "Return a JSON object. Use either:",
                '{"action":"tool","tool_name":"name","args":{...}}',
                'or {"action":"final","answer":"..."}',
            ]
        )
        user = "\n".join(user_lines)
        return [
            ChatMessage(
                role="system",
                content=(
                    "You are a careful tool-using agent. "
                    "Call tools when needed and answer only when observations are sufficient."
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
