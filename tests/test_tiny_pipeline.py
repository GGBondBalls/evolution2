from __future__ import annotations

import json
from pathlib import Path

from ntmemevo.experiments.run_stream import run
from ntmemevo.memory.extractor import CandidateExtractionContext, CandidateMemoryExtractor
from ntmemevo.memory.gate import RetrieverGate, RetrieverGateConfig
from ntmemevo.memory.schema import CandidateMemory, candidate_memory_json_schema
from ntmemevo.types import AgentResult, Task


def test_tiny_pipeline_runs(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    output_dir = tmp_path / "runs" / "tiny"
    split_file = Path("data/task_splits/tiny_tool_tasks.json").resolve()
    config_path.write_text(
        f"""
experiment:
  name: tiny_test
  seed: 1
  output_dir: {output_dir.as_posix()}
benchmark:
  name: tiny_tools
  split_file: {split_file.as_posix()}
  max_tasks: 2
agent:
  type: react_tool_agent
  max_steps: 4
  memory_top_k: 0
models:
  actor:
    provider: mock
    model: mock-tool-agent
    temperature: 0.0
    max_tokens: 512
logging:
  save_raw_model_io: true
  save_trace_events: true
  save_costs: true
""",
        encoding="utf-8",
    )

    metrics = run(str(config_path))

    assert metrics["num_tasks"] == 2
    assert metrics["success_rate"] == 1.0
    assert metrics["memory_policy"] == "none"
    assert (output_dir / "runs.jsonl").exists()
    assert (output_dir / "trace_events.jsonl").exists()


def test_raw_trace_rag_writes_and_retrieves_memories(tmp_path: Path) -> None:
    config_path = tmp_path / "config_raw.yaml"
    output_dir = tmp_path / "runs" / "raw"
    split_file = Path("data/task_splits/tiny_tool_tasks.json").resolve()
    config_path.write_text(
        f"""
experiment:
  name: tiny_raw_test
  seed: 1
  output_dir: {output_dir.as_posix()}
benchmark:
  name: tiny_tools
  split_file: {split_file.as_posix()}
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
    max_tokens: 512
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
    memories = (output_dir / "memories.jsonl").read_text(encoding="utf-8").strip().splitlines()
    updates = (output_dir / "memory_updates.jsonl").read_text(encoding="utf-8").strip().splitlines()
    runs = (output_dir / "runs.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(memories) == 3
    assert len(runs) == 3
    assert any("retrieved_memory_ids" in line for line in updates)


def test_reflexion_writes_and_retrieves_reflections(tmp_path: Path) -> None:
    config_path = tmp_path / "config_reflexion.yaml"
    output_dir = tmp_path / "runs" / "reflexion"
    split_file = Path("data/task_splits/tiny_tool_tasks.json").resolve()
    config_path.write_text(
        f"""
experiment:
  name: tiny_reflexion_test
  seed: 1
  output_dir: {output_dir.as_posix()}
benchmark:
  name: tiny_tools
  split_file: {split_file.as_posix()}
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
    max_tokens: 512
memory:
  method: reflexion
  top_k: 2
  save_successes: true
  save_failures: true
  max_reflection_chars: 700
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
    assert metrics["memory_policy"] == "reflexion"
    assert metrics["memory_size"] == 3

    memory_records = [
        json.loads(line)
        for line in (output_dir / "memories.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    run_records = [
        json.loads(line)
        for line in (output_dir / "runs.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    update_records = [
        json.loads(line)
        for line in (output_dir / "memory_updates.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]

    assert len(memory_records) == 3
    assert all(record["reflection_type"] == "strategy" for record in memory_records)
    assert all(record["memory_policy"] == "reflexion" for record in run_records)
    assert any(record["used_memory_ids"] for record in run_records[1:])
    assert any(record.get("reflection_type") == "strategy" for record in update_records)


def test_candidate_memory_schema_roundtrip() -> None:
    task = Task(
        task_id="tiny_schema_001",
        instruction="Check whether SKU-RED-M is in stock.",
        expected_answer_contains=("in_stock",),
    )
    result = AgentResult(
        task_id=task.task_id,
        success=True,
        reward=1.0,
        final_answer="SKU SKU-RED-M is in_stock with quantity 12.",
        num_steps=2,
        prompt_tokens=10,
        completion_tokens=4,
        tool_calls=1,
        trace_summary=("check_inventory({'sku': 'SKU-RED-M'}) -> SKU SKU-RED-M is in_stock.",),
    )
    memory = CandidateMemoryExtractor().extract(
        task=task,
        result=result,
        context=CandidateExtractionContext(
            benchmark="tiny_tools",
            experiment_id="tiny_schema_test",
            run_id="tiny_schema_test_tiny_schema_001",
            iteration=1,
        ),
    )
    record = memory.to_json()
    schema = candidate_memory_json_schema()

    assert set(schema["required"]).issubset(record)
    assert record["type"] == "tool_usage"
    assert record["scope"]["intent"] == "inventory_check"
    assert record["utility"]["alpha"] == 1.0
    assert record["utility"]["beta"] == 1.0
    assert record["utility"]["num_used"] == 0
    assert record["lifecycle"]["status"] == "candidate"
    assert record["positive_evidence"] == ["tiny_schema_test_tiny_schema_001"]
    assert record["negative_evidence"] == []

    roundtrip = CandidateMemory.from_json(record)
    assert roundtrip.to_json() == record


def test_nt_memevo_candidate_writes_structured_memories(tmp_path: Path) -> None:
    config_path = tmp_path / "config_nt_candidate.yaml"
    output_dir = tmp_path / "runs" / "nt_candidate"
    split_file = Path("data/task_splits/tiny_tool_tasks.json").resolve()
    config_path.write_text(
        f"""
experiment:
  name: tiny_nt_candidate_test
  seed: 1
  output_dir: {output_dir.as_posix()}
benchmark:
  name: tiny_tools
  split_file: {split_file.as_posix()}
  max_tasks: 3
agent:
  type: react_tool_agent
  max_steps: 4
  memory_top_k: 0
models:
  actor:
    provider: mock
    model: mock-tool-agent
    temperature: 0.0
    max_tokens: 512
memory:
  method: nt_memevo_candidate
  top_k: 0
  save_successes: true
  save_failures: true
  extractor_model: deterministic_candidate_extractor_v1
  domain: retail
  ttl: 50
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
    assert metrics["memory_policy"] == "nt_memevo_candidate"
    assert metrics["memory_size"] == 3
    assert metrics["memory_top_k"] == 0

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

    assert len(candidate_records) == 3
    assert all(record["lifecycle"]["status"] == "candidate" for record in candidate_records)
    assert all(record["utility"]["num_used"] == 0 for record in candidate_records)
    assert all(record["source"]["created_from"] for record in candidate_records)
    assert all(record["memory_policy"] == "nt_memevo_candidate" for record in run_records)
    assert all(record["used_memory_ids"] == [] for record in run_records)
    assert all(record["event_type"] == "candidate_extract" for record in update_records)
    assert all(record["candidate_status"] == "candidate" for record in update_records)


def test_retriever_gate_accepts_scoped_candidate_and_rejects_negative_evidence() -> None:
    task = Task(
        task_id="tiny_refund_gate_001",
        instruction="Decide whether order ORD-1002 can be refunded.",
        expected_answer_contains=("not refundable",),
    )
    success_result = AgentResult(
        task_id=task.task_id,
        success=True,
        reward=1.0,
        final_answer="Order ORD-1002 is cancelled and not refundable.",
        num_steps=2,
        prompt_tokens=10,
        completion_tokens=4,
        tool_calls=1,
        trace_summary=("get_order_status({'order_id': 'ORD-1002'}) -> Order ORD-1002 is cancelled and not refundable.",),
    )
    failed_result = AgentResult(
        task_id=task.task_id,
        success=False,
        reward=0.0,
        final_answer="Delivered retail orders can be returned within 30 days.",
        num_steps=2,
        prompt_tokens=10,
        completion_tokens=4,
        tool_calls=1,
        trace_summary=("lookup_policy({'policy_name': 'return_window'}) -> Delivered retail orders can be returned within 30 days.",),
        error_type="expected_answer_mismatch",
    )
    extractor = CandidateMemoryExtractor()
    positive = extractor.extract(
        task=task,
        result=success_result,
        context=CandidateExtractionContext(
            benchmark="tiny_tools",
            experiment_id="gate_unit",
            run_id="gate_unit_success",
            iteration=1,
        ),
    )
    negative = extractor.extract(
        task=task,
        result=failed_result,
        context=CandidateExtractionContext(
            benchmark="tiny_tools",
            experiment_id="gate_unit",
            run_id="gate_unit_failed",
            iteration=2,
        ),
    )

    selected, decisions = RetrieverGate(
        memories=[negative, positive],
        config=RetrieverGateConfig(top_k=2),
    ).retrieve(task=task, iteration=3)

    accepted_ids = {memory.memory_id for memory in selected}
    negative_decision = next(decision for decision in decisions if decision.memory_id == negative.memory_id)
    positive_decision = next(decision for decision in decisions if decision.memory_id == positive.memory_id)

    assert positive.memory_id in accepted_ids
    assert positive_decision.gate_decision == "accept"
    assert negative_decision.gate_decision == "reject"
    assert negative_decision.rejection_reason == "negative_evidence_present"


def test_nt_memevo_gate_retrieves_structured_candidates(tmp_path: Path) -> None:
    split_file = tmp_path / "repeated_tasks.json"
    split_file.write_text(
        json.dumps(
            [
                {
                    "task_id": "tiny_order_repeat_001",
                    "instruction": "Find the delivery status for order ORD-1001.",
                    "expected_answer_contains": ["delivered"],
                    "initial_state": {},
                },
                {
                    "task_id": "tiny_order_repeat_002",
                    "instruction": "Find the delivery status for order ORD-1001.",
                    "expected_answer_contains": ["delivered"],
                    "initial_state": {},
                },
            ]
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "config_nt_gate.yaml"
    output_dir = tmp_path / "runs" / "nt_gate"
    config_path.write_text(
        f"""
experiment:
  name: tiny_nt_gate_test
  seed: 1
  output_dir: {output_dir.as_posix()}
benchmark:
  name: tiny_tools
  split_file: {split_file.as_posix()}
  max_tasks: 2
agent:
  type: react_tool_agent
  max_steps: 4
  memory_top_k: 1
models:
  actor:
    provider: mock
    model: mock-tool-agent
    temperature: 0.0
    max_tokens: 512
memory:
  method: nt_memevo_gate
  top_k: 1
  save_successes: true
  save_failures: true
  extractor_model: deterministic_candidate_extractor_v1
  domain: retail
  ttl: 50
  gate:
    min_score: 0.30
    min_similarity: 0.02
    min_precondition: 0.25
    reject_negative_evidence: true
logging:
  save_raw_model_io: true
  save_trace_events: true
  save_costs: true
""",
        encoding="utf-8",
    )

    metrics = run(str(config_path))

    assert metrics["num_tasks"] == 2
    assert metrics["success_rate"] == 1.0
    assert metrics["memory_policy"] == "nt_memevo_gate"
    assert metrics["memory_size"] == 2
    assert metrics["memory_top_k"] == 1
    assert metrics["gate_accepted_count"] >= 1

    run_records = [
        json.loads(line)
        for line in (output_dir / "runs.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    update_records = [
        json.loads(line)
        for line in (output_dir / "memory_updates.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]

    assert run_records[0]["used_memory_ids"] == []
    assert run_records[1]["used_memory_ids"]
    assert any(record.get("event_type") == "gate_decision" for record in update_records)
    assert any(record.get("gate_decision") == "accept" for record in update_records)


def test_nt_memevo_gate_updates_utility_and_promotes_active_memory(tmp_path: Path) -> None:
    split_file = tmp_path / "repeated_tasks.json"
    split_file.write_text(
        json.dumps(
            [
                {
                    "task_id": "tiny_order_repeat_001",
                    "instruction": "Find the delivery status for order ORD-1001.",
                    "expected_answer_contains": ["delivered"],
                    "initial_state": {},
                    "no_memory_success": True,
                },
                {
                    "task_id": "tiny_order_repeat_002",
                    "instruction": "Find the delivery status for order ORD-1001.",
                    "expected_answer_contains": ["delivered"],
                    "initial_state": {},
                    "no_memory_success": True,
                },
                {
                    "task_id": "tiny_order_repeat_003",
                    "instruction": "Find the delivery status for order ORD-1001.",
                    "expected_answer_contains": ["delivered"],
                    "initial_state": {},
                    "no_memory_success": True,
                },
            ]
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "config_nt_gate_utility.yaml"
    output_dir = tmp_path / "runs" / "nt_gate_utility"
    config_path.write_text(
        f"""
experiment:
  name: tiny_nt_gate_utility_test
  seed: 1
  output_dir: {output_dir.as_posix()}
benchmark:
  name: tiny_tools
  split_file: {split_file.as_posix()}
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
    max_tokens: 512
memory:
  method: nt_memevo_gate
  top_k: 2
  save_successes: true
  save_failures: true
  extractor_model: deterministic_candidate_extractor_v1
  domain: retail
  ttl: 50
  utility:
    promote_after_helpful: 2
    quarantine_after_harmful: 1
  gate:
    min_score: 0.30
    min_similarity: 0.02
    min_precondition: 0.25
    reject_negative_evidence: true
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
    assert metrics["gate_accepted_count"] >= 3
    assert metrics["utility_update_count"] == 3
    assert metrics["utility_helpful_count"] == 3
    assert metrics["utility_harmful_count"] == 0
    assert metrics["active_memory_count"] == 1

    candidate_records = [
        json.loads(line)
        for line in (output_dir / "candidate_memories.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    update_records = [
        json.loads(line)
        for line in (output_dir / "memory_updates.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    first_memory = next(
        record
        for record in candidate_records
        if record["memory_id"] == "cand_000001_tiny_order_repeat_001"
    )

    assert len(candidate_records) == 3
    assert first_memory["utility"]["num_used"] == 2
    assert first_memory["utility"]["num_helpful"] == 2
    assert first_memory["utility"]["num_harmful"] == 0
    assert first_memory["lifecycle"]["status"] == "active"
    assert first_memory["lifecycle"]["last_used_iter"] == 3
    assert any(
        record.get("event_type") == "utility_update"
        and record.get("outcome") == "helpful"
        and record.get("lifecycle_before", {}).get("status") == "candidate"
        and record.get("lifecycle_after", {}).get("status") == "active"
        for record in update_records
    )


def test_nt_memevo_gate_replay_updates_utility_and_promotes_active_memory(tmp_path: Path) -> None:
    split_file = tmp_path / "memory_dependent_tasks.json"
    split_file.write_text(
        json.dumps(
            [
                {
                    "task_id": "tiny_memory_order_seed_001",
                    "instruction": "Find the delivery status for order ORD-1001.",
                    "expected_answer_contains": ["delivered"],
                    "initial_state": {},
                    "no_memory_success": True,
                    "no_memory_reward": 1.0,
                },
                {
                    "task_id": "tiny_memory_order_replay_002",
                    "instruction": (
                        "Find the delivery status for the same order from the prior "
                        "order-status example."
                    ),
                    "expected_answer_contains": ["delivered"],
                    "initial_state": {},
                    "no_memory_success": False,
                    "no_memory_reward": 0.0,
                },
                {
                    "task_id": "tiny_memory_order_replay_003",
                    "instruction": (
                        "Find the delivery status for the same order from the prior "
                        "order-status example."
                    ),
                    "expected_answer_contains": ["delivered"],
                    "initial_state": {},
                    "no_memory_success": False,
                    "no_memory_reward": 0.0,
                },
            ]
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "config_nt_gate_replay.yaml"
    output_dir = tmp_path / "runs" / "nt_gate_replay"
    config_path.write_text(
        f"""
experiment:
  name: tiny_nt_gate_replay_test
  seed: 1
  output_dir: {output_dir.as_posix()}
benchmark:
  name: tiny_tools
  split_file: {split_file.as_posix()}
  max_tasks: 3
agent:
  type: react_tool_agent
  max_steps: 4
  memory_top_k: 1
models:
  actor:
    provider: mock
    model: mock-memory-sensitive-agent
    follow_memory_hints: true
    temperature: 0.0
    max_tokens: 512
memory:
  method: nt_memevo_gate
  top_k: 1
  save_successes: true
  save_failures: true
  extractor_model: deterministic_candidate_extractor_v1
  domain: retail
  ttl: 50
  utility:
    promote_after_helpful: 2
    quarantine_after_harmful: 1
  replay:
    enabled: true
    delta_threshold: 0.0
    max_memories: 1
    log_context_modes: true
    promote_requires_positive_lcb: true
  gate:
    min_score: 0.30
    min_similarity: 0.02
    min_precondition: 0.25
    weight_utility: 0.60
    reject_negative_evidence: true
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
    assert metrics["gate_accepted_count"] == 2
    assert metrics["replay_leave_one_count"] == 2
    assert metrics["replay_helpful_count"] == 2
    assert metrics["replay_harmful_count"] == 0
    assert metrics["replay_utility_update_count"] == 2
    assert metrics["online_proxy_utility_update_count"] == 0
    assert metrics["utility_helpful_count"] == 2
    assert metrics["active_memory_count"] == 1

    candidate_records = [
        json.loads(line)
        for line in (output_dir / "candidate_memories.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    replay_records = [
        json.loads(line)
        for line in (output_dir / "replay_results.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    update_records = [
        json.loads(line)
        for line in (output_dir / "memory_updates.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    first_memory = next(
        record
        for record in candidate_records
        if record["memory_id"] == "cand_000001_tiny_memory_order_seed_001"
    )
    leave_one_records = [
        record for record in replay_records if record["mode"] == "leave_one_memory_out"
    ]

    assert first_memory["utility"]["num_used"] == 2
    assert first_memory["utility"]["num_helpful"] == 2
    assert first_memory["utility"]["mean_delta_reward"] == 1.0
    assert first_memory["utility"]["lcb_delta_reward"] > 0.0
    assert first_memory["lifecycle"]["status"] == "active"
    assert first_memory["lifecycle"]["last_used_iter"] == 3
    assert {record["mode"] for record in replay_records} == {
        "with_selected_memory",
        "without_selected_memory",
        "leave_one_memory_out",
    }
    assert len(leave_one_records) == 2
    assert all(record["delta_reward"] == 1.0 for record in leave_one_records)
    assert all(record["attribution_label"] == "helpful" for record in leave_one_records)
    assert any(
        record.get("event_type") == "utility_update"
        and record.get("credit_source") == "leave_one_memory_out"
        and record.get("replay_attribution_label") == "helpful"
        and record.get("lifecycle_after", {}).get("status") == "active"
        for record in update_records
    )


def test_nt_memevo_gate_support_verification_promotes_active_memory(tmp_path: Path) -> None:
    config_path = tmp_path / "config_nt_gate_verify.yaml"
    output_dir = tmp_path / "runs" / "nt_gate_verify"
    split_file = Path("data/task_splits/tiny_memory_dependent_tasks.json").resolve()
    support_split_file = Path("data/task_splits/tiny_support_verification_tasks.json").resolve()
    config_path.write_text(
        f"""
experiment:
  name: tiny_nt_gate_verify_test
  seed: 1
  output_dir: {output_dir.as_posix()}
benchmark:
  name: tiny_tools
  split_file: {split_file.as_posix()}
  max_tasks: 3
agent:
  type: react_tool_agent
  max_steps: 4
  memory_top_k: 1
models:
  actor:
    provider: mock
    model: mock-memory-sensitive-agent
    follow_memory_hints: true
    temperature: 0.0
    max_tokens: 512
memory:
  method: nt_memevo_gate
  top_k: 1
  save_successes: true
  save_failures: true
  extractor_model: deterministic_candidate_extractor_v1
  domain: retail
  ttl: 50
  utility:
    promote_after_helpful: 2
    quarantine_after_harmful: 1
  replay:
    enabled: true
    delta_threshold: 0.0
    max_memories: 1
    log_context_modes: true
    promote_requires_positive_lcb: true
  verification:
    enabled: true
    support_split_file: {support_split_file.as_posix()}
    max_support_tasks: 2
    min_support_tasks: 2
    min_support_similarity: 0.10
    require_intent_match: true
    require_domain_match: true
    min_helpful_before_verify: 2
    disable_immediate_promotion: true
    delta_threshold: 0.0
    min_delta_mean: 0.0
    min_lcb_delta_reward: 0.0
    max_negative_transfer_rate: 0.0
  gate:
    min_score: 0.30
    min_similarity: 0.02
    min_precondition: 0.25
    weight_utility: 0.60
    reject_negative_evidence: true
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
    assert metrics["replay_leave_one_count"] == 2
    assert metrics["support_replay_count"] == 2
    assert metrics["support_replay_helpful_count"] == 2
    assert metrics["support_replay_harmful_count"] == 0
    assert metrics["verification_count"] == 1
    assert metrics["verification_passed_count"] == 1
    assert metrics["verification_failed_count"] == 0
    assert metrics["active_memory_count"] == 1

    candidate_records = [
        json.loads(line)
        for line in (output_dir / "candidate_memories.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    replay_records = [
        json.loads(line)
        for line in (output_dir / "replay_results.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    update_records = [
        json.loads(line)
        for line in (output_dir / "memory_updates.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    first_memory = next(
        record
        for record in candidate_records
        if record["memory_id"] == "cand_000001_tiny_memory_order_seed_001"
    )
    support_replays = [
        record for record in replay_records if record["replay_scope"] == "support_task_replay"
    ]

    assert first_memory["lifecycle"]["status"] == "active"
    assert "tiny_support_order_001" in {record["task_id"] for record in support_replays}
    assert "tiny_support_order_002" in {record["task_id"] for record in support_replays}
    assert all(record["mode"] == "support_task_replay" for record in support_replays)
    assert all(record["delta_reward"] == 1.0 for record in support_replays)
    assert all(record["cost_adjusted_delta_reward"] == 1.0 for record in support_replays)
    assert all(
        not (
            record.get("event_type") == "utility_update"
            and record.get("lifecycle_after", {}).get("status") == "active"
        )
        for record in update_records
    )
    assert any(
        record.get("event_type") == "verification_update"
        and record.get("verification_passed") is True
        and record.get("support_delta_mean") == 1.0
        and record.get("support_lcb_delta_reward") > 0.0
        and record.get("lifecycle_before", {}).get("status") == "candidate"
        and record.get("lifecycle_after", {}).get("status") == "active"
        for record in update_records
    )


def test_support_verification_failure_keeps_candidate_when_support_delta_is_neutral(
    tmp_path: Path,
) -> None:
    support_split_file = tmp_path / "neutral_support_tasks.json"
    support_split_file.write_text(
        json.dumps(
            [
                {
                    "task_id": "tiny_support_order_direct_001",
                    "instruction": "Find the delivery status for order ORD-1001.",
                    "expected_answer_contains": ["delivered"],
                    "domain": "retail",
                    "intent": "order_status",
                    "tool_names": ["get_order_status"],
                },
                {
                    "task_id": "tiny_support_order_direct_002",
                    "instruction": "Report the current delivery status for order ORD-1001.",
                    "expected_answer_contains": ["delivered"],
                    "domain": "retail",
                    "intent": "order_status",
                    "tool_names": ["get_order_status"],
                },
            ]
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "config_nt_gate_verify_neutral.yaml"
    output_dir = tmp_path / "runs" / "nt_gate_verify_neutral"
    split_file = Path("data/task_splits/tiny_memory_dependent_tasks.json").resolve()
    config_path.write_text(
        f"""
experiment:
  name: tiny_nt_gate_verify_neutral_test
  seed: 1
  output_dir: {output_dir.as_posix()}
benchmark:
  name: tiny_tools
  split_file: {split_file.as_posix()}
  max_tasks: 3
agent:
  type: react_tool_agent
  max_steps: 4
  memory_top_k: 1
models:
  actor:
    provider: mock
    model: mock-memory-sensitive-agent
    follow_memory_hints: true
    temperature: 0.0
    max_tokens: 512
memory:
  method: nt_memevo_gate
  top_k: 1
  save_successes: true
  save_failures: true
  extractor_model: deterministic_candidate_extractor_v1
  domain: retail
  ttl: 50
  utility:
    promote_after_helpful: 2
    quarantine_after_harmful: 1
  replay:
    enabled: true
    delta_threshold: 0.0
    max_memories: 1
    log_context_modes: true
    promote_requires_positive_lcb: true
  verification:
    enabled: true
    support_split_file: {support_split_file.as_posix()}
    max_support_tasks: 2
    min_support_tasks: 2
    min_support_similarity: 0.10
    require_intent_match: true
    require_domain_match: true
    min_helpful_before_verify: 2
    disable_immediate_promotion: true
    delta_threshold: 0.0
    min_delta_mean: 0.0
    min_lcb_delta_reward: 0.0
    max_negative_transfer_rate: 0.0
  gate:
    min_score: 0.30
    min_similarity: 0.02
    min_precondition: 0.25
    weight_utility: 0.60
    reject_negative_evidence: true
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
    assert metrics["support_replay_count"] == 2
    assert metrics["support_replay_helpful_count"] == 0
    assert metrics["support_replay_neutral_count"] == 2
    assert metrics["verification_count"] == 1
    assert metrics["verification_passed_count"] == 0
    assert metrics["verification_failed_count"] == 1
    assert metrics["active_memory_count"] == 0
    assert metrics["candidate_memory_count"] == 3

    candidate_records = [
        json.loads(line)
        for line in (output_dir / "candidate_memories.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    replay_records = [
        json.loads(line)
        for line in (output_dir / "replay_results.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    update_records = [
        json.loads(line)
        for line in (output_dir / "memory_updates.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    first_memory = next(
        record
        for record in candidate_records
        if record["memory_id"] == "cand_000001_tiny_memory_order_seed_001"
    )
    support_replays = [
        record for record in replay_records if record["replay_scope"] == "support_task_replay"
    ]

    assert first_memory["lifecycle"]["status"] == "candidate"
    assert all(record["delta_reward"] == 0.0 for record in support_replays)
    assert any(
        record.get("event_type") == "verification_update"
        and record.get("verification_passed") is False
        and record.get("failure_reason") == "support_delta_mean_below_threshold"
        and record.get("lifecycle_before", {}).get("status") == "candidate"
        and record.get("lifecycle_after", {}).get("status") == "candidate"
        for record in update_records
    )


def test_support_verification_mixed_evidence_refines_scope_and_logs_selection(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config_nt_gate_refine.yaml"
    output_dir = tmp_path / "runs" / "nt_gate_refine"
    split_file = Path("data/task_splits/tiny_memory_dependent_tasks.json").resolve()
    support_split_file = Path("data/task_splits/tiny_mixed_support_verification_tasks.json").resolve()
    config_path.write_text(
        f"""
experiment:
  name: tiny_nt_gate_refine_test
  seed: 1
  output_dir: {output_dir.as_posix()}
benchmark:
  name: tiny_tools
  split_file: {split_file.as_posix()}
  max_tasks: 3
agent:
  type: react_tool_agent
  max_steps: 4
  memory_top_k: 1
models:
  actor:
    provider: mock
    model: mock-memory-sensitive-agent
    follow_memory_hints: true
    temperature: 0.0
    max_tokens: 512
memory:
  method: nt_memevo_gate
  top_k: 1
  save_successes: true
  save_failures: true
  extractor_model: deterministic_candidate_extractor_v1
  domain: retail
  ttl: 50
  utility:
    promote_after_helpful: 2
    quarantine_after_harmful: 1
  replay:
    enabled: true
    delta_threshold: 0.0
    max_memories: 1
    log_context_modes: true
    promote_requires_positive_lcb: true
  verification:
    enabled: true
    support_split_file: {support_split_file.as_posix()}
    max_support_tasks: 4
    min_support_tasks: 4
    min_support_similarity: 0.0
    require_intent_match: false
    require_domain_match: true
    min_helpful_before_verify: 2
    disable_immediate_promotion: true
    delta_threshold: 0.0
    min_delta_mean: 0.0
    min_lcb_delta_reward: 0.0
    max_negative_transfer_rate: 0.0
    log_support_selection: true
    refinement:
      enabled: true
      min_helpful: 2
      refined_status: active
      quarantine_parent: true
  gate:
    min_score: 0.30
    min_similarity: 0.02
    min_precondition: 0.25
    weight_utility: 0.60
    reject_negative_evidence: true
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
    assert metrics["support_replay_count"] == 4
    assert metrics["support_replay_helpful_count"] == 2
    assert metrics["support_replay_harmful_count"] == 2
    assert metrics["verification_count"] == 1
    assert metrics["verification_passed_count"] == 0
    assert metrics["verification_failed_count"] == 1
    assert metrics["memory_refinement_count"] == 1
    assert metrics["memory_split_count"] == 1
    assert metrics["candidate_memory_count"] == 2
    assert metrics["active_memory_count"] == 1
    assert metrics["quarantined_memory_count"] == 1
    assert metrics["support_selection_count"] == 4
    assert metrics["replay_prompt_tokens"] < metrics["replay_record_prompt_tokens"]
    assert metrics["support_replay_prompt_tokens"] == metrics["support_replay_record_prompt_tokens"]

    candidate_records = [
        json.loads(line)
        for line in (output_dir / "candidate_memories.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    update_records = [
        json.loads(line)
        for line in (output_dir / "memory_updates.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    replay_records = [
        json.loads(line)
        for line in (output_dir / "replay_results.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]

    parent = next(
        record
        for record in candidate_records
        if record["memory_id"] == "cand_000001_tiny_memory_order_seed_001"
    )
    child = next(
        record
        for record in candidate_records
        if record["memory_id"].startswith("cand_000001_tiny_memory_order_seed_001__refined_")
    )

    assert parent["lifecycle"]["status"] == "quarantined"
    assert child["lifecycle"]["status"] == "active"
    assert child["scope"]["intent"] == "order_status"
    assert any(
        record.get("event_type") == "support_selection"
        and record.get("memory_id") == "cand_000001_tiny_memory_order_seed_001"
        and record.get("source_task_id") == "tiny_memory_order_replay_003"
        and str(record.get("support_task_id", "")).startswith("tiny_mixed_support_")
        and record.get("support_match_score") is not None
        and record.get("intent_score") is not None
        and record.get("tool_score") is not None
        and record.get("lexical_score") is not None
        for record in update_records
    )
    assert any(
        record.get("event_type") == "memory_refine"
        and record.get("parent_memory_id") == "cand_000001_tiny_memory_order_seed_001"
        and record.get("child_memory_id") == child["memory_id"]
        and record.get("trigger_reason") == "mixed_support_harmful"
        for record in update_records
    )
    assert any(
        record.get("replay_scope") == "support_task_replay"
        and record.get("attribution_label") == "harmful"
        for record in replay_records
    )


def test_verification_budget_skips_when_exhausted(tmp_path: Path) -> None:
    config_path = tmp_path / "config_nt_gate_budget.yaml"
    output_dir = tmp_path / "runs" / "nt_gate_budget"
    split_file = Path("data/task_splits/tiny_memory_dependent_tasks.json").resolve()
    support_split_file = Path("data/task_splits/tiny_support_verification_tasks.json").resolve()
    config_path.write_text(
        f"""
experiment:
  name: tiny_nt_gate_budget_test
  seed: 1
  output_dir: {output_dir.as_posix()}
benchmark:
  name: tiny_tools
  split_file: {split_file.as_posix()}
  max_tasks: 3
agent:
  type: react_tool_agent
  max_steps: 4
  memory_top_k: 1
models:
  actor:
    provider: mock
    model: mock-memory-sensitive-agent
    follow_memory_hints: true
    temperature: 0.0
    max_tokens: 512
memory:
  method: nt_memevo_gate
  top_k: 1
  save_successes: true
  save_failures: true
  extractor_model: deterministic_candidate_extractor_v1
  domain: retail
  ttl: 50
  utility:
    promote_after_helpful: 2
    quarantine_after_harmful: 1
  replay:
    enabled: true
    delta_threshold: 0.0
    max_memories: 1
    log_context_modes: true
    promote_requires_positive_lcb: true
  verification:
    enabled: true
    support_split_file: {support_split_file.as_posix()}
    max_support_tasks: 2
    min_support_tasks: 2
    min_support_similarity: 0.10
    require_intent_match: true
    require_domain_match: true
    min_helpful_before_verify: 2
    disable_immediate_promotion: true
    delta_threshold: 0.0
    min_delta_mean: 0.0
    min_lcb_delta_reward: 0.0
    max_negative_transfer_rate: 0.0
    max_verifications_per_run: 0
  gate:
    min_score: 0.30
    min_similarity: 0.02
    min_precondition: 0.25
    weight_utility: 0.60
    reject_negative_evidence: true
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
    assert metrics["verification_count"] == 0
    assert metrics["verification_budget_skipped_count"] == 1
    assert metrics["verification_budget_skip_reasons"] == {
        "max_verifications_per_run_exhausted": 1
    }
    assert metrics["support_replay_count"] == 0
    assert metrics["memory_refinement_count"] == 0

    update_records = [
        json.loads(line)
        for line in (output_dir / "memory_updates.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    assert any(
        record.get("event_type") == "verification_skipped"
        and record.get("skip_reason") == "max_verifications_per_run_exhausted"
        for record in update_records
    )


def test_nt_memevo_gate_rejects_polluted_bootstrap_memory(tmp_path: Path) -> None:
    config_path = tmp_path / "config_nt_gate_polluted.yaml"
    output_dir = tmp_path / "runs" / "nt_gate_polluted"
    split_file = Path("data/task_splits/tiny_tool_tasks.json").resolve()
    bootstrap_file = Path("data/memory_fixtures/tiny_polluted_candidates.jsonl").resolve()
    config_path.write_text(
        f"""
experiment:
  name: tiny_nt_gate_polluted_test
  seed: 1
  output_dir: {output_dir.as_posix()}
benchmark:
  name: tiny_tools
  split_file: {split_file.as_posix()}
  max_tasks: 3
agent:
  type: react_tool_agent
  max_steps: 4
  memory_top_k: 2
models:
  actor:
    provider: mock
    model: mock-memory-sensitive-agent
    follow_memory_hints: true
    temperature: 0.0
    max_tokens: 512
memory:
  method: nt_memevo_gate
  top_k: 2
  bootstrap_file: {bootstrap_file.as_posix()}
  save_successes: true
  save_failures: true
  extractor_model: deterministic_candidate_extractor_v1
  domain: retail
  ttl: 50
  gate:
    min_score: 0.30
    min_similarity: 0.02
    min_precondition: 0.25
    reject_negative_evidence: true
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
    assert metrics["negative_transfer_rate"] == 0.0
    assert metrics["gate_rejected_count"] >= 1
    assert metrics["gate_rejection_reasons"]["negative_evidence_present"] >= 1

    run_records = [
        json.loads(line)
        for line in (output_dir / "runs.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    update_records = [
        json.loads(line)
        for line in (output_dir / "memory_updates.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]

    assert all("polluted_refund_lookup_policy_001" not in record["used_memory_ids"] for record in run_records)
    assert any(record.get("event_type") == "bootstrap_candidate" for record in update_records)
    assert any(
        record.get("memory_id") == "polluted_refund_lookup_policy_001"
        and record.get("rejection_reason") == "negative_evidence_present"
        for record in update_records
    )


def test_unsafe_polluted_gate_triggers_negative_transfer_metric(tmp_path: Path) -> None:
    split_file = tmp_path / "refund_task.json"
    split_file.write_text(
        json.dumps(
            [
                {
                    "task_id": "tiny_refund_polluted_001",
                    "instruction": "Decide whether order ORD-1002 can be refunded.",
                    "expected_answer_contains": ["not refundable"],
                    "initial_state": {},
                }
            ]
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "config_nt_gate_unsafe_polluted.yaml"
    output_dir = tmp_path / "runs" / "nt_gate_unsafe_polluted"
    bootstrap_file = Path("data/memory_fixtures/tiny_polluted_candidates.jsonl").resolve()
    config_path.write_text(
        f"""
experiment:
  name: tiny_nt_gate_unsafe_polluted_test
  seed: 1
  output_dir: {output_dir.as_posix()}
benchmark:
  name: tiny_tools
  split_file: {split_file.as_posix()}
  max_tasks: 1
agent:
  type: react_tool_agent
  max_steps: 4
  memory_top_k: 1
models:
  actor:
    provider: mock
    model: mock-memory-sensitive-agent
    follow_memory_hints: true
    temperature: 0.0
    max_tokens: 512
memory:
  method: nt_memevo_gate
  top_k: 1
  bootstrap_file: {bootstrap_file.as_posix()}
  save_successes: true
  save_failures: true
  extractor_model: deterministic_candidate_extractor_v1
  domain: retail
  ttl: 50
  replay:
    enabled: true
    delta_threshold: 0.0
    max_memories: 1
    log_context_modes: true
    promote_requires_positive_lcb: true
  gate:
    min_score: -1.0
    min_similarity: 0.0
    min_precondition: 0.0
    max_risk: 1.0
    reject_negative_evidence: false
    allowed_statuses: ["candidate", "active", "quarantined"]
logging:
  save_raw_model_io: true
  save_trace_events: true
  save_costs: true
""",
        encoding="utf-8",
    )

    metrics = run(str(config_path))

    assert metrics["num_tasks"] == 1
    assert metrics["success_rate"] == 0.0
    assert metrics["with_memory_fail_no_memory_success"] == 1
    assert metrics["negative_transfer_rate"] == 1.0
    assert metrics["harmful_memory_ids"] == ["polluted_refund_lookup_policy_001"]
    assert metrics["utility_update_count"] == 1
    assert metrics["utility_harmful_count"] == 1
    assert metrics["replay_leave_one_count"] == 1
    assert metrics["replay_harmful_count"] == 1
    assert metrics["replay_utility_update_count"] == 1
    assert metrics["online_proxy_utility_update_count"] == 0
    assert metrics["quarantined_memory_count"] == 1

    candidate_records = [
        json.loads(line)
        for line in (output_dir / "candidate_memories.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    replay_records = [
        json.loads(line)
        for line in (output_dir / "replay_results.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    update_records = [
        json.loads(line)
        for line in (output_dir / "memory_updates.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    polluted = next(
        record for record in candidate_records if record["memory_id"] == "polluted_refund_lookup_policy_001"
    )

    assert polluted["utility"]["num_used"] == 3
    assert polluted["utility"]["num_harmful"] == 3
    assert polluted["lifecycle"]["status"] == "quarantined"
    assert polluted["lifecycle"]["last_used_iter"] == 1
    assert "tiny_nt_gate_unsafe_polluted_test_tiny_refund_polluted_001" in polluted["negative_evidence"]
    assert any(
        record.get("mode") == "leave_one_memory_out"
        and record.get("memory_id") == "polluted_refund_lookup_policy_001"
        and record.get("delta_reward") == -1.0
        and record.get("attribution_label") == "harmful"
        for record in replay_records
    )
    assert any(
        record.get("event_type") == "utility_update"
        and record.get("memory_id") == "polluted_refund_lookup_policy_001"
        and record.get("outcome") == "harmful"
        and record.get("credit_source") == "leave_one_memory_out"
        and record.get("replay_attribution_label") == "harmful"
        for record in update_records
    )
