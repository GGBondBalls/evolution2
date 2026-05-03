from __future__ import annotations

import json
from pathlib import Path

import pytest

from ntmemevo.envs.tau_bench import TauBenchEnv
from ntmemevo.experiments.run_stream import run


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
    assert metrics["tool_semantic_error_count"] == 1
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
