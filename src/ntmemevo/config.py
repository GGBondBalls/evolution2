from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ExperimentConfig:
    raw: dict[str, Any]
    path: Path

    @property
    def experiment(self) -> dict[str, Any]:
        return self.raw.get("experiment", {})

    @property
    def benchmark(self) -> dict[str, Any]:
        return self.raw.get("benchmark", {})

    @property
    def agent(self) -> dict[str, Any]:
        return self.raw.get("agent", {})

    @property
    def models(self) -> dict[str, Any]:
        return self.raw.get("models", {})

    @property
    def logging(self) -> dict[str, Any]:
        return self.raw.get("logging", {})

    @property
    def output_dir(self) -> Path:
        value = self.experiment.get("output_dir")
        if not value:
            name = self.experiment.get("name", "experiment")
            value = f"runs/{name}"
        return Path(value)


def load_config(path: str | Path) -> ExperimentConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping: {config_path}")

    _require_sections(data, ["experiment", "benchmark", "agent", "models"])
    return ExperimentConfig(raw=data, path=config_path)


def _require_sections(data: dict[str, Any], sections: list[str]) -> None:
    missing = [section for section in sections if section not in data]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Config is missing required section(s): {joined}")
