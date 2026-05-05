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
cat runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/replay_results.jsonl
grep 'polluted_refund_lookup_policy_001' runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/memory_updates.jsonl
head -n 2 runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/candidate_memories.jsonl
```

### 配置文件

`configs/tiny_nt_memevo_gate_unsafe_polluted.yaml`

关键参数：`benchmark.split_file=data/task_splits/tiny_refund_only_tasks.json`，`memory.bootstrap_file=data/memory_fixtures/tiny_polluted_candidates.jsonl`，`memory.replay.enabled=true`，`gate.reject_negative_evidence=false`，`gate.min_score=-1.0`，`gate.max_risk=1.0`，`models.actor.follow_memory_hints=true`。

说明：第七轮已在该配置中启用 replay，下面记录的是用户重新运行后的 replay-backed harmful attribution 结果。

### 输出目录

`runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/`

### 结果

`pytest` 结果：

```text
11 passed in 0.04s
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
  "utility_credit_sources": {
    "leave_one_memory_out": 1
  },
  "online_proxy_utility_update_count": 0,
  "replay_utility_update_count": 1,
  "replay_result_count": 3,
  "replay_leave_one_count": 1,
  "replay_helpful_count": 0,
  "replay_harmful_count": 1,
  "replay_neutral_count": 0,
  "candidate_memory_count": 1,
  "active_memory_count": 0,
  "quarantined_memory_count": 1,
  "retired_memory_count": 0
}
```

`replay_results.jsonl` 抽查结果：

1. 共写入 3 条 replay 记录：`with_selected_memory`、`without_selected_memory` 和 `leave_one_memory_out`。
2. `without_selected_memory` 记录显示：`with_reward=0.0`、`without_reward=1.0`、`delta_reward=-1.0`、`with_success=false`、`without_success=true`、`attribution_label=harmful`。
3. 针对污染记忆 `polluted_refund_lookup_policy_001` 的 `leave_one_memory_out` 记录显示：`with_reward=0.0`、`without_reward=1.0`、`delta_reward=-1.0`、`with_success=false`、`without_success=true`、`attribution_label=harmful`。

`memory_updates.jsonl` 抽查结果：

1. 第 0 轮写入 `bootstrap_candidate`，污染记忆 `polluted_refund_lookup_policy_001` 被导入 candidate pool。
2. unsafe gate 对污染记忆产生 `gate_decision=accept`，`selected_rank=1`，`final_gate_score=-0.013266`；该配置故意设置 `gate.reject_negative_evidence=false`、`gate.min_score=-1.0`、`gate.max_risk=1.0`。
3. `retrieve` 事件显示 `retrieved_memory_ids=["polluted_refund_lookup_policy_001"]`，污染记忆进入 agent prompt。
4. 任务失败后写入 replay-backed `utility_update`：`outcome=harmful`、`credit_source=leave_one_memory_out`、`baseline_reward=1.0`、`delta_reward=-1.0`、`replay_attribution_label=harmful`。
5. 污染记忆 utility 从 `alpha=1.0`、`beta=3.0`、`num_used=2`、`num_harmful=2` 更新为 `alpha=1.0`、`beta=4.0`、`num_used=3`、`num_harmful=3`。
6. 污染记忆 lifecycle 从 `candidate` 更新为 `quarantined`，`last_used_iter=1`。
7. 污染记忆 `negative_evidence` 追加 `tiny_nt_memevo_gate_unsafe_polluted_seed1_tiny_refund_polluted_001`。

`candidate_memories.jsonl` 抽查结果：

1. 第一条污染记忆最终为 `lifecycle.status=quarantined`，`mean_delta_reward=-1.0`，`lcb_delta_reward=-1.0`，`num_harmful=3`。
2. 本轮失败任务还抽取出一条新的 warning candidate：`cand_000001_tiny_refund_polluted_001`，其 `negative_evidence` 指向当前失败 run。

### 现象与问题

unsafe polluted ablation 复验通过。放宽 gate 后，带负证据的污染记忆被接受并注入 prompt，mock agent 跟随错误工具提示调用 `lookup_policy`，导致 refund-only 任务失败；负迁移指标稳定触发，`negative_transfer_rate=1.0`。

第七轮 replay-backed utility update 按预期生效：污染记忆的 harmful 判断来自 `leave_one_memory_out` replay，`delta_reward=-1.0` 说明移除该记忆后任务从失败恢复为成功；随后 `beta` 与 `num_harmful` 增加，当前失败 run 被追加到 `negative_evidence`，并且 lifecycle 进入 `quarantined`。

### 下一步

该实验是有意放宽 gate 的反例配置，不应作为方法主结果；它用于对照 `tiny_nt_memevo_gate_polluted_seed1`，证明安全 gate 拒绝污染记忆时可避免该负迁移。第七轮已将该配置升级为 replay-backed harmful attribution，下一步应把单任务 harmful replay 扩展为 support-set verification。

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
  "utility_credit_sources": {
    "online_proxy": 3
  },
  "online_proxy_utility_update_count": 3,
  "replay_utility_update_count": 0,
  "replay_result_count": 0,
  "replay_leave_one_count": 0,
  "replay_helpful_count": 0,
  "replay_harmful_count": 0,
  "replay_neutral_count": 0,
  "candidate_memory_count": 2,
  "active_memory_count": 1,
  "quarantined_memory_count": 0,
  "retired_memory_count": 0
}
```

`memory_updates.jsonl` 抽查结果：

1. 共写入 3 条 `utility_update` 事件，全部为 `outcome=helpful` 且 `credit_source=online_proxy`。
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

第七轮已实现 leave-one-memory-out replay。后续复验时可把本实验作为 online proxy fallback 对照，再与 `tiny_nt_memevo_gate_replay_seed1` 的 replay-backed attribution 对比。

## tiny_nt_memevo_gate_replay_seed1

### 实验名称

`tiny_nt_memevo_gate_replay_seed1`

### 日期与环境

2026-05-01，Linux，机器标识 `BNUZ`，交互式 conda 环境 `(rm)`，Python 3.12.13，pytest 9.0.3，pluggy 1.6.0。

### 运行命令

```bash
conda activate rm
pip install -e ".[dev]"
python -m pytest
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_replay.yaml
cat runs/tiny_nt_memevo_gate_replay_seed1/metrics.json
cat runs/tiny_nt_memevo_gate_replay_seed1/replay_results.jsonl
grep '"credit_source": "leave_one_memory_out"' runs/tiny_nt_memevo_gate_replay_seed1/memory_updates.jsonl
head -n 3 runs/tiny_nt_memevo_gate_replay_seed1/candidate_memories.jsonl
```

### 配置文件

`configs/tiny_nt_memevo_gate_replay.yaml`

关键参数：`benchmark.name=tiny_tools`，`split_file=data/task_splits/tiny_memory_dependent_tasks.json`，`max_tasks=3`，`memory.method=nt_memevo_gate`，`memory.top_k=1`，`memory.replay.enabled=true`，`memory.replay.max_memories=1`，`memory.replay.promote_requires_positive_lcb=true`，`models.actor.follow_memory_hints=true`。

### 输出目录

`runs/tiny_nt_memevo_gate_replay_seed1/`

### 结果

`pytest` 结果：

```text
11 passed in 0.04s
```

`tiny_nt_memevo_gate_replay_seed1/metrics.json`：

```json
{
  "num_tasks": 3,
  "success_rate": 1.0,
  "avg_reward": 1.0,
  "avg_steps": 2.0,
  "avg_prompt_tokens": 514.0,
  "avg_completion_tokens": 71.0,
  "avg_tool_calls": 1.0,
  "with_memory_fail_no_memory_success": 0,
  "memory_attributed_failures": 0,
  "negative_transfer_rate": 0.0,
  "harmful_memory_ids": [],
  "negative_transfer_failure_examples": [],
  "memory_policy": "nt_memevo_gate",
  "memory_size": 3,
  "memory_top_k": 1,
  "gate_decision_count": 3,
  "gate_accepted_count": 2,
  "gate_rejected_count": 1,
  "gate_rejection_reasons": {
    "accepted": 2,
    "top_k_pruned": 1
  },
  "utility_update_count": 2,
  "utility_helpful_count": 2,
  "utility_harmful_count": 0,
  "utility_neutral_count": 0,
  "utility_credit_sources": {
    "leave_one_memory_out": 2
  },
  "online_proxy_utility_update_count": 0,
  "replay_utility_update_count": 2,
  "replay_result_count": 6,
  "replay_leave_one_count": 2,
  "replay_helpful_count": 2,
  "replay_harmful_count": 0,
  "replay_neutral_count": 0,
  "candidate_memory_count": 2,
  "active_memory_count": 1,
  "quarantined_memory_count": 0,
  "retired_memory_count": 0
}
```

`replay_results.jsonl` 抽查结果：

1. 共写入 6 条 replay 记录，两个 memory-dependent 任务各有 `with_selected_memory`、`without_selected_memory` 和 `leave_one_memory_out`。
2. 两条 `leave_one_memory_out` 记录均针对 `cand_000001_tiny_memory_order_seed_001`。
3. 两条 `leave_one_memory_out` 记录均为 `with_reward=1.0`、`without_reward=0.0`、`delta_reward=1.0`、`with_success=true`、`without_success=false`、`attribution_label=helpful`。
4. 两条 `without_selected_memory` 记录同样显示空记忆重放失败，说明该 memory-dependent split 确实依赖 seed memory 中的工具证据。

`memory_updates.jsonl` 抽查结果：

1. 两条 `utility_update` 均为 `credit_source=leave_one_memory_out`、`outcome=helpful`、`replay_attribution_label=helpful`、`replay_delta_reward=1.0`。
2. 第一次 replay-backed update 后，seed memory `alpha=2.0`、`beta=1.0`、`mean_delta_reward=1.0`、`lcb_delta_reward=0.0`、`num_used=1`、`num_helpful=1`，仍保持 `candidate`。
3. 第二次 replay-backed update 后，seed memory `alpha=3.0`、`beta=1.0`、`mean_delta_reward=1.0`、`lcb_delta_reward=0.292893`、`num_used=2`、`num_helpful=2`，并从 `candidate` 提升为 `active`。

`candidate_memories.jsonl` 抽查结果：

1. 第一条 seed memory `cand_000001_tiny_memory_order_seed_001` 最终为 `lifecycle.status=active`、`last_used_iter=3`。
2. 该 seed memory 的 `positive_evidence` 包含 seed run 和两个 replay-dependent run，`negative_evidence=[]`。
3. 第二、三条 replay-dependent candidate 均保持 `candidate`，尚未被后续任务使用。

`runs.jsonl` 抽查结果：

1. 第 1 个任务 `tiny_memory_order_seed_001` 不使用记忆，成功调用 `get_order_status({'order_id': 'ORD-1001'})`。
2. 第 2、3 个任务均使用 `cand_000001_tiny_memory_order_seed_001`，并成功通过记忆中的工具证据调用 `get_order_status({'order_id': 'ORD-1001'})`。

### 现象与问题

replay-backed utility update 复验通过。与 `tiny_nt_memevo_gate_repeated_seed1` 的 online proxy 对照不同，本配置中 helpful 证据来自 leave-one-memory-out replay：带 seed memory 时任务成功，移除该 memory 后任务失败，因此 `delta_reward=1.0`。第二次 replay-helpful 更新后，`lcb_delta_reward=0.292893>0`，满足 `promote_requires_positive_lcb=true` 的 replay-backed promotion 条件，seed memory 进入 `active`。

当前 split 是人工构造的 memory-dependent 链路验证：它证明 replay attribution、replay-backed utility update 和 active promotion 可以稳定复现，但不代表真实 benchmark 难度。

### 下一步

