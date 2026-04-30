from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


ALLOWED_MEMORY_TYPES = {
    "strategy",
    "warning",
    "constraint",
    "tool_usage",
    "bug_pattern",
    "user_policy",
}
ALLOWED_LIFECYCLE_STATUSES = {"candidate", "active", "quarantined", "retired"}


@dataclass(frozen=True)
class MemoryScope:
    benchmark: str
    domain: str
    intent: str
    tool_names: tuple[str, ...] = ()
    preconditions: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["tool_names"] = list(self.tool_names)
        data["preconditions"] = list(self.preconditions)
        return data

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "MemoryScope":
        return cls(
            benchmark=str(data["benchmark"]),
            domain=str(data["domain"]),
            intent=str(data["intent"]),
            tool_names=tuple(str(item) for item in data.get("tool_names", [])),
            preconditions=tuple(str(item) for item in data.get("preconditions", [])),
        )


@dataclass(frozen=True)
class MemoryUtility:
    alpha: float = 1.0
    beta: float = 1.0
    mean_delta_reward: float = 0.0
    lcb_delta_reward: float = 0.0
    num_used: int = 0
    num_helpful: int = 0
    num_harmful: int = 0

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict[str, Any] | None) -> "MemoryUtility":
        data = data or {}
        return cls(
            alpha=float(data.get("alpha", 1.0)),
            beta=float(data.get("beta", 1.0)),
            mean_delta_reward=float(data.get("mean_delta_reward", 0.0)),
            lcb_delta_reward=float(data.get("lcb_delta_reward", 0.0)),
            num_used=int(data.get("num_used", 0)),
            num_helpful=int(data.get("num_helpful", 0)),
            num_harmful=int(data.get("num_harmful", 0)),
        )


@dataclass(frozen=True)
class MemoryLifecycle:
    status: str = "candidate"
    created_iter: int = 0
    last_used_iter: int | None = None
    ttl: int = 50

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict[str, Any] | None) -> "MemoryLifecycle":
        data = data or {}
        last_used = data.get("last_used_iter")
        return cls(
            status=str(data.get("status", "candidate")),
            created_iter=int(data.get("created_iter", 0)),
            last_used_iter=int(last_used) if last_used is not None else None,
            ttl=int(data.get("ttl", 50)),
        )


@dataclass(frozen=True)
class MemorySource:
    created_from: tuple[str, ...]
    extractor_model: str
    prompt_hash: str

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["created_from"] = list(self.created_from)
        return data

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "MemorySource":
        return cls(
            created_from=tuple(str(item) for item in data.get("created_from", [])),
            extractor_model=str(data["extractor_model"]),
            prompt_hash=str(data["prompt_hash"]),
        )


