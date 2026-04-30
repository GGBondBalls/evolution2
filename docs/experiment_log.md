# 实验日志

本文件用于记录人工运行实验后的结果。编码智能体只维护模板，具体实验完成后由实验执行者填写。

## tiny_nomem_seed1

### 实验名称

`tiny_nomem_seed1`

### 日期与环境

2026-04-29，Windows PowerShell，conda 环境 `rm`，Python 3.12.13。

### 运行命令

```powershell
python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml
Get-Content .\runs\tiny_nomem_seed1\metrics.json
pytest
```

### 配置文件

`configs/tiny_nomem.yaml`

关键参数：`benchmark.name=tiny_tools`，`max_tasks=5`，`agent.max_steps=4`，`memory_top_k=0`，`models.actor.provider=mock`。

### 输出目录

`runs/tiny_nomem_seed1/`

### 结果

```json
{
  "num_tasks": 5,
  "success_rate": 1.0,
  "avg_reward": 1.0,
  "avg_steps": 2.0,
  "avg_prompt_tokens": 310.4,
  "avg_completion_tokens": 74.2,
  "avg_tool_calls": 1.0,
  "memory_policy": "none",
  "memory_size": 0,
  "memory_top_k": 0
}
```

`pytest` 结果：`1 passed in 0.09s`。

### 现象与问题

第一阶段 no-memory 离线烟测通过。第二轮编码后，日志已改为默认重新初始化输出文件，避免重复运行同一配置时追加旧结果。

### 下一步

实现 Raw Trace RAG baseline，形成第一组 `no-memory vs raw-trace-rag` 对照链路。

## tiny_raw_trace_rag_seed1

### 实验名称

`tiny_raw_trace_rag_seed1`

### 日期与环境

2026-04-29，Windows PowerShell，conda 环境 `rm`，Python 3.12.13。

### 运行命令

```powershell
python -m ntmemevo.experiments.run_stream --config configs/tiny_raw_trace_rag.yaml
Get-Content .\runs\tiny_raw_trace_rag_seed1\metrics.json
pytest
```

### 配置文件

`configs/tiny_raw_trace_rag.yaml`

关键参数：`benchmark.name=tiny_tools`，`max_tasks=5`，`agent.max_steps=4`，`memory.method=raw_trace_rag`，`memory.top_k=2`，`models.actor.provider=mock`。

### 输出目录

`runs/tiny_raw_trace_rag_seed1/`

### 结果

```json
{
  "num_tasks": 5,
  "success_rate": 1.0,
  "avg_reward": 1.0,
  "avg_steps": 2.0,
  "avg_prompt_tokens": 530.6,
  "avg_completion_tokens": 74.2,
  "avg_tool_calls": 1.0,
  "memory_policy": "raw_trace_rag",
  "memory_size": 5,
  "memory_top_k": 2
}
```

`pytest` 结果：`2 passed in 0.14s`。

用户复验补充：2026-04-29，用户在交互式 `(rm)` 环境下运行同一组命令，`pytest` 结果为 `2 passed in 0.13s`，no-memory 与 raw-trace-rag 指标均与本日志记录一致。

### 现象与问题

Raw Trace RAG 已写入 5 条轨迹记忆，并在后续任务中检索历史轨迹。当前 tiny benchmark 过简单，no-memory 和 raw-trace-rag 成功率都为 1.0；差异主要体现在 raw-trace-rag 的 prompt token 成本更高。

### 下一步

继续实现 Reflexion baseline，或接入 tau-bench retail 以获得更有意义的成功率和负迁移对比。

## tiny_reflexion_seed1

### 实验名称

`tiny_reflexion_seed1`

### 日期与环境

2026-04-29，Windows PowerShell，用户交互式 conda 环境 `(rm2)`，Python 3.12.13。

### 运行命令

```powershell
python -m pytest
python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_raw_trace_rag.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_reflexion.yaml
Get-Content .\runs\tiny_reflexion_seed1\metrics.json
Get-Content .\runs\tiny_reflexion_seed1\memories.jsonl -TotalCount 2
Get-Content .\runs\tiny_reflexion_seed1\runs.jsonl -Tail 2
```

### 配置文件

`configs/tiny_reflexion.yaml`

关键参数：`benchmark.name=tiny_tools`，`max_tasks=5`，`agent.max_steps=4`，`memory.method=reflexion`，`memory.top_k=2`，`memory.save_successes=true`，`memory.save_failures=true`，`models.actor.provider=mock`。

### 输出目录

`runs/tiny_reflexion_seed1/`

### 结果

```json
{
  "num_tasks": 5,
  "success_rate": 1.0,
  "avg_reward": 1.0,
  "avg_steps": 2.0,
  "avg_prompt_tokens": 832.2,
  "avg_completion_tokens": 74.2,
  "avg_tool_calls": 1.0,
  "memory_policy": "reflexion",
  "memory_size": 5,
  "memory_top_k": 2
}
```