将单任务 replay 扩展为 support-set / matched replay，并加入 replay 成本指标。

## 第一阶段第七轮完整对照复验摘要

### 日期与环境

2026-05-01，Linux，机器标识 `BNUZ`，交互式 conda 环境 `(rm)`，Python 3.12.13，pytest 9.0.3，pluggy 1.6.0。

### 测试结果

```text
11 passed in 0.04s
```

### 对照指标

1. `tiny_nomem_seed1`：`success_rate=1.0`，`avg_prompt_tokens=310.4`，`memory_policy=none`，`memory_size=0`，`negative_transfer_rate=0.0`。
2. `tiny_raw_trace_rag_seed1`：`success_rate=1.0`，`avg_prompt_tokens=538.6`，`memory_policy=raw_trace_rag`，`memory_size=5`，`memory_top_k=2`，`negative_transfer_rate=0.0`。
3. `tiny_reflexion_seed1`：`success_rate=1.0`，`avg_prompt_tokens=832.2`，`memory_policy=reflexion`，`memory_size=5`，`memory_top_k=2`，`negative_transfer_rate=0.0`。
4. `tiny_nt_memevo_candidate_seed1`：`success_rate=1.0`，`avg_prompt_tokens=310.4`，`memory_policy=nt_memevo_candidate`，`memory_size=5`，`candidate_memory_count=5`，`active_memory_count=0`，`quarantined_memory_count=0`。
5. `tiny_nt_memevo_gate_seed1`：`success_rate=1.0`，`memory_size=5`，`gate_decision_count=10`，`gate_accepted_count=0`，`gate_rejection_reasons={"precondition_below_threshold": 10}`，`utility_update_count=0`。
6. `tiny_nt_memevo_gate_repeated_seed1`：`num_tasks=3`，`success_rate=1.0`，`gate_accepted_count=3`，`utility_update_count=3`，`utility_credit_sources={"online_proxy": 3}`，`online_proxy_utility_update_count=3`，`replay_utility_update_count=0`，`active_memory_count=1`。
7. `tiny_nt_memevo_gate_replay_seed1`：`num_tasks=3`，`success_rate=1.0`，`gate_accepted_count=2`，`replay_result_count=6`，`replay_leave_one_count=2`，`replay_helpful_count=2`，`utility_credit_sources={"leave_one_memory_out": 2}`，`replay_utility_update_count=2`，`active_memory_count=1`。
8. `tiny_nt_memevo_gate_polluted_seed1`：`success_rate=1.0`，`memory_size=6`，`gate_decision_count=15`，`gate_accepted_count=0`，`gate_rejection_reasons={"negative_evidence_present": 5, "precondition_below_threshold": 10}`，`negative_transfer_rate=0.0`，`utility_update_count=0`。
9. `tiny_nt_memevo_gate_unsafe_polluted_seed1`：`num_tasks=1`，`success_rate=0.0`，`negative_transfer_rate=1.0`，`harmful_memory_ids=["polluted_refund_lookup_policy_001"]`，`replay_leave_one_count=1`，`replay_harmful_count=1`，`replay_utility_update_count=1`，`quarantined_memory_count=1`。

### 结论

第七轮完整复验通过。基础 baseline、candidate schema、保守 gate、online proxy fallback、replay-helpful attribution、safe polluted rejection 和 unsafe polluted replay-harmful attribution 均稳定。当前日志已经能区分 `online_proxy` 与 `leave_one_memory_out` 两类 utility credit source，并能在 `replay_results.jsonl` 中记录 helpful/harmful 的局部反事实证据。

## 第一阶段第八轮完整对照复验摘要

### 日期与环境

2026-05-02，Linux，机器标识 `BNUZ`，交互式 conda 环境 `(rm)`，Python 3.12.13，pytest 9.0.3，pluggy 1.6.0。

### 测试结果

```text
13 passed in 0.08s
```

### 对照指标

1. `tiny_nomem_seed1`：`success_rate=1.0`，`avg_prompt_tokens=310.4`，`memory_policy=none`，`memory_size=0`，`negative_transfer_rate=0.0`，`verification_count=0`。
2. `tiny_raw_trace_rag_seed1`：`success_rate=1.0`，`avg_prompt_tokens=538.6`，`memory_policy=raw_trace_rag`，`memory_size=5`，`memory_top_k=2`，`verification_count=0`。
3. `tiny_reflexion_seed1`：`success_rate=1.0`，`avg_prompt_tokens=832.2`，`memory_policy=reflexion`，`memory_size=5`，`memory_top_k=2`，`verification_count=0`。
4. `tiny_nt_memevo_candidate_seed1`：`success_rate=1.0`，`avg_prompt_tokens=310.4`，`memory_policy=nt_memevo_candidate`，`memory_size=5`，`candidate_memory_count=5`，`active_memory_count=0`，`quarantined_memory_count=0`。
5. `tiny_nt_memevo_gate_seed1`：`success_rate=1.0`，`memory_size=5`，`gate_decision_count=10`，`gate_accepted_count=0`，`gate_rejection_reasons={"precondition_below_threshold": 10}`，`utility_update_count=0`。
6. `tiny_nt_memevo_gate_repeated_seed1`：`num_tasks=3`，`success_rate=1.0`，`gate_accepted_count=3`，`utility_update_count=3`，`utility_credit_sources={"online_proxy": 3}`，`online_proxy_utility_update_count=3`，`replay_utility_update_count=0`，`active_memory_count=1`。
7. `tiny_nt_memevo_gate_replay_seed1`：`num_tasks=3`，`success_rate=1.0`，`gate_accepted_count=2`，`replay_result_count=6`，`replay_leave_one_count=2`，`replay_helpful_count=2`，`utility_credit_sources={"leave_one_memory_out": 2}`，`support_replay_count=0`，`active_memory_count=1`。
8. `tiny_nt_memevo_gate_verify_seed1`：`num_tasks=3`，`success_rate=1.0`，`gate_accepted_count=2`，`replay_result_count=8`，`replay_leave_one_count=2`，`support_replay_count=2`，`support_replay_helpful_count=2`，`verification_count=1`，`verification_passed_count=1`，`verification_failed_count=0`，`active_memory_count=1`。
9. `tiny_nt_memevo_gate_polluted_seed1`：`success_rate=1.0`，`memory_size=6`，`gate_decision_count=15`，`gate_accepted_count=0`，`gate_rejection_reasons={"negative_evidence_present": 5, "precondition_below_threshold": 10}`，`negative_transfer_rate=0.0`，`verification_count=0`。
10. `tiny_nt_memevo_gate_unsafe_polluted_seed1`：`num_tasks=1`，`success_rate=0.0`，`negative_transfer_rate=1.0`，`harmful_memory_ids=["polluted_refund_lookup_policy_001"]`，`replay_leave_one_count=1`，`replay_harmful_count=1`，`replay_utility_update_count=1`，`quarantined_memory_count=1`。

### 结论

第八轮完整复验通过。基础 baseline、candidate schema、保守 gate、online proxy fallback、source-task replay、support-set verification、safe polluted rejection 和 unsafe polluted harmful attribution 均稳定。新增 `tiny_nt_memevo_gate_verify_seed1` 证明 candidate memory 可以先通过 source-task replay 累计 helpful evidence，但不即时 promotion；随后由 support-set verification 统一决定 `candidate -> active`。

关键日志检查也通过：

1. `memory_updates.jsonl` 中存在 1 条 `event_type=verification_update`。
2. `verification_update` 显示 `support_task_ids=["tiny_support_order_001","tiny_support_order_002"]`、`support_delta_mean=1.0`、`support_lcb_delta_reward=0.292893`、`support_negative_transfer_rate=0.0`。
3. `verification_update.lifecycle_before.status=candidate`，`lifecycle_after.status=active`。
4. `replay_results.jsonl` 中两条 `replay_scope=support_task_replay` 均为 `delta_reward=1.0`、`cost_adjusted_delta_reward=1.0`、`attribution_label=helpful`。
5. `candidate_memories.jsonl` 中 `cand_000001_tiny_memory_order_seed_001` 最终为 `active`，且 positive evidence 包含两个 support replay ids。

## 当前下一轮方向

第一阶段第九轮建议优先扩展 support pool 与 matched replay，并开始实现 memory scope refinement / merge-split。第八轮已经证明 support-set verification 能够独立决定 `candidate -> active`，但当前 support pool 仍是 tiny 人工构造的 order-status 正向链路，尚不能覆盖“同一记忆在部分任务有益、部分任务有害”的核心负迁移场景。

第九轮建议范围：

1. 扩充 tiny support/task split，覆盖 `refund_eligibility`、`exchange_eligibility`、`inventory_check` 和 `policy_lookup` 的 memory-dependent 正例、neutral 例子和 harmful support 例子。
2. 新增 matched replay selector 日志，记录每个 support task 的 `support_match_score`、`intent_score`、`domain_score`、`tool_score` 和 `lexical_score`，使 support 选择过程可审计。
3. 实现 scope refinement：当 support replay 的 harmful/neutral evidence 集中在某些 intent、tool 或 precondition 上时，生成更窄 scope 的 refined memory，而不是只 quarantine 原 memory。
4. 新增 `memory_refine` / `memory_split` / `memory_merge` 事件，记录 parent memory id、child memory id、scope 变化、证据迁移和触发原因。
5. 增加 replay budget controls，限制每轮 verification 的最大 memory 数、最大 support task 数和最大 replay 执行数，并将预算消耗写入 metrics。
6. 将 replay 成本统计升级为 unique execution 口径，避免 context mode 与 comparison record 重复计数。
7. 保持第八轮全部配置不回归，尤其是 `tiny_nt_memevo_gate_verify_seed1` 的 `verification_passed_count=1` 和 `tiny_nt_memevo_gate_unsafe_polluted_seed1` 的 `negative_transfer_rate=1.0`。
8. 若 support/refinement 日志稳定，可并行开始 tau-bench retail adapter 的最小接入；否则继续先稳定 tiny 上的负迁移拆分链路。

## tiny_nt_memevo_gate_verify_seed1

### 实验名称

`tiny_nt_memevo_gate_verify_seed1`

### 日期与环境

2026-05-02，Linux，机器标识 `BNUZ`，交互式 conda 环境 `(rm)`，Python 3.12.13，pytest 9.0.3，pluggy 1.6.0。

### 运行命令

```bash
conda activate rm
pip install -e ".[dev]"
python -m pytest
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_verify.yaml
cat runs/tiny_nt_memevo_gate_verify_seed1/metrics.json
grep '"event_type": "verification_update"' runs/tiny_nt_memevo_gate_verify_seed1/memory_updates.jsonl
grep '"replay_scope": "support_task_replay"' runs/tiny_nt_memevo_gate_verify_seed1/replay_results.jsonl
head -n 3 runs/tiny_nt_memevo_gate_verify_seed1/candidate_memories.jsonl
```

### 配置文件

`configs/tiny_nt_memevo_gate_verify.yaml`

关键参数：`benchmark.split_file=data/task_splits/tiny_memory_dependent_tasks.json`，`memory.method=nt_memevo_gate`，`memory.top_k=1`，`memory.replay.enabled=true`，`memory.verification.enabled=true`，`memory.verification.support_split_file=data/task_splits/tiny_support_verification_tasks.json`，`memory.verification.disable_immediate_promotion=true`，`models.actor.follow_memory_hints=true`。

### 输出目录

`runs/tiny_nt_memevo_gate_verify_seed1/`

### 结果

`pytest` 结果：

```text
13 passed in 0.08s
```

`tiny_nt_memevo_gate_verify_seed1/metrics.json`：

