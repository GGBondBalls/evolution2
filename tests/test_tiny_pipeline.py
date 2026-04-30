from __future__ import annotations

import json
from pathlib import Path

from ntmemevo.experiments.run_stream import run
from ntmemevo.memory.extractor import CandidateExtractionContext, CandidateMemoryExtractor
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
