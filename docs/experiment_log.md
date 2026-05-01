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

2026-04-30 初次运行；2026-05-01 第六轮复验补充，Linux，机器标识 `BNUZ`，交互式 conda 环境 `(rm)`，Python 3.12.13，pytest 9.0.3，pluggy 1.6.0。

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
10 passed in 0.05s
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
  },
  "utility_update_count": 0,
  "utility_helpful_count": 0,
  "utility_harmful_count": 0,
  "utility_neutral_count": 0,
  "candidate_memory_count": 5,
  "active_memory_count": 0,
  "quarantined_memory_count": 0,
  "retired_memory_count": 0
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

该结果说明 gate 对跨 intent candidate 的保守拒绝仍然稳定。由于没有记忆被注入，`utility_update_count=0`，所有 candidate 仍处于 `candidate` 状态。accepted path 和 active promotion 已由第六轮新增的 `tiny_nt_memevo_gate_repeated_seed1` 覆盖。

### 下一步

与 repeated 和 polluted/unsafe polluted 配置一起对照，下一轮应加入 replay 归因，验证被接受或被拒绝的记忆是否在局部反事实重放中真实改变任务结果。

## tiny_nt_memevo_gate_polluted_seed1

### 实验名称

`tiny_nt_memevo_gate_polluted_seed1`

### 日期与环境

2026-04-30 初次运行；2026-05-01 第六轮复验补充，Linux，机器标识 `BNUZ`，交互式 conda 环境 `(rm)`，Python 3.12.13，pytest 9.0.3，pluggy 1.6.0。

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
10 passed in 0.05s
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
  },
  "utility_update_count": 0,
  "utility_helpful_count": 0,
  "utility_harmful_count": 0,
  "utility_neutral_count": 0,
  "candidate_memory_count": 6,
  "active_memory_count": 0,
  "quarantined_memory_count": 0,
  "retired_memory_count": 0
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

污染记忆拒绝实验通过。虽然污染记忆在 `tiny_refund_001` 上有较高 `precondition_score=0.9`，但由于带有 `negative_evidence` 且配置 `reject_negative_evidence=true`，gate 仍将其拒绝。因此本实验 `success_rate=1.0`、`negative_transfer_rate=0.0`，证明污染记忆阻断链路有效。

第六轮复验还确认：拒绝路径不会触发 `utility_update`，因此安全 gate 不会因为未注入的污染记忆更新 utility 或 lifecycle。与后续 unsafe polluted ablation 对照可见，只有污染记忆实际进入 `used_memory_ids` 并导致失败时，才会产生 harmful update 和 quarantine。

### 下一步

下一轮应通过 leave-one-memory-out replay 验证这种“拒绝避免负迁移 / 接受导致负迁移”的归因，而不是只依赖在线结果代理。

## tiny_nt_memevo_gate_unsafe_polluted_seed1

### 实验名称

`tiny_nt_memevo_gate_unsafe_polluted_seed1`

### 日期与环境

2026-05-01，Linux，机器标识 `BNUZ`，交互式 conda 环境 `(rm)`，Python 3.12.13，pytest 9.0.3，pluggy 1.6.0。

### 运行命令

```bash
conda activate rm
pip install -e ".[dev]"
python -m pytest
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_unsafe_polluted.yaml
cat runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/metrics.json
grep 'polluted_refund_lookup_policy_001' runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/memory_updates.jsonl
head -n 2 runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/candidate_memories.jsonl
```

### 配置文件

`configs/tiny_nt_memevo_gate_unsafe_polluted.yaml`

关键参数：`benchmark.split_file=data/task_splits/tiny_refund_only_tasks.json`，`memory.bootstrap_file=data/memory_fixtures/tiny_polluted_candidates.jsonl`，`gate.reject_negative_evidence=false`，`gate.min_score=-1.0`，`gate.max_risk=1.0`，`models.actor.follow_memory_hints=true`。

### 输出目录

`runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/`

### 结果

`pytest` 结果：

```text
10 passed in 0.05s
```

`tiny_nt_memevo_gate_unsafe_polluted_seed1/metrics.json`：

```json
{
  "num_tasks": 1,
  "success_rate": 0.0,
  "avg_reward": 0.0,
  "avg_steps": 2.0,
  "avg_prompt_tokens": 577.0,
  "avg_completion_tokens": 79.0,
  "avg_tool_calls": 1.0,
  "with_memory_fail_no_memory_success": 1,
  "memory_attributed_failures": 1,
  "negative_transfer_rate": 1.0,
  "harmful_memory_ids": [
    "polluted_refund_lookup_policy_001"
  ],
  "negative_transfer_failure_examples": [
    {
      "task_id": "tiny_refund_polluted_001",
      "used_memory_ids": [
        "polluted_refund_lookup_policy_001"
      ],
      "reward": 0.0,
      "error_type": "expected_answer_mismatch"
    }
  ],
  "memory_policy": "nt_memevo_gate",
  "memory_size": 2,
  "memory_top_k": 1,
  "gate_decision_count": 1,
  "gate_accepted_count": 1,
  "gate_rejected_count": 0,
  "gate_rejection_reasons": {
    "accepted": 1
  },
  "utility_update_count": 1,
  "utility_helpful_count": 0,
  "utility_harmful_count": 1,
  "utility_neutral_count": 0,
  "candidate_memory_count": 1,
  "active_memory_count": 0,
  "quarantined_memory_count": 1,
  "retired_memory_count": 0
}
```

