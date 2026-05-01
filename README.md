# NT-MemEvo

This repository implements the first-stage scaffold for **Negative-Transfer-Aware Memory Evolution for Self-Improving LLM Agents**.

Current scope:

1. Load experiment configs.
2. Run a minimal ReAct-style tool agent.
3. Support an offline deterministic mock LLM.
4. Execute a tiny tool-use benchmark.
5. Persist task, run, trace, memory, and metric logs in the format required by the research roadmap.
6. Run a first Raw Trace RAG baseline that stores prior trajectories and retrieves lexical nearest traces for later tasks.
7. Run a Reflexion baseline that stores natural-language reflections and retrieves them with the same online memory protocol.
8. Generate structured NT-MemEvo candidate memories with scope, evidence, utility, lifecycle, and source fields.
9. Run risk-aware gated retrieval over structured candidate memories and log every gate decision.
10. Bootstrap polluted candidate memories to test negative-transfer detection and gate rejection.
11. Update used candidate-memory utility online and apply minimal lifecycle transitions to active or quarantined states.
12. Run leave-one-memory-out replay for gated memories and use replay deltas for higher-confidence utility updates.

## Environment

```powershell
conda activate rm
pip install -e ".[dev]"
```

## Smoke Test

```powershell
python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml
```

Raw Trace RAG baseline:

```powershell
python -m ntmemevo.experiments.run_stream --config configs/tiny_raw_trace_rag.yaml
```

Reflexion baseline:

```powershell
python -m ntmemevo.experiments.run_stream --config configs/tiny_reflexion.yaml
```

Structured NT-MemEvo candidate memory:

```powershell
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_candidate.yaml
```

Risk-aware NT-MemEvo gated retrieval:

```powershell
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate.yaml
```

Repeated-intent utility update check:

```powershell
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_repeated.yaml
```

Replay-backed utility update check:

```powershell
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_replay.yaml
```

Polluted-memory gate check:

```powershell
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_polluted.yaml
```

Unsafe polluted ablation that intentionally accepts a harmful memory:

```powershell
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_unsafe_polluted.yaml
```

or:

```powershell
ntmemevo-run-stream --config configs/tiny_nomem.yaml
```

Expected output files:

```text
runs/tiny_nomem_seed1/
  config.yaml
  tasks.jsonl
  runs.jsonl
  trace_events.jsonl
  memories.jsonl
  candidate_memories.jsonl
  memory_updates.jsonl
  replay_results.jsonl
  metrics.json
```

For `memory.method=nt_memevo_gate`, `memory_updates.jsonl` includes `gate_decision` events with:

```text
similarity_score
precondition_score
utility_score
risk_score
age_penalty
cost_penalty
final_gate_score
gate_decision
rejection_reason
```

When a gated memory is actually injected into the agent context, `memory_updates.jsonl` also includes `utility_update` events with:

```text
outcome
credit_source
baseline_reward
delta_reward
utility_before
utility_after
lifecycle_before
lifecycle_after
positive_evidence
negative_evidence
replay_id
source_run_id
```

For configs with `memory.replay.enabled=true`, `replay_results.jsonl` records replay attribution with:

```text
replay_id
source_run_id
task_id
memory_id
mode
with_reward
without_reward
delta_reward
with_success
without_success
attribution_label
```

`metrics.json` also includes `with_memory_fail_no_memory_success`, `negative_transfer_rate`, `harmful_memory_ids`, and gate acceptance/rejection counts.
For structured candidate-memory runs it additionally reports utility update counts and lifecycle counts:
`utility_update_count`, `utility_helpful_count`, `utility_harmful_count`, `candidate_memory_count`, `active_memory_count`, and `quarantined_memory_count`.
Replay-enabled runs additionally report `replay_result_count`, `replay_leave_one_count`, `replay_helpful_count`, `replay_harmful_count`, `replay_neutral_count`, `replay_utility_update_count`, `online_proxy_utility_update_count`, and `utility_credit_sources`.

## Tests

```powershell
pytest
```

## Next Milestone

The next coding round should add verification-gated consolidation or connect tau-bench:

1. Add support-task replay sets for candidate consolidation beyond single-task leave-one-memory-out.
2. Add verification-gated consolidation beyond the current replay-backed lifecycle thresholds.
3. Add repeated-intent and polluted splits with broader task diversity.
4. Wire the tau-bench adapter to replace the toy environment.