```json
{
  "num_tasks": 3,
  "success_rate": 1.0,
  "avg_reward": 1.0,
  "avg_steps": 2.0,
  "avg_prompt_tokens": 514.0,
  "avg_completion_tokens": 71.0,
  "avg_tool_calls": 1.0,
  "with_memory_fail_no_memory_success": 0,
  "memory_attributed_failures": 0,
  "negative_transfer_rate": 0.0,
  "harmful_memory_ids": [],
  "negative_transfer_failure_examples": [],
  "memory_policy": "nt_memevo_gate",
  "memory_size": 3,
  "memory_top_k": 1,
  "gate_decision_count": 3,
  "gate_accepted_count": 2,
  "gate_rejected_count": 1,
  "gate_rejection_reasons": {
    "accepted": 2,
    "top_k_pruned": 1
  },
  "utility_update_count": 2,
  "utility_helpful_count": 2,
  "utility_harmful_count": 0,
  "utility_neutral_count": 0,
  "utility_credit_sources": {
    "leave_one_memory_out": 2
  },
  "online_proxy_utility_update_count": 0,
  "replay_utility_update_count": 2,
  "replay_result_count": 8,
  "replay_leave_one_count": 2,
  "replay_helpful_count": 2,
  "replay_harmful_count": 0,
  "replay_neutral_count": 0,
  "support_replay_count": 2,
  "support_replay_helpful_count": 2,
  "support_replay_harmful_count": 0,
  "support_replay_neutral_count": 0,
  "verification_count": 1,
  "verification_passed_count": 1,
  "verification_failed_count": 0,
  "verification_update_count": 1,
  "replay_prompt_tokens": 5876,
  "replay_completion_tokens": 800,
  "replay_tool_calls": 8,
  "replay_delta_prompt_tokens": 2764,
  "replay_delta_tool_calls": 6,
  "support_replay_prompt_tokens": 1540,
  "support_replay_completion_tokens": 218,
  "support_replay_tool_calls": 2,
  "candidate_memory_count": 2,
  "active_memory_count": 1,
  "quarantined_memory_count": 0,
  "retired_memory_count": 0
}
```

`memory_updates.jsonl` 抽查结果：

1. 存在 1 条 `event_type=verification_update`。
2. 该 verification 对应 `memory_id=cand_000001_tiny_memory_order_seed_001`。
3. `verification_passed=true`，`failure_reason=null`。
4. `support_task_ids=["tiny_support_order_001","tiny_support_order_002"]`。
5. `support_delta_mean=1.0`，`support_lcb_delta_reward=0.292893`，`support_negative_transfer_rate=0.0`。
6. `support_replay_count=2`，`support_replay_helpful_count=2`，`support_replay_harmful_count=0`。
7. `lifecycle_before.status=candidate`，`lifecycle_after.status=active`。
8. `positive_evidence` 在 source-task evidence 之外追加了两个 support replay id。

`replay_results.jsonl` 抽查结果：

1. 共 8 条 replay 记录，其中 6 条来自 source-task replay，2 条来自 support-task replay。
2. 两条 support replay 的 `replay_scope=support_task_replay`，`mode=support_task_replay`。
3. 两条 support replay 分别对应 `tiny_support_order_001` 和 `tiny_support_order_002`。
4. 两条 support replay 均为 `with_reward=1.0`、`without_reward=0.0`、`delta_reward=1.0`、`cost_adjusted_delta_reward=1.0`、`with_success=true`、`without_success=false`、`attribution_label=helpful`。
5. Support replay 成本字段完整：两条记录均包含 `with_prompt_tokens`、`without_prompt_tokens`、`delta_prompt_tokens`、`with_completion_tokens`、`without_completion_tokens`、`delta_completion_tokens`、`with_tool_calls`、`without_tool_calls` 和 `delta_tool_calls`。

`candidate_memories.jsonl` 抽查结果：

1. 第一条 seed memory `cand_000001_tiny_memory_order_seed_001` 最终为 `lifecycle.status=active`。
2. 该 memory 最终 `alpha=3.0`、`beta=1.0`、`mean_delta_reward=1.0`、`lcb_delta_reward=0.292893`、`num_used=2`、`num_helpful=2`、`num_harmful=0`。
3. 该 memory 的 `positive_evidence` 包含 seed run、两个 source replay-dependent run 和两个 support replay ids。
4. 第二、三条 replay-dependent candidate 仍保持 `candidate`，尚未被后续任务验证或 promotion。

### 现象与问题

第八轮 support-set verification 复验通过。与 `tiny_nt_memevo_gate_replay_seed1` 不同，本配置使用 `memory.verification.disable_immediate_promotion=true`，因此 seed memory 在两次 source-task leave-one-memory-out replay helpful 后先保持 `candidate`；随后 support-set verification 在两个相似 support tasks 上均得到 `delta_reward=1.0`，最终由 `verification_update` 将其提升为 `active`。

该实验说明第一阶段已经具备三层递进链路：

1. `online_proxy`：快速 outcome update，用于 repeated-intent fallback。
2. `leave_one_memory_out`：当前任务局部反事实归因，用于 source-task helpful/harmful 判断。
3. `support_task_replay`：相似支持任务集合验证，用于更稳健的 candidate consolidation。

当前问题是 support pool 仍是 tiny 人工构造，且本实验只验证了 order-status 正向链路。后续需要覆盖 refund、exchange、inventory、policy 等更多 intent，并加入 neutral/harmful support 例子，用于验证 scope refinement 和 memory split。

### 下一步

第九轮应扩展 support pool 与 matched replay，并开始实现 memory scope refinement / merge-split。重点是让 support replay 能发现“某条记忆在部分 support tasks helpful、在另一部分 support tasks neutral/harmful”的情况，并把这种证据转化为更窄 scope 的 refined memory，而不是只做 active/quarantined 二分。

## tiny_nt_memevo_gate_refine_seed1

### 实验名称

`tiny_nt_memevo_gate_refine_seed1`

### 日期与环境

2026-05-02，Linux，机器标识 `BNUZ`，交互式 conda 环境 `(rm)`，Python 3.12.13，pytest 9.0.3，pluggy 1.6.0。

### 运行命令

```bash
conda activate rm
pip install -e ".[dev]"
python -m pytest
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_refine.yaml
cat runs/tiny_nt_memevo_gate_refine_seed1/metrics.json
grep '"event_type": "support_selection"' runs/tiny_nt_memevo_gate_refine_seed1/memory_updates.jsonl
grep '"event_type": "memory_refine"' runs/tiny_nt_memevo_gate_refine_seed1/memory_updates.jsonl
```

### 配置文件

`configs/tiny_nt_memevo_gate_refine.yaml`

关键参数：`benchmark.split_file=data/task_splits/tiny_memory_dependent_tasks.json`，`memory.verification.support_split_file=data/task_splits/tiny_mixed_support_verification_tasks.json`，`memory.verification.require_intent_match=false`，`memory.verification.max_support_tasks=4`，`memory.verification.min_support_tasks=4`，`memory.verification.refinement.enabled=true`，`memory.verification.budget.max_verifications_per_run=2`，`models.actor.follow_memory_hints=true`。

### 输出目录

`runs/tiny_nt_memevo_gate_refine_seed1/`

### 结果

`pytest` 结果：

```text
15 passed in 0.07s
```

`tiny_nt_memevo_gate_refine_seed1/metrics.json`：

```json
{
  "num_tasks": 3,
  "success_rate": 1.0,
  "avg_reward": 1.0,
  "avg_steps": 2.0,
  "avg_prompt_tokens": 514.0,
  "avg_completion_tokens": 71.0,
  "avg_tool_calls": 1.0,
  "with_memory_fail_no_memory_success": 0,
  "memory_attributed_failures": 0,
  "negative_transfer_rate": 0.0,
  "harmful_memory_ids": [],
  "negative_transfer_failure_examples": [],
  "memory_policy": "nt_memevo_gate",
  "memory_size": 4,
  "memory_top_k": 1,
  "gate_decision_count": 3,
  "gate_accepted_count": 2,
  "gate_rejected_count": 1,
  "gate_rejection_reasons": {
    "accepted": 2,
    "top_k_pruned": 1
  },
  "utility_update_count": 2,
  "utility_helpful_count": 2,
  "utility_harmful_count": 0,
  "utility_neutral_count": 0,
  "utility_credit_sources": {
    "leave_one_memory_out": 2
  },
  "online_proxy_utility_update_count": 0,
  "replay_utility_update_count": 2,
  "replay_result_count": 10,
  "replay_leave_one_count": 2,
  "replay_helpful_count": 2,
  "replay_harmful_count": 0,
  "replay_neutral_count": 0,
  "support_replay_count": 4,
  "support_replay_helpful_count": 2,
  "support_replay_harmful_count": 2,
  "support_replay_neutral_count": 0,
  "verification_count": 1,
  "verification_passed_count": 0,
  "verification_failed_count": 1,
  "verification_update_count": 1,
  "support_selection_count": 4,
  "memory_refinement_count": 1,
  "memory_split_count": 1,
  "verification_budget_skipped_count": 0,
  "verification_budget_skip_reasons": {},
  "verification_budget_max_verifications": 2,
  "verification_budget_max_support_replay_records": 8,
  "verification_budget_verifications_used": 1,
  "verification_budget_support_replay_records_used": 4,
  "replay_record_prompt_tokens": 7757,
  "replay_record_completion_tokens": 1108,
  "replay_record_tool_calls": 12,
  "replay_unique_execution_count": 12,
  "replay_prompt_tokens": 4971,
  "replay_completion_tokens": 744,
  "replay_tool_calls": 8,
  "replay_delta_prompt_tokens": 3343,
  "replay_delta_tool_calls": 6,
  "support_replay_record_prompt_tokens": 3421,
  "support_replay_record_completion_tokens": 526,
  "support_replay_record_tool_calls": 6,
  "support_replay_unique_execution_count": 8,
  "support_replay_prompt_tokens": 3421,
  "support_replay_completion_tokens": 526,
  "support_replay_tool_calls": 6,
  "candidate_memory_count": 2,
  "active_memory_count": 1,
  "quarantined_memory_count": 1,
  "retired_memory_count": 0
}
```

`support_selection` 抽查结果：

1. 共 4 条 `event_type=support_selection`。
2. rank 1 和 rank 2 为 `order_status` support：`support_match_score=0.954119` / `0.929079`，`attribution_label=helpful`，`delta_reward=1.0`，`with_success=true`，`without_success=false`。
3. rank 3 为 `refund_eligibility` support：`support_match_score=0.356605`，`attribution_label=harmful`，`delta_reward=-1.0`，`with_success=false`，`without_success=true`。
4. rank 4 为 `exchange_eligibility` support：`support_match_score=0.162116`，`attribution_label=harmful`，`delta_reward=-1.0`，`with_success=false`，`without_success=true`。
5. 用户复验输出暴露一个字段命名问题：`support_selection` 顶层 `task_id` 表示 source task，support task id 没有独立字段；编码侧已补充 `source_task_id` 和 `support_task_id`，并重新运行 `PYTHONPATH=src python -m pytest -q`，结果为 `15 passed in 0.12s`。

`memory_refine` 抽查结果：

1. 存在 1 条 `event_type=memory_refine`。
2. `parent_memory_id=cand_000001_tiny_memory_order_seed_001`。
3. `child_memory_id=cand_000001_tiny_memory_order_seed_001__refined_001`。
4. `trigger_reason=mixed_support_harmful`。
5. `helpful_support_task_ids=["tiny_mixed_support_order_001","tiny_mixed_support_order_002"]`。
6. `harmful_support_task_ids=["tiny_mixed_support_refund_001","tiny_mixed_support_exchange_001"]`。
7. `child_lifecycle.status=active`。
8. `child_utility.mean_delta_reward=1.0`，`child_utility.lcb_delta_reward=0.292893`，`child_utility.num_helpful=2`，`child_utility.num_harmful=0`。