`pytest` 结果：`3 passed in 0.14s`。

同轮对照结果：

1. `tiny_nomem_seed1`：`success_rate=1.0`，`avg_prompt_tokens=310.4`，`memory_policy=none`，`memory_size=0`。
2. `tiny_raw_trace_rag_seed1`：`success_rate=1.0`，`avg_prompt_tokens=538.6`，`memory_policy=raw_trace_rag`，`memory_size=5`。
3. `tiny_reflexion_seed1`：`success_rate=1.0`，`avg_prompt_tokens=832.2`，`memory_policy=reflexion`，`memory_size=5`。

### 现象与问题

Reflexion baseline 已生成 5 条 reflection memory。`memories.jsonl` 中包含 `memory_id`、`reflection`、`reflection_type`、`trace_summary`、`reward`、`success` 和 `text`；`runs.jsonl` 中后续任务包含 `used_memory_ids` 和 `trace_summary`。

当前 tiny benchmark 仍然过简单，三组 baseline 成功率均为 1.0，差异主要体现在 prompt token 成本：`none < raw_trace_rag < reflexion`。因此本实验只验证第三轮链路和日志字段，不用于证明记忆收益。

### 下一步

第三轮已完成。下一轮应进入结构化 NT-MemEvo candidate memory schema，或为 tiny benchmark 增加困难任务与污染记忆 fixture，开始铺设 negative transfer 指标链路。

## tiny_nt_memevo_candidate_seed1

### 实验名称

`tiny_nt_memevo_candidate_seed1`

### 日期与环境

2026-04-30，Linux，机器标识 `BNUZ`，conda 环境 `rm`，Python 3.12.13，pytest 9.0.3。

### 运行命令

```bash
conda activate rm
python -m pytest
python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_raw_trace_rag.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_reflexion.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_candidate.yaml
tail -n 2 runs/tiny_nt_memevo_candidate_seed1/runs.jsonl
tail -n 5 runs/tiny_nt_memevo_candidate_seed1/memory_updates.jsonl
head -n 2 runs/tiny_nt_memevo_candidate_seed1/candidate_memories.jsonl
cat runs/tiny_nt_memevo_candidate_seed1/metrics.json
```

### 配置文件

`configs/tiny_nt_memevo_candidate.yaml`

关键参数：`benchmark.name=tiny_tools`，`max_tasks=5`，`agent.max_steps=4`，`memory.method=nt_memevo_candidate`，`memory.top_k=0`，`memory.save_successes=true`，`memory.save_failures=true`，`models.actor.provider=mock`。

### 输出目录

`runs/tiny_nt_memevo_candidate_seed1/`

### 结果

`pytest` 结果：

```text
5 passed in 0.03s
```

本轮四组对照结果：

1. `tiny_nomem_seed1`：`success_rate=1.0`，`avg_prompt_tokens=310.4`，`memory_policy=none`，`memory_size=0`，`memory_top_k=0`。
2. `tiny_raw_trace_rag_seed1`：`success_rate=1.0`，`avg_prompt_tokens=538.6`，`memory_policy=raw_trace_rag`，`memory_size=5`，`memory_top_k=2`。
3. `tiny_reflexion_seed1`：`success_rate=1.0`，`avg_prompt_tokens=832.2`，`memory_policy=reflexion`，`memory_size=5`，`memory_top_k=2`。
4. `tiny_nt_memevo_candidate_seed1`：`success_rate=1.0`，`avg_prompt_tokens=310.4`，`memory_policy=nt_memevo_candidate`，`memory_size=5`，`memory_top_k=0`。

`tiny_nt_memevo_candidate_seed1/metrics.json`：

```json
{
  "num_tasks": 5,
  "success_rate": 1.0,
  "avg_reward": 1.0,
  "avg_steps": 2.0,
  "avg_prompt_tokens": 310.4,
  "avg_completion_tokens": 74.2,
  "avg_tool_calls": 1.0,
  "memory_policy": "nt_memevo_candidate",
  "memory_size": 5,
  "memory_top_k": 0
}
```

`runs.jsonl` 抽查结果：

1. 第 4 个任务 `tiny_exchange_001`：`memory_policy=nt_memevo_candidate`，`success=true`，`used_memory_ids=[]`，trace 为 `check_exchange_eligibility(...)`。
2. 第 5 个任务 `tiny_policy_001`：`memory_policy=nt_memevo_candidate`，`success=true`，`used_memory_ids=[]`，trace 为 `lookup_policy(...)`。

`memory_updates.jsonl` 抽查结果：

1. 5 条事件均为 `event_type=candidate_extract`。
2. 5 条 candidate memory id 分别为 `cand_000001_tiny_order_status_001` 到 `cand_000005_tiny_policy_001`。
3. candidate 类型覆盖 `tool_usage`、`constraint` 和 `user_policy`。
4. 5 条记录均为 `candidate_status=candidate`，`positive_evidence` 均指向对应 run id，`negative_evidence=[]`。

