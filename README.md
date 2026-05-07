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
17. Run phase-two tau-retail state/evaluator alignment checks with task-level DB reset, mutation-tool semantics, state-diff details, action-argument normalization, and policy/precondition violation logging.
18. Run phase-two probes directly against a cloned official `sierra-research/tau2-bench` retail checkout, including official nested task loading, split filtering, and raw-trace memory logging.
19. Run a phase-two official tau2 action-replay oracle that executes `evaluation_criteria.actions` step by step and separates actor mismatch from tool/evaluator semantic gaps.
20. Run a local-Qwen real actor through a vLLM OpenAI-compatible endpoint without requiring the OpenAI Python SDK in the experiment process.

## Environment

```powershell
conda activate rm
pip install -e ".[dev]"
```

Optional local vLLM actor service for Qwen:

```bash
conda activate rm
pip install -e ".[dev,vllm]"

# Start in a dedicated terminal. Pin CUDA_VISIBLE_DEVICES to avoid colliding
# with other experiments on the same server.
CUDA_VISIBLE_DEVICES=0 bash scripts/start_vllm_qwen35_9b.sh

# Health check from another terminal.
curl http://127.0.0.1:8000/v1/models
```

The default script serves `/home/fyk/models/Qwen/Qwen3.5-9B` as
`qwen3.5-9b` on `http://127.0.0.1:8000/v1`. Override scheduling parameters
with environment variables:

```bash
CUDA_VISIBLE_DEVICES=1 PORT=8001 GPU_MEMORY_UTILIZATION=0.80 MAX_MODEL_LEN=8192 \
  bash scripts/start_vllm_qwen35_9b.sh
```

For a 24G dual-GPU server, use tensor parallelism:

```bash
CUDA_VISIBLE_DEVICES=0,1 TENSOR_PARALLEL_SIZE=2 GPU_MEMORY_UTILIZATION=0.90 MAX_MODEL_LEN=4096 \
  bash scripts/start_vllm_qwen35_9b.sh
```

The experiment client uses the OpenAI-compatible HTTP API directly via the
standard library. It does not require `openai` or an `OPENAI_API_KEY`.

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

Phase-one tau-retail real/export sample closure:

```powershell
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_real_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_real_raw_trace_rag.yaml
```

Phase-two tau-retail state/evaluator alignment:

```powershell
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_raw_trace_rag.yaml
```

Phase-two official tau2-bench retail probe:

```bash
git clone https://github.com/sierra-research/tau-bench.git data/external/tau-bench
git clone https://github.com/sierra-research/tau2-bench.git data/external/tau2-bench

python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_raw_trace_rag.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_action_replay.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_action_replay_scan10.yaml

# Requires the local vLLM service above.
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_real_actor_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_real_actor_nomem_scan3.yaml

# Run only after the no-memory scan3 failure taxonomy is stable.
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_real_actor_raw_trace_rag_scan3.yaml
```

`data/external/` is ignored by git. The old `tau-bench` repository is kept for
compatibility and historical trajectories; its README currently points to
`tau2-bench` / tau-three as the updated task source. The phase-two official
configs therefore use:

```text
data/external/tau2-bench/data/tau2/domains/retail/tasks.json
data/external/tau2-bench/data/tau2/domains/retail/split_tasks.json
data/external/tau2-bench/data/tau2/domains/retail/db.json
```

`configs/tau_retail_nomem.yaml` uses local smoke fixtures by default:

```text
data/task_splits/tau_retail_smoke_tasks.json
data/tau_bench/retail_smoke_db.json
```

`configs/tau_retail_real_nomem.yaml` and
`configs/tau_retail_real_raw_trace_rag.yaml` use the versioned export-format sample:

```text
data/task_splits/tau_retail_export_sample_tasks.py
data/tau_bench/retail_export_sample/db.json
```

To run against a real tau-bench retail checkout or exported split, set
`benchmark.split_file` to a local JSON/JSONL/Python task file and set
`benchmark.data_file` or `benchmark.data_dir` to retail data. The adapter also
accepts `benchmark.task_module` or an installed tau-bench package with task modules.
For official tau2-bench JSON files, set `benchmark.task_split_file` to
`split_tasks.json` and choose `benchmark.task_split=base|train|test`; optionally
set `benchmark.task_ids` to a comma-separated string or list for a minimal
debug subset.
Use `benchmark.validate_export_schema=true` for exported files so missing task
outcomes or malformed DB sections fail before the agent loop starts. The expected
local export format is documented in `docs/tau_retail_export_schema.md`. Missing
task/data paths raise explicit setup errors.

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
  failure_taxonomy.json
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

