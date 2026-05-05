from __future__ import annotations

import argparse
import random
from collections import Counter
from pathlib import Path
from typing import Any

from ntmemevo.agents.action_replay_agent import ActionReplayAgent
from ntmemevo.agents.react_agent import ReActToolAgent
from ntmemevo.config import load_config
from ntmemevo.envs.factory import create_env
from ntmemevo.evaluation.metrics import aggregate_negative_transfer, aggregate_results
from ntmemevo.evaluation.replay import ReplayConfig, ReplayResult, run_memory_replays
from ntmemevo.evaluation.verification import (
    MemoryVerifier,
    VerificationConfig,
    VerificationResult,
)
from ntmemevo.llm.client import create_llm_client
from ntmemevo.logging.run_logger import RunLogger
from ntmemevo.logging.trace_logger import TraceLogger
from ntmemevo.memory.extractor import CandidateMemoryExtractor
from ntmemevo.memory.gate import GateDecision, RetrieverGate, RetrieverGateConfig
from ntmemevo.memory.raw_trace_store import RawTraceMemoryStore
from ntmemevo.memory.reflection_memory import ReflectionExtractor, ReflectionMemoryStore
from ntmemevo.memory.retriever import LexicalMemoryRetriever
from ntmemevo.memory.store import (
    CandidateMemoryStore,
    ScopeRefinementUpdate,
    UtilityUpdate,
    VerificationUpdate,
)
from ntmemevo.types import AgentResult


