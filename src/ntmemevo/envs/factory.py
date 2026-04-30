from __future__ import annotations

from pathlib import Path
from typing import Any

from ntmemevo.envs.base import AgentEnv
from ntmemevo.envs.tau_bench import TauBenchEnv
from ntmemevo.envs.tiny_tools import TinyToolsEnv


def create_env(config: dict[str, Any]) -> AgentEnv:
    name = str(config.get("name", "")).lower()
    if name == "tiny_tools":
        return TinyToolsEnv(split_file=Path(config["split_file"]))
    if name == "tau_bench":
        return TauBenchEnv(config=config)
    raise ValueError(f"Unsupported benchmark: {name}")
