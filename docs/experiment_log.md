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

## tiny_nt_memevo_gate_seed1

### 实验名称

`tiny_nt_memevo_gate_seed1`

### 日期与环境

2026-04-30，Linux，机器标识 `BNUZ`，交互式 conda 环境 `(rm)`，Python 3.12.13，pytest 9.0.3，pluggy 1.6.0。

### 运行命令

```bash
conda activate rm
python -m pytest
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate.yaml
cat runs/tiny_nt_memevo_gate_seed1/metrics.json
tail -n 20 runs/tiny_nt_memevo_gate_seed1/memory_updates.jsonl
tail -n 5 runs/tiny_nt_memevo_gate_seed1/runs.jsonl
```

### 配置文件

`configs/tiny_nt_memevo_gate.yaml`

关键参数：`benchmark.name=tiny_tools`，`max_tasks=5`，`memory.method=nt_memevo_gate`，`memory.top_k=2`，`gate.reject_negative_evidence=true`，`gate.allowed_statuses=["candidate","active"]`，`models.actor.provider=mock`。

### 输出目录

`runs/tiny_nt_memevo_gate_seed1/`

### 结果

`pytest` 结果：

```text
9 passed in 0.05s
```

`tiny_nt_memevo_gate_seed1/metrics.json`：

```json
{
  "num_tasks": 5,
  "success_rate": 1.0,
  "avg_reward": 1.0,
  "avg_steps": 2.0,
  "avg_prompt_tokens": 310.4,
  "avg_completion_tokens": 74.2,
  "avg_tool_calls": 1.0,
  "with_memory_fail_no_memory_success": 0,
  "memory_attributed_failures": 0,
  "negative_transfer_rate": 0.0,
  "harmful_memory_ids": [],
  "negative_transfer_failure_examples": [],
  "memory_policy": "nt_memevo_gate",
  "memory_size": 5,
  "memory_top_k": 2,
  "gate_decision_count": 10,
  "gate_accepted_count": 0,
  "gate_rejected_count": 10,
  "gate_rejection_reasons": {
    "precondition_below_threshold": 10
  }
}
```

`memory_updates.jsonl` 抽查结果：

1. 第 1 个任务无历史 candidate，`retrieve` 事件为空检索。
2. 第 2 至第 5 个任务共写入 10 条 `gate_decision` 事件。
3. 10 条 `gate_decision` 均为 `gate_decision=reject`，`rejection_reason=precondition_below_threshold`。
4. 每个任务结束后均写入 1 条 `candidate_extract`，共生成 5 条 candidate memory。

`runs.jsonl` 抽查结果：

1. 5 个任务均 `success=true`、`reward=1.0`。
2. 5 个任务均 `used_memory_ids=[]`，说明本配置下 gate 未注入跨 intent candidate memory。
3. 工具调用路径符合预期：order status、inventory、refund、exchange、policy 分别调用对应工具。

### 现象与问题

本实验通过。主 tiny 五任务 intent 基本不同，保守 gate 全部拒绝跨 intent candidate memory，因此 `avg_prompt_tokens=310.4` 与 no-memory 一致，且 `negative_transfer_rate=0.0`。

该结果说明第五轮 gate 决策日志链路已跑通，但主 tiny 五任务无法验证 accepted path；accepted path 目前由测试里的 repeated-task pipeline 覆盖。

### 下一步

下一轮应加入 repeated-intent tiny split，并实现 online utility update，使 gate 在安全同 intent 场景中能接受记忆、注入记忆并更新 utility。

## tiny_nt_memevo_gate_polluted_seed1

### 实验名称

`tiny_nt_memevo_gate_polluted_seed1`

### 日期与环境

2026-04-30，Linux，机器标识 `BNUZ`，交互式 conda 环境 `(rm)`，Python 3.12.13，pytest 9.0.3，pluggy 1.6.0。

### 运行命令

```bash
conda activate rm
python -m pytest
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_polluted.yaml
cat runs/tiny_nt_memevo_gate_polluted_seed1/metrics.json
head -n 3 runs/tiny_nt_memevo_gate_polluted_seed1/candidate_memories.jsonl
grep 'polluted_refund_lookup_policy_001' runs/tiny_nt_memevo_gate_polluted_seed1/memory_updates.jsonl
tail -n 20 runs/tiny_nt_memevo_gate_polluted_seed1/memory_updates.jsonl
```

### 配置文件

`configs/tiny_nt_memevo_gate_polluted.yaml`

关键参数：`memory.method=nt_memevo_gate`，`memory.bootstrap_file=data/memory_fixtures/tiny_polluted_candidates.jsonl`，`gate.reject_negative_evidence=true`，`models.actor.follow_memory_hints=true`。

### 输出目录

`runs/tiny_nt_memevo_gate_polluted_seed1/`

### 结果

`pytest` 结果：

```text
9 passed in 0.05s
```

`tiny_nt_memevo_gate_polluted_seed1/metrics.json`：

```json
{
  "num_tasks": 5,
  "success_rate": 1.0,
  "avg_reward": 1.0,
  "avg_steps": 2.0,
  "avg_prompt_tokens": 310.4,
  "avg_completion_tokens": 74.2,
  "avg_tool_calls": 1.0,
  "with_memory_fail_no_memory_success": 0,
  "memory_attributed_failures": 0,
  "negative_transfer_rate": 0.0,
  "harmful_memory_ids": [],
  "negative_transfer_failure_examples": [],
  "memory_policy": "nt_memevo_gate",
  "memory_size": 6,
  "memory_top_k": 2,
  "gate_decision_count": 15,
  "gate_accepted_count": 0,
  "gate_rejected_count": 15,
  "gate_rejection_reasons": {
    "negative_evidence_present": 5,
    "precondition_below_threshold": 10
  }
}
```