`replay_results.jsonl` 抽查结果：

1. 共 4 条 `replay_scope=support_task_replay`。
2. 两条 order support replay 为 helpful：`with_reward=1.0`、`without_reward=0.0`、`delta_reward=1.0`、`cost_adjusted_delta_reward=1.0`。
3. refund 和 exchange support replay 为 harmful：`with_reward=0.0`、`without_reward=1.0`、`delta_reward=-1.0`、`cost_adjusted_delta_reward=-1.0`。
4. support replay 记录包含 `with_execution_id` 和 `without_execution_id`，用于 unique-execution 成本统计。

`candidate_memories.jsonl` 抽查结果：

1. parent memory `cand_000001_tiny_memory_order_seed_001` 最终为 `lifecycle.status=quarantined`，包含两个 harmful support replay id 作为 `negative_evidence`。
2. refined child memory `cand_000001_tiny_memory_order_seed_001__refined_001` 最终为 `lifecycle.status=active`。
3. refined child memory 的 `scope.intent=order_status`，`tool_names=["get_order_status"]`，preconditions 中包含 parent id、verification id 和 helpful support task ids。
4. refined child memory 的 `utility.alpha=3.0`、`beta=1.0`、`mean_delta_reward=1.0`、`lcb_delta_reward=0.292893`、`num_used=2`、`num_helpful=2`、`num_harmful=0`。

第九轮完整对照结果：

1. `tiny_nomem_seed1`：`success_rate=1.0`，`avg_prompt_tokens=310.4`，`memory_policy=none`，`memory_size=0`，`negative_transfer_rate=0.0`。
2. `tiny_raw_trace_rag_seed1`：`success_rate=1.0`，`avg_prompt_tokens=538.6`，`memory_policy=raw_trace_rag`，`memory_size=5`，`memory_top_k=2`。
3. `tiny_reflexion_seed1`：`success_rate=1.0`，`avg_prompt_tokens=832.2`，`memory_policy=reflexion`，`memory_size=5`，`memory_top_k=2`。
4. `tiny_nt_memevo_candidate_seed1`：`success_rate=1.0`，`memory_size=5`，`candidate_memory_count=5`，`active_memory_count=0`，`quarantined_memory_count=0`。
5. `tiny_nt_memevo_gate_seed1`：`success_rate=1.0`，`gate_decision_count=10`，`gate_accepted_count=0`，`gate_rejection_reasons={"precondition_below_threshold": 10}`。
6. `tiny_nt_memevo_gate_repeated_seed1`：`num_tasks=3`，`gate_accepted_count=3`，`utility_credit_sources={"online_proxy": 3}`，`active_memory_count=1`。
7. `tiny_nt_memevo_gate_replay_seed1`：`num_tasks=3`，`replay_result_count=6`，`replay_leave_one_count=2`，`replay_helpful_count=2`，`active_memory_count=1`，`replay_prompt_tokens=1550`，`replay_record_prompt_tokens=4336`。
8. `tiny_nt_memevo_gate_verify_seed1`：`num_tasks=3`，`support_replay_count=2`，`support_replay_helpful_count=2`，`verification_passed_count=1`，`active_memory_count=1`，`replay_prompt_tokens=3090`，`replay_record_prompt_tokens=5876`。
9. `tiny_nt_memevo_gate_refine_seed1`：`num_tasks=3`，`support_replay_count=4`，`support_replay_helpful_count=2`，`support_replay_harmful_count=2`，`verification_passed_count=0`，`memory_refinement_count=1`，`memory_split_count=1`，`active_memory_count=1`，`quarantined_memory_count=1`。
10. `tiny_nt_memevo_gate_polluted_seed1`：`success_rate=1.0`，`gate_rejected_count=15`，`gate_rejection_reasons={"negative_evidence_present": 5, "precondition_below_threshold": 10}`，`negative_transfer_rate=0.0`。
11. `tiny_nt_memevo_gate_unsafe_polluted_seed1`：`num_tasks=1`，`success_rate=0.0`，`negative_transfer_rate=1.0`，`harmful_memory_ids=["polluted_refund_lookup_policy_001"]`，`replay_harmful_count=1`，`quarantined_memory_count=1`。

### 现象与问题

第九轮复验通过。`tiny_nt_memevo_gate_refine_seed1` 稳定触发 mixed-support 场景：同一条 order-status seed memory 在 order support tasks 上是 helpful，在 refund/exchange support tasks 上是 harmful，因此 support-set verification 不通过，并生成 refined child memory。该结果验证了第九轮的核心目标：当 support evidence 显示记忆只在部分范围内有益时，系统可以保留有益子范围，而不是只删除或保留原始记忆。

Unique-execution 成本统计按预期生效。`tiny_nt_memevo_gate_refine_seed1` 中 `replay_record_prompt_tokens=7757`，而 unique 口径 `replay_prompt_tokens=4971`，说明 context / comparison / leave-one 记录复用同一 replay execution 时不会重复计入主成本口径。`tiny_nt_memevo_gate_replay_seed1` 和 `tiny_nt_memevo_gate_verify_seed1` 也表现出 record-level 与 unique-execution 口径的差异。

当前仍是 tiny 人工 mixed-support fixture；它证明日志、归因和 lifecycle 机制可用，但还不能证明真实 benchmark 上的 memory split 效果。

### 下一步

第十轮建议优先接入 tau-bench retail 最小 adapter。第一阶段前九轮已经在 tiny 环境中跑通 candidate schema、risk gate、online utility、leave-one-memory-out replay、support-set verification、mixed-support scope refinement 和 unique-execution 成本统计；继续扩 tiny fixture 的边际收益下降，下一步应验证真实工具任务上的 task loader、tool wrapper、evaluator 和统一日志协议。

第十轮应保持第九轮全部 tiny 配置不回归，尤其是 `tiny_nt_memevo_gate_refine_seed1` 的 `memory_refinement_count=1` 和 `tiny_nt_memevo_gate_unsafe_polluted_seed1` 的 `negative_transfer_rate=1.0`。

## 第一阶段第十轮方向

优先方向：接入 tau-bench retail 的最小 adapter，并把现有日志协议迁移到真实工具任务。

理由：第九轮已经在 tiny 环境中验证 mixed-support scope refinement、support selection 审计、verification budget 和 unique-execution replay cost。当前 tiny fixture 的日志链路已经足够稳定，继续扩人工场景容易过拟合；下一步应让真实 benchmark 暴露 task loading、tool API、policy evaluation、state transition 和 replay cost 的真实问题。

第十轮建议范围：

1. 新增 tau-bench retail adapter，支持从本地数据目录或配置路径加载少量 retail tasks。
2. 把 tau-bench task 转换为项目内 `Task`，保留 domain、intent、tool_names、policy metadata 和 no-memory baseline 估计字段。
3. 封装 retail tool API wrapper，先支持极小 smoke 所需工具，保证 ReAct agent 能通过统一 `AgentEnv.call_tool()` 调用。
4. 接入 evaluator，把 tau-bench 的终态评估映射为 `success`、`reward` 和 `error_type`。
5. 新增 `configs/tau_retail_nomem.yaml` 或更新现有配置，使 `max_tasks=1` 的 no-memory smoke 可生成完整 `tasks.jsonl`、`runs.jsonl`、`trace_events.jsonl` 和 `metrics.json`。
6. 外部 tau-bench 依赖或数据不存在时，应给出明确错误信息和安装路径说明；tiny 测试不应依赖 tau-bench 安装。
7. 保持第九轮 tiny 全部配置不回归：特别是 `tiny_nt_memevo_gate_refine_seed1` 的 `memory_refinement_count=1`、`support_replay_harmful_count=2`，以及 unsafe polluted 的 `negative_transfer_rate=1.0`。

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

## tau_retail_nomem_seed1

### 实验名称

`tau_retail_nomem_seed1`

### 日期与环境

2026-05-02，Linux，机器标识 `BNUZ`，交互式 conda 环境 `(rm)`，Python 3.12.13，pytest 9.0.3，pluggy 1.6.0。

### 运行命令

```bash
conda activate rm
python -m pytest
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nomem.yaml
cat runs/tau_retail_nomem_seed1/metrics.json
head -n 3 runs/tau_retail_nomem_seed1/tasks.jsonl
tail -n 3 runs/tau_retail_nomem_seed1/runs.jsonl
grep '"event_type": "tool_call"' runs/tau_retail_nomem_seed1/trace_events.jsonl
```

### 配置文件

`configs/tau_retail_nomem.yaml`

关键参数：`benchmark.name=tau_bench`，`benchmark.domain=retail`，`benchmark.split_file=data/task_splits/tau_retail_smoke_tasks.json`，`benchmark.data_file=data/tau_bench/retail_smoke_db.json`，`benchmark.evaluation=auto`，`max_tasks=3`，`agent.max_steps=4`，`memory_top_k=0`，`models.actor.provider=mock`。

### 输出目录

`runs/tau_retail_nomem_seed1/`

### 结果

`pytest` 结果：

```text
18 passed in 0.10s
```

`tau_retail_nomem_seed1/metrics.json`：

```json
{
  "num_tasks": 3,
  "success_rate": 1.0,
  "avg_reward": 1.0,
  "avg_steps": 2.0,
  "avg_prompt_tokens": 858.0,
  "avg_completion_tokens": 110.66666666666667,
  "avg_tool_calls": 1.0,
  "with_memory_fail_no_memory_success": 0,
  "memory_attributed_failures": 0,
  "negative_transfer_rate": 0.0,
  "harmful_memory_ids": [],
  "negative_transfer_failure_examples": [],
  "memory_policy": "none",
  "memory_size": 0,
  "memory_top_k": 0,
  "gate_decision_count": 0,
  "gate_accepted_count": 0,
  "gate_rejected_count": 0,
  "gate_rejection_reasons": {},
  "utility_update_count": 0,
  "utility_helpful_count": 0,
  "utility_harmful_count": 0,
  "utility_neutral_count": 0,
  "utility_credit_sources": {},
  "online_proxy_utility_update_count": 0,
  "replay_utility_update_count": 0,
  "replay_result_count": 0,
  "replay_leave_one_count": 0,
  "replay_helpful_count": 0,
  "replay_harmful_count": 0,
  "replay_neutral_count": 0,
  "support_replay_count": 0,
  "support_replay_helpful_count": 0,
  "support_replay_harmful_count": 0,
  "support_replay_neutral_count": 0,
  "verification_count": 0,
  "verification_passed_count": 0,
  "verification_failed_count": 0,
  "verification_update_count": 0,
  "support_selection_count": 0,
  "memory_refinement_count": 0,
  "memory_split_count": 0,
  "verification_budget_skipped_count": 0,
  "verification_budget_skip_reasons": {},
  "verification_budget_max_verifications": null,
  "verification_budget_max_support_replay_records": null,
  "verification_budget_verifications_used": 0,
  "verification_budget_support_replay_records_used": 0,
  "replay_record_prompt_tokens": 0,
  "replay_record_completion_tokens": 0,
  "replay_record_tool_calls": 0,
  "replay_unique_execution_count": 0,
  "replay_prompt_tokens": 0,
  "replay_completion_tokens": 0,
  "replay_tool_calls": 0,
  "replay_delta_prompt_tokens": 0,
  "replay_delta_tool_calls": 0,
  "support_replay_record_prompt_tokens": 0,
  "support_replay_record_completion_tokens": 0,
  "support_replay_record_tool_calls": 0,
  "support_replay_unique_execution_count": 0,
  "support_replay_prompt_tokens": 0,
  "support_replay_completion_tokens": 0,
  "support_replay_tool_calls": 0
}
```

`tasks.jsonl` 抽查结果：

