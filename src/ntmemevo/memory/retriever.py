from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence
from typing import Protocol

from ntmemevo.memory.raw_trace_store import RawTraceMemory
from ntmemevo.types import RetrievedMemory


TOKEN_RE = re.compile(r"[A-Za-z0-9_-]+")


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]


class LexicalMemory(Protocol):
    memory_id: str
    task_id: str
    success: bool
    reward: float
    created_iter: int

    @property
    def text(self) -> str:
        raise NotImplementedError


class LexicalMemoryRetriever:
    def __init__(self, memories: Sequence[LexicalMemory]) -> None:
        self.memories = list(memories)

    def retrieve(self, query: str, top_k: int) -> list[RetrievedMemory]:
        if top_k <= 0 or not self.memories:
            return []
        scored = [
            (self._score(query, memory), memory)
            for memory in self.memories
        ]
        scored = [(score, memory) for score, memory in scored if score > 0.0]
        scored.sort(key=lambda item: (-item[0], item[1].created_iter, item[1].memory_id))
        return [
            RetrievedMemory(
                memory_id=memory.memory_id,
                text=memory.text,
                score=score,
                metadata={
                    "task_id": memory.task_id,
                    "success": memory.success,
                    "reward": memory.reward,
                    "created_iter": memory.created_iter,
                    "memory_kind": memory.__class__.__name__,
                    "reflection_type": getattr(memory, "reflection_type", None),
                },
            )
            for score, memory in scored[:top_k]
        ]

    def _score(self, query: str, memory: LexicalMemory) -> float:
        query_terms = Counter(tokenize(query))
        memory_terms = Counter(tokenize(memory.text))
        if not query_terms or not memory_terms:
            return 0.0
        overlap = set(query_terms) & set(memory_terms)
        if not overlap:
            return 0.0
        dot = sum(query_terms[token] * memory_terms[token] for token in overlap)
        query_norm = math.sqrt(sum(value * value for value in query_terms.values()))
        memory_norm = math.sqrt(sum(value * value for value in memory_terms.values()))
        if query_norm == 0.0 or memory_norm == 0.0:
            return 0.0
        return dot / (query_norm * memory_norm)


class LexicalRawTraceRetriever(LexicalMemoryRetriever):
    def __init__(self, memories: list[RawTraceMemory]) -> None:
        super().__init__(memories)
