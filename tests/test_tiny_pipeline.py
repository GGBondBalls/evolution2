from __future__ import annotations

import json
from pathlib import Path

from ntmemevo.experiments.run_stream import run


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