`candidate_memories.jsonl` 抽查结果：

1. 前两条 memory 均包含完整结构化字段：`memory_id`、`type`、`claim`、`scope`、`action_hint`、`avoid_hint`、`positive_evidence`、`negative_evidence`、`utility`、`lifecycle`、`source` 和 `text`。
2. `utility` 默认值符合设计：`alpha=1.0`，`beta=1.0`，`mean_delta_reward=0.0`，`lcb_delta_reward=0.0`，`num_used=0`，`num_helpful=0`，`num_harmful=0`。
3. `lifecycle` 默认值符合设计：`status=candidate`，`last_used_iter=null`，`ttl=50`。
4. `source.created_from` 与 `positive_evidence` 对齐，`source.extractor_model=deterministic_candidate_extractor_v1`，`prompt_hash` 已生成。

### 验收标准

1. `pytest` 全部通过。
2. 新增 candidate memory schema 校验测试，覆盖必填字段、默认 utility、lifecycle 和 source 元信息。
3. `tiny_nt_memevo_candidate_seed1` 能生成标准日志目录，并写出结构化 candidate memory JSONL。
4. `memory_updates.jsonl` 能记录 candidate extraction 事件、来源 run、任务结果和 candidate memory id。
5. 现有 `tiny_nomem`、`tiny_raw_trace_rag`、`tiny_reflexion` 三组配置不回归。
6. 本轮只要求 candidate pool 稳定写入，不要求实现 verification gate、utility learning 或 quarantine。

### 现象与问题

第四轮复验通过。`nt_memevo_candidate` 能稳定生成 5 条结构化 candidate memory，且不会注入当前 agent prompt；因此 `used_memory_ids=[]`，`avg_prompt_tokens=310.4`，与 no-memory 一致。这符合第四轮边界：只验证 candidate pool 写入，不验证记忆检索收益。

当前 tiny benchmark 仍然过简单，四组配置成功率均为 1.0，无法衡量记忆是否提升任务能力，也无法触发 negative transfer。Raw Trace RAG 和 Reflexion 的主要差异仍体现在 prompt token 成本：`none = nt_memevo_candidate < raw_trace_rag < reflexion`。

本次用户粘贴的 `metrics.json` 末尾少了右花括号，但工作区实际 `runs/tiny_nt_memevo_candidate_seed1/metrics.json` 是完整 JSON，不是日志写入问题。

### 下一步

第四轮完成。下一轮应进入 `RetrieverGate + tiny 污染记忆 fixture`，目标是把“结构化记忆能被写入”推进到“结构化记忆能被风险感知地选择，并能在离线 tiny 环境中稳定触发和记录 negative transfer”。

## 当前下一轮方向

第一阶段第五轮建议优先实现 `RetrieverGate + tiny 污染记忆 fixture`。第四轮已将 candidate memory schema、store、extractor 和日志路径落成，下一步应开始让记忆“可选择、可伤害、可度量”，否则 negative transfer 仍无法在离线 tiny 环境中复现。

第五轮建议范围：

1. 新增风险感知 `RetrieverGate`，初版用线性分数整合 lexical similarity、precondition match、utility、risk、age 和 context cost。
2. 新增 active memory 或 gated candidate retrieval 的最小路径，使结构化 memory 可以被转换为 `RetrievedMemory` 并注入 prompt，但必须记录 gate 决策。
3. 新增 tiny pollution fixture，手工注入与当前任务高相似但错误的 candidate / active memory，例如把 refund/order/exchange 的 action hint 故意绑定到错误工具或错误结论。
4. 在 `memory_updates.jsonl` 中记录每条候选记忆的 `similarity_score`、`precondition_score`、`utility_score`、`risk_score`、`final_gate_score`、`gate_decision` 和 `rejection_reason`。
5. 新增 negative transfer 指标占位：`with_memory_fail_no_memory_success`、`harmful_memory_ids`、`memory_attributed_failures` 和 `negative_transfer_rate`。
6. 保持 `none / raw_trace_rag / reflexion / nt_memevo_candidate` 四组配置继续可运行，并新增一组污染实验配置，例如 `tiny_nt_memevo_gate_polluted.yaml`。
7. 第五轮仍不建议直接接 tau-bench；应先在 tiny 中让污染记忆和 gate 日志可复现，再接真实 benchmark。

## 实验记录模板

### 实验名称

填写实验名，例如 `tiny_nomem_seed1`。

### 日期与环境

填写运行日期、机器、conda 环境、Python 版本、依赖版本。

### 运行命令

```powershell
conda activate rm
pip install -e ".[dev]"
python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml
```

### 配置文件

填写配置文件路径和关键参数。

### 输出目录

填写 `runs/...` 目录。

### 结果

填写 `metrics.json` 中的结果。

### 现象与问题

记录失败任务、异常、成本、日志缺失、可复现性问题。

### 下一步

记录下一轮应修改的代码或实验设置。
