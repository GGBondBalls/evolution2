from __future__ import annotations

import argparse
import random
from typing import Any

from ntmemevo.agents.react_agent import ReActToolAgent
from ntmemevo.config import load_config
from ntmemevo.envs.factory import create_env
from ntmemevo.evaluation.metrics import aggregate_results
from ntmemevo.llm.client import create_llm_client
from ntmemevo.logging.run_logger import RunLogger
from ntmemevo.logging.trace_logger import TraceLogger
from ntmemevo.memory.raw_trace_store import RawTraceMemoryStore
from ntmemevo.memory.reflection_memory import ReflectionExtractor, ReflectionMemoryStore
from ntmemevo.memory.retriever import LexicalMemoryRetriever
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
    if memory_policy == "raw_trace_rag":
        memory_store = RawTraceMemoryStore(
            path=config.output_dir / "memories.jsonl",
            save_failures=bool(memory_config.get("save_failures", True)),
        )
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
    elif memory_policy not in {"none", "null"}:
        raise ValueError(f"Unsupported memory method: {memory_policy}")

    results: list[AgentResult] = []
    for index, task in enumerate(tasks, start=1):
        run_id = f"{experiment_id}_{task.task_id}"
        trace_logger = TraceLogger(run_logger=run_logger, run_id=run_id)

        memories = []
        if memory_store is not None:
            memories = LexicalMemoryRetriever(memory_store.all()).retrieve(
                query=task.instruction,
                top_k=memory_top_k,
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
            memory = memory_store.add_from_result(task=task, result=result, iteration=index)
            run_logger.append_jsonl(
                "memory_updates.jsonl",
                {
                    "event_type": "add",
                    "iteration": index,
                    "task_id": task.task_id,
                    "memory_policy": memory_policy,
                    "memory_id": memory.memory_id if memory else None,
                    "memory_kind": memory.__class__.__name__ if memory else None,
                    "reflection_type": getattr(memory, "reflection_type", None) if memory else None,
                    "success": result.success,
                    "reward": result.reward,
                },
            )

    metrics = aggregate_results(results)
    metrics["memory_policy"] = memory_policy
    metrics["memory_size"] = len(memory_store.all()) if memory_store is not None else 0
    metrics["memory_top_k"] = memory_top_k
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