`memory_updates.jsonl` 抽查结果：

1. 第 0 轮写入 `bootstrap_candidate`，污染记忆 `polluted_refund_lookup_policy_001` 被导入 candidate pool。
2. unsafe gate 对污染记忆产生 `gate_decision=accept`，`selected_rank=1`，`final_gate_score=-0.013266`；该配置故意设置 `gate.reject_negative_evidence=false`、`gate.min_score=-1.0`、`gate.max_risk=1.0`。
3. `retrieve` 事件显示 `retrieved_memory_ids=["polluted_refund_lookup_policy_001"]`，污染记忆进入 agent prompt。
4. 任务失败后写入 `utility_update`：`outcome=harmful`、`baseline_reward=1.0`、`delta_reward=-1.0`。
5. 污染记忆 utility 从 `alpha=1.0`、`beta=3.0`、`num_used=2`、`num_harmful=2` 更新为 `alpha=1.0`、`beta=4.0`、`num_used=3`、`num_harmful=3`。
6. 污染记忆 lifecycle 从 `candidate` 更新为 `quarantined`，`last_used_iter=1`。
7. 污染记忆 `negative_evidence` 追加 `tiny_nt_memevo_gate_unsafe_polluted_seed1_tiny_refund_polluted_001`。

`candidate_memories.jsonl` 抽查结果：

1. 第一条污染记忆最终为 `lifecycle.status=quarantined`，`mean_delta_reward=-1.0`，`lcb_delta_reward=-1.0`，`num_harmful=3`。
2. 本轮失败任务还抽取出一条新的 warning candidate：`cand_000001_tiny_refund_polluted_001`，其 `negative_evidence` 指向当前失败 run。

### 现象与问题

unsafe polluted ablation 复验通过。放宽 gate 后，带负证据的污染记忆被接受并注入 prompt，mock agent 跟随错误工具提示调用 `lookup_policy`，导致 refund-only 任务失败；负迁移指标稳定触发，`negative_transfer_rate=1.0`。

第六轮新增的 online utility update 也按预期生效：污染记忆被判为 `harmful`，`beta` 与 `num_harmful` 增加，当前失败 run 被追加到 `negative_evidence`，并且 lifecycle 进入 `quarantined`。

### 下一步

该实验是有意放宽 gate 的反例配置，不应作为方法主结果；它用于对照 `tiny_nt_memevo_gate_polluted_seed1`，证明安全 gate 拒绝污染记忆时可避免该负迁移。下一轮应加入 leave-one-memory-out replay，把这里的 online harmful proxy 升级为局部反事实归因。

## tiny_nt_memevo_gate_repeated_seed1

### 实验名称

`tiny_nt_memevo_gate_repeated_seed1`

### 日期与环境

2026-05-01，Linux，机器标识 `BNUZ`，交互式 conda 环境 `(rm)`，Python 3.12.13，pytest 9.0.3，pluggy 1.6.0。

### 运行命令

```bash
conda activate rm
pip install -e ".[dev]"
python -m pytest
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_repeated.yaml
cat runs/tiny_nt_memevo_gate_repeated_seed1/metrics.json
grep '"event_type": "utility_update"' runs/tiny_nt_memevo_gate_repeated_seed1/memory_updates.jsonl
head -n 3 runs/tiny_nt_memevo_gate_repeated_seed1/candidate_memories.jsonl
```

### 配置文件

`configs/tiny_nt_memevo_gate_repeated.yaml`

关键参数：`benchmark.name=tiny_tools`，`split_file=data/task_splits/tiny_repeated_intent_tasks.json`，`max_tasks=3`，`memory.method=nt_memevo_gate`，`memory.top_k=2`，`memory.utility.promote_after_helpful=2`，`memory.utility.quarantine_after_harmful=1`，`models.actor.provider=mock`。

### 输出目录

`runs/tiny_nt_memevo_gate_repeated_seed1/`

### 结果

`tiny_nt_memevo_gate_repeated_seed1/metrics.json`：