1. 三条任务均包含 `metadata.benchmark=tau_bench` 和 `metadata.domain=retail`。
2. 三条任务 intent 分别为 `customer_lookup`、`order_lookup` 和 `product_lookup`。
3. 三条任务均保留 `tool_names`、`expected_actions` 和 `no_memory_success=true`，后续可直接接入 gate / replay / negative-transfer 指标。

`runs.jsonl` 抽查结果：

1. 三条任务均 `success=true`、`reward=1.0`、`num_steps=2`、`tool_calls=1`。
2. 三条任务均 `memory_policy=none`、`used_memory_ids=[]`，符合 no-memory smoke 预期。
3. `tau_retail_smoke_customer_001` 调用 `find_user_id_by_name_zip`，最终回答包含 `user_id=user_1`。
4. `tau_retail_smoke_order_001` 调用 `get_order_details`，最终回答包含 `W2378156` 和 `delivered`。
5. `tau_retail_smoke_product_001` 调用 `get_product_details`，最终回答包含 `1656367028` 和 `Everyday Hoodie`。

`trace_events.jsonl` 抽查结果：

1. 共 3 条 `event_type=tool_call`。
2. tool call 覆盖 `find_user_id_by_name_zip`、`get_order_details` 和 `get_product_details`。
3. 三条 tool call 均 `ok=true`，参数与 smoke task 的 expected action 一致。

### 现象与问题

第十轮 tau-retail no-memory smoke 复验通过。该实验确认最小 `TauBenchEnv` 已能在 Linux + conda `rm` 环境中加载本地 retail smoke task、调用 retail DB wrapper、写出统一日志并汇总 metrics。

当前结果仍是本地 smoke fixture，不代表官方 tau-bench retail 完整 benchmark。三条任务均较简单，mock agent 通过确定性规则选择工具，因此该实验只验证 adapter、日志协议和 evaluator 映射，不用于报告方法效果。

`avg_prompt_tokens=858.0` 明显高于 tiny no-memory 的 `310.4`，主要来自 tau-retail tool description 更长、tool schema 更复杂；后续真实 tau-bench 对照需要单独记录 token 成本。

### 下一步

第十轮 smoke 已通过。第一阶段实验收口还应补两轮：

1. 第十一轮：把 `raw_trace_rag`、`reflexion`、`nt_memevo_candidate` 和 `nt_memevo_gate` 迁移到 tau-retail smoke，小样本验证统一日志和 memory 字段不回归。
2. 第十二轮：接入真实或导出的 tau-bench retail 小样本，至少跑 `max_tasks=1/3` 的 no-memory 与一个 memory baseline，补齐官方 evaluator / action sequence / state diff 的最小适配问题。

## tau_retail_multi_baseline_smoke_seed1

### 实验名称

`tau_retail_multi_baseline_smoke_seed1`

### 日期与环境

2026-05-02，Linux，机器标识 `BNUZ`，交互式 conda 环境 `(rm)`，Python 3.12.13，pytest 9.0.3，pluggy 1.6.0。

### 运行命令

```bash
conda activate rm
python -m pytest

python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_raw_trace_rag.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_reflexion.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nt_memevo_candidate.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nt_memevo_gate.yaml

cat runs/tau_retail_nomem_seed1/metrics.json
cat runs/tau_retail_raw_trace_rag_seed1/metrics.json
cat runs/tau_retail_reflexion_seed1/metrics.json
cat runs/tau_retail_nt_memevo_candidate_seed1/metrics.json
cat runs/tau_retail_nt_memevo_gate_seed1/metrics.json

head -n 3 runs/tau_retail_raw_trace_rag_seed1/memories.jsonl
head -n 3 runs/tau_retail_reflexion_seed1/memories.jsonl
head -n 3 runs/tau_retail_nt_memevo_candidate_seed1/candidate_memories.jsonl
grep '"event_type": "gate_decision"' runs/tau_retail_nt_memevo_gate_seed1/memory_updates.jsonl
tail -n 3 runs/tau_retail_nt_memevo_gate_seed1/runs.jsonl
```

### 配置文件

1. `configs/tau_retail_nomem.yaml`
2. `configs/tau_retail_raw_trace_rag.yaml`
3. `configs/tau_retail_reflexion.yaml`
4. `configs/tau_retail_nt_memevo_candidate.yaml`
5. `configs/tau_retail_nt_memevo_gate.yaml`

共同关键参数：`benchmark.name=tau_bench`，`benchmark.domain=retail`，`benchmark.split_file=data/task_splits/tau_retail_smoke_tasks.json`，`benchmark.data_file=data/tau_bench/retail_smoke_db.json`，`benchmark.evaluation=auto`，`max_tasks=3`，`agent.max_steps=4`，`models.actor.provider=mock`。

baseline 关键参数：

1. `tau_retail_nomem.yaml`：`memory.method` 未设置，`memory_top_k=0`。
2. `tau_retail_raw_trace_rag.yaml`：`memory.method=raw_trace_rag`，`memory.top_k=2`。
3. `tau_retail_reflexion.yaml`：`memory.method=reflexion`，`memory.top_k=2`。
4. `tau_retail_nt_memevo_candidate.yaml`：`memory.method=nt_memevo_candidate`，`memory.top_k=0`。
5. `tau_retail_nt_memevo_gate.yaml`：`memory.method=nt_memevo_gate`，`memory.top_k=2`，`gate.min_precondition=0.25`，`gate.reject_negative_evidence=true`。

### 输出目录

1. `runs/tau_retail_nomem_seed1/`
2. `runs/tau_retail_raw_trace_rag_seed1/`
3. `runs/tau_retail_reflexion_seed1/`
4. `runs/tau_retail_nt_memevo_candidate_seed1/`
5. `runs/tau_retail_nt_memevo_gate_seed1/`

### 结果

`python -m pytest` 结果：

```text
22 passed in 0.09s
```

五组 tau-retail smoke baseline 的关键结果如下：

| config | success_rate | memory_policy | memory_size | memory_top_k | avg_prompt_tokens | gate_decision_count | gate_accepted_count | gate_rejected_count | negative_transfer_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `tau_retail_nomem.yaml` | 1.0 | `none` | 0 | 0 | 858.0 | 0 | 0 | 0 | 0.0 |
| `tau_retail_raw_trace_rag.yaml` | 1.0 | `raw_trace_rag` | 3 | 2 | 1117.3333333333333 | 0 | 0 | 0 | 0.0 |
| `tau_retail_reflexion.yaml` | 1.0 | `reflexion` | 3 | 2 | 1381.3333333333333 | 0 | 0 | 0 | 0.0 |
| `tau_retail_nt_memevo_candidate.yaml` | 1.0 | `nt_memevo_candidate` | 3 | 0 | 858.0 | 0 | 0 | 0 | 0.0 |
| `tau_retail_nt_memevo_gate.yaml` | 1.0 | `nt_memevo_gate` | 3 | 2 | 858.0 | 3 | 0 | 3 | 0.0 |

`tau_retail_nt_memevo_gate.yaml` 的拒绝原因：

```json
{"precondition_below_threshold": 3}
```

### 日志抽查

1. `runs/tau_retail_raw_trace_rag_seed1/memory_updates.jsonl` 同时包含 `retrieve` 和 `add` 事件，第三个任务检索到两条历史 raw trace memory。
2. `runs/tau_retail_reflexion_seed1/memories.jsonl` 生成 3 条 `reflection_type=strategy` 的 reflection memory。
3. `runs/tau_retail_nt_memevo_candidate_seed1/candidate_memories.jsonl` 中三条 candidate 的 `scope.intent` 分别为 `customer_lookup`、`order_lookup` 和 `product_lookup`。
4. `runs/tau_retail_nt_memevo_gate_seed1/memory_updates.jsonl` 中 3 条 `gate_decision` 全部为 `reject`，`runs.jsonl` 中三条任务的 `used_memory_ids` 均为空。

### 现象与问题

1. `none < raw_trace_rag < reflexion` 的 prompt token 成本顺序在 tau-retail smoke 上成立，说明真实工具描述和记忆注入成本已经显现。
2. `nt_memevo_candidate` 与 `none` 的 prompt token 成本一致，符合当前候选记忆只写入、不注入的设计。
3. `nt_memevo_gate` 在本次 smoke 中拒绝全部跨 intent memory，说明第十一轮的保守 gate 在 tau-retail smoke 上没有引入误注入。
4. 当前 smoke split 每个 intent 只出现一次，因此 gate 只验证了跨 intent rejection，没有验证同 intent accepted path。

### 下一步

第一阶段的收口方向已经明确收敛到真实或导出的 tau-bench retail 小样本，后续不再继续扩展 smoke fixture。第十二轮应至少跑通 `no-memory + 一个 memory baseline`，并在 `tasks.jsonl`、`runs.jsonl`、`trace_events.jsonl`、`memory` 和 `metrics.json` 中稳定输出；如果真实数据暂不可用，则必须给出 local export schema、DB 文件要求、工具缺口和 blocker，作为第一阶段收口材料。

## tau_retail_real_export_sample_seed1

### 实验名称

`tau_retail_real_export_sample_seed1`

### 日期与环境

2026-05-03，Linux，机器标识 `BNUZ`，交互式 conda 环境 `(rm)`，Python 3.12.13，pytest 9.0.3，pluggy 1.6.0。

本次使用仓库内 versioned export sample：

1. `data/task_splits/tau_retail_export_sample_tasks.py`
2. `data/tau_bench/retail_export_sample/db.json`

### 运行命令

仓库内导出样例复验：

```bash
conda activate rm
pip install -e ".[dev]"
python -m pytest

python -m ntmemevo.experiments.run_stream --config configs/tau_retail_real_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_real_raw_trace_rag.yaml

cat runs/tau_retail_real_nomem_seed1/metrics.json
cat runs/tau_retail_real_raw_trace_rag_seed1/metrics.json
head -n 3 runs/tau_retail_real_nomem_seed1/tasks.jsonl
tail -n 3 runs/tau_retail_real_nomem_seed1/runs.jsonl
grep '"event_type": "tool_call"' runs/tau_retail_real_nomem_seed1/trace_events.jsonl
head -n 3 runs/tau_retail_real_raw_trace_rag_seed1/memories.jsonl
grep '"event_type": "retrieve"' runs/tau_retail_real_raw_trace_rag_seed1/memory_updates.jsonl
```

若替换为真实导出数据，先复制配置并只改路径：

```bash
cp configs/tau_retail_real_nomem.yaml configs/tau_retail_real_nomem_local.yaml
cp configs/tau_retail_real_raw_trace_rag.yaml configs/tau_retail_real_raw_trace_rag_local.yaml
# 手工修改 benchmark.split_file 和 benchmark.data_file / benchmark.data_dir，先保留 max_tasks=1 或 max_tasks=3。
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_real_nomem_local.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_real_raw_trace_rag_local.yaml
```

### 配置文件

1. `configs/tau_retail_real_nomem.yaml`
2. `configs/tau_retail_real_raw_trace_rag.yaml`

关键参数：`benchmark.name=tau_bench`，`benchmark.domain=retail`，`benchmark.split_file=data/task_splits/tau_retail_export_sample_tasks.py`，`benchmark.data_dir=data/tau_bench/retail_export_sample`，`benchmark.require_data=true`，`benchmark.validate_export_schema=true`，`benchmark.max_tasks=3`，`models.actor.provider=mock`。

导出格式说明：`docs/tau_retail_export_schema.md`。

### 输出目录

1. `runs/tau_retail_real_nomem_seed1/`
2. `runs/tau_retail_real_raw_trace_rag_seed1/`

### 结果

`python -m pytest` 结果：

```text
25 passed in 0.08s
```

两组 real/export sample 的关键结果如下：

