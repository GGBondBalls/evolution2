from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ntmemevo.logging.run_logger import RunLogger


class TraceLogger:
    def __init__(self, run_logger: RunLogger, run_id: str) -> None:
        self.run_logger = run_logger
        self.run_id = run_id

    def log_event(self, task_id: str, step: int, event_type: str, payload: dict[str, Any]) -> None:
        record = {
            "run_id": self.run_id,
            "task_id": task_id,
            "step": step,
            "event_type": event_type,
            "created_at": datetime.now(UTC).isoformat(),
            **payload,
        }
        self.run_logger.append_jsonl("trace_events.jsonl", record)