`candidate_memories.jsonl` 抽查结果：

1. 第一条为 bootstrap 污染记忆 `polluted_refund_lookup_policy_001`。
2. 该污染记忆 `type=warning`，`scope.intent=refund_eligibility`，`tool_names=["lookup_policy"]`。
3. 该污染记忆包含 `negative_evidence=["polluted_bad_run_refund_001"]`。
4. 该污染记忆的人工 utility 表示有害先验：`alpha=1.0`、`beta=3.0`、`mean_delta_reward=-1.0`、`lcb_delta_reward=-1.0`、`num_used=2`、`num_harmful=2`。
5. 后续 5 条为本轮在线抽取的 candidate memory，总 memory size 为 6。

`memory_updates.jsonl` 抽查结果：

1. 第 0 轮写入 `event_type=bootstrap_candidate`，说明污染记忆已导入本轮 candidate pool。
2. 污染记忆 `polluted_refund_lookup_policy_001` 在 5 个任务上均产生 `gate_decision=reject`。
3. 污染记忆 5 次拒绝原因均为 `negative_evidence_present`。
4. 其他 10 条候选记忆决策因 `precondition_below_threshold` 被拒绝。
5. 5 次 `retrieve` 事件均为空检索，污染记忆未进入 prompt。

### 现象与问题

污染记忆拒绝实验通过。虽然污染记忆在 `tiny_refund_001` 上有较高 `precondition_score=0.9`，但由于带有 `negative_evidence` 且配置 `reject_negative_evidence=true`，gate 仍将其拒绝。因此本实验 `success_rate=1.0`、`negative_transfer_rate=0.0`，证明第五轮的污染记忆阻断链路有效。

当前污染实验只验证“污染被拒绝”。为了验证“污染若被接受会造成失败”，仍需运行 `tiny_nt_memevo_gate_unsafe_polluted.yaml` 对照配置。

### 下一步

运行 unsafe polluted ablation，确认放宽 gate 后污染记忆会进入 `used_memory_ids` 并触发 `with_memory_fail_no_memory_success`。

## tiny_nt_memevo_gate_unsafe_polluted_seed1

### 实验名称

`tiny_nt_memevo_gate_unsafe_polluted_seed1`

### 日期与环境

待运行。建议记录 Linux 发行版 / 机器标识、conda 环境 `rm`、Python 版本、pytest 版本。

### 运行命令

```bash
conda activate rm
pip install -e ".[dev]"
python -m pytest
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_unsafe_polluted.yaml
cat runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/metrics.json
cat runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/runs.jsonl
cat runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/memory_updates.jsonl
```

### 配置文件

`configs/tiny_nt_memevo_gate_unsafe_polluted.yaml`

关键参数：`benchmark.split_file=data/task_splits/tiny_refund_only_tasks.json`，`memory.bootstrap_file=data/memory_fixtures/tiny_polluted_candidates.jsonl`，`gate.reject_negative_evidence=false`，`gate.min_score=-1.0`，`gate.max_risk=1.0`，`models.actor.follow_memory_hints=true`。

### 输出目录

`runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/`

### 结果

待运行。重点记录：

1. `with_memory_fail_no_memory_success`。
2. `negative_transfer_rate`。
3. `harmful_memory_ids` 是否包含 `polluted_refund_lookup_policy_001`。
4. `runs.jsonl` 中 `used_memory_ids` 和失败 `error_type`。

### 现象与问题

待运行。当前预期：unsafe gate 会接受污染记忆，mock agent 跟随错误工具提示，导致 refund-only 任务失败，用于证明负迁移指标链路可稳定触发。

### 下一步

该实验是有意放宽 gate 的反例配置，不应作为方法主结果；只用于对照 gated polluted 配置。

## 当前下一轮方向

第一阶段第六轮建议优先实现 `online utility update + repeated-intent tiny split`。第五轮已经跑通 gate 决策、污染记忆导入、污染拒绝和负迁移指标占位，但主 tiny 五任务中没有自然 accepted path，导致 `gate_accepted_count=0`，还不能验证“被接受记忆如何更新 utility 和 lifecycle”。

第六轮建议范围：

1. 新增 repeated-intent tiny split，例如连续两个 `order_status` 或 `refund_eligibility` 任务，使安全 candidate memory 能被 gate 接受并注入 prompt。
2. 实现 candidate memory 的 online utility update：更新 `num_used`、`num_helpful`、`num_harmful`、`alpha`、`beta`、`mean_delta_reward`、`lcb_delta_reward` 和 `last_used_iter`。
3. 在 `memory_updates.jsonl` 中新增 `utility_update` 事件，记录更新前后 utility、任务结果、memory id 和 helpful/harmful 判断。
4. 实现最小 lifecycle 迁移：helpful candidate 可进入或保持 `active`，harmful 或带 negative evidence 的 memory 可进入 `quarantined`。
5. 运行并记录 `tiny_nt_memevo_gate_unsafe_polluted.yaml`，确认 unsafe gate 接受污染记忆后 `negative_transfer_rate=1.0`，作为 polluted gate 的对照。
6. 新增测试覆盖 accepted path、utility update、quarantine 迁移和前五轮配置不回归。
7. 暂缓 tau-bench 接入；待 gate accepted path、utility update 和 quarantine 日志稳定后，再迁移到 tau-bench retail。

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