| config | success_rate | memory_policy | memory_size | memory_top_k | avg_prompt_tokens | negative_transfer_rate |
| --- | --- | --- | --- | --- | --- | --- |
| `tau_retail_real_nomem.yaml` | 1.0 | `none` | 0 | 0 | 851.6666666666666 | 0.0 |
| `tau_retail_real_raw_trace_rag.yaml` | 1.0 | `raw_trace_rag` | 3 | 2 | 1096.3333333333333 | 0.0 |

`tau_retail_real_nomem_seed1/metrics.json` 摘要：

```json
{
  "num_tasks": 3,
  "success_rate": 1.0,
  "avg_reward": 1.0,
  "avg_steps": 2.0,
  "avg_prompt_tokens": 851.6666666666666,
  "avg_completion_tokens": 107.33333333333333,
  "avg_tool_calls": 1.0,
  "memory_policy": "none",
  "memory_size": 0,
  "memory_top_k": 0,
  "negative_transfer_rate": 0.0,
  "gate_decision_count": 0,
  "utility_update_count": 0,
  "replay_result_count": 0,
  "verification_count": 0
}
```

`tau_retail_real_raw_trace_rag_seed1/metrics.json` 摘要：

```json
{
  "num_tasks": 3,
  "success_rate": 1.0,
  "avg_reward": 1.0,
  "avg_steps": 2.0,
  "avg_prompt_tokens": 1096.3333333333333,
  "avg_completion_tokens": 107.33333333333333,
  "avg_tool_calls": 1.0,
  "memory_policy": "raw_trace_rag",
  "memory_size": 3,
  "memory_top_k": 2,
  "negative_transfer_rate": 0.0,
  "gate_decision_count": 0,
  "utility_update_count": 0,
  "replay_result_count": 0,
  "verification_count": 0
}
```

### 日志抽查

1. `runs/tau_retail_real_nomem_seed1/tasks.jsonl` 三条任务均包含 `metadata.benchmark=tau_bench`、`domain=retail`、`intent`、`tool_names`、`expected_actions` 和 `no_memory_success=true`。
2. 三条任务 intent 分别为 `customer_lookup`、`order_lookup` 和 `product_lookup`，与 export sample 设计一致。
3. `runs/tau_retail_real_nomem_seed1/runs.jsonl` 中三条任务均 `success=true`、`reward=1.0`、`num_steps=2`、`tool_calls=1`、`used_memory_ids=[]`。
4. no-memory trace 中三条 `tool_call` 分别为 `find_user_id_by_email`、`get_order_details` 和 `get_product_details`，且 `ok=true`。
5. 第二个任务输入为 `#W2378156`，mock actor 调用参数为 `{"order_id": "W2378156"}`，DB 返回的 observation 保留 `"order_id": "#W2378156"`；这确认第十二轮 order id 兼容逻辑生效。
6. `runs/tau_retail_real_raw_trace_rag_seed1/memories.jsonl` 生成 3 条 raw trace memory：`raw_000001_tau_retail_0001`、`raw_000002_tau_retail_0002`、`raw_000003_tau_retail_0003`。
7. `runs/tau_retail_real_raw_trace_rag_seed1/memory_updates.jsonl` 包含逐轮 `retrieve` 事件：第 1 轮为空检索，第 2 轮检索到第 1 条 raw trace，第 3 轮检索到第 2 条和第 1 条 raw trace。
8. raw-trace-rag 相比 no-memory 的平均 prompt token 从 `851.6666666666666` 增加到 `1096.3333333333333`，增加约 `244.66666666666674` token，约 `28.7%`；这是记忆注入成本，不代表任务收益。

### 现象与问题

1. 第十二轮 real/export sample 的 no-memory 与 raw-trace-rag 均通过，说明第一阶段收口要求中的“真实或导出 tau-bench retail 小样本至少跑通 no-memory 与一个 memory baseline”已经满足。
2. 本次使用的是仓库内 export-format sample，不是官方 tau-bench retail 完整 benchmark；因此成功率只能证明 task/data export 入口、retail tool wrapper、日志协议和 memory baseline 写入/检索链路可用。
3. `raw_trace_rag` 成功生成 3 条 memory，并在第 2/3 个任务检索历史轨迹，说明 memory logs 与 `memory_updates.jsonl` 在 real/export 配置下稳定生成。
4. no-memory 与 raw-trace-rag 成功率均为 1.0，因为 mock actor 不依赖记忆即可完成这三条小样本任务；本实验不证明 raw trace memory 带来收益。
5. 本次没有暴露缺失 tool semantic、evaluator mismatch、state mutation mismatch 或 mock actor 覆盖不足问题。真实 tau-bench retail 数据接入时仍需重新检查这些风险。

### 下一步

第一阶段实验侧已经满足收口条件。第二阶段优先工作：

1. 用真实 tau-bench retail split 替换 export sample，先保持 `max_tasks=1/3`。
2. 对齐官方 tau-bench retail evaluator、state mutation 和 policy violation。
3. 接真实模型 actor，评估当前 mock actor 无法覆盖的复杂任务。
4. 构造 tau-retail support pool，把 tiny 上已经跑通的 gate/replay/verification/refinement 迁移到真实任务。
5. 在真实任务上验证同 intent accepted path、utility update、负迁移检测和 replay/verification budget。

## first_stage_closure_regression_2026_05_03

### 实验名称

`first_stage_closure_regression_2026_05_03`

### 日期与环境

2026-05-03，Linux，机器标识 `BNUZ`，交互式 conda 环境 `(rm)`，Python 3.12.13，pytest 9.0.3，pluggy 1.6.0。

### 运行命令

```bash
python -m pytest

python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_refine.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_unsafe_polluted.yaml

python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_raw_trace_rag.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_reflexion.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nt_memevo_candidate.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nt_memevo_gate.yaml

python -m ntmemevo.experiments.run_stream --config configs/tau_retail_real_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_real_raw_trace_rag.yaml
```

### 结果摘要

`python -m pytest`：

```text
25 passed in 0.08s
```

核心 tiny 回归：

| config | success_rate | memory_policy | key result |
| --- | --- | --- | --- |
| `tiny_nt_memevo_gate_refine.yaml` | 1.0 | `nt_memevo_gate` | `memory_refinement_count=1`，`memory_split_count=1`，`support_replay_helpful_count=2`，`support_replay_harmful_count=2`，`active_memory_count=1`，`quarantined_memory_count=1` |
| `tiny_nt_memevo_gate_unsafe_polluted.yaml` | 0.0 | `nt_memevo_gate` | `negative_transfer_rate=1.0`，`harmful_memory_ids=["polluted_refund_lookup_policy_001"]`，`replay_harmful_count=1`，`quarantined_memory_count=1` |

tau-retail smoke baseline 回归：

| config | success_rate | memory_policy | memory_size | memory_top_k | avg_prompt_tokens | key result |
| --- | --- | --- | --- | --- | --- | --- |
| `tau_retail_nomem.yaml` | 1.0 | `none` | 0 | 0 | 858.0 | no-memory smoke 稳定 |
| `tau_retail_raw_trace_rag.yaml` | 1.0 | `raw_trace_rag` | 3 | 2 | 1117.3333333333333 | raw trace memory 稳定写入/检索 |
| `tau_retail_reflexion.yaml` | 1.0 | `reflexion` | 3 | 2 | 1381.3333333333333 | reflection memory 稳定写入/检索 |
| `tau_retail_nt_memevo_candidate.yaml` | 1.0 | `nt_memevo_candidate` | 3 | 0 | 858.0 | `candidate_memory_count=3` |
| `tau_retail_nt_memevo_gate.yaml` | 1.0 | `nt_memevo_gate` | 3 | 2 | 858.0 | `gate_accepted_count=0`，`gate_rejected_count=3`，`gate_rejection_reasons={"precondition_below_threshold": 3}` |

tau-retail real/export sample 收口：

| config | success_rate | memory_policy | memory_size | memory_top_k | avg_prompt_tokens | key result |
| --- | --- | --- | --- | --- | --- | --- |
| `tau_retail_real_nomem.yaml` | 1.0 | `none` | 0 | 0 | 851.6666666666666 | export sample no-memory 稳定 |
| `tau_retail_real_raw_trace_rag.yaml` | 1.0 | `raw_trace_rag` | 3 | 2 | 1096.3333333333333 | export sample memory baseline 稳定 |

### 收口判断

1. 第一阶段自动化测试通过：`25 passed in 0.08s`。
2. tiny 核心负迁移链路未回归：scope refinement 能产生 split/refined memory，unsafe polluted ablation 能稳定触发 `negative_transfer_rate=1.0`。
3. tau-retail smoke 五 baseline 均通过，日志协议覆盖 `none/raw_trace_rag/reflexion/nt_memevo_candidate/nt_memevo_gate`。
4. tau-retail real/export sample 跑通 no-memory 与 raw-trace-rag，满足第一阶段最后一项收口要求。
5. 第一阶段正式收口；后续不再扩大 smoke fixture，真实 tau-bench retail 复杂语义进入第二阶段。

## second_stage_round1_plan_2026_05_03

### 实验名称

`second_stage_round1_plan_2026_05_03`

### 日期与环境

计划记录日期：2026-05-03。

目标运行环境：Linux，交互式 conda 环境 `(rm)`，Python 3.12。

### 阶段定位

第二阶段第一轮实验不以提升方法成功率为目标，而是验证 tau-bench retail 的真实语义对齐是否可靠。第一阶段已经完成 tiny 负迁移闭环和 tau-retail smoke/real-export 小样本收口；第二阶段第一轮应优先让 no-memory 的失败可以被 evaluator/state/tool 日志解释。

### 第一轮实验前置条件

1. `python -m pytest` 全量通过。
2. 第一阶段关键回归通过：
   - `configs/tiny_nt_memevo_gate_refine.yaml` 保持 `memory_refinement_count=1`、`memory_split_count=1`。
   - `configs/tiny_nt_memevo_gate_unsafe_polluted.yaml` 保持 `negative_transfer_rate=1.0`。
   - `configs/tau_retail_real_nomem.yaml` 与 `configs/tau_retail_real_raw_trace_rag.yaml` 继续通过。
3. 新增或替换的真实 tau-retail task/data export 必须符合 `docs/tau_retail_export_schema.md`，或在本日志中记录 schema 差异。
4. 第一轮若接入真实 tau-bench checkout，需记录仓库 URL、commit、domain、split、任务数量、DB 来源和导出脚本/命令。

### 第一轮建议运行命令

基础回归：

```bash
conda activate rm
pip install -e ".[dev]"
python -m pytest

python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_refine.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_unsafe_polluted.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_real_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_real_raw_trace_rag.yaml
```

第二阶段第一轮新增配置完成后，建议按下面顺序复验：

```bash
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_nomem.yaml
cat runs/tau_retail_phase2_state_nomem_seed1/metrics.json
tail -n 5 runs/tau_retail_phase2_state_nomem_seed1/runs.jsonl
grep '"event_type": "tool_call"' runs/tau_retail_phase2_state_nomem_seed1/trace_events.jsonl
```

若 no-memory 的 evaluator/state 日志稳定，再运行一个 memory baseline：

```bash
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_raw_trace_rag.yaml
cat runs/tau_retail_phase2_state_raw_trace_rag_seed1/metrics.json
head -n 3 runs/tau_retail_phase2_state_raw_trace_rag_seed1/memories.jsonl
grep '"event_type": "retrieve"' runs/tau_retail_phase2_state_raw_trace_rag_seed1/memory_updates.jsonl
```

如果替换为真实 tau-bench retail export，先把 `max_tasks` 固定为 `1`，确认日志可解释后再扩到 `3`。

### 需要记录的新增指标

第二阶段第一轮应在 `metrics.json` 或日志抽查中记录以下字段；字段名可随实现调整，但语义必须可追踪：

