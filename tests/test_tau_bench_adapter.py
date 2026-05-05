from __future__ import annotations

import json
from pathlib import Path

import pytest

from ntmemevo.envs.tau_bench import TauBenchEnv
from ntmemevo.experiments.run_stream import run
from ntmemevo.types import Task


def _write_tau_retail_config(
    config_path: Path,
    output_dir: Path,
    experiment_name: str,
    memory_top_k: int,
    memory_block: str = "",
) -> None:
    split_file = Path("data/task_splits/tau_retail_smoke_tasks.json").resolve()
    data_file = Path("data/tau_bench/retail_smoke_db.json").resolve()
    memory_section = f"\nmemory:\n{memory_block}\n" if memory_block else ""
    config_path.write_text(
        f"""
experiment:
  name: {experiment_name}
  seed: 1
  output_dir: {output_dir.as_posix()}
benchmark:
  name: tau_bench
  domain: retail
  split_file: {split_file.as_posix()}
  data_file: {data_file.as_posix()}
  evaluation: auto
  max_tasks: 3
agent:
  type: react_tool_agent
  max_steps: 4
  memory_top_k: {memory_top_k}
models:
  actor:
    provider: mock
    model: mock-tool-agent
    temperature: 0.0
    max_tokens: 2048
{memory_section}logging:
  save_raw_model_io: true
  save_trace_events: true
  save_costs: true
""",
        encoding="utf-8",
    )


def _write_tau_retail_phase2_config(
    config_path: Path,
    output_dir: Path,
    experiment_name: str,
    memory_block: str = "",
) -> None:
    split_file = Path("data/task_splits/tau_retail_phase2_state_tasks.py").resolve()
    data_dir = Path("data/tau_bench/retail_phase2_state").resolve()
    memory_section = f"\nmemory:\n{memory_block}\n" if memory_block else ""
    config_path.write_text(
        f"""
experiment:
  name: {experiment_name}
  seed: 1
  output_dir: {output_dir.as_posix()}
benchmark:
  name: tau_bench
  domain: retail
  split_file: {split_file.as_posix()}
  data_dir: {data_dir.as_posix()}
  evaluation: official_like
  compare_action_args: true
  require_data: true
  validate_export_schema: true
  max_tasks: 3
agent:
  type: react_tool_agent
  max_steps: 4
  memory_top_k: 2
models:
  actor:
    provider: mock
    model: mock-tool-agent
    temperature: 0.0
    max_tokens: 2048
{memory_section}logging:
  save_raw_model_io: true
  save_trace_events: true
  save_costs: true
""",
        encoding="utf-8",
    )


