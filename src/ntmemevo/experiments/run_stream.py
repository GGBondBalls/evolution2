from __future__ import annotations

import argparse
import random
from collections import Counter
from pathlib import Path
from typing import Any

from ntmemevo.agents.react_agent import ReActToolAgent
from ntmemevo.config import load_config
from ntmemevo.envs.factory import create_env
from ntmemevo.evaluation.metrics import aggregate_negative_transfer, aggregate_results
from ntmemevo.llm.client import create_llm_client
from ntmemevo.logging.run_logger import RunLogger
from ntmemevo.logging.trace_logger import TraceLogger
from ntmemevo.memory.extractor import CandidateMemoryExtractor
from ntmemevo.memory.gate import GateDecision, RetrieverGate, RetrieverGateConfig
from ntmemevo.memory.raw_trace_store import RawTraceMemoryStore
from ntmemevo.memory.reflection_memory import ReflectionExtractor, ReflectionMemoryStore
from ntmemevo.memory.retriever import LexicalMemoryRetriever
from ntmemevo.memory.store import CandidateMemoryStore
from ntmemevo.types import AgentResult


def run(config_path: str) -> dict[str, Any]:
    config = load_config(config_path)
    seed = int(config.experiment.get("seed", 0))
    random.seed(seed)

    env = create_env(config.benchmark)
    max_tasks = config.benchmark.get("max_tasks")
    tasks = env.load_tasks(max_tasks=int(max_tasks) if max_tasks is not None else None)

    actor_config = config.models.get("actor", {})
    llm = create_llm_client(actor_config)
    agent = ReActToolAgent(
        llm=llm,
        model_config=actor_config,
        max_steps=int(config.agent.get("max_steps", 8)),
        memory_top_k=int(config.agent.get("memory_top_k", 0)),
    )

    run_logger = RunLogger(output_dir=config.output_dir, config_path=config.path)
    run_logger.prepare(tasks)

    experiment_id = str(config.experiment.get("name", "experiment"))
    memory_config = config.raw.get("memory", {})
    memory_policy = str(memory_config.get("method", "none")).lower()
    memory_top_k = int(memory_config.get("top_k", config.agent.get("memory_top_k", 0)))
    memory_store = None
    gate_config: RetrieverGateConfig | None = None
    retrieval_enabled = False
    gate_decisions: list[GateDecision] = []
    if memory_policy == "raw_trace_rag":
        memory_store = RawTraceMemoryStore(
            path=config.output_dir / "memories.jsonl",
            save_failures=bool(memory_config.get("save_failures", True)),
        )
        retrieval_enabled = True
    elif memory_policy == "reflexion":
        extractor = ReflectionExtractor(
            max_reflection_chars=int(memory_config.get("max_reflection_chars", 700)),
        )
        memory_store = ReflectionMemoryStore(
            path=config.output_dir / "memories.jsonl",
            save_successes=bool(memory_config.get("save_successes", True)),
            save_failures=bool(memory_config.get("save_failures", True)),
            extractor=extractor,
        )
        retrieval_enabled = True
    elif memory_policy in {"nt_memevo_candidate", "nt_memevo_gate"}:
        extractor = CandidateMemoryExtractor(
            extractor_model=str(
                memory_config.get("extractor_model", "deterministic_candidate_extractor_v1")
            ),
            domain=str(memory_config.get("domain", "retail")),
            ttl=int(memory_config.get("ttl", 50)),
            max_claim_chars=int(memory_config.get("max_claim_chars", 700)),
        )
        memory_store = CandidateMemoryStore(
            path=config.output_dir / "candidate_memories.jsonl",
            benchmark=str(config.benchmark.get("name", "unknown_benchmark")),
            experiment_id=experiment_id,
            save_successes=bool(memory_config.get("save_successes", True)),
            save_failures=bool(memory_config.get("save_failures", True)),
            extractor=extractor,
        )
        if memory_policy == "nt_memevo_gate":
            retrieval_enabled = True
            gate_config = RetrieverGateConfig.from_config(memory_config, top_k=memory_top_k)
        bootstrap_file = memory_config.get("bootstrap_file")
        if bootstrap_file:
            bootstrap_path = Path(str(bootstrap_file))
            imported = memory_store.import_jsonl(bootstrap_path, append_to_store_file=True)
            for memory in imported:
                run_logger.append_jsonl(
                    "memory_updates.jsonl",
                    {
                        "event_type": "bootstrap_candidate",
                        "iteration": 0,
                        "task_id": None,
                        "memory_policy": memory_policy,
                        "memory_id": memory.memory_id,
                        "candidate_type": memory.type,
                        "candidate_status": memory.lifecycle.status,
                        "positive_evidence": list(memory.positive_evidence),
                        "negative_evidence": list(memory.negative_evidence),
                    },
                )
    elif memory_policy not in {"none", "null"}:
        raise ValueError(f"Unsupported memory method: {memory_policy}")
    effective_memory_top_k = memory_top_k if retrieval_enabled else 0

    results: list[AgentResult] = []
    for index, task in enumerate(tasks, start=1):
        run_id = f"{experiment_id}_{task.task_id}"
        trace_logger = TraceLogger(run_logger=run_logger, run_id=run_id)

        memories = []
        if memory_store is not None and retrieval_enabled:
            if memory_policy == "nt_memevo_gate":
                if gate_config is None:
                    raise RuntimeError("nt_memevo_gate requires a RetrieverGateConfig")
                memories, current_gate_decisions = RetrieverGate(
                    memories=memory_store.all(),
                    config=gate_config,
                ).retrieve(
                    task=task,
                    iteration=index,
                    top_k=effective_memory_top_k,
                )
                gate_decisions.extend(current_gate_decisions)
                for decision in current_gate_decisions:
                    record = decision.to_json()
                    record.update(
                        {
                            "event_type": "gate_decision",
                            "iteration": index,
                            "memory_policy": memory_policy,
                        }
                    )
                    run_logger.append_jsonl("memory_updates.jsonl", record)
            else:
                memories = LexicalMemoryRetriever(memory_store.all()).retrieve(
                    query=task.instruction,
                    top_k=effective_memory_top_k,
                )
            run_logger.append_jsonl(
                "memory_updates.jsonl",
                {
                    "event_type": "retrieve",
                    "iteration": index,
                    "task_id": task.task_id,
                    "memory_policy": memory_policy,
                    "retrieved_memory_ids": [memory.memory_id for memory in memories],
                    "retrieved_scores": [memory.score for memory in memories],
                    "retrieved_memory_kinds": [memory.metadata.get("memory_kind") for memory in memories],
                    "retrieved_candidate_types": [
                        memory.metadata.get("candidate_type") for memory in memories
                    ],
                },
            )

        result = agent.run(task=task, env=env, trace_logger=trace_logger, memories=memories)
        results.append(result)
        run_logger.log_run(
            experiment_id=experiment_id,
            iteration=index,
            result=result,
            memory_policy=memory_policy,
        )

        if memory_store is not None:
            if memory_policy in {"nt_memevo_candidate", "nt_memevo_gate"}:
                memory = memory_store.add_from_result(
                    task=task,
                    result=result,
                    iteration=index,
                    run_id=run_id,
                )
            else:
                memory = memory_store.add_from_result(task=task, result=result, iteration=index)
            event_type = (
                "candidate_extract"
                if memory_policy in {"nt_memevo_candidate", "nt_memevo_gate"}
                else "add"
            )
            run_logger.append_jsonl(
                "memory_updates.jsonl",
                {
                    "event_type": event_type,
                    "iteration": index,
                    "task_id": task.task_id,
                    "memory_policy": memory_policy,
                    "memory_id": memory.memory_id if memory else None,
                    "memory_kind": memory.__class__.__name__ if memory else None,
                    "candidate_type": getattr(memory, "type", None) if memory else None,
                    "candidate_status": (
                        getattr(memory, "lifecycle", None).status
                        if memory and getattr(memory, "lifecycle", None)
                        else None
                    ),
                    "reflection_type": getattr(memory, "reflection_type", None) if memory else None,
                    "positive_evidence": (
                        list(getattr(memory, "positive_evidence", ())) if memory else []
                    ),
                    "negative_evidence": (
                        list(getattr(memory, "negative_evidence", ())) if memory else []
                    ),
                    "success": result.success,
                    "reward": result.reward,
                },
            )

    metrics = aggregate_results(results)
    no_memory_success_by_task = {
        task.task_id: bool(task.metadata.get("no_memory_success", True))
        for task in tasks
    }
    metrics.update(
        aggregate_negative_transfer(
            results=results,
            no_memory_success_by_task=no_memory_success_by_task,
        )
    )
    metrics["memory_policy"] = memory_policy
    metrics["memory_size"] = len(memory_store.all()) if memory_store is not None else 0
    metrics["memory_top_k"] = effective_memory_top_k
    gate_reason_counts = Counter(
        decision.rejection_reason or "accepted"
        for decision in gate_decisions
    )
    metrics["gate_decision_count"] = len(gate_decisions)
    metrics["gate_accepted_count"] = sum(
        1 for decision in gate_decisions if decision.gate_decision == "accept"
    )
    metrics["gate_rejected_count"] = sum(
        1 for decision in gate_decisions if decision.gate_decision == "reject"
    )
    metrics["gate_rejection_reasons"] = dict(sorted(gate_reason_counts.items()))
    run_logger.write_metrics(metrics)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a streaming NT-MemEvo experiment.")
    parser.add_argument("--config", required=True, help="Path to a YAML experiment config.")
    args = parser.parse_args()
    metrics = run(args.config)
    print("Experiment complete.")
    for key, value in metrics.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