| 指标 | 目的 |
| --- | --- |
| `evaluation_modes` | 统计 `answer_contains/action_sequence/state_diff/official_like` 实际使用次数 |
| `state_diff_passed_count` | 统计 state diff 通过任务数 |
| `state_diff_failed_count` | 统计 state diff 失败任务数 |
| `policy_violation_count` | 统计 policy/precondition 违规次数 |
| `expected_actions_matched_count` | 统计 expected action sequence 通过次数 |
| `expected_actions_failed_count` | 统计 action sequence 失败次数 |
| `tool_semantic_error_count` | 统计工具语义或状态更新错误次数 |
| `evaluator_error_types` | 统计 evaluator 输出的错误类型分布 |

仍需保留第一阶段关键指标：

1. `success_rate`
2. `avg_reward`
3. `avg_prompt_tokens`
4. `memory_policy`
5. `memory_size`
6. `negative_transfer_rate`
7. `gate_decision_count`
8. `utility_update_count`
9. `replay_result_count`
10. `verification_count`

### 结果填写模板

第二阶段第一轮完成后，在此处补齐实际结果：

| config | num_tasks | success_rate | evaluation modes | state diff | policy violations | memory_policy | memory_size | key failure |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `tau_retail_phase2_state_nomem.yaml` | 3 | 0.6666666666666666 | `{"official_like": 3}` | `1/1 passed` | 1 | `none` | 0 | pending order return 触发预期 policy violation |
| `tau_retail_phase2_state_raw_trace_rag.yaml` | 3 | 0.6666666666666666 | `{"official_like": 3}` | `1/1 passed` | 1 | `raw_trace_rag` | 3 | 与 no-memory 同一 policy violation，另验证 raw trace 写入/检索 |

### 2026-05-03 用户复验记录（环境待修正）

用户本次在 Linux 机器 `BNUZ` 的 `(base)` 环境下执行复验，命令行显示 Python 版本为 `3.12.7`、pytest 版本为 `7.4.4`、pluggy 版本为 `1.0.0`。该环境不是本轮建议的交互式 conda 环境 `(rm)`。

`python -m pytest` 通过：

```text
29 passed in 0.09s
```

注意：pytest 能在 `(base)` 下通过，是因为 `pyproject.toml` 的 pytest 配置包含 `pythonpath = ["src"]`，测试进程可以直接导入源码树；这不等价于当前 Python 环境已安装 `ntmemevo` 包。

随后用户在 `(base)` 下运行以下实验入口均失败：

```bash
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_refine.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_unsafe_polluted.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_real_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_real_raw_trace_rag.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_raw_trace_rag.yaml
```

共同错误：

```text
ModuleNotFoundError: No module named 'ntmemevo'
```

判断：这是环境/安装问题，不是代码回归。当前 `(base)` Python 没有安装 editable package，也没有设置 `PYTHONPATH=src`。本次 run_stream 六条命令没有真正执行，因此不能把这些命令计为用户侧成功复验。

用户随后抽查了现有 `runs/tau_retail_phase2_state_*` artifacts。这些 artifacts 与编码侧 smoke 结果一致，但由于前面的 run_stream 命令失败，本日志将其记录为“现有日志抽查”，不记录为“本次重新运行生成”。

现有 `tau_retail_phase2_state_nomem_seed1/metrics.json` 抽查结果：

| field | value |
| --- | --- |
| `num_tasks` | 3 |
| `success_rate` | 0.6666666666666666 |
| `evaluation_modes` | `{"official_like": 3}` |
| `state_diff_evaluated_count` | 1 |
| `state_diff_passed_count` | 1 |
| `expected_actions_matched_count` | 3 |
| `policy_violation_count` | 1 |
| `tool_semantic_error_count` | 1 |
| `evaluator_error_types` | `{"policy_violation": 1}` |
| `memory_policy` | `none` |
| `memory_size` | 0 |

`runs.jsonl` 抽查现象：

1. `tau_retail_phase2_read_001` 成功，`evaluation_mode=official_like`，`expected_actions_matched=true`。
2. `tau_retail_phase2_cancel_001` 成功，`state_diff_passed=true`，`state_diff_summary` 记录 `#PEND2001` 从 `pending` 更新为 `cancelled`，并新增 `cancel_reason=customer_request`。
3. `tau_retail_phase2_return_policy_fail_001` 按预期失败，`error_type=policy_violation`，`policy_violation_count=1`，`tool_semantic_error_count=1`，失败 observation 为 pending order 不能调用 delivered-item return。

`trace_events.jsonl` 抽查现象：

1. `get_order_details` 工具调用 `ok=true`。
2. `cancel_pending_order` 工具调用 `ok=true`。
3. `return_delivered_order_items` 工具调用 `ok=false`，对应 policy/precondition failure。

现有 `tau_retail_phase2_state_raw_trace_rag_seed1/metrics.json` 抽查结果：

| field | value |
| --- | --- |
| `num_tasks` | 3 |
| `success_rate` | 0.6666666666666666 |
| `evaluation_modes` | `{"official_like": 3}` |
| `state_diff_passed_count` | 1 |
| `expected_actions_matched_count` | 3 |
| `policy_violation_count` | 1 |
| `tool_semantic_error_count` | 1 |
| `memory_policy` | `raw_trace_rag` |
| `memory_size` | 3 |
| `memory_top_k` | 2 |

`memories.jsonl` 抽查确认生成 3 条 raw trace memory，其中第三条保存了预期的 policy/precondition failure 轨迹。`memory_updates.jsonl` 抽查确认第 1 轮空检索，第 2 轮检索 `raw_000001_tau_retail_phase2_read_001`，第 3 轮检索 `raw_000002_tau_retail_phase2_cancel_001` 和 `raw_000001_tau_retail_phase2_read_001`。

### 当前复验结论（2026-05-03 base 环境，后续已由 rm 环境正式复验补齐）

1. 单元/集成测试通过：`29 passed in 0.09s`。
2. run_stream 命令未通过，原因是 `(base)` 环境未安装 `ntmemevo` 包。
3. 现有 phase-two artifacts 与编码侧 smoke 指标一致，说明日志内容可读且符合预期，但需要在正确环境中重新运行来完成正式用户复验。
4. 下一次复验应先执行 `conda activate rm` 和 `pip install -e ".[dev]"`；若临时使用 `(base)`，必须改用 `PYTHONPATH=src python -m ntmemevo.experiments.run_stream ...`。

### 当时待重新运行命令（后续已完成 rm 环境正式复验）

推荐使用目标环境重新执行：

```bash
conda activate rm
pip install -e ".[dev]"
python -m pytest

python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_refine.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_unsafe_polluted.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_real_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_real_raw_trace_rag.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_raw_trace_rag.yaml
```

如果只想在当前 `(base)` 环境临时复验，不安装包，也可以使用：

```bash
PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_nomem.yaml
PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_raw_trace_rag.yaml
```

日志抽查应至少记录：

1. `tasks.jsonl` 中真实 tau-retail metadata 是否包含 `intent`、`tool_names`、`expected_actions`、可选 `expected_state_diff` 或 evaluator 需要的终态字段。
2. `trace_events.jsonl` 中 mutation tool 是否产生正确 observation，失败工具是否有 `ok=false`。
3. `runs.jsonl` 中失败任务的 `error_type` 是否能区分 answer mismatch、action mismatch、state diff mismatch、policy violation 和 tool semantic error。
4. `metrics.json` 中 evaluator/state/policy 指标是否能解释总 `success_rate`。
5. raw-trace-rag 是否只增加 memory 写入/检索与 token 成本，不改变 evaluator 语义。

### 第一轮实验判断规则

1. 如果 no-memory 在 phase-two state/evaluator 小样本上通过，说明 evaluator/state 对齐路径可以进入真实 export 小批量复验。
2. 如果 no-memory 失败但日志能指出明确原因，第一轮仍可接受；下一步应补 tool/evaluator 语义，而不是调整 memory 方法。
3. 如果失败只能表现为笼统的 `expected_answer_mismatch` 或 `empty_or_unusable_final_answer`，说明第一轮日志还不够，需继续补 evaluator detail。
4. 如果真实 export 的任务字段与 `docs/tau_retail_export_schema.md` 不兼容，应优先更新 schema/loader，并记录真实字段差异。
5. 只有当 no-memory reward 可解释后，第二阶段才应进入真实 actor、`nt_memevo_gate`、replay/verification 或更大任务数。

### 2026-05-03 正式复验补充（rm 环境）

用户随后在 Linux 机器 `BNUZ` 的交互式 conda 环境 `(rm)` 下完成正式复验，环境为 Python 3.12.13、pytest 9.0.3、pluggy 1.6.0。

`python -m pytest` 通过：

```text
31 passed in 0.10s
```

本地 phase-two state/evaluator fixture 复验结果：

1. `tau_retail_phase2_state_nomem_seed1`：`num_tasks=3`、`success_rate=0.6666666666666666`、`avg_prompt_tokens=1011.3333333333334`、`evaluation_modes={"official_like": 3}`、`state_diff_evaluated_count=1`、`state_diff_passed_count=1`、`expected_actions_matched_count=3`、`policy_violation_count=1`、`tool_semantic_error_count=1`、`memory_policy=none`、`memory_size=0`。
2. `tau_retail_phase2_state_raw_trace_rag_seed1`：`num_tasks=3`、`success_rate=0.6666666666666666`、`avg_prompt_tokens=1354.6666666666667`、`evaluation_modes={"official_like": 3}`、`state_diff_passed_count=1`、`expected_actions_matched_count=3`、`policy_violation_count=1`、`tool_semantic_error_count=1`、`memory_policy=raw_trace_rag`、`memory_size=3`、`memory_top_k=2`。
3. no-memory 的 `runs.jsonl` 抽查确认三条任务分别覆盖 order read 成功、pending cancel 成功并通过 state diff、pending order return 按预期触发 `policy_violation`。
4. no-memory 的 `trace_events.jsonl` 抽查确认 `get_order_details` 和 `cancel_pending_order` 为 `ok=true`，`return_delivered_order_items` 对 pending order 为 `ok=false`。
5. raw-trace-rag 与 no-memory 成功率和 evaluator 结论一致，额外验证 3 条 raw trace memory 写入和逐轮 retrieve；该配置 token 成本高于 no-memory，符合 memory 注入预期。

本次正式复验结论：第二阶段第一轮环境问题已修正，`python -m ntmemevo.experiments.run_stream ...` 可以在 `(rm)` 环境直接运行；本地 phase-two state/evaluator fixture 的 action/state/policy 日志链路通过。

## tau_retail_phase2_official_tau2_seed1

### 实验名称

`tau_retail_phase2_official_tau2_seed1`

### 日期与环境

2026-05-03，Linux，机器标识 `BNUZ`，交互式 conda 环境 `(rm)`，Python 3.12.13，pytest 9.0.3，pluggy 1.6.0。

### 官方数据来源

1. `data/external/tau-bench` commit：`59a200c6d575d595120f1cb70fea53cef0632f6b`。
2. `data/external/tau2-bench` commit：`2be691669909439cf88dedc13decf94b7664d262`。
3. 官方 tau2 retail 数据路径：`data/external/tau2-bench/data/tau2/domains/retail/`。
4. retail 数据规模：`tasks=114`、splits 为 `train=74`、`test=40`、`base=114`；DB 规模为 `products=50`、`users=500`、`orders=1000`。

### 运行命令

