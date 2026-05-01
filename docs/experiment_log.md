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

## 当前下一轮方向

第一阶段第八轮建议优先实现 `support-set replay + verification-gated consolidation`。第七轮已经跑通单任务 leave-one-memory-out 归因：safe replay 中 seed memory 的 `delta_reward=1.0` 并进入 `active`，unsafe polluted replay 中污染记忆的 `delta_reward=-1.0` 并进入 `quarantined`。下一轮应把这种“当前任务局部反事实”升级为“相似支持任务集合验证”，并把 candidate consolidation 从主循环即时阈值迁移到独立验证队列。

第八轮建议范围：

1. 新增 support task selector：根据 `scope.intent`、domain、preconditions、tool names 和 lexical similarity 从 tiny support pool 中选择相似任务。
2. 新增 `MemoryVerifier` 或 consolidation runner：对 candidate memory 在 support task set 上运行 `with memory` / `without memory` replay。
3. 新增 support task fixtures，至少覆盖 `order_status`、`refund_eligibility` 和 `exchange_eligibility`，避免第七轮只验证 order-status 单一路径。
4. 将 `candidate -> active` 从主循环即时更新迁移为 verification-gated consolidation，记录 `verification_passed`、`support_delta_mean`、`support_negative_transfer_rate` 和 `support_lcb_delta_reward`。
5. 扩展 `replay_results.jsonl`，区分 `source_task_replay` 与 `support_task_replay`。
6. 增加 replay cost metrics：`replay_prompt_tokens`、`replay_completion_tokens`、`replay_tool_calls`、`delta_prompt_tokens`、`delta_tool_calls` 和 cost-adjusted delta。
7. 新增 metrics：`verification_count`、`verification_passed_count`、`verification_failed_count`、`support_replay_count`、`support_replay_helpful_count` 和 `support_replay_harmful_count`。
8. 保持第七轮所有配置不回归：`repeated` 继续覆盖 online proxy fallback，`replay` 覆盖 helpful attribution，`polluted` 覆盖 safe rejection，`unsafe_polluted` 覆盖 harmful attribution 和 quarantine。
9. consolidation 日志稳定后再迁移 tau-bench retail。

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
