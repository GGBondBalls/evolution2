from __future__ import annotations

import json
from pathlib import Path

from ntmemevo.memory.extractor import CandidateExtractionContext, CandidateMemoryExtractor
from ntmemevo.memory.schema import CandidateMemory
from ntmemevo.types import AgentResult, Task


class CandidateMemoryStore:
    def __init__(
        self,
        path: str | Path,
        benchmark: str,
        experiment_id: str,
        save_successes: bool = True,
        save_failures: bool = True,
        extractor: CandidateMemoryExtractor | None = None,
    ) -> None:
        self.path = Path(path)
        self.benchmark = benchmark
        self.experiment_id = experiment_id
        self.save_successes = save_successes
        self.save_failures = save_failures
        self.extractor = extractor or CandidateMemoryExtractor()
        self.memories: list[CandidateMemory] = []
        if self.path.exists() and self.path.stat().st_size > 0:
            self.load()

    def load(self) -> None:
        self.memories = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                self.memories.append(CandidateMemory.from_json(json.loads(line)))

    def add_from_result(
        self,
        task: Task,
        result: AgentResult,
        iteration: int,
        run_id: str | None = None,
    ) -> CandidateMemory | None:
        if result.success and not self.save_successes:
            return None
        if not result.success and not self.save_failures:
            return None
        source_run_id = run_id or f"{self.experiment_id}_{task.task_id}"
        memory = self.extractor.extract(
            task=task,
            result=result,
            context=CandidateExtractionContext(
                benchmark=self.benchmark,
                experiment_id=self.experiment_id,
                run_id=source_run_id,
                iteration=iteration,
            ),
        )
        self.memories.append(memory)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(memory.to_json(), ensure_ascii=False) + "\n")
        return memory

    def import_jsonl(self, path: str | Path, append_to_store_file: bool = True) -> list[CandidateMemory]:
        source_path = Path(path)
        imported: list[CandidateMemory] = []
        if not source_path.exists():
            raise FileNotFoundError(f"Candidate memory bootstrap file not found: {source_path}")

        existing_ids = {memory.memory_id for memory in self.memories}
        with source_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                memory = CandidateMemory.from_json(json.loads(line))
                if memory.memory_id in existing_ids:
                    raise ValueError(f"Duplicate candidate memory id: {memory.memory_id}")
                existing_ids.add(memory.memory_id)
                imported.append(memory)

        self.memories.extend(imported)
        if append_to_store_file and imported:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                for memory in imported:
                    handle.write(json.dumps(memory.to_json(), ensure_ascii=False) + "\n")
        return imported

    def all(self) -> list[CandidateMemory]:
        return list(self.memories)