```bash
conda activate rm
pip install -e ".[dev]"
python -m pytest

# 如果 data/external 下缺少官方仓库，先克隆：
git clone https://github.com/sierra-research/tau-bench.git data/external/tau-bench
git clone https://github.com/sierra-research/tau2-bench.git data/external/tau2-bench

python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_raw_trace_rag.yaml

cat runs/tau_retail_phase2_official_tau2_nomem_seed1/metrics.json
tail -n 3 runs/tau_retail_phase2_official_tau2_nomem_seed1/runs.jsonl
grep '"event_type": "tool_call"' runs/tau_retail_phase2_official_tau2_nomem_seed1/trace_events.jsonl

cat runs/tau_retail_phase2_official_tau2_raw_trace_rag_seed1/metrics.json
head -n 3 runs/tau_retail_phase2_official_tau2_raw_trace_rag_seed1/memories.jsonl
grep '"event_type": "retrieve"' runs/tau_retail_phase2_official_tau2_raw_trace_rag_seed1/memory_updates.jsonl
```

### 配置文件

1. `configs/tau_retail_phase2_official_tau2_nomem.yaml`
2. `configs/tau_retail_phase2_official_tau2_raw_trace_rag.yaml`

关键参数：

1. `benchmark.split_file=data/external/tau2-bench/data/tau2/domains/retail/tasks.json`
2. `benchmark.task_split_file=data/external/tau2-bench/data/tau2/domains/retail/split_tasks.json`
3. `benchmark.task_split=base`
4. `benchmark.data_file=data/external/tau2-bench/data/tau2/domains/retail/db.json`
5. `benchmark.evaluation=official_like`
6. `benchmark.compare_action_args=true`
7. `benchmark.max_tasks=3`
8. no-memory：`agent.max_steps=6`、`agent.memory_top_k=0`
9. raw-trace-rag：`memory.method=raw_trace_rag`、`memory.top_k=2`、`memory.save_failures=true`

### 输出目录

1. `runs/tau_retail_phase2_official_tau2_nomem_seed1/`
2. `runs/tau_retail_phase2_official_tau2_raw_trace_rag_seed1/`

### 结果

`python -m pytest` 结果：

```text
31 passed in 0.10s
```

官方 tau2 no-memory 结果：

```json
{
  "num_tasks": 3,
  "success_rate": 0.0,
  "avg_reward": 0.0,
  "avg_steps": 1.6666666666666667,
  "avg_prompt_tokens": 988.0,
  "avg_completion_tokens": 73.33333333333333,
  "avg_tool_calls": 0.6666666666666666,
  "evaluation_modes": {
    "official_like": 3
  },
  "expected_actions_evaluated_count": 3,
  "expected_actions_matched_count": 0,
  "expected_actions_failed_count": 3,
  "evaluator_error_types": {
    "expected_action_sequence_mismatch": 1,
    "expected_tool_name_mismatch": 2
  },
  "policy_violation_count": 0,
  "tool_semantic_error_count": 0,
  "negative_transfer_rate": 0.0,
  "memory_policy": "none",
  "memory_size": 0,
  "memory_top_k": 0
}
```

官方 tau2 raw-trace-rag 结果：

```json
{
  "num_tasks": 3,
  "success_rate": 0.0,
  "avg_reward": 0.0,
  "avg_steps": 1.6666666666666667,
  "avg_prompt_tokens": 1279.6666666666667,
  "avg_completion_tokens": 73.33333333333333,
  "avg_tool_calls": 0.6666666666666666,
  "evaluation_modes": {
    "official_like": 3
  },
  "expected_actions_evaluated_count": 3,
  "expected_actions_matched_count": 0,
  "expected_actions_failed_count": 3,
  "evaluator_error_types": {
    "expected_action_sequence_mismatch": 1,
    "expected_tool_name_mismatch": 2
  },
  "policy_violation_count": 0,
  "tool_semantic_error_count": 0,
  "negative_transfer_rate": 0.0,
  "memory_policy": "raw_trace_rag",
  "memory_size": 3,
  "memory_top_k": 2
}
```

`runs.jsonl` 抽查结果：

1. 官方 task `0` 和 `1` 当前均被 mock actor 直接调用 `exchange_delivered_order_items({"order_id": "W2378156", "item_ids": [], "new_item_ids": []})`，但 expected action sequence 需要先调用 `find_user_id_by_name_zip`、`get_order_details`、`get_product_details` 等 5 步，因此失败类型为 `expected_tool_name_mismatch`。
2. 官方 task `2` 当前 mock actor 未发起工具调用，expected action sequence 长度为 11，失败类型为 `expected_action_sequence_mismatch`。
3. 三条失败均没有 `policy_violation` 或 `tool_semantic_error`，说明当前失败主因是 actor/action-sequence 覆盖不足，而不是工具 precondition 或 evaluator 崩溃。

`trace_events.jsonl` 抽查结果：

1. no-memory 只记录 2 条 tool call，分别来自 task `0` 和 `1`。
2. 两条 tool call 均为 `exchange_delivered_order_items`，observation 为 `Order W2378156 exchange requested for item_ids=[]; product_ids=[].`。
3. task `2` 没有 tool call，最终回答为 `Unable to determine the answer from the available tools.`。

`memories.jsonl` 与 `memory_updates.jsonl` 抽查结果：

1. raw-trace-rag 写入 3 条 memory，均为失败轨迹，`memory_id` 分别为 `raw_000001_0`、`raw_000002_1`、`raw_000003_2`。
2. 第 1 轮 retrieve 为空；第 2 轮检索 `raw_000001_0`，score 为 `0.8618575020903775`；第 3 轮检索 `raw_000002_1` 和 `raw_000001_0`，scores 为 `0.5100626769586553` 和 `0.4962962962962962`。
3. raw trace 注入只增加 prompt tokens：no-memory `avg_prompt_tokens=988.0`，raw-trace-rag `avg_prompt_tokens=1279.6666666666667`；成功率仍为 `0.0`，符合“本轮只验证官方 task/DB loader、action mismatch 分类和 memory 日志”的目标。

### 现象与问题

官方 tau2 小批量实验已能稳定生成 `tasks.jsonl`、`runs.jsonl`、`trace_events.jsonl`、`memories.jsonl`、`memory_updates.jsonl` 和 `metrics.json`。当前 `success_rate=0.0` 是预期现象：mock actor 只覆盖本地 phase-two fixture 的简单 tool-use 模式，不具备完成官方 tau2 exchange/return 多步任务的能力。

本轮最重要的结论是失败已经可解释：

1. 失败主因是 expected action sequence 与当前 mock actor 行为不匹配，而不是日志缺失。
2. 前 3 条官方 base 任务需要 5/5/11 步 expected actions，当前 mock actor 只做 0-1 步。
3. `expected_actions_failed_count=3`、`expected_actions_matched_count=0` 是当前 actor 能力边界，不应解释为 memory 方法失败。
4. `negative_transfer_rate=0.0` 是正确口径：官方任务缺少 no-memory 反事实成功证据时，不把 raw-trace-rag 的失败归因成 memory 负迁移。
5. raw-trace-rag 已证明官方任务上的 memory 写入、失败轨迹保存和逐轮检索链路可用，但当前失败 memory 不应用于声称收益。

### 下一步

下一轮应把第二阶段第三轮收窄为“官方 tau2 action/evaluator 对齐层”的建设，而不是直接比较 memory 方法收益：

1. 优先接入 action-replay oracle 或 scripted expected-action actor，使官方前 3 条任务能按 `evaluation_criteria.actions` 逐步执行，用于验证工具语义、DB mutation 和 evaluator，而不被 mock actor 能力阻塞。
2. 基于 task `0`/`1` 的 exchange 流程补 `find_user_id_by_name_zip`、`get_order_details`、`get_product_details`、`exchange_delivered_order_items` 的官方参数和返回结构语义，尤其是 `item_ids`、`new_item_ids`、product variant 和 replacement 选择。
3. 基于 task `2` 的 return/count 场景补多订单读取、商品查询、return tool state update 和 `communicate_info` / `nl_assertions` 映射。
4. 将 evaluator 从单纯 action sequence 对齐推进到 action + DB state + natural-language assertion 的组合 detail，继续保持 failure reason 可分类。
5. 等 oracle/scripted actor 能让至少 1-3 条官方任务通过或产生可解释 state mismatch 后，再接真实 LLM actor；`nt_memevo_gate`、support verification 和 scope refinement 暂不作为第三轮主验收。

## tau_retail_phase2_official_tau2_action_replay_seed1

### 实验名称

`tau_retail_phase2_official_tau2_action_replay_seed1`

### 日期与环境

待实验执行者填写。目标环境：Linux，`conda activate rm`，Python 3.12。

### 官方数据来源

沿用第二阶段第二轮官方 tau2 数据：

1. `data/external/tau-bench`
2. `data/external/tau2-bench`
3. 官方 tau2 retail 数据路径：`data/external/tau2-bench/data/tau2/domains/retail/`

复验时请记录两个官方仓库的 commit hash：

```bash
git -C data/external/tau-bench rev-parse HEAD
git -C data/external/tau2-bench rev-parse HEAD
```

### 运行命令

```bash
conda activate rm
pip install -e ".[dev]"
python -m pytest

# 如果 data/external 下缺少官方仓库，先克隆：
git clone https://github.com/sierra-research/tau-bench.git data/external/tau-bench
git clone https://github.com/sierra-research/tau2-bench.git data/external/tau2-bench

python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_raw_trace_rag.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_raw_trace_rag.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_action_replay.yaml

cat runs/tau_retail_phase2_official_tau2_action_replay_seed1/metrics.json
tail -n 3 runs/tau_retail_phase2_official_tau2_action_replay_seed1/runs.jsonl
grep '6086499569' runs/tau_retail_phase2_official_tau2_action_replay_seed1/trace_events.jsonl
grep '"event_type": "scripted_action"' runs/tau_retail_phase2_official_tau2_action_replay_seed1/trace_events.jsonl
```

### 配置文件

`configs/tau_retail_phase2_official_tau2_action_replay.yaml`

关键参数：

1. `benchmark.split_file=data/external/tau2-bench/data/tau2/domains/retail/tasks.json`
2. `benchmark.task_split_file=data/external/tau2-bench/data/tau2/domains/retail/split_tasks.json`
3. `benchmark.task_split=base`
4. `benchmark.max_tasks=3`
5. `benchmark.evaluation=official_like`
6. `benchmark.compare_action_args=true`
7. `agent.type=action_replay_agent`
8. `agent.max_steps=16`
9. `models.actor.provider=action_replay`

### 输出目录

`runs/tau_retail_phase2_official_tau2_action_replay_seed1/`

### 待记录结果

实验执行者完成后填写：

```json
{
  "num_tasks": null,
  "success_rate": null,
  "avg_tool_calls": null,
  "expected_actions_matched_count": null,
  "expected_actions_failed_count": null,
  "communicate_info_passed_count": null,
  "nl_assertion_passed_count": null,
  "tool_semantic_error_count": null,
  "unsupported_official_criteria_count": null,
  "evaluator_error_types": null
}
```

### 抽查重点

1. `runs.jsonl.agent` 应为 `action_replay_agent`。
2. task `0` 与 task `1` 应完整执行 5 步 expected actions。
3. task `2` 应完整执行 11 步 expected actions。
4. `expected_actions_matched_count` 应显示 action replay 是否消除了第二阶段第二轮的 actor mismatch。
5. 若 task `2` 仍失败，记录 `evaluation_details.tool_semantic_errors` 是否指向 `get_product_details(product_id=6086499569)`。
6. `communicate_info_passed_count` 与 `nl_assertion_passed_count` 应说明 task `2` 的自然语言要求是否被 action replay final answer 表达。

### 现象与问题

待实验执行者填写。建议重点区分：

1. actor mismatch 是否已消除。
2. 剩余失败是否来自 official DB/tool semantic gap。
3. 是否出现 unsupported official criterion。
4. 该结果只用于 adapter/evaluator 对齐，不用于报告 NT-MemEvo 方法收益。
