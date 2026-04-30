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
  memory_updates.jsonl
  replay_results.jsonl
  metrics.json
```

## Tests

```powershell
pytest
```

## Next Milestone

The next coding round should add structured NT-MemEvo candidate memory or connect tau-bench:

1. Add structured candidate memory schema with scope, evidence, utility, and lifecycle fields.
2. Keep the same `run_stream` protocol and output logs.
3. Compare `none`, `raw_trace_rag`, and `reflexion` on the tiny benchmark and then tau-bench.
4. Wire the tau-bench adapter to replace the toy environment.
