from __future__ import annotations

from abc import ABC, abstractmethod

from ntmemevo.envs.base import AgentEnv
from ntmemevo.logging.trace_logger import TraceLogger
from ntmemevo.types import AgentResult, RetrievedMemory, Task


class Agent(ABC):
    @abstractmethod
    def run(
        self,
        task: Task,
        env: AgentEnv,
        trace_logger: TraceLogger,
        memories: list[RetrievedMemory] | None = None,
    ) -> AgentResult:
        raise NotImplementedError