def test_tau_retail_smoke_adapter_runs(tmp_path: Path) -> None:
    config_path = tmp_path / "tau_retail_smoke.yaml"
    output_dir = tmp_path / "runs" / "tau_retail"
    _write_tau_retail_config(
        config_path=config_path,
        output_dir=output_dir,
        experiment_name="tau_retail_smoke_test",
        memory_top_k=0,
    )

    metrics = run(str(config_path))

    assert metrics["num_tasks"] == 3
    assert metrics["success_rate"] == 1.0
    assert metrics["memory_policy"] == "none"
    assert metrics["memory_size"] == 0

    task_records = [
        json.loads(line)
        for line in (output_dir / "tasks.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    run_records = [
        json.loads(line)
        for line in (output_dir / "runs.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    trace_records = [
        json.loads(line)
        for line in (output_dir / "trace_events.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]

    assert {record["metadata"]["benchmark"] for record in task_records} == {"tau_bench"}
    assert {record["metadata"]["domain"] for record in task_records} == {"retail"}
    assert all(record["success"] for record in run_records)
    assert any(
        record.get("tool_name") == "find_user_id_by_name_zip"
        for record in trace_records
        if record["event_type"] == "tool_call"
    )
    assert any(
        record.get("tool_name") == "get_order_details"
        for record in trace_records
        if record["event_type"] == "tool_call"
    )
    assert any(
        record.get("tool_name") == "get_product_details"
        for record in trace_records
        if record["event_type"] == "tool_call"
    )


@pytest.mark.parametrize(
    ("memory_policy", "memory_top_k", "memory_block", "memory_file"),
    [
        (
            "raw_trace_rag",
            2,
            "  method: raw_trace_rag\n  top_k: 2\n  save_failures: true",
            "memories.jsonl",
        ),
        (
            "reflexion",
            2,
            (
                "  method: reflexion\n"
                "  top_k: 2\n"
                "  save_successes: true\n"
                "  save_failures: true\n"
                "  max_reflection_chars: 700"
            ),
            "memories.jsonl",
        ),
        (
            "nt_memevo_candidate",
            0,
            (
                "  method: nt_memevo_candidate\n"
                "  top_k: 0\n"
                "  save_successes: true\n"
                "  save_failures: true\n"
                "  extractor_model: deterministic_candidate_extractor_v1\n"
                "  domain: retail\n"
                "  ttl: 50"
            ),
            "candidate_memories.jsonl",
        ),
    ],
)
def test_tau_retail_memory_baselines_write_expected_logs(
    tmp_path: Path,
    memory_policy: str,
    memory_top_k: int,
    memory_block: str,
    memory_file: str,
) -> None:
    config_path = tmp_path / f"tau_retail_{memory_policy}.yaml"
    output_dir = tmp_path / "runs" / memory_policy
    _write_tau_retail_config(
        config_path=config_path,
        output_dir=output_dir,
        experiment_name=f"tau_retail_{memory_policy}_test",
        memory_top_k=memory_top_k,
        memory_block=memory_block,
    )

    metrics = run(str(config_path))

    assert metrics["num_tasks"] == 3
    assert metrics["success_rate"] == 1.0
    assert metrics["memory_policy"] == memory_policy
    assert metrics["memory_size"] == 3

    memory_records = [
        json.loads(line)
        for line in (output_dir / memory_file).read_text(encoding="utf-8").strip().splitlines()
    ]
    update_records = [
        json.loads(line)
        for line in (output_dir / "memory_updates.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    run_records = [
        json.loads(line)
        for line in (output_dir / "runs.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]

    assert len(memory_records) == 3
    assert len(run_records) == 3
    assert all(record["success"] for record in run_records)

    if memory_policy == "nt_memevo_candidate":
        assert metrics["memory_top_k"] == 0
        assert {record["scope"]["intent"] for record in memory_records} == {
            "customer_lookup",
            "order_lookup",
            "product_lookup",
        }
        assert all(record["scope"]["domain"] == "retail" for record in memory_records)
        assert all(record["type"] == "tool_usage" for record in memory_records)
        assert all(record["used_memory_ids"] == [] for record in run_records)
        assert all(record["event_type"] == "candidate_extract" for record in update_records)
    else:
        assert metrics["memory_top_k"] == 2
        assert any(record["event_type"] == "retrieve" for record in update_records)
        assert any(record["event_type"] == "add" for record in update_records)


def test_tau_retail_nt_memevo_gate_logs_cross_intent_rejections(tmp_path: Path) -> None:
    config_path = tmp_path / "tau_retail_gate.yaml"
    output_dir = tmp_path / "runs" / "gate"
    _write_tau_retail_config(
        config_path=config_path,
        output_dir=output_dir,
        experiment_name="tau_retail_gate_test",
        memory_top_k=2,
        memory_block=(
            "  method: nt_memevo_gate\n"
            "  top_k: 2\n"
            "  save_successes: true\n"
            "  save_failures: true\n"
            "  extractor_model: deterministic_candidate_extractor_v1\n"
            "  domain: retail\n"
            "  ttl: 50\n"
            "  gate:\n"
            "    min_score: 0.30\n"
            "    min_similarity: 0.02\n"
            "    min_precondition: 0.25\n"
            "    max_risk: 0.65\n"
            "    reject_negative_evidence: true\n"
            "    allowed_statuses: [\"candidate\", \"active\"]"
        ),
    )

    metrics = run(str(config_path))

    assert metrics["num_tasks"] == 3
    assert metrics["success_rate"] == 1.0
    assert metrics["memory_policy"] == "nt_memevo_gate"
    assert metrics["memory_size"] == 3
    assert metrics["gate_decision_count"] == 3
    assert metrics["gate_accepted_count"] == 0
    assert metrics["gate_rejected_count"] == 3
    assert metrics["utility_update_count"] == 0
    assert metrics["candidate_memory_count"] == 3

    candidate_records = [
        json.loads(line)
        for line in (output_dir / "candidate_memories.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    run_records = [
        json.loads(line)
        for line in (output_dir / "runs.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    update_records = [
        json.loads(line)
        for line in (output_dir / "memory_updates.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    gate_records = [
        record for record in update_records if record.get("event_type") == "gate_decision"
    ]

    assert {record["scope"]["intent"] for record in candidate_records} == {
        "customer_lookup",
        "order_lookup",
        "product_lookup",
    }
    assert all(record["used_memory_ids"] == [] for record in run_records)
    assert len(gate_records) == 3
    assert all(record["gate_decision"] == "reject" for record in gate_records)
    assert all(record["rejection_reason"] for record in gate_records)
    assert any(record["event_type"] == "retrieve" for record in update_records)
    assert any(record["event_type"] == "candidate_extract" for record in update_records)


def test_tau_retail_export_sample_loads_python_tasks_and_data_dir() -> None:
    env = TauBenchEnv(
        {
            "domain": "retail",
            "split_file": "data/task_splits/tau_retail_export_sample_tasks.py",
            "data_dir": "data/tau_bench/retail_export_sample",
            "evaluation": "auto",
            "require_data": True,
            "validate_export_schema": True,
        }
    )

    tasks = env.load_tasks(max_tasks=3)

    assert [task.task_id for task in tasks] == [
        "tau_retail_0001",
        "tau_retail_0002",
        "tau_retail_0003",
    ]
    assert [task.metadata["intent"] for task in tasks] == [
        "customer_lookup",
        "order_lookup",
        "product_lookup",
    ]

    user_result = env.call_tool(
        "find_user_id_by_name_zip",
        {"first_name": "Yusuf", "last_name": "Rossi", "zip": "19122"},
    )
    order_result = env.call_tool("get_order_details", {"order_id": "W2378156"})

    assert user_result.ok
    assert "user_id=user_1" in user_result.observation
    assert order_result.ok
    assert "#W2378156" in order_result.observation


def test_tau2_official_nested_task_format_loads_and_filters(tmp_path: Path) -> None:
    tasks_path = tmp_path / "official_tasks.json"
    split_path = tmp_path / "official_splits.json"
    tasks_path.write_text(
        json.dumps(
            [
                {
                    "id": "0",
                    "user_scenario": {
                        "instructions": {
                            "task_instructions": "Be concise.",
                            "domain": "retail",
                            "reason_for_call": "Look up the details for order #READ1001.",
                            "known_info": "You are Mira Chen.",
                            "unknown_info": "You do not know anything else.",
                        }
                    },
                    "evaluation_criteria": {
                        "actions": [
                            {
                                "action_id": "0_0",
                                "name": "get_order_details",
                                "arguments": {"order_id": "#READ1001"},
                            }
                        ],
                        "communicate_info": [],
                        "nl_assertions": None,
                        "reward_basis": ["DB"],
                    },
                },
                {
                    "id": "1",
                    "user_scenario": {
                        "instructions": {
                            "reason_for_call": "This task should be filtered out.",
                            "known_info": "No relevant info.",
                        }
                    },
                    "evaluation_criteria": {
                        "actions": [
                            {
                                "name": "get_order_details",
                                "arguments": {"order_id": "#PEND2001"},
                            }
                        ],
                        "reward_basis": ["DB"],
                    },
                },
            ]
        ),
        encoding="utf-8",
    )
    split_path.write_text(json.dumps({"base": ["0"], "test": ["1"]}), encoding="utf-8")

    env = TauBenchEnv(
        {
            "domain": "retail",
            "split_file": str(tasks_path),
            "task_split_file": str(split_path),
            "task_split": "base",
            "data_dir": "data/tau_bench/retail_phase2_state",
            "evaluation": "official_like",
            "compare_action_args": True,
            "require_data": True,
            "validate_export_schema": True,
        }
    )

    tasks = env.load_tasks()

    assert [task.task_id for task in tasks] == ["0"]
    assert "Customer request: Look up the details for order #READ1001." in tasks[0].instruction
    assert tasks[0].metadata["source_format"] == "tau2_official"
    assert tasks[0].metadata["no_memory_success"] is False
    assert tasks[0].metadata["expected_actions"] == [
        {
            "name": "get_order_details",
            "args": {"order_id": "#READ1001"},
            "action_id": "0_0",
            "info": None,
            "optional_args": [],
            "ignore_args": [],
        }
    ]
    assert tasks[0].metadata["communicate_info"] == []
    assert tasks[0].metadata["nl_assertions"] == []


def test_tau2_official_nested_task_config_runs_with_official_like_evaluator(tmp_path: Path) -> None:
    tasks_path = tmp_path / "official_tasks.json"
    split_path = tmp_path / "official_splits.json"
    tasks_path.write_text(
        json.dumps(
            [
                {
                    "id": "0",
                    "user_scenario": {
                        "instructions": {
                            "task_instructions": "Be concise.",
                            "domain": "retail",
                            "reason_for_call": "Look up the details for order #READ1001.",
                            "known_info": "You are Mira Chen.",
                            "unknown_info": "You do not know anything else.",
                        }
                    },
                    "evaluation_criteria": {
                        "actions": [
                            {
                                "name": "get_order_details",
                                "arguments": {"order_id": "#READ1001"},
                            }
                        ],
                        "communicate_info": [],
                        "nl_assertions": None,
                        "reward_basis": ["DB"],
                    },
                }
            ]
        ),
        encoding="utf-8",
    )
    split_path.write_text(json.dumps({"base": ["0"]}), encoding="utf-8")

    output_dir = tmp_path / "runs" / "official_nested"
    config_path = tmp_path / "official_nested.yaml"
    config_path.write_text(
        f"""
experiment:
  name: official_nested_test
  seed: 1
  output_dir: {output_dir.as_posix()}
benchmark:
  name: tau_bench
  domain: retail
  split_file: {tasks_path.as_posix()}
  task_split_file: {split_path.as_posix()}
  task_split: base
  data_dir: data/tau_bench/retail_phase2_state
  evaluation: official_like
  compare_action_args: true
  require_data: true
  validate_export_schema: true
  max_tasks: 1
agent:
  type: react_tool_agent
  max_steps: 4
  memory_top_k: 0
models:
  actor:
    provider: mock
    model: mock-tool-agent
    temperature: 0.0
    max_tokens: 2048
logging:
  save_raw_model_io: true
  save_trace_events: true
  save_costs: true
""",
        encoding="utf-8",
    )

    metrics = run(str(config_path))

    assert metrics["num_tasks"] == 1
    assert metrics["success_rate"] == 1.0
    assert metrics["evaluation_modes"] == {"official_like": 1}
    assert metrics["expected_actions_matched_count"] == 1

    run_record = json.loads((output_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert run_record["evaluation_details"]["expected_actions_matched"] is True
    assert run_record["evaluation_details"]["action_args_compared"] is True


def test_tau2_action_replay_agent_executes_expected_actions_and_nl_checks(tmp_path: Path) -> None:
    tasks_path = tmp_path / "official_action_replay_tasks.json"
    split_path = tmp_path / "official_action_replay_splits.json"
    tasks_path.write_text(
        json.dumps(
            [
                {
                    "id": "0",
                    "user_scenario": {
                        "instructions": {
                            "task_instructions": "Be concise.",
                            "domain": "retail",
                            "reason_for_call": "Look up the details for order #READ1001 and report the count.",
                            "known_info": "You are Mira Chen.",
                            "unknown_info": "",
                        }
                    },
                    "evaluation_criteria": {
                        "actions": [
                            {
                                "action_id": "0_0",
                                "name": "get_order_details",
                                "arguments": {"order_id": "#READ1001"},
                            }
                        ],
                        "communicate_info": ["10"],
                        "nl_assertions": [
                            "Agent should tell the user that there are 10 t-shirt options available."
                        ],
                        "reward_basis": ["DB", "NL_ASSERTION"],
                    },
                }
            ]
        ),
        encoding="utf-8",
    )
    split_path.write_text(json.dumps({"base": ["0"]}), encoding="utf-8")

    output_dir = tmp_path / "runs" / "official_action_replay"
    config_path = tmp_path / "official_action_replay.yaml"
    config_path.write_text(
        f"""
experiment:
  name: official_action_replay_test
  seed: 1
  output_dir: {output_dir.as_posix()}
benchmark:
  name: tau_bench
  domain: retail
  split_file: {tasks_path.as_posix()}
  task_split_file: {split_path.as_posix()}
  task_split: base
  data_dir: data/tau_bench/retail_phase2_state
  evaluation: official_like
  compare_action_args: true
  require_data: true
  validate_export_schema: true
  max_tasks: 1
agent:
  type: action_replay_agent
  max_steps: 4
  memory_top_k: 0
models:
  actor:
    provider: action_replay
    model: scripted-expected-actions
    temperature: 0.0
    max_tokens: 0
logging:
  save_raw_model_io: false
  save_trace_events: true
  save_costs: true
""",
        encoding="utf-8",
    )

    metrics = run(str(config_path))

    assert metrics["num_tasks"] == 1
    assert metrics["success_rate"] == 1.0
    assert metrics["expected_actions_matched_count"] == 1
    assert metrics["communicate_info_passed_count"] == 1
    assert metrics["nl_assertion_passed_count"] == 1
    assert metrics["unsupported_official_criteria_count"] == 0

    run_record = json.loads((output_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines()[0])
    trace_records = [
        json.loads(line)
        for line in (output_dir / "trace_events.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    assert run_record["agent"] == "action_replay_agent"
    assert run_record["tool_calls"] == 1
    assert "10" in run_record["final_answer"]
    assert run_record["evaluation_details"]["expected_actual_action_alignment"][0]["matched"] is True
    assert any(record["event_type"] == "scripted_action" for record in trace_records)


def test_tau_retail_env_reports_expected_actions_completed(tmp_path: Path) -> None:
    tasks_path = tmp_path / "official_expected_complete_tasks.json"
    split_path = tmp_path / "official_expected_complete_splits.json"
    tasks_path.write_text(
        json.dumps(
            [
                {
                    "id": "0",
                    "user_scenario": {
                        "instructions": {
                            "reason_for_call": "Look up the details for order #READ1001.",
                            "known_info": "You are Mira Chen.",
                        }
                    },
                    "evaluation_criteria": {
                        "actions": [
                            {
                                "action_id": "0_0",
                                "name": "get_order_details",
                                "arguments": {"order_id": "#READ1001"},
                            }
                        ],
                        "reward_basis": ["ACTION"],
                    },
                }
            ]
        ),
        encoding="utf-8",
    )
    split_path.write_text(json.dumps({"base": ["0"]}), encoding="utf-8")
    env = TauBenchEnv(
        {
            "domain": "retail",
            "split_file": str(tasks_path),
            "task_split_file": str(split_path),
            "task_split": "base",
            "data_dir": "data/tau_bench/retail_phase2_state",
            "evaluation": "official_like",
            "compare_action_args": True,
            "require_data": True,
            "validate_export_schema": True,
        }
    )
    task = env.load_tasks(max_tasks=1)[0]
    env.start_task(task)

    assert env.expected_actions_completed(task) is False

    result = env.call_tool("get_order_details", {"order_id": "#READ1001"})

    assert result.ok
    assert env.expected_actions_completed(task) is True


def test_tau2_expected_read_tool_error_is_classified_as_negative_observation(
    tmp_path: Path,
) -> None:
    tasks_path = tmp_path / "official_expected_negative_tasks.json"
    tasks_path.write_text(
        json.dumps(
            [
                {
                    "id": "expected_negative_lookup",
                    "user_scenario": {
                        "instructions": {
                            "reason_for_call": "Look up an unavailable product id.",
                            "known_info": "No other information is needed.",
                        }
                    },
                    "evaluation_criteria": {
                        "actions": [
                            {
                                "action_id": "neg_0",
                                "name": "get_product_details",
                                "arguments": {"product_id": "6086499569"},
                            }
                        ],
                        "reward_basis": ["DB"],
                    },
                }
            ]
        ),
        encoding="utf-8",
    )

    output_dir = tmp_path / "runs" / "expected_negative_lookup"
    config_path = tmp_path / "expected_negative_lookup.yaml"
    config_path.write_text(
        f"""
experiment:
  name: expected_negative_lookup_test
  seed: 1
  output_dir: {output_dir.as_posix()}
benchmark:
  name: tau_bench
  domain: retail
  split_file: {tasks_path.as_posix()}
  data_dir: data/tau_bench/retail_phase2_state
  evaluation: official_like
  compare_action_args: true
  require_data: true
  validate_export_schema: true
  max_tasks: 1
agent:
  type: action_replay_agent
  max_steps: 4
  memory_top_k: 0
models:
  actor:
    provider: action_replay
    model: scripted-expected-actions
    temperature: 0.0
    max_tokens: 0
logging:
  save_raw_model_io: false
  save_trace_events: true
  save_costs: true
""",
        encoding="utf-8",
    )

    metrics = run(str(config_path))

    assert metrics["success_rate"] == 1.0
    assert metrics["expected_actions_matched_count"] == 1
    assert metrics["tool_observation_error_count"] == 1
    assert metrics["expected_negative_observation_count"] == 1
    assert metrics["policy_violation_count"] == 0
    assert metrics["tool_semantic_error_count"] == 0

    run_record = json.loads((output_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines()[0])
    details = run_record["evaluation_details"]
    assert run_record["success"] is True
    assert run_record["error_type"] is None
    assert details["expected_negative_observations"][0]["tool_name"] == "get_product_details"
    assert details["expected_negative_observations"][0]["classification"] == (
        "expected_negative_observation"
    )
    assert details["expected_actual_action_alignment"][0]["actual_ok"] is False
    assert "was not found" in details["expected_actual_action_alignment"][0]["actual_observation"]


def test_tau2_unexpected_read_tool_error_remains_tool_semantic_error() -> None:
    env = TauBenchEnv(
        {
            "name": "tau_bench",
            "domain": "retail",
            "split_file": "data/task_splits/tau_retail_phase2_state_tasks.py",
            "data_dir": "data/tau_bench/retail_phase2_state",
            "evaluation": "official_like",
            "compare_action_args": True,
            "require_data": True,
            "validate_export_schema": True,
        }
    )
    task = Task(
        task_id="unexpected_negative_lookup",
        instruction="Call a product lookup that is not part of the gold actions.",
        metadata={"expected_actions": []},
    )

    env.start_task(task)
    tool_result = env.call_tool("get_product_details", {"product_id": "6086499569"})
    success, reward, error_type = env.evaluate(task, tool_result.observation)

    assert success is False
    assert reward == 0.0
    assert error_type == "tool_semantic_error"
    assert env.last_evaluation_detail["tool_observation_error_count"] == 1
    assert env.last_evaluation_detail["expected_negative_observation_count"] == 0
    assert env.last_evaluation_detail["tool_semantic_error_count"] == 1
    assert env.last_evaluation_detail["tool_semantic_errors"][0]["classification"] == (
        "tool_semantic_error"
    )


def test_tau2_official_like_reports_unsupported_criteria(tmp_path: Path) -> None:
    tasks_path = tmp_path / "official_unsupported_tasks.json"
    tasks_path.write_text(
        json.dumps(
            [
                {
                    "id": "0",
                    "user_scenario": {
                        "instructions": {
                            "reason_for_call": "Look up the details for order #READ1001.",
                            "known_info": "You are Mira Chen.",
                        }
                    },
                    "evaluation_criteria": {
                        "actions": [
                            {
                                "name": "get_order_details",
                                "arguments": {"order_id": "#READ1001"},
                            }
                        ],
                        "external_judge": {"kind": "not_supported_locally"},
                        "reward_basis": ["CUSTOM_JUDGE"],
                    },
                }
            ]
        ),
        encoding="utf-8",
    )

    output_dir = tmp_path / "runs" / "official_unsupported"
    config_path = tmp_path / "official_unsupported.yaml"
    config_path.write_text(
        f"""
experiment:
  name: official_unsupported_test
  seed: 1
  output_dir: {output_dir.as_posix()}
benchmark:
  name: tau_bench
  domain: retail
  split_file: {tasks_path.as_posix()}
  data_dir: data/tau_bench/retail_phase2_state
  evaluation: official_like
  compare_action_args: true
  require_data: true
  validate_export_schema: true
  max_tasks: 1
agent:
  type: action_replay_agent
  max_steps: 4
  memory_top_k: 0
models:
  actor:
    provider: action_replay
    model: scripted-expected-actions
    temperature: 0.0
    max_tokens: 0
logging:
  save_raw_model_io: false
  save_trace_events: true
  save_costs: true
""",
        encoding="utf-8",
    )

    metrics = run(str(config_path))

    assert metrics["success_rate"] == 0.0
    assert metrics["expected_actions_matched_count"] == 1
    assert metrics["unsupported_official_criteria_count"] >= 1
    assert metrics["evaluator_error_types"] == {"unsupported_official_criterion": 1}

    run_record = json.loads((output_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert run_record["error_type"] == "unsupported_official_criterion"
    assert run_record["evaluation_details"]["unsupported_official_criteria_count"] >= 1


def test_tau_retail_real_export_raw_trace_config_path_runs(tmp_path: Path) -> None:
    split_file = Path("data/task_splits/tau_retail_export_sample_tasks.py").resolve()
    data_dir = Path("data/tau_bench/retail_export_sample").resolve()
    output_dir = tmp_path / "runs" / "tau_retail_real_raw_trace"
    config_path = tmp_path / "tau_retail_real_raw_trace.yaml"
    config_path.write_text(
        f"""
experiment:
  name: tau_retail_real_raw_trace_test
  seed: 1
  output_dir: {output_dir.as_posix()}
benchmark:
  name: tau_bench
  domain: retail
  split_file: {split_file.as_posix()}
  data_dir: {data_dir.as_posix()}
  evaluation: auto
  require_data: true
  validate_export_schema: true
  max_tasks: 3
agent:
  type: react_tool_agent
  max_steps: 4
  memory_top_k: 2
models:
  actor:
    provider: mock
    model: mock-tool-agent
    temperature: 0.0
    max_tokens: 2048
memory:
  method: raw_trace_rag
  top_k: 2
  save_failures: true
logging:
  save_raw_model_io: true
  save_trace_events: true
  save_costs: true
""",
        encoding="utf-8",
    )

    metrics = run(str(config_path))

    assert metrics["num_tasks"] == 3
    assert metrics["success_rate"] == 1.0
    assert metrics["memory_policy"] == "raw_trace_rag"
    assert metrics["memory_size"] == 3
    assert metrics["memory_top_k"] == 2

    task_records = [
        json.loads(line)
        for line in (output_dir / "tasks.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    memory_records = [
        json.loads(line)
        for line in (output_dir / "memories.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]

    assert {record["metadata"]["intent"] for record in task_records} == {
        "customer_lookup",
        "order_lookup",
        "product_lookup",
    }
    assert len(memory_records) == 3


def test_tau_retail_export_schema_validation_reports_missing_outcome(tmp_path: Path) -> None:
    tasks_path = tmp_path / "bad_tasks.json"
    tasks_path.write_text(
        json.dumps([{"id": "bad_task", "instruction": "This task has no expected outcome."}]),
        encoding="utf-8",
    )

    env = TauBenchEnv(
        {
            "domain": "retail",
            "split_file": str(tasks_path),
            "data_dir": "data/tau_bench/retail_export_sample",
            "evaluation": "auto",
            "require_data": True,
            "validate_export_schema": True,
        }
    )

    with pytest.raises(ValueError, match="expected_answer_contains"):
        env.load_tasks()


def test_tau_retail_missing_split_has_clear_error(tmp_path: Path) -> None:
    data_file = Path("data/tau_bench/retail_smoke_db.json").resolve()
    env = TauBenchEnv(
        {
            "name": "tau_bench",
            "domain": "retail",
            "split_file": str(tmp_path / "missing_tau_tasks.json"),
            "data_file": str(data_file),
        }
    )

    with pytest.raises(FileNotFoundError, match="benchmark.split_file"):
        env.load_tasks()


def test_tau_retail_tool_sequence_evaluator(tmp_path: Path) -> None:
    task_file = tmp_path / "tasks.json"
    task_file.write_text(
        json.dumps(
            [
                {
                    "task_id": "tau_action_001",
                    "instruction": "Look up the details for order #W2378156.",
                    "actions": [
                        {
                            "name": "get_order_details",
                            "args": {"order_id": "W2378156"},
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    env = TauBenchEnv(
        {
            "name": "tau_bench",
            "domain": "retail",
            "split_file": str(task_file),
            "data_file": "data/tau_bench/retail_smoke_db.json",
            "evaluation": "tool_sequence",
        }
    )
    task = env.load_tasks()[0]
    tool_result = env.call_tool("get_order_details", {"order_id": "W2378156"})
    success, reward, error_type = env.evaluate(task, tool_result.observation)

    assert success is True
    assert reward == 1.0
    assert error_type is None


def test_tau_retail_action_args_normalize_order_ids() -> None:
    env = TauBenchEnv(
        {
            "name": "tau_bench",
            "domain": "retail",
            "split_file": "data/task_splits/tau_retail_phase2_state_tasks.py",
            "data_dir": "data/tau_bench/retail_phase2_state",
            "evaluation": "action_sequence",
            "compare_action_args": True,
            "require_data": True,
            "validate_export_schema": True,
        }
    )
    task = next(task for task in env.load_tasks() if task.task_id == "tau_retail_phase2_read_001")

    env.start_task(task)
    tool_result = env.call_tool("get_order_details", {"order_id": "READ1001"})
    success, reward, error_type = env.evaluate(task, tool_result.observation)

    assert success is True
    assert reward == 1.0
    assert error_type is None
    assert env.last_evaluation_detail["expected_actions_matched"] is True
    assert env.last_evaluation_detail["action_mismatches"] == []


def test_tau_retail_task_state_resets_between_tasks() -> None:
    env = TauBenchEnv(
        {
            "name": "tau_bench",
            "domain": "retail",
            "split_file": "data/task_splits/tau_retail_phase2_state_tasks.py",
            "data_dir": "data/tau_bench/retail_phase2_state",
            "evaluation": "official_like",
            "compare_action_args": True,
            "require_data": True,
            "validate_export_schema": True,
        }
    )
    tasks = {task.task_id: task for task in env.load_tasks()}

    cancel_task = tasks["tau_retail_phase2_cancel_001"]
    env.start_task(cancel_task)
    cancel_result = env.call_tool(
        "cancel_pending_order",
        {"order_id": "PEND2001", "reason": "customer_request"},
    )
    success, _, error_type = env.evaluate(cancel_task, cancel_result.observation)
    assert success is True
    assert error_type is None
    assert env.last_evaluation_detail["state_diff_passed"] is True
    assert env._get_order_record("PEND2001")["status"] == "cancelled"

    env.start_task(tasks["tau_retail_phase2_read_001"])
    reset_result = env.call_tool("get_order_details", {"order_id": "PEND2001"})
    assert reset_result.ok
    assert '"status": "pending"' in reset_result.observation


def test_tau_retail_official_exchange_and_return_mutations(tmp_path: Path) -> None:
    db_path = tmp_path / "official_mutation_db.json"
    task_path = tmp_path / "tasks.json"
    db_path.write_text(
        json.dumps(
            {
                "users": {
                    "user_1": {
                        "user_id": "user_1",
                        "name": {"first_name": "Yusuf", "last_name": "Rossi"},
                        "address": {"zip": "19122"},
                        "payment_methods": {
                            "credit_card_1": {
                                "id": "credit_card_1",
                                "source": "credit_card",
                            }
                        },
                    }
                },
                "orders": {
                    "#EX1": {
                        "order_id": "#EX1",
                        "user_id": "user_1",
                        "status": "delivered",
                        "items": [
                            {
                                "item_id": "old_item",
                                "product_id": "product_1",
                                "price": 10.0,
                            }
                        ],
                        "payment_history": [
                            {
                                "transaction_type": "payment",
                                "amount": 10.0,
                                "payment_method_id": "credit_card_1",
                            }
                        ],
                    },
                    "#RET1": {
                        "order_id": "#RET1",
                        "user_id": "user_1",
                        "status": "delivered",
                        "items": [
                            {
                                "item_id": "return_item",
                                "product_id": "product_1",
                                "price": 10.0,
                            }
                        ],
                        "payment_history": [
                            {
                                "transaction_type": "payment",
                                "amount": 10.0,
                                "payment_method_id": "credit_card_1",
                            }
                        ],
                    },
                },
                "products": {
                    "product_1": {
                        "product_id": "product_1",
                        "name": "Mechanical Keyboard",
                        "variants": {
                            "old_item": {
                                "item_id": "old_item",
                                "available": True,
                                "price": 10.0,
                            },
                            "new_item": {
                                "item_id": "new_item",
                                "available": True,
                                "price": 12.5,
                            },
                            "return_item": {
                                "item_id": "return_item",
                                "available": True,
                                "price": 10.0,
                            },
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    task_path.write_text(
        json.dumps(
            [
                {
                    "id": "mutation_fixture",
                    "instruction": "Mutation fixture.",
                    "expected_answer_contains": ["done"],
                }
            ]
        ),
        encoding="utf-8",
    )
    env = TauBenchEnv(
        {
            "name": "tau_bench",
            "domain": "retail",
            "split_file": str(task_path),
            "data_file": str(db_path),
            "evaluation": "answer_contains",
            "require_data": True,
            "validate_export_schema": True,
        }
    )

    find_user = env.call_tool(
        "find_user_id_by_name_zip",
        {"first_name": "Yusuf", "last_name": "Rossi", "zip": "19122"},
    )
    exchange = env.call_tool(
        "exchange_delivered_order_items",
        {
            "order_id": "#EX1",
            "item_ids": ["old_item"],
            "new_item_ids": ["new_item"],
            "payment_method_id": "credit_card_1",
        },
    )
    returned = env.call_tool(
        "return_delivered_order_items",
        {
            "order_id": "#RET1",
            "item_ids": ["return_item"],
            "payment_method_id": "credit_card_1",
        },
    )

    assert find_user.ok
    assert "user_id=user_1" in find_user.observation
    assert exchange.ok
    assert env._get_order_record("#EX1")["status"] == "exchange requested"
    assert env._get_order_record("#EX1")["exchange_price_difference"] == 2.5
    assert returned.ok
    assert env._get_order_record("#RET1")["status"] == "return requested"
    assert env._get_order_record("#RET1")["return_items"] == ["return_item"]


def test_tau_retail_phase2_state_config_logs_evaluator_details(tmp_path: Path) -> None:
    config_path = tmp_path / "tau_retail_phase2_state.yaml"
    output_dir = tmp_path / "runs" / "phase2_state"
    _write_tau_retail_phase2_config(
        config_path=config_path,
        output_dir=output_dir,
        experiment_name="tau_retail_phase2_state_test",
    )

    metrics = run(str(config_path))

    assert metrics["num_tasks"] == 3
    assert metrics["success_rate"] == pytest.approx(2 / 3)
    assert metrics["evaluation_modes"] == {"official_like": 3}
    assert metrics["expected_actions_matched_count"] == 3
    assert metrics["state_diff_evaluated_count"] == 1
    assert metrics["state_diff_passed_count"] == 1
    assert metrics["policy_violation_count"] == 1
    assert metrics["tool_observation_error_count"] == 1
    assert metrics["expected_negative_observation_count"] == 0
    assert metrics["tool_semantic_error_count"] == 0
    assert metrics["evaluator_error_types"] == {"policy_violation": 1}

    run_records = [
        json.loads(line)
        for line in (output_dir / "runs.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    cancel_record = next(
        record for record in run_records if record["task_id"] == "tau_retail_phase2_cancel_001"
    )
    policy_fail_record = next(
        record
        for record in run_records
        if record["task_id"] == "tau_retail_phase2_return_policy_fail_001"
    )

    assert cancel_record["success"] is True
    assert cancel_record["evaluation_details"]["state_diff_passed"] is True
    assert "#PEND2001" in cancel_record["evaluation_details"]["state_diff_summary"]["orders"]
    assert policy_fail_record["success"] is False
    assert policy_fail_record["error_type"] == "policy_violation"
    assert policy_fail_record["evaluation_details"]["policy_violation_count"] == 1
    assert policy_fail_record["evaluation_details"]["tool_observation_error_count"] == 1
    assert policy_fail_record["evaluation_details"]["tool_semantic_error_count"] == 0
    assert policy_fail_record["evaluation_details"]["expected_actions_matched"] is True


def test_tau_retail_phase2_raw_trace_keeps_evaluator_details(tmp_path: Path) -> None:
    config_path = tmp_path / "tau_retail_phase2_raw.yaml"
    output_dir = tmp_path / "runs" / "phase2_raw"
    _write_tau_retail_phase2_config(
        config_path=config_path,
        output_dir=output_dir,
        experiment_name="tau_retail_phase2_raw_test",
        memory_block="  method: raw_trace_rag\n  top_k: 2\n  save_failures: true",
    )

    metrics = run(str(config_path))

    assert metrics["num_tasks"] == 3
    assert metrics["memory_policy"] == "raw_trace_rag"
    assert metrics["memory_size"] == 3
    assert metrics["policy_violation_count"] == 1

    memory_records = [
        json.loads(line)
        for line in (output_dir / "memories.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    run_records = [
        json.loads(line)
        for line in (output_dir / "runs.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]

    assert len(memory_records) == 3
    assert all("evaluation_details" in record for record in run_records)