For tau-retail runs, `runs.jsonl` includes `evaluation_details` with:

```text
evaluation_requested
evaluation_mode
answer_contains_passed
expected_actions_matched
action_mismatches
expected_actual_action_alignment
state_diff_passed
state_diff_summary
state_diff_mismatches
communicate_info_passed
communicate_info_mismatches
nl_assertions_passed
nl_assertion_mismatches
unsupported_official_criteria
policy_violation_count
policy_violations
tool_observation_error_count
tool_observation_errors
expected_negative_observation_count
expected_negative_observations
tool_semantic_error_count
tool_semantic_errors
```

`metrics.json` also includes `with_memory_fail_no_memory_success`, `negative_transfer_rate`, `harmful_memory_ids`, and gate acceptance/rejection counts.
Tau-retail evaluator-alignment runs additionally report `evaluation_modes`, `state_diff_evaluated_count`, `state_diff_passed_count`, `state_diff_failed_count`, `expected_actions_evaluated_count`, `expected_actions_matched_count`, `expected_actions_failed_count`, `communicate_info_evaluated_count`, `communicate_info_passed_count`, `nl_assertion_evaluated_count`, `nl_assertion_passed_count`, `unsupported_official_criteria_count`, `policy_violation_count`, `tool_observation_error_count`, `expected_negative_observation_count`, `tool_semantic_error_count`, and `evaluator_error_types`.
`tool_observation_error_count` counts every `ok=false` tool result, while `expected_negative_observation_count` separates matched expected read lookups that return a negative observation under official tau2 action-replay. `tool_semantic_error_count` is reserved for remaining non-policy, non-expected tool failures.
Every run also writes `failure_taxonomy.json`, which summarizes each task's
primary failure type, key evaluator counts, trace event counts, the last
model decision audit fields, and the first model parse-error audit fields when
JSON parsing fails. Token-budget JSON truncation is separated as
`truncated_json_response` when the response starts like a JSON object, remains
unclosed, and the completion appears to hit the response token budget.
`metrics.json` mirrors the aggregate taxonomy
counts as `failure_taxonomy_*`, `expected_actions_complete_count`,
`model_action_repair_count`, `model_parse_error_count`, and
`truncated_json_response_count`.
For local real-actor runs, `models.actor.provider=vllm` expects an
OpenAI-compatible endpoint. Useful actor fields are `base_url_env`, `base_url`,
`api_key` or `api_key_env`, `healthcheck`, `timeout_seconds`, `request_retries`,
`strip_thinking`, `extract_json_object`, `disable_response_format`,
`response_format`, and `extra_body`. `response_format` defaults to
`json_object`; set it to `json_schema` only after confirming the local
OpenAI-compatible server supports JSON schema response formats. For local
4096-token context windows, keep real-actor
`max_tokens` conservative for one-step JSON decisions; the client also supports
`context_overflow_margin_tokens` to lower `max_tokens` and retry when vLLM
returns a context-overflow 400 response.
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

Phase two round eight hardens the local Qwen/vLLM real actor before any
memory-method comparison. The code now asks for compact JSON decisions with an
empty or very short `thought`, adds retail tool-use guardrails, exposes an
opt-in JSON schema response format, and splits token-budget truncation from
generic invalid JSON. The next milestone is experimental validation:

1. Keep `configs/tau_retail_phase2_official_tau2_action_replay_scan10.yaml` as
   the adapter/evaluator/failure-taxonomy compatibility guardrail.
2. Re-run
   `configs/tau_retail_phase2_official_tau2_real_actor_nomem_scan3.yaml` after
   the parser/output-control fix and inspect `failure_taxonomy.json` for
   `truncated_json_response_count`, `model_parse_error_count`, and per-task
   `first_model_parse_error`.
3. Run
   `configs/tau_retail_phase2_official_tau2_real_actor_raw_trace_rag_scan3.yaml`
   only after no-memory scan3 no longer fails from parser truncation and any
   remaining failures are explainable via action/tool/communicate/nl taxonomy.
4. If the local vLLM server supports schema response formats, try setting
   `models.actor.response_format: json_schema` in a temporary scan3 config and
   compare parser failure counts against the default `json_object` run.
5. Continue to keep `nt_memevo_gate`, support verification, scope refinement,
   and larger memory-method comparisons out of the official real-actor path
   until no-memory and raw-trace small-sample failure taxonomies are stable.
