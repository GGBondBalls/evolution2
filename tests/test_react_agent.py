from __future__ import annotations

from typing import Any

from ntmemevo.agents.react_agent import ReActToolAgent
from ntmemevo.envs.base import AgentEnv
from ntmemevo.llm.client import LLMClient
from ntmemevo.types import ChatMessage, LLMResponse, LLMUsage, Task, ToolResult


class _SequenceLLM(LLMClient):
    def __init__(self, responses: list[str], completion_tokens: int = 5) -> None:
        self.responses = list(responses)
        self.completion_tokens = completion_tokens
        self.response_formats: list[dict[str, Any] | None] = []
        self.message_history: list[list[ChatMessage]] = []

    def complete(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.0,
        max_tokens: int = 1024,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        del temperature, max_tokens
        self.response_formats.append(response_format)
        self.message_history.append(list(messages))
        if not self.responses:
            raise AssertionError("No fake LLM responses remain.")
        content = self.responses.pop(0)
        return LLMResponse(
            content=content,
            model="fake-model",
            usage=LLMUsage(
                prompt_tokens=10,
                completion_tokens=self.completion_tokens,
                total_tokens=10 + self.completion_tokens,
            ),
        )


class _OneToolEnv(AgentEnv):
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.complete_after_calls: int | None = None

    def load_tasks(self, max_tasks: int | None = None) -> list[Task]:
        return []

    def tool_descriptions(self) -> str:
        return "get_order_status(order_id: str) -> order status"

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> ToolResult:
        self.calls.append((tool_name, args))
        return ToolResult(
            tool_name=tool_name,
            args=args,
            observation=f"Order {args.get('order_id')} status is delivered.",
            ok=True,
        )

    def evaluate(self, task: Task, final_answer: str) -> tuple[bool, float, str | None]:
        success = "delivered" in final_answer.lower()
        return success, 1.0 if success else 0.0, None if success else "expected_answer_mismatch"

    def expected_actions_completed(self, task: Task) -> bool:
        del task
        return self.complete_after_calls is not None and len(self.calls) >= self.complete_after_calls


class _CapturingTraceLogger:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def log_event(
        self,
        task_id: str,
        step: int,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        self.events.append(
            {
                "task_id": task_id,
                "step": step,
                "event_type": event_type,
                **payload,
            }
        )


def _task() -> Task:
    return Task(
        task_id="repair_task_001",
        instruction="Find the delivery status for order ORD-1001.",
        expected_answer_contains=("delivered",),
    )


def test_react_agent_keeps_valid_tool_action_unchanged() -> None:
    raw_tool_response = (
        '{"thought":"Need order status.","action":"tool",'
        '"tool_name":"get_order_status","args":{"order_id":"ORD-1001"}}'
    )
    llm = _SequenceLLM(
        [
            raw_tool_response,
            '{"thought":"Observation is enough.","action":"final","answer":"Order ORD-1001 is delivered."}',
        ]
    )
    env = _OneToolEnv()
    trace_logger = _CapturingTraceLogger()
    result = ReActToolAgent(
        llm=llm,
        model_config={},
        max_steps=4,
        log_raw_model_io=True,
    ).run(task=_task(), env=env, trace_logger=trace_logger)

    decisions = [event for event in trace_logger.events if event["event_type"] == "model_decision"]

    assert result.success is True
    assert env.calls == [("get_order_status", {"order_id": "ORD-1001"})]
    assert not any(event["event_type"] == "model_action_repair" for event in trace_logger.events)
    assert decisions[0]["action"] == "tool"
    assert decisions[0]["tool_name"] == "get_order_status"
    assert decisions[0]["repair_status"] == "not_needed"
    assert decisions[0]["raw_response"] == raw_tool_response
    assert llm.response_formats[0] == {"type": "json_object"}
    assert "Keep thought empty or under 8 words." in llm.message_history[0][1].content


def test_react_agent_repairs_missing_action_when_tool_fields_are_present() -> None:
    raw_tool_response = (
        '{"thought":"Need order status.","tool":"get_order_status",'
        '"arguments":{"order_id":"ORD-1001"}}'
    )
    llm = _SequenceLLM(
        [
            raw_tool_response,
            '{"thought":"Observation is enough.","action":"final","answer":"Order ORD-1001 is delivered."}',
        ]
    )
    env = _OneToolEnv()
    trace_logger = _CapturingTraceLogger()
    result = ReActToolAgent(
        llm=llm,
        model_config={},
        max_steps=4,
        log_raw_model_io=True,
    ).run(task=_task(), env=env, trace_logger=trace_logger)

    repair_events = [
        event for event in trace_logger.events if event["event_type"] == "model_action_repair"
    ]
    decisions = [event for event in trace_logger.events if event["event_type"] == "model_decision"]

    assert result.success is True
    assert env.calls == [("get_order_status", {"order_id": "ORD-1001"})]
    assert len(repair_events) == 1
    assert repair_events[0]["repair_reason"] == "missing_action_with_arguments"
    assert repair_events[0]["action_before"] == ""
    assert repair_events[0]["action_after"] == "tool"
    assert repair_events[0]["tool_name"] == "get_order_status"
    assert repair_events[0]["raw_response"] == raw_tool_response
    assert decisions[0]["action"] == "tool"
    assert decisions[0]["tool_name"] == "get_order_status"
    assert decisions[0]["repair_status"] == "repaired"
    assert decisions[0]["repair_reason"] == "missing_action_with_arguments"


def test_react_agent_logs_unrepairable_missing_action_raw_response() -> None:
    raw_response = '{"thought":"I should call get_order_status next."}'
    llm = _SequenceLLM([raw_response])
    env = _OneToolEnv()
    trace_logger = _CapturingTraceLogger()
    result = ReActToolAgent(
        llm=llm,
        model_config={},
        max_steps=4,
        log_raw_model_io=True,
    ).run(task=_task(), env=env, trace_logger=trace_logger)

    decisions = [event for event in trace_logger.events if event["event_type"] == "model_decision"]

    assert result.success is False
    assert result.error_type == "unsupported_action"
    assert result.final_answer == "Unsupported action: "
    assert env.calls == []
    assert not any(event["event_type"] == "model_action_repair" for event in trace_logger.events)
    assert decisions[0]["action"] == ""
    assert decisions[0]["repair_status"] == "unrepairable"
    assert decisions[0]["repair_reason"] == "missing_action_without_tool_fields"
    assert decisions[0]["raw_response"] == raw_response
    assert decisions[0]["parsed_decision"] == {"thought": "I should call get_order_status next."}


def test_react_agent_can_stop_after_expected_actions_complete() -> None:
    llm = _SequenceLLM(
        [
            (
                '{"thought":"Need order status.","action":"tool",'
                '"tool_name":"get_order_status","args":{"order_id":"ORD-1001"}}'
            ),
            (
                '{"thought":"This should not be called.","action":"tool",'
                '"tool_name":"lookup_policy","args":{"policy_name":"exchange"}}'
            ),
        ]
    )
    env = _OneToolEnv()
    env.complete_after_calls = 1
    trace_logger = _CapturingTraceLogger()
    result = ReActToolAgent(
        llm=llm,
        model_config={},
        max_steps=4,
        stop_after_expected_actions=True,
    ).run(task=_task(), env=env, trace_logger=trace_logger)

    assert result.success is True
    assert result.num_steps == 2
    assert result.tool_calls == 1
    assert env.calls == [("get_order_status", {"order_id": "ORD-1001"})]
    assert len(llm.responses) == 1
    assert any(
        event["event_type"] == "expected_actions_complete"
        for event in trace_logger.events
    )


def test_react_agent_can_request_json_schema_response_format() -> None:
    llm = _SequenceLLM(
        ['{"action":"final","answer":"Order ORD-1001 is delivered."}']
    )
    env = _OneToolEnv()
    trace_logger = _CapturingTraceLogger()

    result = ReActToolAgent(
        llm=llm,
        model_config={"response_format": "json_schema"},
        max_steps=4,
    ).run(task=_task(), env=env, trace_logger=trace_logger)

    response_format = llm.response_formats[0]
    assert result.success is True
    assert response_format is not None
    assert response_format["type"] == "json_schema"
    schema = response_format["json_schema"]["schema"]
    assert schema["properties"]["action"]["enum"] == ["tool", "final"]
    assert schema["properties"]["thought"]["maxLength"] == 80


def test_react_agent_classifies_token_budget_truncated_json() -> None:
    raw_response = '{"thought":"I will copy a very long observation and never close'
    llm = _SequenceLLM([raw_response], completion_tokens=100)
    env = _OneToolEnv()
    trace_logger = _CapturingTraceLogger()

    result = ReActToolAgent(
        llm=llm,
        model_config={"max_tokens": 100},
        max_steps=4,
        log_raw_model_io=True,
    ).run(task=_task(), env=env, trace_logger=trace_logger)

    parse_errors = [
        event for event in trace_logger.events if event["event_type"] == "model_parse_error"
    ]
    assert result.success is False
    assert result.error_type == "truncated_json_response"
    assert len(parse_errors) == 1
    assert parse_errors[0]["error_type"] == "truncated_json_response"
    assert parse_errors[0]["parse_error"] == "truncated_json_response"
    assert parse_errors[0]["starts_with_json_object"] is True
    assert parse_errors[0]["unclosed_json_object"] is True
    assert parse_errors[0]["token_budget_hit"] is True
