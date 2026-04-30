from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ntmemevo.types import AgentResult, Task


class RunLogger:
    def __init__(self, output_dir: str | Path, config_path: str | Path) -> None:
        self.output_dir = Path(output_dir)
        self.config_path = Path(config_path)

    def prepare(self, tasks: list[Task]) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.config_path, self.output_dir / "config.yaml")
        self._write_jsonl(self.output_dir / "tasks.jsonl", [self._task_record(task) for task in tasks], mode="w")
        for name in ["runs.jsonl", "trace_events.jsonl", "memories.jsonl", "memory_updates.jsonl", "replay_results.jsonl"]:
            path = self.output_dir / name
            path.write_text("", encoding="utf-8")

    def log_run(self, experiment_id: str, iteration: int, result: AgentResult, memory_policy: str) -> None:
        record = {
            "run_id": f"{experiment_id}_{result.task_id}",
            "experiment_id": experiment_id,
            "task_id": result.task_id,
            "iteration": iteration,
            "agent": "react_tool_agent",
            "memory_policy": memory_policy,
            "success": result.success,
            "reward": result.reward,
            "num_steps": result.num_steps,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "tool_calls": result.tool_calls,
            "used_memory_ids": list(result.used_memory_ids),
            "trace_summary": list(result.trace_summary),
            "error_type": result.error_type,
            "final_answer": result.final_answer,
        }
        self.append_jsonl("runs.jsonl", record)

    def write_metrics(self, metrics: dict[str, Any]) -> None:
        (self.output_dir / "metrics.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def append_jsonl(self, filename: str, record: dict[str, Any]) -> None:
        with (self.output_dir / filename).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _write_jsonl(self, path: Path, records: list[dict[str, Any]], mode: str = "a") -> None:
        with path.open(mode, encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _task_record(self, task: Task) -> dict[str, Any]:
        record = asdict(task)
        record["expected_answer_contains"] = list(task.expected_answer_contains)
        return record