def run(config_path: str) -> dict[str, Any]:
    config = load_config(config_path)
    seed = int(config.experiment.get("seed", 0))
    random.seed(seed)

    env = create_env(config.benchmark)
    max_tasks = config.benchmark.get("max_tasks")
    tasks = env.load_tasks(max_tasks=int(max_tasks) if max_tasks is not None else None)

    actor_config = config.models.get("actor", {})
    agent_type = str(config.agent.get("type", "react_tool_agent")).lower()
    max_steps = int(config.agent.get("max_steps", 8))
    if agent_type in {"action_replay", "action_replay_agent", "scripted_expected_actions"}:
        agent = ActionReplayAgent(max_steps=max_steps)
        run_agent_label = "action_replay_agent"
    elif agent_type == "react_tool_agent":
        llm = create_llm_client(actor_config)
        agent = ReActToolAgent(
            llm=llm,
            model_config=actor_config,
            max_steps=max_steps,
            memory_top_k=int(config.agent.get("memory_top_k", 0)),
            log_raw_model_io=bool(config.logging.get("save_raw_model_io", False)),
            stop_after_expected_actions=bool(
                config.agent.get("stop_after_expected_actions", False)
            ),
        )
        run_agent_label = "react_tool_agent"
    else:
        raise ValueError(f"Unsupported agent.type: {agent_type}")

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
    utility_updates: list[UtilityUpdate] = []
    utility_config = memory_config.get("utility", {}) or {}
    promote_after_helpful = int(utility_config.get("promote_after_helpful", 2))
    quarantine_after_harmful = int(utility_config.get("quarantine_after_harmful", 1))
    replay_config = ReplayConfig.from_config(memory_config.get("replay"))
    replay_results: list[ReplayResult] = []
    verification_config = VerificationConfig.from_config(memory_config.get("verification"))
    verification_results: list[VerificationResult] = []
    verification_updates: list[VerificationUpdate] = []
    refinement_updates: list[ScopeRefinementUpdate] = []
    verified_memory_ids: set[str] = set()
    verification_budget_skips: Counter[str] = Counter()
    support_tasks = []
    support_benchmark_config: dict[str, Any] | None = None
    if verification_config.enabled:
        if verification_config.support_split_file is None:
            raise ValueError(
                "memory.verification.support_split_file is required when verification is enabled"
            )
        support_benchmark_config = dict(config.benchmark)
        support_benchmark_config["split_file"] = str(verification_config.support_split_file)
        support_env = create_env(support_benchmark_config)
        support_tasks = support_env.load_tasks()
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
    no_memory_success_by_task = {
        task.task_id: bool(task.metadata.get("no_memory_success", True))
        for task in tasks
    }
    no_memory_reward_by_task = {
        task.task_id: task.metadata.get("no_memory_reward")
        for task in tasks
    }

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
            agent_type=run_agent_label,
        )
        if (
            memory_policy == "nt_memevo_gate"
            and isinstance(memory_store, CandidateMemoryStore)
            and result.used_memory_ids
        ):
            replay_updates_by_memory_id: dict[str, ReplayResult] = {}
            if replay_config.enabled:
                selected_memories = [
                    memory
                    for memory in memories
                    if memory.memory_id in set(result.used_memory_ids)
                ]
                current_replay_results = run_memory_replays(
                    task=task,
                    agent=agent,
                    env_factory=lambda: create_env(config.benchmark),
                    source_run_id=run_id,
                    selected_memories=selected_memories,
                    config=replay_config,
                )
                replay_results.extend(current_replay_results)
                for replay_result in current_replay_results:
                    run_logger.append_jsonl(
                        "replay_results.jsonl",
                        replay_result.to_json(),
                    )
                    if (
                        replay_result.mode == "leave_one_memory_out"
                        and replay_result.memory_id is not None
                    ):
                        replay_updates_by_memory_id[replay_result.memory_id] = replay_result

            for memory_id in result.used_memory_ids:
                replay_result = replay_updates_by_memory_id.get(memory_id)
                if (
                    replay_result is not None
                    and replay_result.with_reward is not None
                    and replay_result.without_reward is not None
                    and replay_result.delta_reward is not None
                ):
                    update = memory_store.update_utility_from_replay(
                        memory_id=memory_id,
                        source_run_id=run_id,
                        replay_id=replay_result.replay_id,
                        iteration=index,
                        with_reward=replay_result.with_reward,
                        without_reward=replay_result.without_reward,
                        delta_reward=replay_result.delta_reward,
                        attribution_label=replay_result.attribution_label,
                        promote_after_helpful=promote_after_helpful,
                        quarantine_after_harmful=quarantine_after_harmful,
                        promote_requires_positive_lcb=(
                            replay_config.promote_requires_positive_lcb
                        ),
                        allow_promotion=_allow_immediate_promotion(verification_config),
                    )
                else:
                    update = memory_store.update_utility(
                        memory_id=memory_id,
                        result=result,
                        iteration=index,
                        run_id=run_id,
                        no_memory_success=no_memory_success_by_task.get(task.task_id, True),
                        no_memory_reward=no_memory_reward_by_task.get(task.task_id),
                        promote_after_helpful=promote_after_helpful,
                        quarantine_after_harmful=quarantine_after_harmful,
                        allow_promotion=_allow_immediate_promotion(verification_config),
                    )
                utility_updates.append(update)
                record = update.to_json()
                record.update(
                    {
                        "event_type": "utility_update",
                        "iteration": index,
                        "task_id": task.task_id,
                        "run_id": run_id,
                        "memory_policy": memory_policy,
                        "success": result.success,
                        "reward": result.reward,
                        "error_type": result.error_type,
                    }
                )
                if replay_result is not None:
                    record.update(
                        {
                            "replay_mode": replay_result.mode,
                            "replay_attribution_label": replay_result.attribution_label,
                            "replay_with_reward": replay_result.with_reward,
                            "replay_without_reward": replay_result.without_reward,
                            "replay_delta_reward": replay_result.delta_reward,
                            "replay_with_success": replay_result.with_success,
                            "replay_without_success": replay_result.without_success,
                        }
                    )
                run_logger.append_jsonl("memory_updates.jsonl", record)
                if _should_verify_memory(
                    update=update,
                    verification_config=verification_config,
                    verified_memory_ids=verified_memory_ids,
                ):
                    budget_skip_reason = _verification_budget_skip_reason(
                        verification_config=verification_config,
                        verification_count=len(verification_results),
                        support_replay_count=sum(
                            1
                            for replay_result in replay_results
                            if replay_result.replay_scope == "support_task_replay"
                        ),
                    )
                    if budget_skip_reason is not None:
                        verification_budget_skips[budget_skip_reason] += 1
                        run_logger.append_jsonl(
                            "memory_updates.jsonl",
                            {
                                "event_type": "verification_skipped",
                                "iteration": index,
                                "task_id": task.task_id,
                                "run_id": run_id,
                                "memory_policy": memory_policy,
                                "memory_id": memory_id,
                                "skip_reason": budget_skip_reason,
                                "verification_count": len(verification_results),
                            },
                        )
                        continue
                    if support_benchmark_config is None:
                        raise RuntimeError("Verification support benchmark is not configured")
                    candidate = memory_store.get(memory_id)
                    verification_result, support_replay_results = MemoryVerifier(
                        agent=agent,
                        env_factory=lambda: create_env(support_benchmark_config),
                        support_tasks=support_tasks,
                        config=verification_config,
                    ).verify(
                        memory=candidate,
                        source_run_id=run_id,
                    )
                    verified_memory_ids.add(memory_id)
                    verification_results.append(verification_result)
                    replay_results.extend(support_replay_results)
                    for support_replay_result in support_replay_results:
                        run_logger.append_jsonl(
                            "replay_results.jsonl",
                            support_replay_result.to_json(),
                        )
                    if verification_config.log_support_selection:
                        for support_detail in verification_result.support_match_details:
                            selection_record = dict(support_detail)
                            support_task_id = selection_record.get("task_id")
                            selection_record.update(
                                {
                                    "event_type": "support_selection",
                                    "iteration": index,
                                    "task_id": task.task_id,
                                    "source_task_id": task.task_id,
                                    "support_task_id": support_task_id,
                                    "run_id": run_id,
                                    "memory_policy": memory_policy,
                                    "memory_id": memory_id,
                                    "verification_id": verification_result.verification_id,
                                }
                            )
                            run_logger.append_jsonl(
                                "memory_updates.jsonl",
                                selection_record,
                            )
                    verification_update = memory_store.apply_verification_result(
                        memory_id=memory_id,
                        verification_id=verification_result.verification_id,
                        source_run_id=verification_result.source_run_id,
                        support_task_ids=verification_result.support_task_ids,
                        support_delta_mean=verification_result.support_delta_mean,
                        support_lcb_delta_reward=(
                            verification_result.support_lcb_delta_reward
                        ),
                        support_negative_transfer_rate=(
                            verification_result.support_negative_transfer_rate
                        ),
                        support_replay_count=verification_result.support_replay_count,
                        support_replay_helpful_count=(
                            verification_result.support_replay_helpful_count
                        ),
                        support_replay_harmful_count=(
                            verification_result.support_replay_harmful_count
                        ),
                        support_replay_neutral_count=(
                            verification_result.support_replay_neutral_count
                        ),
                        verification_passed=verification_result.verification_passed,
                        failure_reason=verification_result.failure_reason,
                        positive_evidence_ids=verification_result.positive_evidence_ids,
                        negative_evidence_ids=verification_result.negative_evidence_ids,
                        quarantine_on_negative_transfer=(
                            verification_config.quarantine_on_negative_transfer
                        ),
                        retire_on_verification_failure=(
                            verification_config.retire_on_verification_failure
                        ),
                    )
                    verification_updates.append(verification_update)
                    verification_record = verification_update.to_json()
                    verification_record.update(
                        {
                            "event_type": "verification_update",
                            "iteration": index,
                            "task_id": task.task_id,
                            "run_id": run_id,
                            "memory_policy": memory_policy,
                        }
                    )
                    run_logger.append_jsonl("memory_updates.jsonl", verification_record)
                    if (
                        verification_config.enable_scope_refinement
                        and not verification_result.verification_passed
                    ):
                        refinement_update = memory_store.refine_scope_from_verification(
                            memory_id=memory_id,
                            verification_id=verification_result.verification_id,
                            source_run_id=verification_result.source_run_id,
                            iteration=index,
                            support_match_details=verification_result.support_match_details,
                            min_helpful=verification_config.min_refinement_helpful,
                            refined_status=verification_config.refined_memory_status,
                            quarantine_parent=(
                                verification_config.quarantine_parent_on_refinement
                            ),
                        )
                        if refinement_update is not None:
                            refinement_updates.append(refinement_update)
                            refinement_record = refinement_update.to_json()
                            refinement_record.update(
                                {
                                    "event_type": "memory_refine",
                                    "iteration": index,
                                    "task_id": task.task_id,
                                    "run_id": run_id,
                                    "memory_policy": memory_policy,
                                }
                            )
                            run_logger.append_jsonl(
                                "memory_updates.jsonl",
                                refinement_record,
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
    utility_outcome_counts = Counter(update.outcome for update in utility_updates)
    utility_credit_counts = Counter(update.credit_source for update in utility_updates)
    metrics["utility_update_count"] = len(utility_updates)
    metrics["utility_helpful_count"] = utility_outcome_counts.get("helpful", 0)
    metrics["utility_harmful_count"] = utility_outcome_counts.get("harmful", 0)
    metrics["utility_neutral_count"] = utility_outcome_counts.get("neutral", 0)
    metrics["utility_credit_sources"] = dict(sorted(utility_credit_counts.items()))
    metrics["online_proxy_utility_update_count"] = utility_credit_counts.get("online_proxy", 0)
    metrics["replay_utility_update_count"] = utility_credit_counts.get(
        "leave_one_memory_out",
        0,
    )
    replay_label_counts = Counter(
        replay_result.attribution_label
        for replay_result in replay_results
        if replay_result.mode == "leave_one_memory_out"
    )
    metrics["replay_result_count"] = len(replay_results)
    metrics["replay_leave_one_count"] = sum(
        1 for replay_result in replay_results if replay_result.mode == "leave_one_memory_out"
    )
    metrics["replay_helpful_count"] = replay_label_counts.get("helpful", 0)
    metrics["replay_harmful_count"] = replay_label_counts.get("harmful", 0)
    metrics["replay_neutral_count"] = replay_label_counts.get("neutral", 0)
    support_replay_results = [
        replay_result
        for replay_result in replay_results
        if replay_result.replay_scope == "support_task_replay"
    ]
    support_label_counts = Counter(
        replay_result.attribution_label for replay_result in support_replay_results
    )
    metrics["support_replay_count"] = len(support_replay_results)
    metrics["support_replay_helpful_count"] = support_label_counts.get("helpful", 0)
    metrics["support_replay_harmful_count"] = support_label_counts.get("harmful", 0)
    metrics["support_replay_neutral_count"] = support_label_counts.get("neutral", 0)
    verification_passed_count = sum(
        1 for result in verification_results if result.verification_passed
    )
    metrics["verification_count"] = len(verification_results)
    metrics["verification_passed_count"] = verification_passed_count
    metrics["verification_failed_count"] = len(verification_results) - verification_passed_count
    metrics["verification_update_count"] = len(verification_updates)
    metrics["support_selection_count"] = sum(
        len(result.support_match_details) for result in verification_results
    )
    metrics["memory_refinement_count"] = len(refinement_updates)
    metrics["memory_split_count"] = len(refinement_updates)
    metrics["verification_budget_skipped_count"] = sum(verification_budget_skips.values())
    metrics["verification_budget_skip_reasons"] = dict(
        sorted(verification_budget_skips.items())
    )
    metrics["verification_budget_max_verifications"] = (
        verification_config.max_verifications_per_run
    )
    metrics["verification_budget_max_support_replay_records"] = (
        verification_config.max_support_replay_records_per_run
    )
    metrics["verification_budget_verifications_used"] = len(verification_results)
    metrics["verification_budget_support_replay_records_used"] = len(
        support_replay_results
    )
    metrics["replay_record_prompt_tokens"] = _sum_replay_tokens(replay_results, "prompt")
    metrics["replay_record_completion_tokens"] = _sum_replay_tokens(
        replay_results,
        "completion",
    )
    metrics["replay_record_tool_calls"] = _sum_replay_tool_calls(replay_results)
    metrics["replay_unique_execution_count"] = _count_unique_replay_executions(
        replay_results
    )
    metrics["replay_prompt_tokens"] = _sum_unique_replay_tokens(replay_results, "prompt")
    metrics["replay_completion_tokens"] = _sum_unique_replay_tokens(
        replay_results,
        "completion",
    )
    metrics["replay_tool_calls"] = _sum_unique_replay_tool_calls(replay_results)
    metrics["replay_delta_prompt_tokens"] = _sum_replay_deltas(
        replay_results,
        "delta_prompt_tokens",
    )
    metrics["replay_delta_tool_calls"] = _sum_replay_deltas(
        replay_results,
        "delta_tool_calls",
    )
    metrics["support_replay_record_prompt_tokens"] = _sum_replay_tokens(
        support_replay_results,
        "prompt",
    )
    metrics["support_replay_record_completion_tokens"] = _sum_replay_tokens(
        support_replay_results,
        "completion",
    )
    metrics["support_replay_record_tool_calls"] = _sum_replay_tool_calls(
        support_replay_results
    )
    metrics["support_replay_unique_execution_count"] = _count_unique_replay_executions(
        support_replay_results
    )
    metrics["support_replay_prompt_tokens"] = _sum_unique_replay_tokens(
        support_replay_results,
        "prompt",
    )
    metrics["support_replay_completion_tokens"] = _sum_unique_replay_tokens(
        support_replay_results,
        "completion",
    )
    metrics["support_replay_tool_calls"] = _sum_unique_replay_tool_calls(
        support_replay_results
    )
    if isinstance(memory_store, CandidateMemoryStore):
        lifecycle_counts = Counter(memory.lifecycle.status for memory in memory_store.all())
        metrics["candidate_memory_count"] = lifecycle_counts.get("candidate", 0)
        metrics["active_memory_count"] = lifecycle_counts.get("active", 0)
        metrics["quarantined_memory_count"] = lifecycle_counts.get("quarantined", 0)
        metrics["retired_memory_count"] = lifecycle_counts.get("retired", 0)
    run_logger.write_metrics(metrics)
    return metrics


def _allow_immediate_promotion(verification_config: VerificationConfig) -> bool:
    return not (
        verification_config.enabled
        and verification_config.disable_immediate_promotion
    )


def _should_verify_memory(
    update: UtilityUpdate,
    verification_config: VerificationConfig,
    verified_memory_ids: set[str],
) -> bool:
    if not verification_config.enabled:
        return False
    if update.outcome != "helpful":
        return False
    if update.memory.memory_id in verified_memory_ids:
        return False
    if update.memory.lifecycle.status != "candidate":
        return False
    return update.memory.utility.num_helpful >= verification_config.min_helpful_before_verify


def _verification_budget_skip_reason(
    verification_config: VerificationConfig,
    verification_count: int,
    support_replay_count: int,
) -> str | None:
    max_verifications = verification_config.max_verifications_per_run
    if max_verifications is not None and verification_count >= max_verifications:
        return "max_verifications_per_run_exhausted"
    max_support_replays = verification_config.max_support_replay_records_per_run
    if (
        max_support_replays is not None
        and support_replay_count + verification_config.max_support_tasks > max_support_replays
    ):
        return "max_support_replay_records_per_run_exhausted"
    return None


def _sum_replay_tokens(replay_results: list[ReplayResult], token_kind: str) -> int:
    with_attr = f"with_{token_kind}_tokens"
    without_attr = f"without_{token_kind}_tokens"
    return sum(
        int(value)
        for replay_result in replay_results
        for value in (
            getattr(replay_result, with_attr),
            getattr(replay_result, without_attr),
        )
        if value is not None
    )


def _sum_replay_tool_calls(replay_results: list[ReplayResult]) -> int:
    return sum(
        int(value)
        for replay_result in replay_results
        for value in (
            replay_result.with_tool_calls,
            replay_result.without_tool_calls,
        )
        if value is not None
    )


def _sum_replay_deltas(replay_results: list[ReplayResult], field_name: str) -> int:
    return sum(
        int(value)
        for replay_result in replay_results
        for value in (getattr(replay_result, field_name),)
        if value is not None
    )


def _count_unique_replay_executions(replay_results: list[ReplayResult]) -> int:
    return len(_unique_replay_executions(replay_results))


def _sum_unique_replay_tokens(
    replay_results: list[ReplayResult],
    token_kind: str,
) -> int:
    field_index = 0 if token_kind == "prompt" else 1
    return sum(values[field_index] for values in _unique_replay_executions(replay_results).values())


def _sum_unique_replay_tool_calls(replay_results: list[ReplayResult]) -> int:
    return sum(values[2] for values in _unique_replay_executions(replay_results).values())


def _unique_replay_executions(
    replay_results: list[ReplayResult],
) -> dict[str, tuple[int, int, int]]:
    executions: dict[str, tuple[int, int, int]] = {}
    for replay_result in replay_results:
        for side in ("with", "without"):
            execution_id = getattr(replay_result, f"{side}_execution_id")
            prompt_tokens = getattr(replay_result, f"{side}_prompt_tokens")
            completion_tokens = getattr(replay_result, f"{side}_completion_tokens")
            tool_calls = getattr(replay_result, f"{side}_tool_calls")
            if (
                prompt_tokens is None
                and completion_tokens is None
                and tool_calls is None
            ):
                continue
            if execution_id is None:
                execution_id = f"{replay_result.replay_id}:{side}"
            executions.setdefault(
                execution_id,
                (
                    int(prompt_tokens or 0),
                    int(completion_tokens or 0),
                    int(tool_calls or 0),
                ),
            )
    return executions


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
