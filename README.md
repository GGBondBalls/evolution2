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

`metrics.json` also includes `with_memory_fail_no_memory_success`, `negative_transfer_rate`, `harmful_memory_ids`, and gate acceptance/rejection counts.

## Tests

```powershell
pytest
```

## Next Milestone

The next coding round should add risk-aware retrieval, verification, or connect tau-bench:

1. Add online utility updates for memories that pass the gate and are actually used.
2. Add verification-gated consolidation from candidate pool to active memory.
3. Add replay or leave-one-memory-out estimation for higher-confidence negative-transfer attribution.
4. Wire the tau-bench adapter to replace the toy environment.