```json
{
  "num_tasks": 3,
  "success_rate": 1.0,
  "avg_reward": 1.0,
  "avg_steps": 2.0,
  "avg_prompt_tokens": 591.3333333333334,
  "avg_completion_tokens": 67.0,
  "avg_tool_calls": 1.0,
  "with_memory_fail_no_memory_success": 0,
  "memory_attributed_failures": 0,
  "negative_transfer_rate": 0.0,
  "harmful_memory_ids": [],
  "negative_transfer_failure_examples": [],
  "memory_policy": "nt_memevo_gate",
  "memory_size": 3,
  "memory_top_k": 2,
  "gate_decision_count": 3,
  "gate_accepted_count": 3,
  "gate_rejected_count": 0,
  "gate_rejection_reasons": {
    "accepted": 3
  },
  "utility_update_count": 3,
  "utility_helpful_count": 3,
  "utility_harmful_count": 0,
  "utility_neutral_count": 0,
  "candidate_memory_count": 2,
  "active_memory_count": 1,
  "quarantined_memory_count": 0,
  "retired_memory_count": 0
}
```

`memory_updates.jsonl` 抽查结果：

1. 共写入 3 条 `utility_update` 事件，全部为 `outcome=helpful`。
2. `cand_000001_tiny_order_repeat_001` 在 iteration 2 首次被使用并更新：`alpha=2.0`、`beta=1.0`、`num_used=1`、`num_helpful=1`、`lifecycle.status=candidate`、`last_used_iter=2`。
3. `cand_000002_tiny_order_repeat_002` 在 iteration 3 被使用并更新：`alpha=2.0`、`beta=1.0`、`num_used=1`、`num_helpful=1`、`lifecycle.status=candidate`、`last_used_iter=3`。
4. `cand_000001_tiny_order_repeat_001` 在 iteration 3 第二次被使用并更新：`alpha=3.0`、`beta=1.0`、`num_used=2`、`num_helpful=2`、`lifecycle.status=active`、`last_used_iter=3`。
5. 三条 `utility_update` 的 `delta_reward` 均为 `0.0`，这是因为本轮使用 `no_memory_success=true` 推断 baseline reward 为 1.0，当前任务 reward 也为 1.0；这符合第六轮 online proxy 设计。

`candidate_memories.jsonl` 抽查结果：

1. 第一条 repeated memory `cand_000001_tiny_order_repeat_001` 已从 `candidate` 提升为 `active`。
2. 第一条 repeated memory 最终 `positive_evidence` 包含 3 个 repeated run，`negative_evidence=[]`，`utility.num_used=2`，`utility.num_helpful=2`，`utility.num_harmful=0`。
3. 第二条 repeated memory `cand_000002_tiny_order_repeat_002` 保持 `candidate`，`num_used=1`，`num_helpful=1`，`last_used_iter=3`。
4. 第三条 repeated memory `cand_000003_tiny_order_repeat_003` 是任务结束后新抽取的 candidate，尚未被后续任务使用，`num_used=0`，`last_used_iter=null`。

### 现象与问题

repeated-intent 实验通过。与主五任务 `tiny_nt_memevo_gate.yaml` 中 gate 全部拒绝跨 intent candidate 不同，本配置连续出现同一个 `order_status` intent，使 gate 出现稳定 accepted path。第六轮新增的 online utility update 能够累计 helpful 证据，并在达到 `promote_after_helpful=2` 后把第一条 candidate promotion 为 `active`。

当前 split 使用同一个 `ORD-1001` order-status 任务，主要用于验证日志链路和 lifecycle 迁移，不代表真实 benchmark 难度，也不能证明记忆带来任务收益。

### 下一步

下一轮应实现 leave-one-memory-out replay：对 repeated 中被注入的 memory 重放 `with memory` 与 `without memory`，把当前 `outcome=helpful` 的 online proxy 升级为 replay-backed attribution；同时把 `candidate -> active` 从简单 helpful 阈值升级为验证门控。

## 当前下一轮方向

第一阶段第七轮建议优先实现 `leave-one-memory-out replay + verification-gated consolidation`。第六轮已经跑通 online utility update、active promotion 和 harmful quarantine，但 helpful/harmful 仍主要来自在线 outcome proxy，还缺少局部反事实估计来支撑论文中的 negative-transfer attribution。

第七轮建议范围：

1. 新增 replay runner，支持对已完成任务重放 `with selected memory` 和 `without selected memory`。
2. 对 `nt_memevo_gate` 的 top-k used memories 做 leave-one-memory-out replay，产出 `delta_reward` 和更可信的 harmful/helpful 判断。
3. 将 replay 结果写入 `replay_results.jsonl`，并在 `memory_updates.jsonl` 中记录 replay-backed utility update。
4. 将 active promotion 从单纯 helpful 阈值升级为 replay/support-task 验证门控。
5. 保留 online proxy 作为低成本默认路径，把 replay 作为可配置高置信路径。
6. 增加 repeated-intent 和 polluted replay 测试，确保第六轮所有配置不回归。
7. replay 日志稳定后再迁移 tau-bench retail。

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
