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
13. Run support-set replay and verification-gated consolidation before promoting candidates to active memory.
14. Record support selection details, replay budget usage, and scope-refinement events when support evidence is mixed.
15. Run a minimal tau-bench retail adapter with local smoke tasks, retail DB tools, evaluator mapping, and the same task/run/trace/metric logs.
16. Run tau-retail smoke baselines for `none`, `raw_trace_rag`, `reflexion`, `nt_memevo_candidate`, and `nt_memevo_gate`.

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

Support-set verification and consolidation check:

```powershell
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_verify.yaml
```

Mixed-support refinement and budget check:

```powershell
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_refine.yaml
```

Polluted-memory gate check:

```powershell
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_polluted.yaml
```

Unsafe polluted ablation that intentionally accepts a harmful memory:

```powershell
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_unsafe_polluted.yaml
```

Minimal tau-bench retail adapter smoke:

```powershell
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nomem.yaml
```

Tau-retail smoke memory baselines:

```powershell
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_raw_trace_rag.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_reflexion.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nt_memevo_candidate.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nt_memevo_gate.yaml
```

`configs/tau_retail_nomem.yaml` uses local smoke fixtures by default:

```text
data/task_splits/tau_retail_smoke_tasks.json
data/tau_bench/retail_smoke_db.json
```

To run against a real tau-bench retail checkout or exported split, set `benchmark.split_file`
to a local JSON/JSONL/Python task file and set `benchmark.data_file` or `benchmark.data_dir`
to retail data. The adapter also accepts `benchmark.task_module` or an installed tau-bench
package with task modules. Missing task/data paths raise explicit setup errors.

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
replay_scope
with_reward
without_reward
delta_reward
cost_adjusted_delta_reward
with_success
without_success
attribution_label
delta_prompt_tokens
delta_tool_calls
```

For configs with `memory.verification.enabled=true`, support-set replay records use
`replay_scope=support_task_replay` and `mode=support_task_replay`. The corresponding
`memory_updates.jsonl` entries use `event_type=verification_update` and record:

```text
verification_id
verification_passed
failure_reason
support_task_ids
support_delta_mean
support_lcb_delta_reward
support_negative_transfer_rate
lifecycle_before
lifecycle_after
```

When `memory.verification.log_support_selection=true`, `memory_updates.jsonl` also includes
`event_type=support_selection` records with:

```text
task_intent
source_task_id
support_task_id
task_domain
task_tool_names
support_match_score
intent_score
domain_score
tool_score
lexical_score
selected_rank
replay_id
attribution_label
delta_reward
cost_adjusted_delta_reward
with_success
without_success
```

When `memory.verification.refinement.enabled=true` and mixed support evidence is detected,
`memory_updates.jsonl` includes `event_type=memory_refine` records with:

```text
parent_memory_id
child_memory_id
trigger_reason
parent_scope_before
child_scope
parent_lifecycle_before
parent_lifecycle_after
child_lifecycle
child_utility
helpful_support_task_ids
harmful_support_task_ids
neutral_support_task_ids
support_match_details
```

`metrics.json` also includes `with_memory_fail_no_memory_success`, `negative_transfer_rate`, `harmful_memory_ids`, and gate acceptance/rejection counts.
For structured candidate-memory runs it additionally reports utility update counts and lifecycle counts:
`utility_update_count`, `utility_helpful_count`, `utility_harmful_count`, `candidate_memory_count`, `active_memory_count`, and `quarantined_memory_count`.
Replay-enabled runs additionally report `replay_result_count`, `replay_leave_one_count`, `replay_helpful_count`, `replay_harmful_count`, `replay_neutral_count`, `replay_utility_update_count`, `online_proxy_utility_update_count`, and `utility_credit_sources`.
Verification-enabled runs additionally report `verification_count`, `verification_passed_count`, `verification_failed_count`, `support_replay_count`, `support_replay_helpful_count`, `support_replay_harmful_count`, `support_replay_neutral_count`, and replay cost counters.
Support-refinement runs additionally report `support_selection_count`, `memory_refinement_count`, `memory_split_count`, verification budget counters, and both record-level and unique-execution replay cost counters.

## Tests

```powershell
pytest
```

## Next Milestone

The next coding round should close the first stage on real or exported tau-bench retail samples:

1. Replace the local tau-retail smoke fixture with an exported real tau-bench retail train/dev split on the target machine.
2. Run no-memory plus at least one memory baseline on `max_tasks=1/3` real or exported retail samples.
3. Broaden tau-bench tool coverage where official retail tasks require mutation, policy, or evaluator details beyond the smoke wrapper.
4. Document any blocker with the local export schema, expected action fields, required DB files, and exact rerun commands.
