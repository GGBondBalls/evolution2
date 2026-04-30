from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ntmemevo.types import ChatMessage


def request_hash(messages: list[ChatMessage], model: str, params: dict[str, Any]) -> str:
    payload = {
        "messages": [message.__dict__ for message in messages],
        "model": model,
        "params": params,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class JsonCache:
    def __init__(self, path: str | Path | None) -> None:
        self.path = Path(path) if path else None
        self._items: dict[str, dict[str, Any]] = {}
        if self.path and self.path.exists():
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    self._items[record["key"]] = record["value"]

    def get(self, key: str) -> dict[str, Any] | None:
        return self._items.get(key)

    def set(self, key: str, value: dict[str, Any]) -> None:
        self._items[key] = value
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"key": key, "value": value}, ensure_ascii=False) + "\n")