@dataclass(frozen=True)
class CandidateMemory:
    memory_id: str
    type: str
    claim: str
    scope: MemoryScope
    action_hint: str
    avoid_hint: str
    positive_evidence: tuple[str, ...] = ()
    negative_evidence: tuple[str, ...] = ()
    utility: MemoryUtility = field(default_factory=MemoryUtility)
    lifecycle: MemoryLifecycle = field(default_factory=MemoryLifecycle)
    source: MemorySource = field(
        default_factory=lambda: MemorySource(
            created_from=(),
            extractor_model="unknown",
            prompt_hash="",
        )
    )

    @property
    def text(self) -> str:
        tools = ", ".join(self.scope.tool_names) if self.scope.tool_names else "no tool"
        return (
            f"{self.type}: {self.claim} "
            f"Scope={self.scope.benchmark}/{self.scope.domain}/{self.scope.intent}. "
            f"Tools={tools}. Action hint: {self.action_hint} "
            f"Avoid: {self.avoid_hint}"
        )

    def validate(self) -> None:
        validate_candidate_memory_json(self.to_json())

    def to_json(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "type": self.type,
            "claim": self.claim,
            "scope": self.scope.to_json(),
            "action_hint": self.action_hint,
            "avoid_hint": self.avoid_hint,
            "positive_evidence": list(self.positive_evidence),
            "negative_evidence": list(self.negative_evidence),
            "utility": self.utility.to_json(),
            "lifecycle": self.lifecycle.to_json(),
            "source": self.source.to_json(),
            "text": self.text,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "CandidateMemory":
        validate_candidate_memory_json(data)
        return cls(
            memory_id=str(data["memory_id"]),
            type=str(data["type"]),
            claim=str(data["claim"]),
            scope=MemoryScope.from_json(data["scope"]),
            action_hint=str(data["action_hint"]),
            avoid_hint=str(data["avoid_hint"]),
            positive_evidence=tuple(str(item) for item in data.get("positive_evidence", [])),
            negative_evidence=tuple(str(item) for item in data.get("negative_evidence", [])),
            utility=MemoryUtility.from_json(data.get("utility")),
            lifecycle=MemoryLifecycle.from_json(data.get("lifecycle")),
            source=MemorySource.from_json(data["source"]),
        )


def candidate_memory_json_schema() -> dict[str, Any]:
    return {
        "required": [
            "memory_id",
            "type",
            "claim",
            "scope",
            "action_hint",
            "avoid_hint",
            "positive_evidence",
            "negative_evidence",
            "utility",
            "lifecycle",
            "source",
        ],
        "scope_required": ["benchmark", "domain", "intent", "tool_names", "preconditions"],
        "utility_required": [
            "alpha",
            "beta",
            "mean_delta_reward",
            "lcb_delta_reward",
            "num_used",
            "num_helpful",
            "num_harmful",
        ],
        "lifecycle_required": ["status", "created_iter", "last_used_iter", "ttl"],
        "source_required": ["created_from", "extractor_model", "prompt_hash"],
        "allowed_memory_types": sorted(ALLOWED_MEMORY_TYPES),
        "allowed_lifecycle_statuses": sorted(ALLOWED_LIFECYCLE_STATUSES),
    }


def validate_candidate_memory_json(data: dict[str, Any]) -> None:
    schema = candidate_memory_json_schema()
    _require_keys(data, schema["required"], "candidate memory")

    for key in ["memory_id", "type", "claim", "action_hint", "avoid_hint"]:
        if not isinstance(data[key], str) or not data[key].strip():
            raise ValueError(f"{key} must be a non-empty string")
    if data["type"] not in ALLOWED_MEMORY_TYPES:
        allowed = ", ".join(sorted(ALLOWED_MEMORY_TYPES))
        raise ValueError(f"type must be one of: {allowed}")

    _validate_scope(data["scope"], schema["scope_required"])
    _validate_string_list(data["positive_evidence"], "positive_evidence")
    _validate_string_list(data["negative_evidence"], "negative_evidence")
    if not data["positive_evidence"] and not data["negative_evidence"]:
        raise ValueError("candidate memory must contain at least one evidence id")
    _validate_utility(data["utility"], schema["utility_required"])
    _validate_lifecycle(data["lifecycle"], schema["lifecycle_required"])
    _validate_source(data["source"], schema["source_required"])


def canonical_json_hash_payload(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _require_keys(data: dict[str, Any], required: list[str], label: str) -> None:
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"{label} is missing required field(s): {', '.join(missing)}")


def _validate_scope(data: Any, required: list[str]) -> None:
    if not isinstance(data, dict):
        raise ValueError("scope must be an object")
    _require_keys(data, required, "scope")
    for key in ["benchmark", "domain", "intent"]:
        if not isinstance(data[key], str) or not data[key].strip():
            raise ValueError(f"scope.{key} must be a non-empty string")
    _validate_string_list(data["tool_names"], "scope.tool_names")
    _validate_string_list(data["preconditions"], "scope.preconditions")


def _validate_utility(data: Any, required: list[str]) -> None:
    if not isinstance(data, dict):
        raise ValueError("utility must be an object")
    _require_keys(data, required, "utility")
    for key in ["alpha", "beta", "mean_delta_reward", "lcb_delta_reward"]:
        if not isinstance(data[key], int | float):
            raise ValueError(f"utility.{key} must be numeric")
    for key in ["num_used", "num_helpful", "num_harmful"]:
        if not isinstance(data[key], int) or data[key] < 0:
            raise ValueError(f"utility.{key} must be a non-negative integer")
    if data["alpha"] < 0 or data["beta"] < 0:
        raise ValueError("utility alpha and beta must be non-negative")


def _validate_lifecycle(data: Any, required: list[str]) -> None:
    if not isinstance(data, dict):
        raise ValueError("lifecycle must be an object")
    _require_keys(data, required, "lifecycle")
    if data["status"] not in ALLOWED_LIFECYCLE_STATUSES:
        allowed = ", ".join(sorted(ALLOWED_LIFECYCLE_STATUSES))
        raise ValueError(f"lifecycle.status must be one of: {allowed}")
    if not isinstance(data["created_iter"], int) or data["created_iter"] < 0:
        raise ValueError("lifecycle.created_iter must be a non-negative integer")
    last_used = data["last_used_iter"]
    if last_used is not None and (not isinstance(last_used, int) or last_used < 0):
        raise ValueError("lifecycle.last_used_iter must be null or a non-negative integer")
    if not isinstance(data["ttl"], int) or data["ttl"] <= 0:
        raise ValueError("lifecycle.ttl must be a positive integer")


def _validate_source(data: Any, required: list[str]) -> None:
    if not isinstance(data, dict):
        raise ValueError("source must be an object")
    _require_keys(data, required, "source")
    _validate_string_list(data["created_from"], "source.created_from")
    if not data["created_from"]:
        raise ValueError("source.created_from must not be empty")
    for key in ["extractor_model", "prompt_hash"]:
        if not isinstance(data[key], str) or not data[key].strip():
            raise ValueError(f"source.{key} must be a non-empty string")


def _validate_string_list(value: Any, label: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{label} must contain only non-empty strings")
