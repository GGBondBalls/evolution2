# 编码日志

## 2026-04-28 第一阶段第一轮

目标：落实路线图 Week 1 的最小项目骨架，保证后续智能体可以从统一入口继续扩展 baseline 和记忆模块。

已完成：

1. 创建 Python 包 `ntmemevo` 和 `pyproject.toml`。
2. 创建离线 tiny tool-use benchmark，支持无 API key 烟测。
3. 实现 `LLMClient` 抽象、`MockLLMClient` 和可选 `OpenAIChatClient`。
4. 实现 `TinyToolsEnv`、`TauBenchEnv` 占位适配器。
5. 实现 ReAct-style tool agent。
6. 实现 `RunLogger` 和 `TraceLogger`，输出 `tasks.jsonl`、`runs.jsonl`、`trace_events.jsonl`、`metrics.json` 以及记忆相关占位日志。
7. 实现实验入口 `python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml`。
8. 添加基础 pipeline 测试。

验证记录：

1. `conda run -n rm python -m pip install -e ".[dev]"` 成功。
2. `conda run -n rm python -m pytest` 通过，结果为 `1 passed`。
3. `conda run -n rm python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml` 成功。
4. 离线 tiny benchmark 结果：`num_tasks=5`，`success_rate=1.0`，`avg_reward=1.0`。
5. 已生成运行日志目录 `runs/tiny_nomem_seed1/`，包含 `config.yaml`、`tasks.jsonl`、`runs.jsonl`、`trace_events.jsonl`、`metrics.json` 和记忆相关占位日志。

当前边界：

1. 本轮不实现长期记忆、Raw Trace RAG、Reflexion 或 NT-MemEvo。
2. `TauBenchEnv` 只保留接口占位，下一轮接入官方 tau-bench 或先实现 Raw Trace RAG。
3. `MockLLMClient` 只覆盖 tiny benchmark 的确定性工具调用，用于验证实验骨架。

下一步建议：

1. 实现 Raw Trace RAG baseline。
2. 为 tiny benchmark 加入故意错误/污染轨迹，用于早期验证负迁移指标。
3. 接入 tau-bench 的 task loader、tool APIs 和 evaluator。

## 2026-04-29 第一阶段第二轮

目标：落实路线图 Week 2 的 Raw Trace RAG baseline，建立 `no-memory vs raw-trace-rag` 的可运行对照链路。

已完成：

1. 新增 `RawTraceMemory` 和 `RawTraceMemoryStore`，将每个任务的压缩工具轨迹写入 `memories.jsonl`。
2. 新增 `LexicalRawTraceRetriever`，使用词法 cosine similarity 检索历史轨迹。
3. 修改 `ReActToolAgent`，支持接收 `RetrievedMemory` 并在 prompt 中注入检索到的原始轨迹摘要。
4. 修改 `AgentResult`，增加 `trace_summary` 和 `used_memory_ids`，支撑后续记忆分析。
5. 修改 `run_stream`，在每个任务前检索记忆、任务后写入新记忆，并记录 `memory_updates.jsonl`。
6. 修改 `RunLogger.prepare`，默认重新初始化输出日志，避免重复运行同一配置时追加旧结果。
7. 新增配置 `configs/tiny_raw_trace_rag.yaml`。
8. 新增 Raw Trace RAG pipeline 测试，测试数从 1 个增加到 2 个。
9. 修正 `MockLLMClient` 的关键词匹配范围：只根据当前 `Instruction` 选择工具，避免被检索到的旧轨迹误导。

验证记录：

1. `conda run -n rm python -m pytest` 通过，结果为 `2 passed`。
2. `conda run -n rm python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml` 成功。
3. `conda run -n rm python -m ntmemevo.experiments.run_stream --config configs/tiny_raw_trace_rag.yaml` 成功。
4. no-memory 结果保持：`num_tasks=5`，`success_rate=1.0`，`avg_prompt_tokens=310.4`。
5. raw-trace-rag 结果：`num_tasks=5`，`success_rate=1.0`，`avg_prompt_tokens=530.6`，`memory_size=5`，`memory_top_k=2`。

用户复验记录：

1. 用户在交互式 conda 环境 `(rm)` 下运行 `python -m pytest`，结果为 `2 passed in 0.13s`。
2. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml`，指标与日志记录一致。
3. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_raw_trace_rag.yaml`，指标与日志记录一致。

当前边界：

1. Raw Trace RAG 目前使用词法检索，不使用 embedding；这是 baseline，不是最终方法。
2. tiny benchmark 当前所有任务都可由 no-memory mock agent 解决，因此第二轮只验证链路，不声称记忆带来收益。
3. 检索分数会受通用词影响，后续接真实 benchmark 或加入 BM25/embedding 后再优化。

下一步建议：

1. 实现 Reflexion baseline，形成 `none / raw_trace_rag / reflexion` 三组对照。
2. 在 tiny benchmark 中加入困难任务或污染记忆实验，用于早期验证 negative transfer 指标。
3. 开始接入 tau-bench retail，优先实现 task loader、tool API wrapper 和 evaluator。

## 第一阶段第三轮方向

优先方向：实现 Reflexion baseline。理由是它是后续论文中最基础、最必要的记忆型 baseline，应先在当前 tiny benchmark 与 Raw Trace RAG 共用同一套日志、配置、运行入口和指标体系。

第三轮建议范围：

1. 新增 `ReflectionMemoryStore`，保存自然语言 reflection 和记忆元信息。
2. 新增 `ReflectionExtractor`，从任务 instruction、trace summary、final answer、reward 和 error type 中生成结构化反思。
3. 支持 `memory.method=reflexion`，在 `run_stream` 中复用当前“任务前检索、任务后写入”的在线协议。
4. 新增 `configs/tiny_reflexion.yaml`，输出到 `runs/tiny_reflexion_seed1/`。
5. 新增测试，要求 `none / raw_trace_rag / reflexion` 三条 tiny pipeline 均可稳定运行。
6. 记录 Reflexion 的 token 成本、memory size、used_memory_ids，为后续负迁移实验保留统一字段。

并行准备方向：tau-bench retail 接入。第三轮不建议同时完整实现 tau-bench，除非 Reflexion baseline 已稳定；可先阅读 tau-bench API，确认 task loader、tool wrapper 和 evaluator 的最小适配接口。

## 2026-04-29 第一阶段第三轮

目标：落实路线图 Week 3 的 Reflexion baseline，形成 `none / raw_trace_rag / reflexion` 三组统一入口、统一日志、统一指标的 tiny benchmark 对照链路。

已完成：

1. 新增 `ReflectionMemory`、`ReflectionExtractor` 和 `ReflectionMemoryStore`，将任务后的自然语言反思写入 `memories.jsonl`。
2. 将词法检索抽象为 `LexicalMemoryRetriever`，支持 raw trace memory 与 reflection memory 共用同一套检索协议。
3. 修改 `run_stream`，支持 `memory.method=reflexion`，复用“任务前检索、任务后写入”的在线记忆流程。
4. 修改 `ReActToolAgent` 的记忆注入文本，统一展示不同 memory kind 和 reflection type。
5. 新增配置 `configs/tiny_reflexion.yaml`，输出目录为 `runs/tiny_reflexion_seed1/`。
6. 新增 Reflexion pipeline 测试，当前测试覆盖 `none / raw_trace_rag / reflexion` 三条 tiny pipeline。
7. 更新 `README.md`，加入 Reflexion baseline 运行命令和下一阶段方向。

验证记录：

1. `conda run -n rm python -m pytest` 通过，结果为 `3 passed in 0.18s`。
2. `conda run -n rm python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml` 成功。
3. `conda run -n rm python -m ntmemevo.experiments.run_stream --config configs/tiny_raw_trace_rag.yaml` 成功。
4. `conda run -n rm python -m ntmemevo.experiments.run_stream --config configs/tiny_reflexion.yaml` 成功。
5. no-memory 结果：`num_tasks=5`，`success_rate=1.0`，`avg_prompt_tokens=310.4`，`memory_size=0`，`memory_top_k=0`。
6. raw-trace-rag 结果：`num_tasks=5`，`success_rate=1.0`，`avg_prompt_tokens=538.6`，`memory_size=5`，`memory_top_k=2`。
7. reflexion 结果：`num_tasks=5`，`success_rate=1.0`，`avg_prompt_tokens=832.2`，`memory_size=5`，`memory_top_k=2`。
8. `runs/tiny_reflexion_seed1/memories.jsonl` 已生成 5 条 reflection memory；`runs.jsonl` 中包含 `memory_policy=reflexion`、`used_memory_ids` 和 `trace_summary`。

用户复验记录：

1. 用户在交互式 conda 环境 `(rm2)` 下运行 `python -m pytest`，结果为 `3 passed in 0.14s`。
2. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml`，结果为 `success_rate=1.0`、`avg_prompt_tokens=310.4`、`memory_policy=none`、`memory_size=0`。
3. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_raw_trace_rag.yaml`，结果为 `success_rate=1.0`、`avg_prompt_tokens=538.6`、`memory_policy=raw_trace_rag`、`memory_size=5`。
4. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_reflexion.yaml`，结果为 `success_rate=1.0`、`avg_prompt_tokens=832.2`、`memory_policy=reflexion`、`memory_size=5`。
5. 用户检查 `runs/tiny_reflexion_seed1/metrics.json`、`memories.jsonl` 和 `runs.jsonl`，确认 reflection memory、`used_memory_ids` 和 `trace_summary` 字段符合第三轮验收标准。

当前边界：

1. Reflexion 当前使用确定性规则抽取自然语言反思，尚未接入独立 LLM extractor；这是离线 baseline 的最小稳定版本。
2. tiny benchmark 仍然过简单，三组 baseline 成功率均为 1.0；本轮只能验证接口、日志和成本差异，不能声称 Reflexion 带来任务收益。
3. Reflexion 的 prompt token 成本明显高于 Raw Trace RAG，后续需要在真实任务、top-k 和记忆压缩策略中继续评估。
4. 本轮未实现 tau-bench retail 接入、结构化 NT-MemEvo schema、utility update、verification gate 或 negative transfer 检测。

用户复验建议命令：

```powershell
conda activate rm
pip install -e ".[dev]"
python -m pytest
python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_raw_trace_rag.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_reflexion.yaml
Get-Content .\runs\tiny_reflexion_seed1\metrics.json
Get-Content .\runs\tiny_reflexion_seed1\memories.jsonl -TotalCount 2
Get-Content .\runs\tiny_reflexion_seed1\runs.jsonl -Tail 2
```

下一步建议：

1. 为 tiny benchmark 构造困难任务和污染记忆任务，开始验证 negative transfer 指标链路。
2. 实现结构化 NT-MemEvo candidate memory schema，包含 scope、positive/negative evidence、utility 和 lifecycle 字段。
3. 接入 tau-bench retail 的 task loader、tool API wrapper 和 evaluator，使三组 baseline 能在真实工具任务上对照。

## 第一阶段第四轮方向

优先方向：实现结构化 NT-MemEvo candidate memory schema。理由是 `none / raw_trace_rag / reflexion` 三组基础 baseline 已经跑通，下一步应从“普通记忆 baseline”进入项目核心方法，先把可验证、可度量、可回滚的记忆单元落成稳定数据结构。

第四轮建议范围：

1. 新增 `memory/schema.py`，定义结构化记忆单元字段：`memory_id`、`type`、`claim`、`scope`、`action_hint`、`avoid_hint`、`positive_evidence`、`negative_evidence`、`utility`、`lifecycle` 和 `source`。
2. 新增 `memory/store.py`，支持 candidate memory 的 JSONL 持久化、读取、追加和基础 schema 校验。
3. 新增 `memory/extractor.py`，先用确定性规则从 tiny trace 中生成 candidate memory，保留后续替换为 LLM extractor 的接口。
4. 支持新配置 `memory.method=nt_memevo_candidate` 或等价实验配置，先只写入 candidate pool，不做 verification gate 和 utility learning。
5. 新增 tiny 级别测试，验证 candidate memory JSON schema、日志字段和现有三组 baseline 不回归。
6. 若时间允许，开始准备污染记忆 fixture，为第五轮 RetrieverGate 和 negative transfer 指标做铺垫。

第四轮暂不建议完整接入 tau-bench；tau-bench 可并行调研，但主编码应先稳定结构化 memory schema，否则真实 benchmark 上的日志和分析字段会反复返工。

## 2026-04-30 第一阶段第四轮

目标：落实结构化 NT-MemEvo candidate memory schema，把项目核心方法的候选记忆单元先落成可校验、可持久化、可供后续 gate / utility / verification 复用的数据结构。

已完成：

1. 新增 `src/ntmemevo/memory/schema.py`，定义 `CandidateMemory`、`MemoryScope`、`MemoryUtility`、`MemoryLifecycle`、`MemorySource`，覆盖 `memory_id`、`type`、`claim`、`scope`、`action_hint`、`avoid_hint`、`positive_evidence`、`negative_evidence`、`utility`、`lifecycle` 和 `source` 字段。
2. 新增 `candidate_memory_json_schema()` 和 `validate_candidate_memory_json()`，对必填字段、memory type、lifecycle status、证据列表、utility 默认计数和 source 元信息做基础校验。
3. 新增 `src/ntmemevo/memory/extractor.py`，实现确定性 `CandidateMemoryExtractor`，从 tiny task instruction、trace summary、final answer、reward 和 success 中抽取 candidate memory。
4. 新增 `src/ntmemevo/memory/store.py`，实现 `CandidateMemoryStore`，支持 `candidate_memories.jsonl` 的读取、追加和写入前校验。
5. 修改 `run_stream`，支持 `memory.method=nt_memevo_candidate`；本轮只写入 candidate pool，不进行检索注入、verification gate、utility learning 或 quarantine。
6. 修改 `RunLogger.prepare`，标准输出目录新增初始化 `candidate_memories.jsonl`。
7. 新增配置 `configs/tiny_nt_memevo_candidate.yaml`，输出目录为 `runs/tiny_nt_memevo_candidate_seed1/`。
8. 新增测试：candidate schema 往返校验、默认 utility/lifecycle/source 校验，以及 `nt_memevo_candidate` tiny pipeline 写入结构化 candidate memory。
9. 更新 `README.md`，加入结构化 candidate memory 的运行命令和后续里程碑方向。

验证记录：

1. `conda run -n rm python -m pytest` 通过，结果为 `5 passed in 0.03s`。
2. `conda run -n rm python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml` 成功。
3. `conda run -n rm python -m ntmemevo.experiments.run_stream --config configs/tiny_raw_trace_rag.yaml` 成功。
4. `conda run -n rm python -m ntmemevo.experiments.run_stream --config configs/tiny_reflexion.yaml` 成功。
5. `conda run -n rm python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_candidate.yaml` 成功。
6. no-memory 结果：`num_tasks=5`，`success_rate=1.0`，`avg_prompt_tokens=310.4`，`memory_size=0`，`memory_top_k=0`。
7. raw-trace-rag 结果：`num_tasks=5`，`success_rate=1.0`，`avg_prompt_tokens=538.6`，`memory_size=5`，`memory_top_k=2`。
8. reflexion 结果：`num_tasks=5`，`success_rate=1.0`，`avg_prompt_tokens=832.2`，`memory_size=5`，`memory_top_k=2`。
9. nt-memevo-candidate 结果：`num_tasks=5`，`success_rate=1.0`，`avg_prompt_tokens=310.4`，`memory_size=5`，`memory_top_k=0`。
10. `runs/tiny_nt_memevo_candidate_seed1/candidate_memories.jsonl` 已生成 5 条结构化 candidate memory；`memory_updates.jsonl` 中记录 5 条 `candidate_extract` 事件。

用户复验记录：

1. 用户在 Linux 机器 `BNUZ`、交互式 conda 环境 `(rm)` 下运行 `python -m pytest`，结果为 `5 passed in 0.03s`。
2. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml`，结果为 `success_rate=1.0`、`avg_prompt_tokens=310.4`、`memory_policy=none`、`memory_size=0`、`memory_top_k=0`。
3. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_raw_trace_rag.yaml`，结果为 `success_rate=1.0`、`avg_prompt_tokens=538.6`、`memory_policy=raw_trace_rag`、`memory_size=5`、`memory_top_k=2`。
4. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_reflexion.yaml`，结果为 `success_rate=1.0`、`avg_prompt_tokens=832.2`、`memory_policy=reflexion`、`memory_size=5`、`memory_top_k=2`。
5. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_candidate.yaml`，结果为 `success_rate=1.0`、`avg_prompt_tokens=310.4`、`memory_policy=nt_memevo_candidate`、`memory_size=5`、`memory_top_k=0`。
6. 用户检查 `runs/tiny_nt_memevo_candidate_seed1/runs.jsonl`，确认后两条任务 `used_memory_ids=[]`，说明 candidate memory 本轮未注入 prompt。
7. 用户检查 `runs/tiny_nt_memevo_candidate_seed1/memory_updates.jsonl`，确认 5 条 `candidate_extract` 事件全部写入，candidate 类型覆盖 `tool_usage`、`constraint` 和 `user_policy`。
8. 用户检查 `runs/tiny_nt_memevo_candidate_seed1/candidate_memories.jsonl`，确认结构化字段完整，`utility`、`lifecycle`、`source`、`positive_evidence` 和 `negative_evidence` 符合第四轮设计。

当前边界：

1. `nt_memevo_candidate` 当前只抽取并写入 candidate pool，不把 candidate memory 注入 agent prompt，因此 prompt token 成本与 no-memory 一致。
2. utility 字段当前只写入默认先验值：`alpha=1.0`、`beta=1.0`、`mean_delta_reward=0.0`、`lcb_delta_reward=0.0`、`num_used=0`、`num_helpful=0`、`num_harmful=0`。
3. lifecycle 当前固定为 `status=candidate`，尚未实现 active/quarantined/retired 状态迁移。
4. extractor 使用确定性规则，适合离线 tiny benchmark 验证 schema 和日志；后续可替换为 LLM extractor。
5. 本轮仍未实现 RetrieverGate、negative transfer 检测、反事实 replay、verification gate 或 tau-bench retail 接入。

用户复验建议命令：

```powershell
conda activate rm
pip install -e ".[dev]"
python -m pytest
python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_raw_trace_rag.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_reflexion.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_candidate.yaml
Get-Content .\runs\tiny_nt_memevo_candidate_seed1\metrics.json
Get-Content .\runs\tiny_nt_memevo_candidate_seed1\candidate_memories.jsonl -TotalCount 2
Get-Content .\runs\tiny_nt_memevo_candidate_seed1\memory_updates.jsonl -Tail 5
```

下一步建议：

1. 实现 `RetrieverGate`，基于 similarity、precondition match、utility、risk、age 和 cost 对 candidate / active memory 打分。
2. 新增 active memory 或 gated candidate retrieval 的最小路径，使结构化 memory 可以被转换为 `RetrievedMemory` 并注入 prompt，但必须记录 gate 决策。
3. 为 tiny benchmark 增加污染记忆 fixture，使 negative transfer 可以在离线环境中被稳定触发和度量。
4. 在 `memory_updates.jsonl` 中记录每条候选记忆的 `similarity_score`、`precondition_score`、`utility_score`、`risk_score`、`final_gate_score`、`gate_decision` 和 `rejection_reason`。
5. 新增 negative transfer 指标占位：`with_memory_fail_no_memory_success`、`harmful_memory_ids`、`memory_attributed_failures` 和 `negative_transfer_rate`。
6. 新增一组污染实验配置，例如 `configs/tiny_nt_memevo_gate_polluted.yaml`，同时保持 `none / raw_trace_rag / reflexion / nt_memevo_candidate` 四组配置不回归。
7. 在 tiny gate 与污染日志稳定后，再接入 tau-bench retail，避免真实 benchmark 接入后反复返工 schema。

## 2026-04-30 第一阶段第五轮

目标：落实 RetrieverGate 的最小可运行版本，把第四轮结构化 candidate memory 从“只写入”推进到“可门控检索、可注入、可记录拒绝原因、可触发负迁移指标”的闭环。

已完成：

1. 新增 `src/ntmemevo/memory/gate.py`，实现 `RetrieverGateConfig`、`GateDecision` 和 `RetrieverGate`。
2. Gate 线性打分覆盖 `similarity_score`、`precondition_score`、`utility_score`、`risk_score`、`age_penalty`、`cost_penalty` 和 `final_gate_score`。
3. Gate 拒绝规则覆盖 lifecycle status、negative evidence、risk threshold、similarity threshold、precondition threshold、final score threshold 和 top-k pruning。
4. 修改 `run_stream`，支持 `memory.method=nt_memevo_gate`，将被 gate 接受的 `CandidateMemory` 转换为 `RetrievedMemory` 并注入 agent prompt。
5. `memory_updates.jsonl` 新增逐条 `gate_decision` 事件，并保留汇总 `retrieve` 事件。
6. `metrics.json` 新增 `with_memory_fail_no_memory_success`、`memory_attributed_failures`、`negative_transfer_rate`、`harmful_memory_ids`、`negative_transfer_failure_examples`、`gate_decision_count`、`gate_accepted_count`、`gate_rejected_count` 和 `gate_rejection_reasons`。
7. `CandidateMemoryStore` 新增 `import_jsonl()`，支持从 fixture/bootstrap file 导入候选记忆，并写入本轮输出目录的 `candidate_memories.jsonl`。
8. `MockLLMClient` 新增可选参数 `follow_memory_hints`，仅在配置显式打开时会从 retrieved memory 中读取工具调用提示，用于离线稳定触发污染记忆负迁移；默认行为不变。
9. 新增污染候选记忆 fixture：`data/memory_fixtures/tiny_polluted_candidates.jsonl`。
10. 新增单任务负迁移 split：`data/task_splits/tiny_refund_only_tasks.json`，用于 unsafe polluted ablation。
11. 新增配置 `configs/tiny_nt_memevo_gate.yaml`、`configs/tiny_nt_memevo_gate_polluted.yaml` 和 `configs/tiny_nt_memevo_gate_unsafe_polluted.yaml`。
12. 新增测试：RetrieverGate 接受/拒绝单元测试、正常 gated retrieval pipeline、污染 bootstrap 被拒绝 pipeline、unsafe polluted gate 触发 negative transfer 指标。
13. 更新 `README.md`，加入 gate / polluted / unsafe polluted 运行命令、gate 日志字段和下一里程碑。

关键实现说明：

1. `nt_memevo_gate` 与 `nt_memevo_candidate` 共用结构化 candidate memory schema；区别是前者在每个任务前对已有 candidate pool 做 gate 检索，后者仍只抽取不注入。
2. 当前 gate 使用确定性规则和线性打分，不依赖 embedding 或 LLM verifier，适合离线 tiny benchmark 和日志链路验证。
3. Intent precondition 匹配采用严格策略：已识别 intent 不相等时不因为共享词（例如 `refund_eligibility` 与 `exchange_eligibility` 的 `eligibility`）获得高分，避免过度泛化导致污染注入。
4. Negative transfer 当前是在线近似指标：当 `used_memory_ids` 非空、任务失败且任务元信息默认认为 no-memory 可成功时，计为 `with_memory_fail_no_memory_success`。正式实验仍需要 replay / leave-one-memory-out 反事实验证。

验证记录：

1. `python -m pytest` 通过，结果为 `9 passed in 0.04s`。
2. 本地 shell 未安装 editable 包，直接 `python -m ntmemevo...` 会找不到模块；编码侧 smoke 使用 `PYTHONPATH=src python -m ...`。用户在 `conda activate rm` 且 `pip install -e ".[dev]"` 后可直接运行 `python -m ...`。
3. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml` 成功：`success_rate=1.0`、`negative_transfer_rate=0.0`、`gate_decision_count=0`。
4. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_raw_trace_rag.yaml` 成功：`success_rate=1.0`、`memory_size=5`、`negative_transfer_rate=0.0`。
5. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_reflexion.yaml` 成功：`success_rate=1.0`、`memory_size=5`、`negative_transfer_rate=0.0`。
6. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_candidate.yaml` 成功：`success_rate=1.0`、`memory_size=5`、`negative_transfer_rate=0.0`。
7. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate.yaml` 成功：`success_rate=1.0`、`memory_size=5`、`memory_top_k=2`、`gate_decision_count=10`、`gate_accepted_count=0`、`gate_rejected_count=10`、拒绝原因为 `precondition_below_threshold`。
8. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_polluted.yaml` 成功：`success_rate=1.0`、`memory_size=6`、`gate_decision_count=15`、`gate_accepted_count=0`、`gate_rejected_count=15`、`negative_transfer_rate=0.0`、拒绝原因包括 `negative_evidence_present=5` 和 `precondition_below_threshold=10`。
9. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_unsafe_polluted.yaml` 成功触发负迁移：`num_tasks=1`、`success_rate=0.0`、`with_memory_fail_no_memory_success=1`、`negative_transfer_rate=1.0`、`harmful_memory_ids=["polluted_refund_lookup_policy_001"]`。

用户复验记录：

1. 用户在 Linux 机器 `BNUZ`、交互式 conda 环境 `(rm)` 下运行 `python -m pytest`，环境为 Python 3.12.13、pytest 9.0.3，结果为 `9 passed in 0.05s`。
2. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml`，结果为 `success_rate=1.0`、`avg_prompt_tokens=310.4`、`memory_policy=none`、`memory_size=0`、`negative_transfer_rate=0.0`、`gate_decision_count=0`。
3. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_raw_trace_rag.yaml`，结果为 `success_rate=1.0`、`avg_prompt_tokens=538.6`、`memory_policy=raw_trace_rag`、`memory_size=5`、`negative_transfer_rate=0.0`、`gate_decision_count=0`。
4. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_reflexion.yaml`，结果为 `success_rate=1.0`、`avg_prompt_tokens=832.2`、`memory_policy=reflexion`、`memory_size=5`、`negative_transfer_rate=0.0`、`gate_decision_count=0`。
5. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_candidate.yaml`，结果为 `success_rate=1.0`、`avg_prompt_tokens=310.4`、`memory_policy=nt_memevo_candidate`、`memory_size=5`、`memory_top_k=0`、`negative_transfer_rate=0.0`、`gate_decision_count=0`。
6. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate.yaml`，结果为 `success_rate=1.0`、`avg_prompt_tokens=310.4`、`memory_policy=nt_memevo_gate`、`memory_size=5`、`memory_top_k=2`、`gate_decision_count=10`、`gate_accepted_count=0`、`gate_rejected_count=10`、`gate_rejection_reasons={"precondition_below_threshold": 10}`、`negative_transfer_rate=0.0`。
7. 用户检查 `runs/tiny_nt_memevo_gate_seed1/memory_updates.jsonl`，确认 10 条 `gate_decision` 均因 `precondition_below_threshold` 被拒绝，5 次 `retrieve` 事件均为空检索，5 条 `candidate_extract` 事件正常写入。
8. 用户检查 `runs/tiny_nt_memevo_gate_seed1/runs.jsonl`，确认 5 个任务均成功且 `used_memory_ids=[]`，说明保守 intent gate 阻止跨 intent candidate 注入。
9. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_polluted.yaml`，结果为 `success_rate=1.0`、`avg_prompt_tokens=310.4`、`memory_policy=nt_memevo_gate`、`memory_size=6`、`memory_top_k=2`、`gate_decision_count=15`、`gate_accepted_count=0`、`gate_rejected_count=15`、`gate_rejection_reasons={"negative_evidence_present": 5, "precondition_below_threshold": 10}`、`negative_transfer_rate=0.0`。
10. 用户检查 `runs/tiny_nt_memevo_gate_polluted_seed1/candidate_memories.jsonl`，确认污染记忆 `polluted_refund_lookup_policy_001` 已作为 bootstrap candidate 导入，且包含 `negative_evidence=["polluted_bad_run_refund_001"]`、`num_harmful=2`、`lcb_delta_reward=-1.0`。
11. 用户通过 `grep 'polluted_refund_lookup_policy_001' runs/tiny_nt_memevo_gate_polluted_seed1/memory_updates.jsonl` 确认该污染记忆在 5 个任务上均被 gate 拒绝，拒绝原因均为 `negative_evidence_present`；因此 polluted 配置没有产生 `used_memory_ids`，`negative_transfer_rate=0.0`。
12. 本次用户复验未粘贴 `configs/tiny_nt_memevo_gate_unsafe_polluted.yaml` 的运行结果；该配置仍保留为第六轮前的对照复验项，用于确认 unsafe gate 接受污染记忆时可稳定触发负迁移指标。

当前边界：

1. Gate 仍是 deterministic heuristic，不是 learned ranker，也未接 embedding similarity。
2. `utility` 仍未在线更新；gate 使用第四轮默认 utility 和 fixture 中的人工污染 utility。
3. `negative_transfer_rate` 是近似在线指标，不等于严格反事实定义；第五轮只把日志字段、触发路径和指标汇总跑通。
4. candidate memory 仍未 promotion 到 active memory，`candidate -> active -> quarantined -> retired` 生命周期迁移尚未实现。
5. `follow_memory_hints=true` 只用于离线 mock 污染实验，真实模型实验不依赖这个参数。
6. 当前 tiny benchmark 每个主任务 intent 基本不同，因此 `tiny_nt_memevo_gate.yaml` 的主配置会拒绝所有跨 intent 记忆；接受路径由测试里的 repeated-task pipeline 覆盖。

用户复验建议命令：

```bash
conda activate rm
pip install -e ".[dev]"
python -m pytest

python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_raw_trace_rag.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_reflexion.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_candidate.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_polluted.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_unsafe_polluted.yaml

cat runs/tiny_nt_memevo_gate_polluted_seed1/metrics.json
tail -n 20 runs/tiny_nt_memevo_gate_polluted_seed1/memory_updates.jsonl
cat runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/metrics.json
tail -n 10 runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/runs.jsonl
```

实验日志填写建议：

1. `tiny_nt_memevo_gate_seed1`：记录 gate 对主 tiny 五任务全部拒绝的现象，说明这是 intent gate 的保守行为。
2. `tiny_nt_memevo_gate_polluted_seed1`：重点记录污染记忆 `polluted_refund_lookup_policy_001` 被 `negative_evidence_present` 拒绝，且 `negative_transfer_rate=0.0`。
3. `tiny_nt_memevo_gate_unsafe_polluted_seed1`：重点记录 unsafe gate 接受污染记忆后失败，`negative_transfer_rate=1.0`，用于证明指标链路能稳定触发。

下一步建议：

1. 实现 online utility update：对被 gate 接受并注入的 memory，根据任务结果更新 `num_used`、`num_helpful`、`num_harmful`、`alpha`、`beta` 和 `last_used_iter`。
2. 实现 candidate consolidation：把长期通过 gate / replay 的 candidate promotion 为 active memory，把高风险或多次有害 memory quarantine。
3. 增加 replay evaluator：至少支持 leave-one-memory-out replay，把第五轮在线近似负迁移升级为局部反事实估计。
4. 为 tiny benchmark 增加 repeated intent 任务，让 gate 在非污染主配置中既有 accepted memory，也有 rejected memory，便于开发 utility update。
5. 在 gate、utility 和 replay 日志稳定后再接 tau-bench retail。

## 第一阶段第六轮方向

优先方向：实现 online utility update，并补齐可正向接受的 repeated-intent tiny 任务。理由是第五轮已经证明 gate 可以保守拒绝跨 intent 记忆和污染记忆，但主 tiny 五任务中没有自然的 accepted path；如果直接进入 replay 或 tau-bench，utility、lifecycle 和 active/quarantine 状态迁移缺少稳定离线验证入口。

第六轮建议范围：

1. 新增 repeated-intent tiny split，例如两个或三个 `order_status` / `refund_eligibility` 任务连续出现，使 `nt_memevo_gate` 能在安全场景中接受同 intent candidate memory。
2. 实现 `CandidateMemoryStore.update_utility()` 或等价更新路径：当 memory 被注入后，根据任务结果更新 `num_used`、`num_helpful`、`num_harmful`、`alpha`、`beta`、`mean_delta_reward`、`lcb_delta_reward` 和 `lifecycle.last_used_iter`。
3. 在 `memory_updates.jsonl` 中新增 `utility_update` 事件，记录更新前后 utility、任务结果、被更新的 memory id 和是否判为 helpful/harmful。
4. 增加 lifecycle 最小迁移：连续 helpful 的 candidate 可以保持或提升为 `active`，出现 harmful 或 negative evidence 的 memory 可以进入 `quarantined`；本轮可先实现确定性阈值，不引入 learned verifier。
5. 对 `tiny_nt_memevo_gate_unsafe_polluted.yaml` 做用户复验，确认 unsafe ablation 的 `negative_transfer_rate=1.0` 和 `harmful_memory_ids=["polluted_refund_lookup_policy_001"]`。
6. 新增测试覆盖：accepted candidate 的 utility 增量、harmful memory 的 `num_harmful` 增量、`last_used_iter` 更新、utility update 日志字段，以及前五轮配置不回归。
7. 第六轮仍建议暂缓 tau-bench 接入；待 gate accepted path、utility update 和 quarantine 日志稳定后，再把同一套机制迁移到 tau-bench retail。

## 2026-05-01 第一阶段第六轮

目标：落实 online utility update，并补齐 repeated-intent tiny 任务，使 `nt_memevo_gate` 在安全场景中出现稳定 accepted path；同时让 unsafe polluted ablation 中的有害记忆被在线反馈更新并进入 quarantine。

已完成：

1. 新增 `CandidateMemoryStore.update_utility()`，对被 gate 接受并实际注入 agent prompt 的 candidate memory 做在线更新。
2. utility 更新覆盖 `num_used`、`num_helpful`、`num_harmful`、`alpha`、`beta`、`mean_delta_reward`、`lcb_delta_reward`。
3. lifecycle 更新覆盖 `last_used_iter`，并实现最小确定性状态迁移：累计 helpful 达到阈值且无 harmful/negative evidence 时从 `candidate` 提升为 `active`；出现 harmful 或 negative evidence 时进入 `quarantined`。
4. `run_stream` 在 `memory.method=nt_memevo_gate` 且 `used_memory_ids` 非空时调用 utility update，并向 `memory_updates.jsonl` 写入 `utility_update` 事件。
5. `utility_update` 事件记录 `outcome`、`baseline_reward`、`delta_reward`、更新前后 `utility`、更新前后 `lifecycle`、正负 evidence、任务结果和 run id。
6. `metrics.json` 新增 `utility_update_count`、`utility_helpful_count`、`utility_harmful_count`、`utility_neutral_count`、`candidate_memory_count`、`active_memory_count`、`quarantined_memory_count` 和 `retired_memory_count`。
7. 新增 repeated-intent split：`data/task_splits/tiny_repeated_intent_tasks.json`，包含 3 个连续 `order_status` 任务。
8. 新增配置 `configs/tiny_nt_memevo_gate_repeated.yaml`，用于稳定验证同 intent candidate 被接受、使用、更新并 promotion 为 active。
9. 扩展 unsafe polluted 测试，确认污染记忆被接受导致失败后，`num_harmful` 增加、`negative_evidence` 追加当前 run、`last_used_iter` 更新，并进入 `quarantined`。
10. 新增/更新测试覆盖：safe accepted utility update、active promotion、harmful utility update、quarantine、utility update 日志字段，以及前五轮 pipeline 不回归。
11. 更新 `README.md`，加入 repeated utility update 运行命令、`utility_update` 日志字段和新增 metrics 字段。

关键实现说明：

1. 本轮采用 Level 1 outcome update，不做 replay 反事实归因。`alpha += reward`、`beta += 1 - reward`，`helpful` 由任务成功近似判定，`harmful` 由“使用了记忆、任务失败、且任务元信息认为 no-memory 可成功”近似判定。
2. `delta_reward` 使用 `reward - no_memory_reward` 的在线代理值；若任务未提供 `no_memory_reward`，则由 `no_memory_success` 推断为 1.0 或 0.0。
3. `mean_delta_reward` 和 `lcb_delta_reward` 是在线代理统计，不等价于严格 causal effect；后续仍需要 leave-one-memory-out replay。
4. promotion 默认阈值为 `memory.utility.promote_after_helpful=2`，quarantine 默认阈值为 `memory.utility.quarantine_after_harmful=1`。
5. `candidate_memories.jsonl` 在 utility update 后会被重写，保证最终文件体现最新 utility、evidence 和 lifecycle；随后当前任务仍会抽取新 candidate 并追加。

验证记录：

1. `python -m pytest` 通过，结果为 `10 passed in 0.07s`。
2. 本地 shell 未安装 editable 包，编码侧 smoke 使用 `PYTHONPATH=src python -m ...`；用户在 `conda activate rm` 且 `pip install -e ".[dev]"` 后可直接运行 `python -m ...`。
3. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml` 成功：`success_rate=1.0`、`memory_size=0`、`negative_transfer_rate=0.0`、`utility_update_count=0`。
4. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_raw_trace_rag.yaml` 成功：`success_rate=1.0`、`memory_size=5`、`negative_transfer_rate=0.0`、`utility_update_count=0`。
5. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_reflexion.yaml` 成功：`success_rate=1.0`、`memory_size=5`、`negative_transfer_rate=0.0`、`utility_update_count=0`。
6. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_candidate.yaml` 成功：`success_rate=1.0`、`memory_size=5`、`candidate_memory_count=5`、`utility_update_count=0`。
7. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate.yaml` 成功：`success_rate=1.0`、`memory_size=5`、`gate_decision_count=10`、`gate_accepted_count=0`、`gate_rejected_count=10`、`utility_update_count=0`。
8. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_repeated.yaml` 成功：`num_tasks=3`、`success_rate=1.0`、`memory_size=3`、`memory_top_k=2`、`gate_decision_count=3`、`gate_accepted_count=3`、`utility_update_count=3`、`utility_helpful_count=3`、`active_memory_count=1`、`candidate_memory_count=2`。
9. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_polluted.yaml` 成功：`success_rate=1.0`、`memory_size=6`、`gate_decision_count=15`、`gate_accepted_count=0`、`gate_rejected_count=15`、`gate_rejection_reasons={"negative_evidence_present": 5, "precondition_below_threshold": 10}`、`utility_update_count=0`、`negative_transfer_rate=0.0`。
10. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_unsafe_polluted.yaml` 成功触发负迁移和 quarantine：`num_tasks=1`、`success_rate=0.0`、`with_memory_fail_no_memory_success=1`、`negative_transfer_rate=1.0`、`harmful_memory_ids=["polluted_refund_lookup_policy_001"]`、`utility_update_count=1`、`utility_harmful_count=1`、`quarantined_memory_count=1`。

用户复验记录：

1. 用户在 Linux 机器 `BNUZ`、交互式 conda 环境 `(rm)` 下运行 `python -m pytest`，环境为 Python 3.12.13、pytest 9.0.3、pluggy 1.6.0，结果为 `10 passed in 0.05s`。
2. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml`，结果为 `success_rate=1.0`、`avg_prompt_tokens=310.4`、`memory_policy=none`、`memory_size=0`、`negative_transfer_rate=0.0`、`utility_update_count=0`。
3. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_raw_trace_rag.yaml`，结果为 `success_rate=1.0`、`avg_prompt_tokens=538.6`、`memory_policy=raw_trace_rag`、`memory_size=5`、`negative_transfer_rate=0.0`、`utility_update_count=0`。
4. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_reflexion.yaml`，结果为 `success_rate=1.0`、`avg_prompt_tokens=832.2`、`memory_policy=reflexion`、`memory_size=5`、`negative_transfer_rate=0.0`、`utility_update_count=0`。
5. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_candidate.yaml`，结果为 `success_rate=1.0`、`avg_prompt_tokens=310.4`、`memory_policy=nt_memevo_candidate`、`memory_size=5`、`candidate_memory_count=5`、`active_memory_count=0`、`quarantined_memory_count=0`。
6. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate.yaml`，结果为 `success_rate=1.0`、`memory_size=5`、`gate_decision_count=10`、`gate_accepted_count=0`、`gate_rejected_count=10`、`gate_rejection_reasons={"precondition_below_threshold": 10}`、`utility_update_count=0`。
7. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_repeated.yaml`，结果为 `num_tasks=3`、`success_rate=1.0`、`memory_size=3`、`memory_top_k=2`、`gate_decision_count=3`、`gate_accepted_count=3`、`gate_rejected_count=0`、`utility_update_count=3`、`utility_helpful_count=3`、`active_memory_count=1`、`candidate_memory_count=2`。
8. 用户检查 `runs/tiny_nt_memevo_gate_repeated_seed1/memory_updates.jsonl`，确认 3 条 `utility_update` 均为 `outcome=helpful`；其中 `cand_000001_tiny_order_repeat_001` 在 iteration 2 和 3 被两次更新，最终 `alpha=3.0`、`beta=1.0`、`num_used=2`、`num_helpful=2`、`lifecycle.status=active`、`last_used_iter=3`。
9. 用户检查 `runs/tiny_nt_memevo_gate_repeated_seed1/candidate_memories.jsonl`，确认第一条 repeated memory 已提升为 `active`，第二条保持 `candidate` 且 `num_used=1`，第三条保持未使用的 `candidate`。
10. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_polluted.yaml`，结果为 `success_rate=1.0`、`memory_size=6`、`gate_decision_count=15`、`gate_accepted_count=0`、`gate_rejected_count=15`、`gate_rejection_reasons={"negative_evidence_present": 5, "precondition_below_threshold": 10}`、`utility_update_count=0`、`negative_transfer_rate=0.0`。
11. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_unsafe_polluted.yaml`，结果为 `num_tasks=1`、`success_rate=0.0`、`with_memory_fail_no_memory_success=1`、`negative_transfer_rate=1.0`、`harmful_memory_ids=["polluted_refund_lookup_policy_001"]`、`gate_accepted_count=1`、`utility_update_count=1`、`utility_harmful_count=1`、`quarantined_memory_count=1`。
12. 用户检查 `runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/memory_updates.jsonl`，确认污染记忆先被 bootstrap 导入，随后在 unsafe gate 下被接受并检索注入，最后产生 `outcome=harmful` 的 `utility_update`。
13. 用户检查 `runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/candidate_memories.jsonl`，确认污染记忆最终 `alpha=1.0`、`beta=4.0`、`mean_delta_reward=-1.0`、`lcb_delta_reward=-1.0`、`num_used=3`、`num_harmful=3`、`lifecycle.status=quarantined`、`last_used_iter=1`，并追加当前失败 run 到 `negative_evidence`。

当前边界：

1. utility update 仍是在线近似，不证明被注入记忆对成功有因果贡献；成功任务只作为 Level 1 helpful signal。
2. `mean_delta_reward` 和 `lcb_delta_reward` 目前使用 no-memory 元信息推断的代理 baseline，尚未通过 replay 得到真实反事实差值。
3. lifecycle promotion/quarantine 是确定性阈值，不是 verification-gated consolidation。
4. repeated-intent split 使用同一个 `ORD-1001` order-status 任务，主要用于稳定覆盖 accepted utility path，不代表真实 benchmark 难度。
5. `tiny_nt_memevo_gate.yaml` 主五任务仍因 intent 不同而全部拒绝跨 intent candidate，这是 gate 的保守行为，不是 utility update 的主要验收配置。
6. 仍未接入 tau-bench retail、embedding retrieval、learned ranker 或 leave-one-memory-out replay。

复验命令归档：

```bash
conda activate rm
pip install -e ".[dev]"
python -m pytest

python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_raw_trace_rag.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_reflexion.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_candidate.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_repeated.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_polluted.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_unsafe_polluted.yaml

cat runs/tiny_nt_memevo_gate_repeated_seed1/metrics.json
grep '"event_type": "utility_update"' runs/tiny_nt_memevo_gate_repeated_seed1/memory_updates.jsonl
head -n 3 runs/tiny_nt_memevo_gate_repeated_seed1/candidate_memories.jsonl

cat runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/metrics.json
grep 'polluted_refund_lookup_policy_001' runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/memory_updates.jsonl
head -n 2 runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/candidate_memories.jsonl
```

实验日志更新状态：

1. `docs/experiment_log.md` 已补齐 `tiny_nt_memevo_gate_repeated_seed1` 的第六轮用户复验结果，记录同 intent memory 被 gate 接受、`utility_update_count=3`、`utility_helpful_count=3`，以及 1 条 memory 进入 `active`。
2. `docs/experiment_log.md` 已补齐 `tiny_nt_memevo_gate_unsafe_polluted_seed1` 的第六轮用户复验结果，记录 unsafe gate 接受污染记忆后失败、`negative_transfer_rate=1.0`、`utility_harmful_count=1` 和 `quarantined_memory_count=1`。
3. `docs/experiment_log.md` 已更新 `tiny_nt_memevo_gate_polluted_seed1` 和 `tiny_nt_memevo_gate_seed1` 的第六轮新增 utility/lifecycle 指标，说明拒绝路径不会触发 utility update。

下一步建议：

1. 实现 leave-one-memory-out replay，把 online proxy negative transfer 升级为局部反事实估计。
2. 实现 verification-gated consolidation，将 `candidate -> active` 从简单阈值升级为 support task replay 验证。
3. 为 repeated-intent tiny split 增加不同 order id、refund 和 exchange 的安全重复任务，避免只验证单一工具路径。
4. 在 utility/replay 日志稳定后接入 tau-bench retail。

## 第一阶段第七轮方向

优先方向：实现 leave-one-memory-out replay，并把第六轮的 online proxy utility update 升级为 replay-backed utility update。理由是第六轮已经证明 safe accepted path、active promotion、unsafe harmful update 和 quarantine 都能稳定复现；下一步需要补上论文定义中更关键的局部反事实证据，避免只依赖“使用记忆后任务成功/失败”的粗粒度归因。

第七轮建议范围：

1. 新增 replay runner：对单个已完成任务支持 `with selected memory`、`without selected memory` 和 `leave-one-memory-out` 三种重放模式。
2. 对 `nt_memevo_gate` 中实际注入的 top-k memory 做局部反事实 replay，计算 `delta_reward`、`delta_success` 和 replay-based harmful/helpful 判断。
3. 将 replay 结果写入 `replay_results.jsonl`，字段至少包括 `replay_id`、`source_run_id`、`task_id`、`memory_id`、`mode`、`with_reward`、`without_reward`、`delta_reward`、`with_success`、`without_success`、`attribution_label`。
4. 在 `memory_updates.jsonl` 中新增 `replay_utility_update` 或扩展 `utility_update`，区分 `credit_source=online_proxy|leave_one_memory_out`。
5. 将 `mean_delta_reward` 和 `lcb_delta_reward` 优先由 replay delta 更新；没有 replay 时保留第六轮 online proxy fallback。
6. 将 `candidate -> active` promotion 从单纯 `num_helpful` 阈值升级为 replay/support-task 验证门控；污染或 replay-harmful memory 继续进入 `quarantined`。
7. 新增测试覆盖 repeated safe replay、unsafe polluted replay、replay_results 日志字段、replay-backed utility update 和第六轮全部配置不回归。
8. 第七轮仍建议暂缓 tau-bench 接入；待 replay attribution 和 consolidation 日志稳定后再迁移真实 benchmark。

## 2026-05-01 第一阶段第七轮

目标：落实 leave-one-memory-out replay，把 `nt_memevo_gate` 中被实际注入的记忆从第六轮 online proxy 更新升级为可选 replay-backed utility update，并让安全有益记忆与污染有害记忆都能在离线 tiny benchmark 中形成局部反事实证据。

已完成：

1. 新增 `src/ntmemevo/evaluation/replay.py`，实现 `ReplayConfig`、`ReplayResult`、`NullTraceLogger` 和 `run_memory_replays()`。
2. Replay runner 支持三类模式：`with_selected_memory`、`without_selected_memory` 和 `leave_one_memory_out`；核心归因字段写入 `replay_results.jsonl`。
3. `replay_results.jsonl` 字段包含 `replay_id`、`source_run_id`、`task_id`、`memory_id`、`mode`、`with_reward`、`without_reward`、`delta_reward`、`with_success`、`without_success`、`attribution_label`、`with_used_memory_ids` 和 `without_used_memory_ids`。
4. 扩展 `CandidateMemoryStore`，新增 `update_utility_from_replay()`；`UtilityUpdate` 新增 `credit_source`、`replay_id` 和 `source_run_id`。
5. Online fallback 保持第六轮行为：未启用 replay 或 replay 缺失时继续使用 `credit_source=online_proxy` 的 outcome update。
6. Replay-backed update 使用 `credit_source=leave_one_memory_out`；`delta_reward>0` 判为 helpful，`delta_reward<0` 判为 harmful，否则 neutral。
7. Replay-backed alpha/beta 更新改为基于归因标签：helpful 增加 alpha，harmful 增加 beta，neutral 不改变 alpha/beta；`mean_delta_reward` 和 `lcb_delta_reward` 由 replay delta 更新。
8. Promotion 追加 replay 验证约束：当配置 `memory.replay.promote_requires_positive_lcb=true` 时，candidate 需要达到 helpful 阈值且 `lcb_delta_reward>0` 才能进入 `active`。
9. 修改 `run_stream`，在 `memory.replay.enabled=true` 且 `nt_memevo_gate` 实际注入 memory 后自动运行 replay，并优先用 leave-one-memory-out 结果更新 utility。
10. `memory_updates.jsonl` 的 `utility_update` 事件新增 `credit_source`、`replay_id`、`source_run_id`、`replay_mode`、`replay_attribution_label`、`replay_with_reward`、`replay_without_reward` 和 `replay_delta_reward`。
11. `metrics.json` 新增 `utility_credit_sources`、`online_proxy_utility_update_count`、`replay_utility_update_count`、`replay_result_count`、`replay_leave_one_count`、`replay_helpful_count`、`replay_harmful_count` 和 `replay_neutral_count`。
12. 新增 memory-dependent tiny split：`data/task_splits/tiny_memory_dependent_tasks.json`。第一个任务产生 order-status seed memory，后两个任务需要依赖该记忆中的工具证据才能被 mock memory-sensitive agent 解出。
13. 新增配置 `configs/tiny_nt_memevo_gate_replay.yaml`，用于稳定验证 replay-helpful、replay-backed utility update 和 replay-backed active promotion。
14. 更新 `configs/tiny_nt_memevo_gate_unsafe_polluted.yaml`，启用 replay，使 unsafe polluted ablation 的 harmful/quarantine 更新由 leave-one-memory-out delta 支撑。
15. 新增测试覆盖 replay-helpful promotion、unsafe polluted replay-harmful、`replay_results.jsonl` 字段、replay-backed `utility_update` 字段，以及第六轮 online fallback 不回归。
16. 更新 `README.md`，加入 replay-backed utility update 运行命令、replay 日志字段、replay metrics 和下一阶段方向。

关键实现说明：

1. Replay 是配置开关，当前由 `memory.replay.enabled` 控制；未启用时不增加额外 agent 运行成本。
2. Replay 使用同一 actor/mock agent 和 fresh env factory 重新运行任务，但用 `NullTraceLogger` 避免污染主 `trace_events.jsonl`。
3. `with_selected_memory` 重放完整 selected-memory 上下文；`without_selected_memory` 重放空记忆上下文；`leave_one_memory_out` 对每条实际注入的 selected memory 分别移除后重放。
4. 第七轮的 replay-backed promotion 仍是局部单任务反事实，不等于完整 support-set verification；它比第六轮 online proxy 更接近论文定义，但还不是最终 verification-gated consolidation。
5. `tiny_nt_memevo_gate_replay.yaml` 使用 `follow_memory_hints=true` 和 memory-dependent split，仅用于离线稳定验证 replay 归因链路；真实模型实验不依赖该 mock 行为。

验证记录：

1. `python -m pytest` 通过，结果为 `11 passed in 0.08s`。
2. 本地 shell 未安装 editable 包，编码侧 smoke 继续使用 `PYTHONPATH=src python -m ...`；用户在 `conda activate rm` 且 `pip install -e ".[dev]"` 后可直接运行 `python -m ...`。
3. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_replay.yaml` 成功：`num_tasks=3`、`success_rate=1.0`、`gate_accepted_count=2`、`replay_leave_one_count=2`、`replay_helpful_count=2`、`replay_utility_update_count=2`、`online_proxy_utility_update_count=0`、`active_memory_count=1`。
4. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_unsafe_polluted.yaml` 成功触发 replay-backed harmful update：`num_tasks=1`、`success_rate=0.0`、`negative_transfer_rate=1.0`、`harmful_memory_ids=["polluted_refund_lookup_policy_001"]`、`replay_leave_one_count=1`、`replay_harmful_count=1`、`replay_utility_update_count=1`、`quarantined_memory_count=1`。

用户复验记录：

1. 用户在 Linux 机器 `BNUZ`、交互式 conda 环境 `(rm)` 下运行 `python -m pytest`，环境为 Python 3.12.13、pytest 9.0.3、pluggy 1.6.0，结果为 `11 passed in 0.04s`。
2. 用户复验 `tiny_nomem.yaml`：`success_rate=1.0`、`avg_prompt_tokens=310.4`、`memory_policy=none`、`memory_size=0`、`negative_transfer_rate=0.0`、`replay_result_count=0`。
3. 用户复验 `tiny_raw_trace_rag.yaml`：`success_rate=1.0`、`avg_prompt_tokens=538.6`、`memory_policy=raw_trace_rag`、`memory_size=5`、`memory_top_k=2`、`negative_transfer_rate=0.0`。
4. 用户复验 `tiny_reflexion.yaml`：`success_rate=1.0`、`avg_prompt_tokens=832.2`、`memory_policy=reflexion`、`memory_size=5`、`memory_top_k=2`、`negative_transfer_rate=0.0`。
5. 用户复验 `tiny_nt_memevo_candidate.yaml`：`success_rate=1.0`、`avg_prompt_tokens=310.4`、`memory_policy=nt_memevo_candidate`、`memory_size=5`、`candidate_memory_count=5`、`active_memory_count=0`、`quarantined_memory_count=0`。
6. 用户复验 `tiny_nt_memevo_gate.yaml`：`success_rate=1.0`、`memory_size=5`、`gate_decision_count=10`、`gate_accepted_count=0`、`gate_rejected_count=10`、`gate_rejection_reasons={"precondition_below_threshold": 10}`、`utility_update_count=0`。
7. 用户复验 `tiny_nt_memevo_gate_repeated.yaml`：`num_tasks=3`、`success_rate=1.0`、`gate_accepted_count=3`、`utility_update_count=3`、`utility_credit_sources={"online_proxy": 3}`、`online_proxy_utility_update_count=3`、`replay_utility_update_count=0`、`active_memory_count=1`。这确认第六轮 online proxy fallback 未回归。
8. 用户复验 `tiny_nt_memevo_gate_replay.yaml`：`num_tasks=3`、`success_rate=1.0`、`gate_accepted_count=2`、`gate_rejected_count=1`、`replay_result_count=6`、`replay_leave_one_count=2`、`replay_helpful_count=2`、`replay_harmful_count=0`、`utility_credit_sources={"leave_one_memory_out": 2}`、`replay_utility_update_count=2`、`online_proxy_utility_update_count=0`、`active_memory_count=1`。
9. 用户检查 `runs/tiny_nt_memevo_gate_replay_seed1/replay_results.jsonl`，确认两条 `leave_one_memory_out` 均对应 `cand_000001_tiny_memory_order_seed_001`，且 `with_reward=1.0`、`without_reward=0.0`、`delta_reward=1.0`、`with_success=true`、`without_success=false`、`attribution_label=helpful`。
10. 用户检查 `runs/tiny_nt_memevo_gate_replay_seed1/memory_updates.jsonl`，确认两条 `utility_update` 均为 `credit_source=leave_one_memory_out`、`replay_attribution_label=helpful`、`replay_delta_reward=1.0`；第二次更新后 `lifecycle.status` 从 `candidate` 迁移到 `active`，`lcb_delta_reward=0.292893`。
11. 用户检查 `runs/tiny_nt_memevo_gate_replay_seed1/candidate_memories.jsonl`，确认 seed memory 最终 `alpha=3.0`、`beta=1.0`、`mean_delta_reward=1.0`、`lcb_delta_reward=0.292893`、`num_used=2`、`num_helpful=2`、`num_harmful=0`、`lifecycle.status=active`、`last_used_iter=3`。
12. 用户复验 `tiny_nt_memevo_gate_polluted.yaml`：`success_rate=1.0`、`memory_size=6`、`gate_decision_count=15`、`gate_accepted_count=0`、`gate_rejected_count=15`、`gate_rejection_reasons={"negative_evidence_present": 5, "precondition_below_threshold": 10}`、`utility_update_count=0`、`negative_transfer_rate=0.0`。
13. 用户检查 `runs/tiny_nt_memevo_gate_polluted_seed1/memory_updates.jsonl`，确认污染记忆 `polluted_refund_lookup_policy_001` 在 5 个任务上均被拒绝，拒绝原因为 `negative_evidence_present`，因此 safe polluted 配置不触发 replay 和 utility update。
14. 用户复验 `tiny_nt_memevo_gate_unsafe_polluted.yaml`：`num_tasks=1`、`success_rate=0.0`、`negative_transfer_rate=1.0`、`harmful_memory_ids=["polluted_refund_lookup_policy_001"]`、`gate_accepted_count=1`、`replay_result_count=3`、`replay_leave_one_count=1`、`replay_harmful_count=1`、`replay_utility_update_count=1`、`online_proxy_utility_update_count=0`、`quarantined_memory_count=1`。
15. 用户检查 `runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/replay_results.jsonl`，确认污染记忆的 `leave_one_memory_out` replay 为 `with_reward=0.0`、`without_reward=1.0`、`delta_reward=-1.0`、`with_success=false`、`without_success=true`、`attribution_label=harmful`。
16. 用户检查 `runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/memory_updates.jsonl`，确认污染记忆的 harmful update 已从第六轮 online proxy 升级为 `credit_source=leave_one_memory_out`，并记录 `replay_delta_reward=-1.0`、`replay_with_success=false`、`replay_without_success=true`。
17. 用户检查 `runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/candidate_memories.jsonl`，确认污染记忆最终 `alpha=1.0`、`beta=4.0`、`mean_delta_reward=-1.0`、`lcb_delta_reward=-1.0`、`num_used=3`、`num_harmful=3`、`lifecycle.status=quarantined`、`last_used_iter=1`，并追加当前失败 run 到 `negative_evidence`。

当前边界：

1. Replay 目前只覆盖单任务局部反事实，不做 support task set 或 matched replay。
2. Replay 仍使用同一个 actor 决策策略；对真实 LLM 来说，重放会引入随机性和成本，需要固定 temperature、seed、缓存和预算。
3. 当前 `ReplayResult` 只做 reward/success 级别归因，尚未实现 token/tool cost-adjusted delta。
4. Promotion 依赖 replay delta 的 LCB，但还没有独立 verifier，也没有 candidate consolidation 队列。
5. `tiny_memory_dependent_tasks.json` 是人工构造的离线链路验证，不代表真实 benchmark 难度。
6. tau-bench retail、embedding retrieval、learned ranker、support-set verification 和记忆合并/拆分仍未实现。

用户复验建议命令：

```bash
conda activate rm
pip install -e ".[dev]"
python -m pytest

python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_raw_trace_rag.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_reflexion.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_candidate.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_repeated.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_replay.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_polluted.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_unsafe_polluted.yaml

cat runs/tiny_nt_memevo_gate_replay_seed1/metrics.json
cat runs/tiny_nt_memevo_gate_replay_seed1/replay_results.jsonl
grep '"credit_source": "leave_one_memory_out"' runs/tiny_nt_memevo_gate_replay_seed1/memory_updates.jsonl
head -n 3 runs/tiny_nt_memevo_gate_replay_seed1/candidate_memories.jsonl

cat runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/metrics.json
cat runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/replay_results.jsonl
grep 'polluted_refund_lookup_policy_001' runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/memory_updates.jsonl
head -n 2 runs/tiny_nt_memevo_gate_unsafe_polluted_seed1/candidate_memories.jsonl
```

实验日志更新状态：

1. `docs/experiment_log.md` 已补齐 `tiny_nt_memevo_gate_replay_seed1` 的第七轮用户复验结果，记录 replay-helpful、`credit_source=leave_one_memory_out`、`delta_reward=1.0` 和 seed memory 进入 `active`。
2. `docs/experiment_log.md` 已更新 `tiny_nt_memevo_gate_unsafe_polluted_seed1` 的第七轮 replay-backed 复验结果，记录 unsafe gate 接受污染记忆后 `delta_reward=-1.0`、`attribution_label=harmful` 和 `quarantined_memory_count=1`。
3. `docs/experiment_log.md` 已补充第七轮完整对照结果摘要，并更新第八轮方向为 support-set replay 与 verification-gated consolidation。

下一步建议：

1. 实现 support-set / matched replay，把单任务 leave-one-memory-out 扩展为多相似任务验证。
2. 实现 verification-gated consolidation 队列，使 `candidate -> active` 由 support replay 统一决定，而不是在主循环里即时状态迁移。
3. 增加 replay cost metrics：`delta_prompt_tokens`、`delta_tool_calls`、cost-adjusted reward 和 replay budget。
4. 为 tiny benchmark 扩充不同 order id、refund、exchange 的 memory-dependent/replay tasks，减少单一路径过拟合。
5. 在 replay/consolidation 日志稳定后接入 tau-bench retail。

## 第一阶段第八轮方向

优先方向：实现 support-set replay 与 verification-gated consolidation。理由是第七轮已经跑通单任务 leave-one-memory-out replay，能够对安全 seed memory 给出 `delta_reward=1.0` 的 helpful 归因，也能对 unsafe polluted memory 给出 `delta_reward=-1.0` 的 harmful 归因；下一步需要把“当前任务局部反事实”升级为“相似支持任务集合上的验证”，使 `candidate -> active` 不再由主循环即时阈值触发，而由独立验证门控决定。

第八轮建议范围：

1. 新增 support task selector：根据 `scope.intent`、domain、preconditions、tool names 和 lexical similarity 从 tiny support pool 中选择相似任务。
2. 新增 `MemoryVerifier` 或 consolidation runner：对 candidate memory 在 support task set 上运行 `with memory` / `without memory` replay。
3. 新增 support task fixtures，至少覆盖 `order_status`、`refund_eligibility` 和 `exchange_eligibility`，避免第七轮只验证 order-status 单一路径。
4. 将 `candidate -> active` promotion 从主循环即时 `num_helpful` 阈值迁移到 verification-gated consolidation，记录 `verification_passed`、`support_delta_mean`、`support_lcb_delta_reward` 和 `support_negative_transfer_rate`。
5. 扩展 `replay_results.jsonl`，区分 `source_task_replay` 与 `support_task_replay`，并保留 support task id、memory id、with/without reward、delta 和 attribution label。
6. 新增 metrics：`verification_count`、`verification_passed_count`、`verification_failed_count`、`support_replay_count`、`support_replay_helpful_count`、`support_replay_harmful_count` 和 replay token/tool 成本。
7. 保持第七轮所有配置不回归：`repeated` 继续覆盖 online proxy fallback，`replay` 覆盖 helpful attribution，`polluted` 覆盖 safe rejection，`unsafe_polluted` 覆盖 harmful attribution 和 quarantine。
8. 第八轮仍建议暂缓 tau-bench retail；待 support-set verification 和 consolidation 日志稳定后再迁移真实 benchmark。

## 2026-05-02 第一阶段第八轮

目标：落实 support-set replay 与 verification-gated consolidation，把第七轮“当前任务 leave-one-memory-out 归因”扩展为“相似支持任务集合验证”，并让 candidate promotion 可以由独立 verification gate 决定。

已完成：

1. 新增 `src/ntmemevo/evaluation/verification.py`，实现 `VerificationConfig`、`SupportTaskSelector`、`MemoryVerifier` 和 `VerificationResult`。
2. Support task selector 根据 intent、domain、tool overlap 和 lexical similarity 从 support pool 中选择相似任务，支持 `require_intent_match`、`require_domain_match`、`min_support_similarity`、`max_support_tasks` 和 `min_support_tasks`。
3. `MemoryVerifier` 对待验证 candidate memory 在 support task set 上运行 `with memory` / `without memory` replay，计算 `support_delta_mean`、`support_lcb_delta_reward`、`support_negative_transfer_rate`、support helpful/harmful/neutral 计数和 `verification_passed`。
4. 扩展 `ReplayResult`，新增 `replay_scope`、`support_task_replay` mode、`cost_adjusted_delta_reward`、`delta_prompt_tokens`、`delta_completion_tokens` 和 `delta_tool_calls`，使 `replay_results.jsonl` 可以区分 `source_task_replay` 与 `support_task_replay`。
5. 扩展 `ReplayConfig`，新增 `prompt_token_cost_weight` 和 `tool_call_cost_weight`，为后续 cost-adjusted replay delta 保留配置入口。
6. 扩展 `CandidateMemoryStore`，新增 `VerificationUpdate` 和 `apply_verification_result()`，可根据 support-set 验证结果把 candidate promotion 为 `active`，或在 support negative transfer 时进入 `quarantined`。
7. `CandidateMemoryStore.update_utility()` 和 `update_utility_from_replay()` 新增 `allow_promotion` 开关；当 `memory.verification.disable_immediate_promotion=true` 时，source-task utility update 只累计 evidence/utility，不直接把 candidate 提升为 active。
8. 修改 `run_stream`，支持 `memory.verification.enabled=true`：加载 support split、触发 support-set verification、写入 support replay 记录、写入 `verification_update` 事件，并汇总 verification/support replay metrics。
9. 新增 support task fixture：`data/task_splits/tiny_support_verification_tasks.json`，覆盖 `order_status`、`refund_eligibility` 和 `exchange_eligibility` 三类 support tasks。
10. 新增配置 `configs/tiny_nt_memevo_gate_verify.yaml`，用于验证 replay-helpful source memory 先保持 `candidate`，随后通过 support-set verification 才进入 `active`。
11. 新增测试：support-set verification 通过后 promotion、support replay 中性时 verification failed 且保持 candidate，同时保留第七轮 replay / repeated / polluted / unsafe polluted 行为不回归。
12. 更新 `README.md`，加入 verification 配置运行命令、`verification_update` 字段、support replay 字段和新增 metrics。

关键实现说明：

1. Verification 是独立配置开关，默认关闭；前七轮配置不启用 verification，因此 repeated online proxy、source-task replay、safe polluted rejection 和 unsafe polluted harmful replay 均保持原语义。
2. `tiny_nt_memevo_gate_verify.yaml` 使用 `memory.verification.disable_immediate_promotion=true`，因此 seed memory 在两次 source-task replay helpful 后仍保持 `candidate`；只有 support-set replay 给出 `support_delta_mean=1.0` 且 `support_lcb_delta_reward=0.292893` 后，`verification_update` 才将其提升为 `active`。
3. Support replay 当前是 deterministic tiny 环境下的 matched support 验证，不是完整 tau-bench support-set verifier；但日志字段和 lifecycle 更新路径已经按真实实验需要预留。
4. Replay cost metrics 当前按 replay log record 汇总，足够用于离线链路检查；后续若要精确报告真实成本，应按 replay cache 的 unique execution 去重统计。
5. `VerificationResult.failure_reason` 覆盖 `insufficient_support_tasks`、`support_negative_transfer_rate_above_threshold`、`support_delta_mean_below_threshold` 和 `support_lcb_delta_reward_below_threshold`。

验证记录：

1. `python -m pytest` 通过，结果为 `13 passed in 0.10s`。
2. 本地 shell 未安装 editable 包，编码侧 smoke 使用 `PYTHONPATH=src python -m ...`；用户在 `conda activate rm` 且 `pip install -e ".[dev]"` 后可直接运行 `python -m ...`。
3. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml` 成功：`success_rate=1.0`、`memory_size=0`、`verification_count=0`。
4. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_raw_trace_rag.yaml` 成功：`success_rate=1.0`、`memory_size=5`、`verification_count=0`。
5. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_reflexion.yaml` 成功：`success_rate=1.0`、`memory_size=5`、`verification_count=0`。
6. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_candidate.yaml` 成功：`success_rate=1.0`、`memory_size=5`、`candidate_memory_count=5`。
7. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate.yaml` 成功：`success_rate=1.0`、`gate_decision_count=10`、`gate_accepted_count=0`、`gate_rejected_count=10`。
8. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_repeated.yaml` 成功：`num_tasks=3`、`gate_accepted_count=3`、`utility_credit_sources={"online_proxy": 3}`、`active_memory_count=1`。
9. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_replay.yaml` 成功：`num_tasks=3`、`gate_accepted_count=2`、`replay_leave_one_count=2`、`replay_helpful_count=2`、`active_memory_count=1`、`support_replay_count=0`。
10. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_verify.yaml` 成功：`num_tasks=3`、`gate_accepted_count=2`、`replay_leave_one_count=2`、`support_replay_count=2`、`support_replay_helpful_count=2`、`verification_count=1`、`verification_passed_count=1`、`verification_failed_count=0`、`active_memory_count=1`。
11. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_polluted.yaml` 成功：`success_rate=1.0`、`gate_rejected_count=15`、`gate_rejection_reasons={"negative_evidence_present": 5, "precondition_below_threshold": 10}`、`negative_transfer_rate=0.0`。
12. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_unsafe_polluted.yaml` 成功触发 replay-backed harmful attribution：`num_tasks=1`、`success_rate=0.0`、`negative_transfer_rate=1.0`、`replay_harmful_count=1`、`quarantined_memory_count=1`。

用户复验记录：

1. 用户在 Linux 机器 `BNUZ`、交互式 conda 环境 `(rm)` 下运行 `python -m pytest`，环境为 Python 3.12.13、pytest 9.0.3、pluggy 1.6.0，结果为 `13 passed in 0.08s`。
2. 用户复验 `tiny_nomem.yaml`：`success_rate=1.0`、`avg_prompt_tokens=310.4`、`memory_policy=none`、`memory_size=0`、`negative_transfer_rate=0.0`、`verification_count=0`。
3. 用户复验 `tiny_raw_trace_rag.yaml`：`success_rate=1.0`、`avg_prompt_tokens=538.6`、`memory_policy=raw_trace_rag`、`memory_size=5`、`memory_top_k=2`、`verification_count=0`。
4. 用户复验 `tiny_reflexion.yaml`：`success_rate=1.0`、`avg_prompt_tokens=832.2`、`memory_policy=reflexion`、`memory_size=5`、`memory_top_k=2`、`verification_count=0`。
5. 用户复验 `tiny_nt_memevo_candidate.yaml`：`success_rate=1.0`、`avg_prompt_tokens=310.4`、`memory_policy=nt_memevo_candidate`、`memory_size=5`、`candidate_memory_count=5`、`active_memory_count=0`、`quarantined_memory_count=0`。
6. 用户复验 `tiny_nt_memevo_gate.yaml`：`success_rate=1.0`、`memory_size=5`、`gate_decision_count=10`、`gate_accepted_count=0`、`gate_rejected_count=10`、`gate_rejection_reasons={"precondition_below_threshold": 10}`、`utility_update_count=0`。
7. 用户复验 `tiny_nt_memevo_gate_repeated.yaml`：`num_tasks=3`、`success_rate=1.0`、`gate_accepted_count=3`、`utility_update_count=3`、`utility_credit_sources={"online_proxy": 3}`、`online_proxy_utility_update_count=3`、`active_memory_count=1`。这确认第六轮 online proxy fallback 未回归。
8. 用户复验 `tiny_nt_memevo_gate_replay.yaml`：`num_tasks=3`、`success_rate=1.0`、`gate_accepted_count=2`、`gate_rejected_count=1`、`replay_result_count=6`、`replay_leave_one_count=2`、`replay_helpful_count=2`、`utility_credit_sources={"leave_one_memory_out": 2}`、`replay_utility_update_count=2`、`support_replay_count=0`、`active_memory_count=1`。这确认第七轮 source-task replay path 未回归。
9. 用户复验 `tiny_nt_memevo_gate_verify.yaml`：`num_tasks=3`、`success_rate=1.0`、`gate_accepted_count=2`、`gate_rejected_count=1`、`replay_result_count=8`、`replay_leave_one_count=2`、`support_replay_count=2`、`support_replay_helpful_count=2`、`verification_count=1`、`verification_passed_count=1`、`verification_failed_count=0`、`verification_update_count=1`、`active_memory_count=1`。
10. 用户检查 `runs/tiny_nt_memevo_gate_verify_seed1/metrics.json`，确认 support-set verification 指标与编码侧 smoke 一致，并新增 replay cost 字段：`replay_prompt_tokens=5876`、`replay_completion_tokens=800`、`replay_tool_calls=8`、`support_replay_prompt_tokens=1540`、`support_replay_completion_tokens=218`、`support_replay_tool_calls=2`。
11. 用户检查 `runs/tiny_nt_memevo_gate_verify_seed1/memory_updates.jsonl`，确认 1 条 `event_type=verification_update`：`memory_id=cand_000001_tiny_memory_order_seed_001`、`verification_passed=true`、`support_task_ids=["tiny_support_order_001","tiny_support_order_002"]`、`support_delta_mean=1.0`、`support_lcb_delta_reward=0.292893`、`support_negative_transfer_rate=0.0`，并且 `lifecycle_before.status=candidate`、`lifecycle_after.status=active`。
12. 用户检查 `runs/tiny_nt_memevo_gate_verify_seed1/replay_results.jsonl`，确认两条 `replay_scope=support_task_replay` 均为 `delta_reward=1.0`、`cost_adjusted_delta_reward=1.0`、`with_success=true`、`without_success=false`、`attribution_label=helpful`。
13. 用户检查 `runs/tiny_nt_memevo_gate_verify_seed1/candidate_memories.jsonl`，确认 `cand_000001_tiny_memory_order_seed_001` 最终 `lifecycle.status=active`、`utility.mean_delta_reward=1.0`、`utility.lcb_delta_reward=0.292893`、`num_used=2`、`num_helpful=2`，且 `positive_evidence` 包含两个 support replay id。
14. 用户复验 `tiny_nt_memevo_gate_polluted.yaml`：`success_rate=1.0`、`memory_size=6`、`gate_decision_count=15`、`gate_accepted_count=0`、`gate_rejected_count=15`、`gate_rejection_reasons={"negative_evidence_present": 5, "precondition_below_threshold": 10}`、`negative_transfer_rate=0.0`、`verification_count=0`。
15. 用户复验 `tiny_nt_memevo_gate_unsafe_polluted.yaml`：`num_tasks=1`、`success_rate=0.0`、`negative_transfer_rate=1.0`、`harmful_memory_ids=["polluted_refund_lookup_policy_001"]`、`gate_accepted_count=1`、`replay_result_count=3`、`replay_leave_one_count=1`、`replay_harmful_count=1`、`replay_utility_update_count=1`、`quarantined_memory_count=1`。

用户复验建议命令：

```bash
conda activate rm
pip install -e ".[dev]"
python -m pytest

python -m ntmemevo.experiments.run_stream --config configs/tiny_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_raw_trace_rag.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_reflexion.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_candidate.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_repeated.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_replay.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_verify.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_polluted.yaml
python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_unsafe_polluted.yaml

cat runs/tiny_nt_memevo_gate_verify_seed1/metrics.json
grep '"event_type": "verification_update"' runs/tiny_nt_memevo_gate_verify_seed1/memory_updates.jsonl
grep '"replay_scope": "support_task_replay"' runs/tiny_nt_memevo_gate_verify_seed1/replay_results.jsonl
head -n 3 runs/tiny_nt_memevo_gate_verify_seed1/candidate_memories.jsonl
```

实验日志填写建议：

1. 新增 `tiny_nt_memevo_gate_verify_seed1` 实验条目，重点记录 `support_replay_count=2`、`verification_passed_count=1`、`support_delta_mean=1.0`、`support_lcb_delta_reward=0.292893` 和 seed memory 通过 `verification_update` 进入 `active`。
2. 对照 `tiny_nt_memevo_gate_replay_seed1`：第七轮配置仍由 source-task replay-backed utility update 直接 promotion；第八轮 verify 配置则禁用即时 promotion，由 support-set verification 决定 promotion。
3. 对照 `tiny_nt_memevo_gate_polluted_seed1` 和 `tiny_nt_memevo_gate_unsafe_polluted_seed1`：safe gate 仍拒绝污染记忆，unsafe gate 仍能触发 replay-backed harmful/quarantine，说明 verification 变更没有破坏负迁移链路。

当前边界：

1. Support pool 仍是 tiny 人工 fixture，主要用于验证日志和 lifecycle 机制；尚不能代表真实 benchmark 难度。
2. Support selector 使用确定性 intent/domain/tool/lexical 打分，还不是 embedding retriever 或 learned selector。
3. Verification 目前只在 memory 达到 `min_helpful_before_verify` 后触发一次；尚未实现周期性 re-verification、quarantined memory 恢复验证或主动 retire。
4. Support replay 只做 reward/success 级别归因，尚未分析工具路径差异、答案差异或 policy violation 类型。
5. tau-bench retail、embedding retrieval、learned ranker、memory merge/split 和精确 replay budget accounting 仍未实现。

下一步建议：

1. 扩展 support pool 和 matched replay，覆盖 refund、exchange、inventory、policy 多类 memory 的正/负验证。
2. 实现 memory merge/split：当 support evidence 显示某条记忆只在部分 intent/domain 有益时，自动收窄 scope 或拆分记忆。
3. 增加 replay budget 和 exact unique-execution cost accounting，避免 context mode 与 comparison record 重复计成本。
4. 在 verification/consolidation 日志稳定后，接入 tau-bench retail 的真实 task loader、tool API wrapper 和 evaluator。

## 第一阶段第九轮方向

优先方向：扩展 support pool 与 matched replay，并开始实现 memory scope refinement / merge-split。理由是第八轮已经证明 support-set verification 能够独立决定 `candidate -> active`，但当前 support pool 仍只有 tiny 人工 order-status 正例；下一轮应让 support 验证覆盖更多 intent、更多正负样本，并开始处理“记忆在部分任务上有益、部分任务上有害”的负迁移核心问题。

第九轮建议范围：

1. 扩充 tiny support/task split，至少覆盖 `refund_eligibility`、`exchange_eligibility`、`inventory_check` 和 `policy_lookup` 的 memory-dependent 正例与 neutral/negative support 例子。
2. 新增 matched replay selector：除 intent/domain/tool 匹配外，记录 support selection details，例如 `support_match_score`、`intent_score`、`tool_score`、`lexical_score`，并写入 `memory_updates.jsonl` 或独立 support selection 日志。
3. 实现 scope refinement：当 support replay 的 harmful/neutral evidence 集中在某些 intent、tool 或 precondition 上时，生成更窄 scope 的 refined memory，而不是只 quarantine 或保留原 memory。
4. 实现最小 merge/split 日志事件：`memory_split`、`memory_refine` 或 `memory_merge`，记录 parent memory id、child memory id、scope 变化、证据迁移和触发原因。
5. 增加 replay budget controls：限制每轮 verification 的最大 memory 数、最大 support task 数和最大 replay 执行数，并把预算消耗写入 metrics。
6. 修正 replay 成本统计为 unique execution 口径，避免 `with_selected_memory`、`without_selected_memory` 和 comparison record 的重复计数影响论文成本曲线。
7. 保持第八轮所有配置不回归，尤其是 `tiny_nt_memevo_gate_verify.yaml` 的 `verification_passed_count=1` 和 unsafe polluted 的 `negative_transfer_rate=1.0`。
8. 若第九轮 support/refinement 日志稳定，可开始 tau-bench retail 接入的最小 adapter；否则继续先稳定 tiny 上的负迁移拆分链路。

## 2026-05-02 第一阶段第九轮

目标：扩展 support pool 与 matched replay 的审计粒度，并实现最小 scope refinement / split 事件与 replay budget 控制，让第八轮的 verification gate 能在混合 support evidence 下产生更窄 scope 的 refined memory，而不是只做 candidate / active / quarantined 的二分。

已完成：

1. 扩展 `src/ntmemevo/evaluation/verification.py`，让 `VerificationConfig` 支持 `log_support_selection`、verification budget、scope refinement 开关与 refined memory status。
2. 扩展 `SupportTaskMatch` / `VerificationResult`，把 `task_intent`、`task_domain`、`task_tool_names`、`support_match_score`、`intent_score`、`domain_score`、`tool_score`、`lexical_score` 与 replay attribution 一并写入结果对象。
3. 扩展 `src/ntmemevo/evaluation/replay.py`，为 replay 记录增加 `with_execution_id` / `without_execution_id`，用于后续按 unique execution 口径统计 replay 成本。
4. 扩展 `src/ntmemevo/memory/store.py`，新增 `ScopeRefinementUpdate` 与 `refine_scope_from_verification()`，在混合 support evidence 下生成 refined child memory，并把 parent 置为 quarantine。
5. 修改 `src/ntmemevo/experiments/run_stream.py`，在 verification 过程中记录 `support_selection`、`verification_skipped` 与 `memory_refine` 事件，并新增 verification budget / replay unique-cost metrics。
6. 扩充 `data/task_splits/tiny_support_verification_tasks.json`，新增 `inventory_check` 与 `policy_lookup` support tasks，使 support pool 覆盖 order、refund、exchange、inventory 与 policy 五类 intent。
7. 新增 `data/task_splits/tiny_mixed_support_verification_tasks.json`，用于制造 order helpful、refund/exchange harmful 的 mixed-support verification 场景。
8. 新增配置 `configs/tiny_nt_memevo_gate_refine.yaml`，用于验证 mixed-support 下的 scope refinement、support selection 审计与 verification budget 消耗统计。
9. 新增测试：mixed-support verification 触发 `memory_refine` 并生成 refined child memory，以及 verification budget exhaustion 的跳过日志与 metrics。
10. 更新 `README.md`，补充第九轮新的实验命令、support selection 字段、memory_refine 字段，以及 unique-execution replay cost 口径。

验证记录：

1. `PYTHONPATH=src python -m pytest` 通过，结果为 `15 passed in 0.13s`。
2. 用户在 Linux 机器 `BNUZ`、交互式 conda 环境 `(rm)` 下运行 `python -m pytest`，环境为 Python 3.12.13、pytest 9.0.3、pluggy 1.6.0，结果为 `15 passed in 0.07s`。
3. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tiny_nt_memevo_gate_refine.yaml` 成功：`num_tasks=3`、`success_rate=1.0`、`gate_accepted_count=2`、`support_replay_count=4`、`support_replay_helpful_count=2`、`support_replay_harmful_count=2`、`verification_count=1`、`verification_passed_count=0`、`verification_failed_count=1`、`memory_refinement_count=1`、`memory_split_count=1`、`active_memory_count=1`、`quarantined_memory_count=1`。
4. 用户检查 `runs/tiny_nt_memevo_gate_refine_seed1/memory_updates.jsonl`，确认 4 条 `support_selection`：两个 `order_status` support replay 为 `helpful`、`delta_reward=1.0`，一个 `refund_eligibility` 和一个 `exchange_eligibility` support replay 为 `harmful`、`delta_reward=-1.0`。
5. 用户检查 `memory_refine` 事件，确认 parent memory `cand_000001_tiny_memory_order_seed_001` 因 `trigger_reason=mixed_support_harmful` 被 quarantine，并生成 child memory `cand_000001_tiny_memory_order_seed_001__refined_001`。
6. 用户检查 `candidate_memories.jsonl`，确认 refined child memory 为 `active`，`scope.intent=order_status`，`utility.mean_delta_reward=1.0`，`utility.lcb_delta_reward=0.292893`，`num_helpful=2`，`negative_evidence=[]`。
7. 用户完整回归第九轮全部配置通过：`tiny_nomem`、`tiny_raw_trace_rag`、`tiny_reflexion`、`tiny_nt_memevo_candidate`、`tiny_nt_memevo_gate`、`tiny_nt_memevo_gate_repeated`、`tiny_nt_memevo_gate_replay`、`tiny_nt_memevo_gate_verify`、`tiny_nt_memevo_gate_refine`、`tiny_nt_memevo_gate_polluted` 和 `tiny_nt_memevo_gate_unsafe_polluted` 均符合预期。
8. 回归结果确认第八轮 `tiny_nt_memevo_gate_verify.yaml` 未回归：`verification_passed_count=1`、`support_replay_helpful_count=2`、`active_memory_count=1`。
9. 回归结果确认 unsafe polluted 负迁移链路未回归：`negative_transfer_rate=1.0`、`harmful_memory_ids=["polluted_refund_lookup_policy_001"]`、`replay_harmful_count=1`、`quarantined_memory_count=1`。
10. 用户复验暴露一个日志可读性问题：`support_selection` 事件中的顶层 `task_id` 表示 source task，support task id 没有独立字段；编码侧已补充 `source_task_id` 和 `support_task_id` 字段，并重新运行 `PYTHONPATH=src python -m pytest -q`，结果为 `15 passed in 0.12s`。

当前边界：

1. 第九轮已把 support selection 审计、verification budget 和 scope refinement 最小路径接通，但 refined memory 仍是确定性规则派生，不是 learned split policy。
2. replay unique execution 口径已经落到 metrics，但当前仍是离线 tiny 验证，后续需要在真实 benchmark 上再校准成本统计。
3. `tiny_nt_memevo_gate_refine.yaml` 的 harmful support 是人工构造的 tiny mixed-support 场景，作用是验证日志和 lifecycle 机制，不代表真实 benchmark 难度。
4. tau-bench retail 接入仍未开始，下一轮可以在 support/refinement 日志稳定后接最小 adapter。

下一步建议：

1. 把同一套 support verification / scope refinement 日志迁移到 tau-bench retail 的最小 adapter，先让真实任务也能输出统一 `tasks/runs/trace/memory/replay/metrics` 文件。
2. 增加真实 benchmark 下的 support pool 构造与 replay budget 控制，避免 tiny fixture 的过拟合。
3. 后续再考虑 learned support selector、memory merge/split 策略和更严格的 unique-execution 成本去重。

## 第一阶段第十轮方向

优先方向：接入 tau-bench retail 的最小 adapter，并把现有 `none / raw_trace_rag / reflexion / nt_memevo_candidate / nt_memevo_gate` 日志协议迁移到真实工具任务。理由是第一阶段前九轮已经在 tiny 环境中跑通 candidate schema、risk gate、online utility、leave-one-memory-out replay、support-set verification 和 scope refinement；继续只扩 tiny fixture 会开始过拟合日志链路，下一步应让同一套机制面对真实 benchmark 的 task loader、tool API 和 evaluator。

第十轮建议范围：

1. 新增 tau-bench retail adapter 的最小入口：支持从本地 tau-bench 数据目录或配置路径加载 retail tasks，并转换为项目内 `Task`。
2. 封装 retail tool API wrapper，至少先支持离线 smoke 或小样本任务所需的 order/customer/product/policy 类工具调用。
3. 接入 evaluator：把 tau-bench 的终态评估或任务 reward 映射到 `success`、`reward`、`error_type`，保持现有 `runs.jsonl` 字段不变。
4. 新增 `configs/tau_retail_nomem.yaml` 的可运行 smoke；若外部数据未安装，应给出明确错误信息和安装路径提示，不破坏 tiny 测试。
5. 先跑极小任务数，例如 `max_tasks=1` 或 `max_tasks=3`，验证 `tasks.jsonl`、`runs.jsonl`、`trace_events.jsonl`、`metrics.json` 都能生成。
6. 保持第九轮 tiny 全部配置不回归，尤其是 `tiny_nt_memevo_gate_refine.yaml` 的 `memory_refinement_count=1` 和 unsafe polluted 的 `negative_transfer_rate=1.0`。
7. 若 tau-bench adapter 的外部依赖过重，本轮至少完成 adapter 接口、配置、错误提示、文档和跳过式测试；真实任务运行步骤写入实验日志，等待环境准备后复验。

## 2026-05-02 第一阶段第十轮

目标：接入 tau-bench retail 的最小 adapter，使项目不再只有 tiny fixture；先用本地 retail smoke split 跑通 `tasks/runs/trace/metrics` 统一日志，并为后续真实 tau-bench 数据路径预留清晰入口和错误提示。

已完成：

1. 重写 `src/ntmemevo/envs/tau_bench.py`，实现 `TauBenchEnv` 的 retail 最小 adapter，不强依赖外部 tau-bench 包。
2. 支持从本地 `.json`、`.jsonl`、`.py` task 文件加载 tau-bench retail 任务；也支持 `benchmark.task_module` 或已安装 tau-bench 包中的 task module。
3. 将 tau task record 统一转换为项目内 `Task`，保留 `benchmark=tau_bench`、`domain=retail`、`intent`、`tool_names`、`expected_actions` 和 `no_memory_success` 等 metadata。
4. 新增 retail DB loader，支持 `benchmark.data_file`、`benchmark.data_dir`，以及可选的 `tau_bench.envs.retail.data.load_data()`。
5. 新增 retail tool wrapper：`find_user_id_by_name_zip`、`find_user_id_by_email`、`get_user_details`、`get_order_details`、`get_product_details`、`list_all_product_types`、`lookup_policy`、`calculate`、`think`、`transfer_to_human_agents` 以及 pending/delivered order mutation 类工具的最小实现。
6. 新增 evaluator 映射：`evaluation=auto` 时优先使用 `expected_answer_contains`，否则可使用 `tool_sequence/action_sequence` 对比工具调用序列；统一返回 `success`、`reward` 和 `error_type`。
7. 扩展 `MockLLMClient`，支持 tau-retail smoke 任务中的 customer/order/product/policy 工具选择，使无 API key 环境也能跑通 tau adapter smoke。
8. 新增本地 smoke fixtures：`data/task_splits/tau_retail_smoke_tasks.json` 和 `data/tau_bench/retail_smoke_db.json`。
9. 更新 `configs/tau_retail_nomem.yaml`，默认运行本地 3 条 tau-retail smoke 任务，输出到 `runs/tau_retail_nomem_seed1/`。
10. 新增 `tests/test_tau_bench_adapter.py`，覆盖 tau-retail smoke pipeline、缺失 split 的明确错误提示、以及 action-sequence evaluator。
11. 更新 `README.md`，加入 tau-retail smoke 命令、本地 fixture 路径、真实 tau-bench 数据接入方式和下一阶段方向。
12. 新增实验日志模板，等待用户在目标 Linux + conda `rm` 环境完整复验后填写结果。

关键实现说明：

1. 第十轮没有引入 tau-bench 作为强依赖，避免破坏现有离线 tiny 测试；真实 tau-bench 数据可通过本地导出的 task/data 文件接入。
2. adapter 当前以 retail smoke 和小样本真实任务为目标，mutation 工具只实现最小状态更新和错误返回；官方复杂 evaluator 仍需在后续轮次对齐。
3. `evaluation=auto` 适合 smoke 和自然语言答案检查；真实 tau-bench 主实验建议在导出 expected actions 后使用 `evaluation=tool_sequence` 或接入官方 evaluator。
4. 缺失 `split_file` 或 `data_file/data_dir` 时会报出带 `benchmark.split_file`、`benchmark.data_file`、`benchmark.data_dir` 的明确错误，方便实验机配置。

验证记录：

1. `python -m py_compile src/ntmemevo/envs/tau_bench.py src/ntmemevo/llm/client.py` 通过。
2. `python -m pytest tests/test_tau_bench_adapter.py -q` 通过，结果为 `3 passed in 0.03s`。
3. `python -m pytest -q` 通过，结果为 `18 passed in 0.08s`。
4. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nomem.yaml` 成功。
5. tau-retail smoke 结果：`num_tasks=3`、`success_rate=1.0`、`avg_reward=1.0`、`avg_tool_calls=1.0`、`memory_policy=none`、`memory_size=0`、`negative_transfer_rate=0.0`、`verification_count=0`。

用户复验建议命令：

```bash
conda activate rm
pip install -e ".[dev]"
python -m pytest

python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nomem.yaml
cat runs/tau_retail_nomem_seed1/metrics.json
head -n 3 runs/tau_retail_nomem_seed1/tasks.jsonl
tail -n 3 runs/tau_retail_nomem_seed1/runs.jsonl
grep '"event_type": "tool_call"' runs/tau_retail_nomem_seed1/trace_events.jsonl
```

真实 tau-bench 数据接入建议：

1. 将真实 retail task split 导出为 JSON/JSONL/Python 文件，并在配置中设置：

```yaml
benchmark:
  name: tau_bench
  domain: retail
  split_file: /path/to/tau_retail_tasks.json
  data_file: /path/to/tau_retail_db.json
  evaluation: auto
  max_tasks: 1
```

2. 若已有已安装 tau-bench 包，可尝试：

```yaml
benchmark:
  name: tau_bench
  domain: retail
  task_module: tau_bench.envs.retail.tasks
  task_split: train
  data_dir: /path/to/retail_data_dir
  evaluation: tool_sequence
  max_tasks: 1
```

3. 先用 `max_tasks=1` 或 `max_tasks=3` 验证 `tasks.jsonl`、`runs.jsonl`、`trace_events.jsonl` 和 `metrics.json`，再扩展到 `none / raw_trace_rag / reflexion / nt_memevo_candidate / nt_memevo_gate` 小样本对照。

当前边界：

1. 本轮只完成 tau-bench retail 最小 adapter 和本地 smoke，不声称已经完整复现官方 tau-bench retail benchmark。
2. 官方 tau-bench 的复杂状态机、完整 retail tool semantics、policy violation evaluator 和终态 evaluator 尚未完全接入。
3. 当前 mock agent 只覆盖 smoke 任务的确定性工具选择；真实 tau-bench 任务需要 OpenAI/其他真实模型或更强的本地 actor。
4. 现有 NT-MemEvo gate/replay/verification 机制还没有在真实 tau-bench split 上跑完整对照；第十轮只是把真实 benchmark 入口和统一日志链路打通。

下一步建议：

1. 在目标实验机准备真实 tau-bench retail 数据，先跑 `max_tasks=1/3` 的 no-memory smoke，并把失败样例补充到 adapter 工具语义。
2. 把 `raw_trace_rag`、`reflexion`、`nt_memevo_candidate`、`nt_memevo_gate` 依次迁移到 tau-retail 小样本配置，确认日志字段不变。
3. 对齐官方 tau-bench evaluator，优先支持 action sequence / state diff / policy violation 三类评估。
4. 构造 tau-retail support pool，把第八/九轮 support verification 与 scope refinement 迁移到真实任务。

用户复验记录：

1. 用户在 Linux 机器 `BNUZ`、交互式 conda 环境 `(rm)` 下运行 `python -m pytest`，环境为 Python 3.12.13、pytest 9.0.3、pluggy 1.6.0，结果为 `18 passed in 0.10s`。
2. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nomem.yaml` 成功。
3. tau-retail smoke 指标为：`num_tasks=3`、`success_rate=1.0`、`avg_reward=1.0`、`avg_steps=2.0`、`avg_prompt_tokens=858.0`、`avg_completion_tokens=110.66666666666667`、`avg_tool_calls=1.0`。
4. no-memory / no-replay / no-verification 指标符合预期：`memory_policy=none`、`memory_size=0`、`memory_top_k=0`、`negative_transfer_rate=0.0`、`gate_decision_count=0`、`utility_update_count=0`、`replay_result_count=0`、`verification_count=0`。
5. 用户检查 `tasks.jsonl`，确认三条 smoke task 都带有 `metadata.benchmark=tau_bench`、`domain=retail`、`intent`、`tool_names`、`expected_actions` 和 `no_memory_success=true`。
6. 用户检查 `runs.jsonl`，确认三条任务均 `success=true`、`reward=1.0`、`tool_calls=1`、`used_memory_ids=[]`。
7. 用户检查 `trace_events.jsonl`，确认三条 `tool_call` 分别为 `find_user_id_by_name_zip`、`get_order_details` 和 `get_product_details`，且 `ok=true`。

第十轮结果分析：

1. tau-retail 最小 adapter 的核心验收通过：本地 task loader、retail DB wrapper、ReAct agent、evaluator 映射和统一日志协议可以在目标 Linux 环境中串起来。
2. 该结果只证明 smoke 级接入可用，不等同于官方 tau-bench retail 完整复现；当前任务数量为 3，且由 mock actor 的确定性规则解决。
3. `avg_prompt_tokens=858.0` 明显高于 tiny no-memory 的 `310.4`，说明真实工具环境的 tool description 成本已经开始显现；后续 tau-retail baseline 必须单独记录 token / tool cost。
4. `tasks.jsonl` 中已经保留 `intent`、`tool_names` 和 `expected_actions`，这对第十一轮迁移 gate / replay / support selection 是关键基础。
5. 第十轮没有触发 memory、gate、utility、replay 或 verification 字段，这是 no-memory smoke 的正常结果；下一轮需要验证这些字段在 tau-retail 小样本上是否仍按 tiny 协议写出。

第一阶段收口判断：

1. 代码主链已经基本具备收口条件：tiny 上的 memory evolution 闭环已覆盖 candidate schema、risk gate、online utility、leave-one-memory-out replay、support-set verification、scope refinement 和 unique-execution 成本统计；tau-retail adapter 也已通过 no-memory smoke。
2. 实验主链还不应立即收口，因为第十轮只跑了 tau-retail no-memory smoke，尚未证明 `raw_trace_rag`、`reflexion`、`nt_memevo_candidate` 和 `nt_memevo_gate` 在 tau-retail 任务上保持统一日志协议。
3. 按严格验收口径，第一阶段还需要 **2 轮** 编码与实验即可收口；若真实 tau-bench 数据暂不可用，第十二轮可以先以导出的本地小样本或更强错误提示作为阶段收口边界，但需要在日志中明确 blocker。

第一阶段剩余轮次方向：

1. 第一阶段第十一轮：tau-retail smoke 多 baseline 迁移。
   - 编码方向：新增 `configs/tau_retail_raw_trace_rag.yaml`、`configs/tau_retail_reflexion.yaml`、`configs/tau_retail_nt_memevo_candidate.yaml` 和 `configs/tau_retail_nt_memevo_gate.yaml`；必要时扩展 `CandidateMemoryExtractor` 对 tau-retail 工具名、intent 和 trace summary 的识别；新增测试覆盖 tau-retail memory 写入、检索、gate 决策和不破坏 tiny 回归。
   - 实验方向：在本地 smoke 上运行 `none / raw_trace_rag / reflexion / nt_memevo_candidate / nt_memevo_gate`，检查 `memories.jsonl`、`candidate_memories.jsonl`、`memory_updates.jsonl`、`runs.jsonl` 和 `metrics.json` 字段完整性。
   - 建议命令：

```bash
conda activate rm
pip install -e ".[dev]"
python -m pytest
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_raw_trace_rag.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_reflexion.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nt_memevo_candidate.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nt_memevo_gate.yaml
```

2. 第一阶段第十二轮：真实或导出 tau-bench retail 小样本收口。
   - 编码方向：对齐真实 tau-bench task/data 格式，补齐缺失 retail tool wrapper；若能拿到官方 evaluator，则接入 action sequence / state diff / policy violation 的最小映射；如果官方依赖不可用，则提供明确的 local export 规范和错误提示。
   - 实验方向：用 `max_tasks=1/3` 先跑 no-memory，再跑一个 memory baseline；验收重点不是成功率，而是 `tasks/runs/trace/memory/replay/metrics` 是否能稳定生成、失败是否可解释、tool/evaluator 缺口是否记录。
   - 建议命令模板：

```bash
conda activate rm
pip install -e ".[dev]"
python -m pytest
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_real_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_real_raw_trace_rag.yaml
cat runs/tau_retail_real_nomem_seed1/metrics.json
tail -n 5 runs/tau_retail_real_nomem_seed1/runs.jsonl
grep '"event_type": "tool_call"' runs/tau_retail_real_nomem_seed1/trace_events.jsonl
```

第一阶段最终收口标准：

1. `python -m pytest` 全量通过。
2. tiny 全部核心配置仍不回归，尤其是 `tiny_nt_memevo_gate_refine.yaml` 的 `memory_refinement_count=1` 和 unsafe polluted 的 `negative_transfer_rate=1.0`。
3. tau-retail smoke 至少覆盖 `none / raw_trace_rag / reflexion / nt_memevo_candidate / nt_memevo_gate` 五组配置，并生成统一日志。
4. 真实或导出的 tau-bench retail 小样本至少跑通 no-memory 与一个 memory baseline；若外部数据暂不可用，必须有明确 blocker、export schema 和复验命令。
5. `docs/coding_log.md` 与 `docs/experiment_log.md` 记录完整复验结果、失败边界和第二阶段入口。

## 2026-05-02 第一阶段第十一轮

目标：落实 tau-retail smoke 多 baseline 迁移，把第十轮只覆盖 no-memory 的本地 tau-retail adapter 扩展到 `raw_trace_rag`、`reflexion`、`nt_memevo_candidate` 和 `nt_memevo_gate`，并确认 memory / gate / metrics 日志协议在 tau-retail 小样本上不回归。

已完成：

1. 新增配置 `configs/tau_retail_raw_trace_rag.yaml`，在本地 tau-retail smoke split 上启用 Raw Trace RAG，输出目录为 `runs/tau_retail_raw_trace_rag_seed1/`。
2. 新增配置 `configs/tau_retail_reflexion.yaml`，在同一 smoke split 上启用 Reflexion baseline，输出目录为 `runs/tau_retail_reflexion_seed1/`。
3. 新增配置 `configs/tau_retail_nt_memevo_candidate.yaml`，在 tau-retail smoke 上写入结构化 candidate memory，输出目录为 `runs/tau_retail_nt_memevo_candidate_seed1/`。
4. 新增配置 `configs/tau_retail_nt_memevo_gate.yaml`，在 tau-retail smoke 上运行风险感知 gate，输出目录为 `runs/tau_retail_nt_memevo_gate_seed1/`。
5. 扩展 `CandidateMemoryExtractor`：优先使用 `task.metadata.intent`，使 tau-retail candidate scope 保留 `customer_lookup`、`order_lookup` 和 `product_lookup`；同时扩展 fallback intent 与 identifier 抽取，覆盖 customer/email/zip/product/return 等 retail 表达。
6. 扩展 `RetrieverGate`：优先使用 `task.metadata.intent` 做 precondition 匹配，避免 tau-retail smoke 中 customer/order/product 跨 intent 记忆被误注入；同时保持无 metadata 的 tiny fallback 仍使用旧的 `order_status`，不破坏第八/九轮 support verification。
7. 扩展 `MockLLMClient._decide_from_retrieved_memory()`，使 memory-hint 解析除 tiny tools 外也能识别 tau-retail smoke 工具，如 `find_user_id_by_name_zip`、`get_order_details` 和 `get_product_details`。
8. 扩展 `tests/test_tau_bench_adapter.py`：新增 tau-retail `raw_trace_rag`、`reflexion`、`nt_memevo_candidate` 三组 baseline 的 memory 写入/检索日志测试；新增 `nt_memevo_gate` 对跨 intent candidate 全部拒绝的 gate 日志测试。
9. 更新 `README.md`，加入 tau-retail 五组 smoke baseline 命令，并把下一轮方向收敛到真实或导出 tau-bench retail 小样本收口。
10. 更新 `docs/experiment_log.md` 第十一轮实验模板，等待用户在 Linux + conda `rm` 环境完成完整复验后填写实际结果。

关键实现说明：

1. tau-retail candidate scope 现在以 task metadata 为准；本地 smoke 三条任务分别生成 `customer_lookup`、`order_lookup` 和 `product_lookup`，不会被统一折叠成 `general_tool_use`。
2. `nt_memevo_gate` 在当前 smoke split 中没有 accepted path 是预期行为：三条任务 intent 不同，gate 应保守拒绝跨 intent candidate，防止 customer lookup 经验注入 order/product lookup。
3. raw/reflexion 的检索仍是词法 baseline，会在 smoke 第 2/3 个任务检索到历史轨迹或反思；mock actor 默认不跟随 memory hints，因此成功率保持 1.0，差异主要体现在 prompt token 成本。
4. 第十一轮没有启用 tau-retail replay、support verification 或 scope refinement；这些机制仍由 tiny 配置覆盖，tau-retail 上先验证五组 baseline 的统一日志协议。

验证记录：

1. `PYTHONPATH=src python -m pytest tests/test_tau_bench_adapter.py -q` 通过，结果为 `7 passed in 0.06s`。
2. `PYTHONPATH=src python -m pytest -q` 通过，结果为 `22 passed in 0.10s`。
3. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nomem.yaml` 成功：`num_tasks=3`、`success_rate=1.0`、`memory_policy=none`、`memory_size=0`、`avg_prompt_tokens=858.0`。
4. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_raw_trace_rag.yaml` 成功：`num_tasks=3`、`success_rate=1.0`、`memory_policy=raw_trace_rag`、`memory_size=3`、`memory_top_k=2`、`avg_prompt_tokens=1117.3333333333333`。
5. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_reflexion.yaml` 成功：`num_tasks=3`、`success_rate=1.0`、`memory_policy=reflexion`、`memory_size=3`、`memory_top_k=2`、`avg_prompt_tokens=1381.3333333333333`。
6. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nt_memevo_candidate.yaml` 成功：`num_tasks=3`、`success_rate=1.0`、`memory_policy=nt_memevo_candidate`、`memory_size=3`、`memory_top_k=0`、`candidate_memory_count=3`、`active_memory_count=0`。
7. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nt_memevo_gate.yaml` 成功：`num_tasks=3`、`success_rate=1.0`、`memory_policy=nt_memevo_gate`、`memory_size=3`、`memory_top_k=2`、`gate_decision_count=3`、`gate_accepted_count=0`、`gate_rejected_count=3`、`gate_rejection_reasons={"precondition_below_threshold": 3}`、`utility_update_count=0`。
8. 抽查 `runs/tau_retail_nt_memevo_candidate_seed1/candidate_memories.jsonl`，确认三条 candidate scope intent 分别为 `customer_lookup`、`order_lookup` 和 `product_lookup`，tool_names 分别对应 `find_user_id_by_name_zip`、`get_order_details`、`get_product_details`。
9. 抽查 `runs/tau_retail_nt_memevo_gate_seed1/memory_updates.jsonl`，确认 3 条 `gate_decision` 均为 `reject`，拒绝原因均为 `precondition_below_threshold`；三条主任务 `used_memory_ids=[]`。
10. 抽查 `runs/tau_retail_raw_trace_rag_seed1/memory_updates.jsonl`，确认存在逐轮 `retrieve` 与 `add` 事件，第三个任务检索到两条 raw trace memory。

用户复验建议命令：

```bash
conda activate rm
pip install -e ".[dev]"
python -m pytest

python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_raw_trace_rag.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_reflexion.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nt_memevo_candidate.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nt_memevo_gate.yaml

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

实验日志填写建议：

1. 新增 `tau_retail_multi_baseline_smoke_seed1` 或分别新增四个 tau-retail baseline 条目，记录五组配置的 `success_rate`、`memory_policy`、`memory_size`、`memory_top_k`、`avg_prompt_tokens`、`gate_decision_count` 和 `gate_rejection_reasons`。
2. 重点记录 token 成本趋势：`none=858.0`，`raw_trace_rag=1117.3333333333333`，`reflexion=1381.3333333333333`，candidate/gate 在未注入 memory 时与 none 一致。
3. 对 `tau_retail_nt_memevo_candidate_seed1`，记录 candidate scope intent 是否为 `customer_lookup/order_lookup/product_lookup`。
4. 对 `tau_retail_nt_memevo_gate_seed1`，记录 gate 全部拒绝跨 intent memory，说明第十一轮保守 gate 在真实工具任务 smoke 上未产生负迁移。

当前边界：

1. tau-retail 仍使用本地 3 条 smoke fixture，不代表官方 tau-bench retail 完整 benchmark。
2. 当前 smoke split 每个 intent 只出现一次，因此 `nt_memevo_gate` 只验证 cross-intent rejection，没有验证 tau-retail 同 intent accepted path、utility update、replay 或 verification。
3. raw/reflexion 的成功率不代表方法收益；mock actor 不依赖 memory 即可完成三条 smoke 任务，memory 主要用于验证日志字段和 token 成本。
4. 官方 tau-bench evaluator、复杂 mutation tools、policy violation、state diff 和真实 support pool 仍需第十二轮或第二阶段继续接入。

下一步建议：

1. 第一阶段第十二轮应接入真实或导出的 tau-bench retail 小样本，至少跑通 `tau_retail_real_nomem` 与一个 memory baseline。
2. 若真实数据暂不可用，应提供本地 export schema、示例任务字段、DB 文件结构、明确 blocker 和复验命令，作为第一阶段收口边界。
3. 对真实小样本优先补齐缺失工具和 evaluator 映射，不急于打开 replay / verification；先保证 `tasks/runs/trace/memory/metrics` 稳定生成。

用户复验记录：

1. 用户在 Linux 机器 `BNUZ`、交互式 conda 环境 `(rm)` 下运行 `python -m pytest`，环境为 Python 3.12.13、pytest 9.0.3、pluggy 1.6.0，结果为 `22 passed in 0.09s`。
2. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nomem.yaml`，结果为 `success_rate=1.0`、`avg_prompt_tokens=858.0`、`memory_policy=none`、`memory_size=0`、`negative_transfer_rate=0.0`、`gate_decision_count=0`。
3. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tau_retail_raw_trace_rag.yaml`，结果为 `success_rate=1.0`、`avg_prompt_tokens=1117.3333333333333`、`memory_policy=raw_trace_rag`、`memory_size=3`、`memory_top_k=2`、`negative_transfer_rate=0.0`。
4. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tau_retail_reflexion.yaml`，结果为 `success_rate=1.0`、`avg_prompt_tokens=1381.3333333333333`、`memory_policy=reflexion`、`memory_size=3`、`memory_top_k=2`、`negative_transfer_rate=0.0`。
5. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nt_memevo_candidate.yaml`，结果为 `success_rate=1.0`、`avg_prompt_tokens=858.0`、`memory_policy=nt_memevo_candidate`、`memory_size=3`、`memory_top_k=0`、`candidate_memory_count=3`、`active_memory_count=0`。
6. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tau_retail_nt_memevo_gate.yaml`，结果为 `success_rate=1.0`、`avg_prompt_tokens=858.0`、`memory_policy=nt_memevo_gate`、`memory_size=3`、`memory_top_k=2`、`gate_decision_count=3`、`gate_accepted_count=0`、`gate_rejected_count=3`、`gate_rejection_reasons={"precondition_below_threshold": 3}`、`negative_transfer_rate=0.0`。
7. 用户抽查 `runs/tau_retail_nt_memevo_candidate_seed1/candidate_memories.jsonl`，确认三条 candidate scope intent 分别为 `customer_lookup`、`order_lookup` 和 `product_lookup`，且 `positive_evidence`、`action_hint`、`preconditions` 与 smoke 任务匹配。
8. 用户抽查 `runs/tau_retail_nt_memevo_gate_seed1/memory_updates.jsonl`，确认 3 条 `gate_decision` 全部为 `reject`，拒绝原因均为 `precondition_below_threshold`，三条主任务 `used_memory_ids=[]`。
9. 用户抽查 `runs/tau_retail_raw_trace_rag_seed1/memory_updates.jsonl` 与 `runs/tau_retail_reflexion_seed1/memories.jsonl`，确认 raw trace 逐轮写入 `retrieve/add` 事件，reflexion 逐轮写入 3 条 `reflection_type=strategy` memory。

第一阶段收口方向（更新）：

1. tau-retail smoke baseline 已完成五组对照验收，后续不再扩展 smoke 级别的横向工作面。
2. 第一阶段的剩余唯一工作面是真实或导出的 tau-bench retail 小样本收口，要求至少跑通 `no-memory + 一个 memory baseline`，并稳定生成 `tasks.jsonl`、`runs.jsonl`、`trace_events.jsonl`、`memory` 和 `metrics`。
3. 如果真实 tau-bench retail 数据暂不可用，就把收口边界明确写成 local export schema、DB 文件要求、工具缺口和 blocker，不再继续增加 smoke fixture。

## 2026-05-03 第一阶段第十二轮与第一阶段收口

目标：落实真实或导出 tau-bench retail 小样本收口，把第十/十一轮文档中提到但仓库缺失的 `tau_retail_real_*` 配置、导出样例、schema 文档和可执行测试补齐；同时明确第一阶段结束边界和第二阶段入口。

已完成：

1. 新增版本化导出任务样例 `data/task_splits/tau_retail_export_sample_tasks.py`，使用 tau-bench-like Python literal task 格式，覆盖 `customer_lookup`、`order_lookup` 和 `product_lookup` 三条小样本任务。
2. 新增版本化导出 DB 样例 `data/tau_bench/retail_export_sample/db.json`，覆盖 `users`、`orders`、`products` 和 `policies`；样例中特意保留 `#W2378156` 形式的 order id，用于验证真实导出常见的井号前缀。
3. 新增 `configs/tau_retail_real_nomem.yaml`，默认读取导出样例、开启 `require_data=true` 与 `validate_export_schema=true`，输出到 `runs/tau_retail_real_nomem_seed1/`。
4. 新增 `configs/tau_retail_real_raw_trace_rag.yaml`，在同一导出样例上启用 `raw_trace_rag`，输出到 `runs/tau_retail_real_raw_trace_rag_seed1/`。
5. 扩展 `TauBenchEnv` 的导出 schema 校验：当 `benchmark.validate_export_schema=true` 时，任务文件为空、任务缺少 instruction、任务没有 expected answer/action、action 结构不可解析、DB 缺少非空 `users/orders/products` 都会在 agent loop 前抛出明确错误。
6. 扩展 retail DB 兼容性：`find_user_id_by_name_zip` 支持从 `address` / `shipping_address` 中读取嵌套 zip；order 工具支持 `W2378156` 与 `#W2378156` 两种 ID 形式互查。
7. 新增 `docs/tau_retail_export_schema.md`，写明 phase-one local export schema、任务字段别名、DB 文件结构、支持工具、配置方式、已知 blocker 和第二阶段缺口。
8. 扩展 `README.md`，加入第十二轮 `tau_retail_real_nomem` / `tau_retail_real_raw_trace_rag` 命令、导出样例路径、`validate_export_schema` 说明和 schema 文档入口。
9. 扩展 `tests/test_tau_bench_adapter.py`，新增导出 `.py` task + `data_dir` 加载、嵌套 zip、`#order_id` 兼容、real/export raw-trace pipeline、schema validation 错误提示等测试。
10. 更新 `docs/experiment_log.md`，新增 `tau_retail_real_export_sample_seed1` 实验模板，等待用户在 Linux + conda `rm` 环境完整复验后填写实际结果。

关键实现说明：

1. 第十二轮仍不把外部 tau-bench 包设为强依赖；真实数据可以通过本地 `.json`、`.jsonl`、`.py` task 文件和 `data_file` / `data_dir` 接入。
2. `validate_export_schema` 默认关闭，避免影响第十/十一轮宽松 smoke 与外部 task_module 入口；第十二轮 real/export 配置显式打开它，用作阶段收口的可复现性防线。
3. 当前 real/export 样例仍是小样本，不声称完整复现官方 tau-bench retail；它的作用是固定本项目接受的本地导出格式，并保证用户没有官方数据时也能复验第一阶段收口命令。
4. 官方 state diff evaluator、policy violation evaluator、完整 mutation semantics、真实模型 actor、真实 support pool 和 tau-retail replay/verification 仍属于第二阶段。

验证记录：

1. `python -m py_compile src/ntmemevo/envs/tau_bench.py` 通过。
2. `python -m pytest tests/test_tau_bench_adapter.py -q` 通过，结果为 `10 passed in 0.06s`。
3. `python -m pytest -q` 通过，结果为 `25 passed in 0.10s`。
4. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_real_nomem.yaml` 成功：`num_tasks=3`、`success_rate=1.0`、`avg_prompt_tokens=851.6666666666666`、`memory_policy=none`、`memory_size=0`、`negative_transfer_rate=0.0`。
5. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_real_raw_trace_rag.yaml` 成功：`num_tasks=3`、`success_rate=1.0`、`avg_prompt_tokens=1096.3333333333333`、`memory_policy=raw_trace_rag`、`memory_size=3`、`memory_top_k=2`、`negative_transfer_rate=0.0`。
6. 抽查 `runs/tau_retail_real_nomem_seed1/tasks.jsonl`，确认三条导出样例任务均保留 `metadata.benchmark=tau_bench`、`domain=retail`、`intent`、`tool_names`、`expected_actions` 和 `no_memory_success=true`。
7. 定向测试确认 `find_user_id_by_name_zip` 可读取嵌套 `address.zip`，`get_order_details({"order_id": "W2378156"})` 可命中 DB 中的 `#W2378156`。

用户复验建议命令：

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

真实数据替换步骤：

1. 按 `docs/tau_retail_export_schema.md` 导出真实 tau-bench retail 小样本任务和 DB。
2. 复制 `configs/tau_retail_real_nomem.yaml`，把 `benchmark.split_file` 指向真实 task export，把 `benchmark.data_file` 或 `benchmark.data_dir` 指向真实 retail DB。
3. 先设置 `max_tasks=1`，跑 no-memory，确认 `tasks/runs/trace/metrics` 都生成且失败可解释。
4. 再复制 `configs/tau_retail_real_raw_trace_rag.yaml`，用相同 task/data 跑一个 memory baseline。
5. 如果失败来自缺失工具语义、官方 evaluator 差异或 state mutation 语义不一致，记录为第二阶段 adapter blocker，不在第一阶段继续扩大 smoke fixture。

第一阶段最终收口判断：

1. 代码收口标准已达成：tiny 上完整覆盖 candidate schema、gate、online utility、leave-one-memory-out replay、support verification、scope refinement 和 replay cost；tau-retail 上覆盖 smoke 五 baseline，并补齐 real/export 小样本入口。
2. 实验收口标准可由用户按上方命令完成复验：`python -m pytest`、tau-retail smoke 五 baseline、`tau_retail_real_nomem` 与 `tau_retail_real_raw_trace_rag`。
3. 若用户后续有官方 tau-bench retail 数据，第一阶段不再新增方法逻辑，只按 export schema 替换路径复验；真实失败样例进入第二阶段 adapter/evaluator 对齐。
4. 第二阶段入口应聚焦真实 tau-bench retail 支持：官方 evaluator/state diff/policy violation、真实 actor、tau-retail support pool、真实任务上的 gate accepted path 与 replay/verification budget。

用户复验记录：

1. 用户在 Linux 机器 `BNUZ`、交互式 conda 环境 `(rm)` 下运行 `python -m pytest`，环境为 Python 3.12.13、pytest 9.0.3、pluggy 1.6.0，结果为 `25 passed in 0.08s`。
2. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tau_retail_real_nomem.yaml`，结果为 `num_tasks=3`、`success_rate=1.0`、`avg_prompt_tokens=851.6666666666666`、`memory_policy=none`、`memory_size=0`、`negative_transfer_rate=0.0`。
3. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tau_retail_real_raw_trace_rag.yaml`，结果为 `num_tasks=3`、`success_rate=1.0`、`avg_prompt_tokens=1096.3333333333333`、`memory_policy=raw_trace_rag`、`memory_size=3`、`memory_top_k=2`、`negative_transfer_rate=0.0`。
4. 用户抽查 `runs/tau_retail_real_nomem_seed1/tasks.jsonl`，确认三条 task 都包含 `metadata.benchmark=tau_bench`、`domain=retail`、`intent`、`tool_names`、`expected_actions` 和 `no_memory_success=true`。
5. 用户抽查 `runs/tau_retail_real_nomem_seed1/runs.jsonl`，确认三条任务均 `success=true`、`reward=1.0`、`tool_calls=1`、`used_memory_ids=[]`。
6. 用户抽查 `runs/tau_retail_real_nomem_seed1/trace_events.jsonl`，确认 tool call 覆盖 `find_user_id_by_email`、`get_order_details` 和 `get_product_details`，且 `ok=true`；其中 `get_order_details({"order_id": "W2378156"})` 成功命中 DB 中的 `#W2378156`。
7. 用户抽查 `runs/tau_retail_real_raw_trace_rag_seed1/memories.jsonl`，确认生成 3 条 raw trace memory。
8. 用户抽查 `runs/tau_retail_real_raw_trace_rag_seed1/memory_updates.jsonl`，确认第 1 轮空检索，第 2 轮检索到 `raw_000001_tau_retail_0001`，第 3 轮检索到 `raw_000002_tau_retail_0002` 和 `raw_000001_tau_retail_0001`。
9. 用户运行 `configs/tiny_nt_memevo_gate_refine.yaml`，确认 `memory_refinement_count=1`、`memory_split_count=1`、`support_replay_helpful_count=2`、`support_replay_harmful_count=2`、`active_memory_count=1`、`quarantined_memory_count=1`。
10. 用户运行 `configs/tiny_nt_memevo_gate_unsafe_polluted.yaml`，确认 `success_rate=0.0`、`negative_transfer_rate=1.0`、`harmful_memory_ids=["polluted_refund_lookup_policy_001"]`、`replay_harmful_count=1`、`quarantined_memory_count=1`。
11. 用户回归 tau-retail smoke 五 baseline，确认 `tau_retail_nomem`、`tau_retail_raw_trace_rag`、`tau_retail_reflexion`、`tau_retail_nt_memevo_candidate` 和 `tau_retail_nt_memevo_gate` 均通过。
12. 用户检查 `runs/tau_retail_nt_memevo_gate_seed1/metrics.json`，确认 `gate_accepted_count=0`、`gate_rejected_count=3`、`gate_rejection_reasons={"precondition_below_threshold": 3}`。

## 第一阶段工作总结

### 阶段目标

第一阶段目标是把 NT-MemEvo 从研究方案落成可复现的最小实验系统：先在离线 tiny benchmark 上跑通负迁移感知记忆自进化闭环，再把同一套日志协议迁移到 tau-bench retail 的 smoke 与 real/export 小样本入口。第一阶段不追求官方 tau-bench 完整复现或真实模型效果，而是优先保证方法链路、日志字段、回归测试和复验命令稳定。

### 已完成能力

1. 基础实验骨架：`run_stream` 统一入口、config loader、ReAct tool agent、mock actor、run/trace/memory/metrics 日志。
2. Baseline：`none`、`raw_trace_rag`、`reflexion` 三组基础对照已统一为在线任务流协议。
3. 结构化候选记忆：`CandidateMemory` schema 覆盖 scope、evidence、utility、lifecycle 和 source。
4. 风险感知 gate：基于 similarity、precondition、utility、risk、age 和 cost 的 deterministic RetrieverGate，并完整记录 `gate_decision`。
5. 负迁移检测：污染 memory fixture、safe polluted rejection、unsafe polluted ablation、`negative_transfer_rate`、`harmful_memory_ids` 和 failure examples。
6. Online utility update：对被实际注入的 candidate memory 更新 `alpha/beta/num_used/num_helpful/num_harmful/mean_delta_reward/lcb_delta_reward`，并支持 active/quarantined 最小生命周期迁移。
7. Leave-one-memory-out replay：对实际注入 memory 做局部反事实归因，输出 `replay_results.jsonl`，并支持 replay-backed utility update。
8. Support-set verification：基于 support pool 做 matched replay，输出 `verification_update`，使 candidate promotion 可以由 support evidence 决定。
9. Scope refinement / split：在 mixed support evidence 下生成 refined child memory，并把 parent quarantine，输出 `memory_refine` 事件。
10. Replay cost accounting：记录 record-level 与 unique-execution prompt/completion/tool call 成本。
11. tau-retail adapter：支持本地 JSON/JSONL/Python task export、`data_file` / `data_dir` DB、最小 retail tool wrapper、answer/action evaluator 映射和统一日志。
12. tau-retail smoke baseline：`none/raw_trace_rag/reflexion/nt_memevo_candidate/nt_memevo_gate` 五组全部通过。
13. tau-retail real/export sample：补齐 `tau_retail_real_nomem` 和 `tau_retail_real_raw_trace_rag`，并提供 `docs/tau_retail_export_schema.md`。

### 最终验收矩阵

| 验收项 | 状态 | 证据 |
| --- | --- | --- |
| 全量测试 | 通过 | `python -m pytest` 为 `25 passed in 0.08s` |
| tiny refinement | 通过 | `memory_refinement_count=1`，`memory_split_count=1` |
| tiny unsafe polluted | 通过 | `negative_transfer_rate=1.0`，污染记忆进入 `quarantined` |
| tau-retail smoke 五 baseline | 通过 | 五组 success_rate 均为 `1.0`，日志字段完整 |
| tau-retail gate conservative rejection | 通过 | `gate_accepted_count=0`，`gate_rejected_count=3` |
| tau-retail real/export no-memory | 通过 | `success_rate=1.0`，`memory_policy=none` |
| tau-retail real/export memory baseline | 通过 | `raw_trace_rag` 生成 3 条 memory，逐轮 retrieve 正常 |
| export schema 文档 | 完成 | `docs/tau_retail_export_schema.md` |

### 关键实验结论

1. tiny 上的核心方法闭环稳定：有益 memory 可被 replay/support evidence 推动到 active；混合 evidence 可触发 refinement；有害污染 memory 可被 unsafe ablation 归因为 harmful 并 quarantine。
2. tau-retail smoke 上的五组 baseline 日志协议稳定：Raw Trace RAG 与 Reflexion 会增加 prompt token 成本，candidate-only 与 gate 未注入 memory 时成本接近 no-memory。
3. tau-retail gate 在 smoke split 中全部拒绝跨 intent memory，这是预期行为；当前 smoke split 每个 intent 只出现一次，因此它验证的是 conservative rejection，不是 accepted path。
4. real/export sample 证明第一阶段可以在无需官方 tau-bench 运行时依赖的情况下加载 tau-like task/data，并稳定生成 `tasks/runs/trace/memory/metrics`。
5. real/export sample 的成功率不代表方法收益，也不代表官方 tau-bench retail 完整复现；它只作为第一阶段可复现收口边界。

### 当前边界

1. 官方 tau-bench retail 的完整 state machine、mutation semantics、policy violation 和 state diff evaluator 尚未对齐。
2. 当前 tau-retail actor 仍是 deterministic mock；真实复杂任务需要 OpenAI/其他真实模型或更强本地 actor。
3. tau-retail 上尚未构造真实 support pool，也未在真实任务上启用 gate accepted path、utility update、replay 或 verification。
4. RetrieverGate、support selector 和 scope refinement 仍是 deterministic heuristic，不是 learned ranker / learned split policy。
5. replay attribution 目前主要基于 reward/success，尚未细分 policy violation 类型、工具路径差异和答案差异。

### 第二阶段入口

第二阶段不应继续扩本地 smoke fixture；应把第一阶段稳定协议迁移到真实 tau-bench retail：

1. 准备真实 tau-bench retail task/data export，先用 `max_tasks=1/3` 复验 no-memory 与一个 memory baseline。
2. 对齐官方 evaluator：action sequence、state diff、policy violation 和终态 reward。
3. 补齐真实 retail mutation tools 的状态更新语义。
4. 接入真实 actor，固定 temperature、seed/cache 和预算。
5. 构造 tau-retail support pool，迁移 support verification、scope refinement 和 replay budget。
6. 在真实任务上报告 negative transfer rate、cost-adjusted reward、gate acceptance/rejection、utility lifecycle 和 replay/verification 成本。

## 2026-05-03 第二阶段总体方向与第一轮编码入口

本节用于在第一阶段正式收口后，进入第二阶段编码和实验前，明确下一阶段的工作重心。当前系统环境按用户说明固定为 Linux，交互式 conda 环境为 `conda activate rm`，Python 版本为 3.12。

### 当前项目状态判断

第一阶段已经完成的是“方法闭环与日志协议稳定性”，不是“官方 tau-bench retail 完整实验结论”。因此第二阶段的起点应按下面边界理解：

1. `tiny_tools` 上已经跑通 NT-MemEvo 的核心闭环：结构化 candidate memory、RetrieverGate、污染记忆负迁移检测、online utility update、leave-one-memory-out replay、support-set verification、scope refinement / split 和记忆生命周期迁移。
2. tau-retail smoke 上已经验证五组 baseline 的统一日志协议：`none`、`raw_trace_rag`、`reflexion`、`nt_memevo_candidate` 和 `nt_memevo_gate`。
3. tau-retail real/export sample 已经跑通 `no-memory + raw_trace_rag`，并补齐 `docs/tau_retail_export_schema.md`，说明本项目可以加载本地 tau-like task/data 并稳定生成 `tasks/runs/trace/memory/metrics`。
4. 现有 tau-retail 成功率主要来自 deterministic mock actor 和小样本 export，不代表真实模型或官方 benchmark 上的方法收益。
5. 当前最大风险不在 memory schema 或 gate/replay 日志，而在真实 tau-bench retail 的 evaluator/state/tool 语义尚未与官方对齐。如果不先解决这一层，后续真实模型和方法对照的 reward 都不可解释。

### 第二阶段总目标

第二阶段目标应从“控制环境中证明链路可运行”转为“在真实 tau-bench retail 语义上做可解释、可复现、可对照的负迁移实验”。建议阶段目标拆成五条主线：

1. **官方语义对齐**：把 tau-retail adapter 从小样本兼容提升到真实任务可用，重点覆盖 action sequence、state diff、policy violation、终态 reward、任务级 DB reset 和 mutation tool semantics。
2. **真实 actor 接入**：在保持 mock 回归的同时接入真实模型 actor，固定 `temperature=0`、seed、cache、预算和失败重试策略，保证 replay/verification 成本可控。
3. **真实任务 support pool**：从真实 tau-retail train/dev export 中构造 support pool，使 tiny 上已经验证的 support verification、scope refinement 和 replay budget 能迁移到真实 retail intent。
4. **方法对照矩阵**：在相同 task split、actor、budget 和日志协议下比较 `none/raw_trace_rag/reflexion/nt_memevo_candidate/nt_memevo_gate`，再逐步打开 replay、verification、refinement 消融。
5. **负迁移分析**：从总体成功率扩展到 `negative_transfer_rate`、`with_memory_fail_no_memory_success`、`harmful_memory_ids`、gate rejection reason、utility lifecycle、replay/support 成本和错误类型分布。

第二阶段明确不建议继续扩大本地 smoke fixture，也不建议立刻做 learned ranker、SWE-bench、WebArena 或大规模多域扩展。第一轮应先把真实 tau-retail evaluator/state 语义打牢。

### 第二阶段第一轮编码方向

第一轮编码优先方向：**tau-bench retail evaluator/state/tool 语义对齐的最小闭环**。

理由：第一阶段已经证明 memory 方法链路能运行；第二阶段若直接接真实模型或打开 NT-MemEvo replay/verification，会把 adapter/evaluator 错误、模型错误和记忆负迁移混在一起。第一轮应先让 no-memory 在真实或导出 tau-retail 小样本上的失败可解释，并让 `metrics.json` 与日志能区分答案错误、工具路径错误、状态差异和 policy violation。

建议编码范围：

1. 扩展 `src/ntmemevo/envs/tau_bench.py` 的任务级状态管理：保留初始 DB 快照，每个任务运行前使用独立 working DB，避免 mutation task 的状态泄漏到后续任务；在 evaluation 后生成最小 `state_diff_summary`。
2. 扩展 evaluator 模式：在现有 `answer_contains` / `action_sequence` 基础上，增加或预留 `state_diff`、`policy_violation` 和 `official_like` 路径；`evaluation=auto` 应能报告实际采用了哪种 evaluator。
3. 强化 action comparison：对 expected action 的 tool name、关键 args、ID 规范化、列表顺序和可选字段做可解释比较；失败时输出 `expected_action_sequence_mismatch` 的细分原因，而不是只返回一个总错误。
4. 补齐 mutation tool 的最小真实语义：优先覆盖 `cancel_pending_order`、`return_delivered_order_items`、`exchange_delivered_order_items`、`modify_pending_order_address/payment/items` 的状态更新、前置条件失败和 observation 文本。
5. 扩展日志字段：在 `runs.jsonl` 或 `memory_updates.jsonl` 之外新增可追踪的 evaluator detail，至少记录 `evaluation_mode`、`state_diff_passed`、`policy_violation_count`、`expected_actions_matched`、`tool_semantic_error_count` 和失败摘要。若要改 `AgentResult`，需保持现有测试和第一阶段日志字段不回归。
6. 新增 phase-two 小样本 fixture 或 export sample：覆盖至少 1 个只读任务、1 个 pending-order mutation 成功任务、1 个 policy/precondition 失败任务；这些 fixture 只用于 evaluator/state 对齐，不再扩大 smoke baseline 的方法结论。
7. 新增配置：建议命名为 `configs/tau_retail_phase2_state_nomem.yaml` 和可选 `configs/tau_retail_phase2_state_raw_trace_rag.yaml`，默认 `max_tasks=3`、`validate_export_schema=true`、`models.actor.provider=mock`。
8. 新增测试：覆盖任务间 DB reset、action args 规范化、state diff 成功/失败、policy violation 失败、mutation tool state update、旧的 25 个第一阶段测试不回归。

第一轮暂不建议实现：

1. 不接 learned gate/ranker。
2. 不扩大到 airline/SWE/WebArena。
3. 不在真实任务上默认打开 support verification/refinement；这些等 evaluator/state 语义稳定后再迁移。
4. 不把真实模型结果作为第一轮验收主指标；真实 actor 可作为第二轮或第一轮后的可选 smoke。

### 第一轮验收标准

第一轮完成后，应满足：

1. `conda activate rm` 后运行 `python -m pytest` 全量通过。
2. 第一阶段核心回归仍通过：`tiny_nt_memevo_gate_refine.yaml` 保持 `memory_refinement_count=1`，`tiny_nt_memevo_gate_unsafe_polluted.yaml` 保持 `negative_transfer_rate=1.0`。
3. `tau_retail_real_nomem.yaml` 与 `tau_retail_real_raw_trace_rag.yaml` 不回归。
4. 新增 phase-two state/evaluator config 至少跑通 no-memory，且日志能明确指出每个任务采用的 evaluator、是否通过 state diff、是否产生 policy violation。
5. 若真实 tau-bench retail export 接入失败，失败必须落到明确类别：缺失工具语义、expected action schema 不兼容、state diff 字段缺失、policy evaluator 不一致、actor 工具调用错误或数据导出不完整。

### 第一轮后的实验方向

第一轮编码通过后，实验侧应先做小规模真实语义复验：

1. 在 phase-two state/evaluator 小样本上运行 no-memory，确认失败可解释。
2. 在同一任务上运行 raw-trace-rag，只验证 memory 写入/检索和 token 成本，不声称收益。
3. 替换为真实 tau-bench retail export，先 `max_tasks=1`，再 `max_tasks=3`。
4. 只有当 no-memory 的 reward/evaluator 可解释后，再接真实 actor 或打开 `nt_memevo_gate`。
5. 将每次真实数据失败样例最小化保存，并记录到 `docs/experiment_log.md`，作为第二阶段 adapter/evaluator 对齐材料。

## 2026-05-03 第二阶段第一轮

目标：落实 tau-bench retail evaluator/state/tool 语义对齐的最小闭环，使 no-memory 在带 mutation / policy precondition 的 tau-retail 小样本上能输出可解释的 evaluator detail，而不是只给笼统的 answer mismatch。

已完成：

1. 扩展 `TauBenchEnv` 任务级状态管理：新增 `start_task()`，每个任务运行前从初始 DB 深拷贝出独立 working DB，避免 mutation task 状态泄漏到后续任务。
2. 扩展 `AgentResult` 和 `RunLogger`：新增 `evaluation_details`，写入 `runs.jsonl`，保留 `evaluation_mode`、action/state/policy/tool semantic 细节。
3. 扩展 tau-retail evaluator：新增 `state_diff`、`policy_violation` 和 `official_like` 模式；`auto` 现在会记录实际采用的 evaluator mode。
4. 强化 action comparison：支持 `compare_action_args=true`、order id `#` 规范化、ID 字段大小写归一、list 参数顺序无关比较、`optional_args` / `ignore_args` 和细分 mismatch reason。
5. 补齐 mutation tool 最小语义：`cancel_pending_order` 会更新状态和 `cancel_reason`；`return_delivered_order_items` / `exchange_delivered_order_items` 会检查 delivered 前置条件、item/product 存在性并更新 order/item 状态；`modify_pending_order_address/payment/items` 使用稳定 tool name 并更新对应字段。
6. 新增最小 state diff evaluator：支持 `expected_state_diff` / `state_diff` / `expected_db_state`，输出 `state_diff_summary` 和 `state_diff_mismatches`。
7. 新增 policy/precondition failure 记录：mutation tool 的 `ok=false` 会进入 `policy_violations`，metrics 汇总 `policy_violation_count` 和 `tool_semantic_error_count`。
8. 扩展 `MockLLMClient`：支持 tau-retail cancel / return / exchange mutation tool 决策，并修正 retail order id 抽取，避免把 `item_pend_1` 误识别为 order id。
9. 新增 phase-two fixture：`data/task_splits/tau_retail_phase2_state_tasks.py` 和 `data/tau_bench/retail_phase2_state/db.json`，覆盖 1 个只读 order lookup、1 个 pending cancel 成功任务、1 个 pending return precondition failure 任务。
10. 新增配置 `configs/tau_retail_phase2_state_nomem.yaml` 和 `configs/tau_retail_phase2_state_raw_trace_rag.yaml`。
11. 新增/扩展测试：任务间 DB reset、action args normalization、state diff success、policy violation failure、phase-two no-memory evaluator detail、phase-two raw-trace-rag 日志，以及第一阶段 tau adapter 回归。
12. 更新 `README.md`、`docs/tau_retail_export_schema.md` 和 `docs/experiment_log.md` 的 phase-two 命令、schema 与实验模板字段。

关键实现说明：

1. `env.evaluate()` 的三元组接口保持不变；tau-retail evaluator detail 通过 `env.last_evaluation_detail` 暴露给 agent，因此 tiny 和现有 memory/replay 代码不需要改接口。
2. `official_like` 是本地 adapter 的可解释近似，不等价于官方 tau-bench evaluator；它用于第二阶段第一轮定位 action/state/policy/tool 语义缺口。
3. phase-two fixture 中第三个任务故意失败：mock actor 对 pending order 调用 return-delivered 工具，工具返回 precondition failure，`runs.jsonl` 中 `error_type=policy_violation`，用于验证失败是否可解释。
4. 新增 metrics 字段包括 `evaluation_modes`、`state_diff_evaluated_count`、`state_diff_passed_count`、`state_diff_failed_count`、`expected_actions_evaluated_count`、`expected_actions_matched_count`、`expected_actions_failed_count`、`policy_violation_count`、`tool_semantic_error_count` 和 `evaluator_error_types`。

验证记录：

1. `python -m pytest tests/test_tau_bench_adapter.py -q` 通过，结果为 `14 passed in 0.06s`。
2. `python -m pytest -q` 通过，结果为 `29 passed in 0.11s`。
3. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_nomem.yaml` 成功：`num_tasks=3`、`success_rate=0.6666666666666666`、`evaluation_modes={"official_like": 3}`、`state_diff_passed_count=1`、`expected_actions_matched_count=3`、`policy_violation_count=1`、`tool_semantic_error_count=1`、`memory_policy=none`。
4. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_raw_trace_rag.yaml` 成功：`num_tasks=3`、`success_rate=0.6666666666666666`、`memory_policy=raw_trace_rag`、`memory_size=3`、`memory_top_k=2`、`policy_violation_count=1`。
5. 第一阶段核心回归通过：`tiny_nt_memevo_gate_refine.yaml` 保持 `memory_refinement_count=1`、`memory_split_count=1`、`support_replay_helpful_count=2`、`support_replay_harmful_count=2`；`tiny_nt_memevo_gate_unsafe_polluted.yaml` 保持 `negative_transfer_rate=1.0`、`replay_harmful_count=1`、`quarantined_memory_count=1`。
6. `tau_retail_real_nomem.yaml` 未回归：`success_rate=1.0`、`evaluation_modes={"answer_contains": 3}`、`expected_actions_matched_count=3`、`policy_violation_count=0`。
7. `tau_retail_real_raw_trace_rag.yaml` 未回归：`success_rate=1.0`、`memory_policy=raw_trace_rag`、`memory_size=3`、`memory_top_k=2`、`policy_violation_count=0`。
8. 抽查 `runs/tau_retail_phase2_state_nomem_seed1/runs.jsonl`：cancel 任务包含 `state_diff_summary.orders["#PEND2001"].status before=pending after=cancelled`；precondition failure 任务包含 `error_type=policy_violation`、`policy_violation_count=1` 和 `tool_semantic_errors`。

用户复验记录：

1. 用户在 Linux 机器 `BNUZ` 的 `(base)` 环境下运行 `python -m pytest`，环境显示 Python 3.12.7、pytest 7.4.4、pluggy 1.0.0，结果为 `29 passed in 0.09s`。
2. 用户随后在 `(base)` 下运行六条 `python -m ntmemevo.experiments.run_stream ...` 命令，全部失败，错误均为 `ModuleNotFoundError: No module named 'ntmemevo'`。
3. 该失败属于环境/安装问题，不是代码回归：pytest 通过依赖 `pyproject.toml` 中的 `pythonpath=["src"]`，但直接 `python -m ntmemevo...` 需要当前 Python 环境安装 editable package 或设置 `PYTHONPATH=src`。
4. 因 run_stream 命令未真正执行，本轮用户侧尚未完成正式实验复验；后续 `cat/tail/grep` 抽查的是已有 `runs/tau_retail_phase2_state_*` artifacts。
5. 用户抽查现有 `runs/tau_retail_phase2_state_nomem_seed1/metrics.json`，指标与编码侧 smoke 一致：`num_tasks=3`、`success_rate=0.6666666666666666`、`evaluation_modes={"official_like": 3}`、`state_diff_passed_count=1`、`expected_actions_matched_count=3`、`policy_violation_count=1`、`tool_semantic_error_count=1`、`memory_policy=none`。
6. 用户抽查现有 `runs/tau_retail_phase2_state_nomem_seed1/runs.jsonl`，确认 read 任务成功、cancel 任务 `state_diff_passed=true` 且记录 `#PEND2001` 从 pending 到 cancelled，policy failure 任务 `error_type=policy_violation` 且 `policy_violation_count=1`。
7. 用户抽查现有 `trace_events.jsonl`，确认 `get_order_details` 与 `cancel_pending_order` 为 `ok=true`，`return_delivered_order_items` 对 pending order 为 `ok=false`。
8. 用户抽查现有 `runs/tau_retail_phase2_state_raw_trace_rag_seed1/metrics.json`，指标与编码侧 smoke 一致：`success_rate=0.6666666666666666`、`memory_policy=raw_trace_rag`、`memory_size=3`、`memory_top_k=2`、`policy_violation_count=1`。
9. 用户抽查现有 `raw_trace_rag` 的 `memories.jsonl` 和 `memory_updates.jsonl`，确认 3 条 raw trace memory 写入，逐轮 retrieve 正常。
10. 正式复验待补：需要在 `conda activate rm` 后执行 `pip install -e ".[dev]"`，再重新运行六条 run_stream 命令；或者临时使用 `PYTHONPATH=src python -m ntmemevo.experiments.run_stream ...`。

用户复验建议命令：

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

cat runs/tau_retail_phase2_state_nomem_seed1/metrics.json
tail -n 3 runs/tau_retail_phase2_state_nomem_seed1/runs.jsonl
grep '"event_type": "tool_call"' runs/tau_retail_phase2_state_nomem_seed1/trace_events.jsonl

cat runs/tau_retail_phase2_state_raw_trace_rag_seed1/metrics.json
head -n 3 runs/tau_retail_phase2_state_raw_trace_rag_seed1/memories.jsonl
grep '"event_type": "retrieve"' runs/tau_retail_phase2_state_raw_trace_rag_seed1/memory_updates.jsonl
```

实验日志填写建议：

1. 在 `second_stage_round1_plan_2026_05_03` 表格中补齐 `tau_retail_phase2_state_nomem.yaml` 和 `tau_retail_phase2_state_raw_trace_rag.yaml` 的实际结果。
2. 重点记录 `success_rate=0.6666666666666666` 是预期现象：第三个任务故意触发 pending order return 的 policy/precondition failure，用于验证失败可解释。
3. 抽查 `runs.jsonl` 的 `evaluation_details`，记录 cancel 任务的 `state_diff_passed=true` 和 policy failure 任务的 `error_type=policy_violation`。
4. 若替换真实 tau-retail export，先 `max_tasks=1`；失败时记录是 action schema、state diff、policy evaluator、tool semantic 还是 actor 工具调用问题。

当前边界：

1. `official_like` 仍不是官方 tau-bench evaluator，只是本项目第二阶段用于语义对齐的本地可解释路径。
2. mutation tools 只覆盖最小状态更新和前置条件，不包含官方完整 refund/exchange/payment/shipping state machine。
3. phase-two fixture 是语义对齐 harness，不用于报告方法收益；真实实验仍需替换为官方或导出的 tau-retail task/data。
4. 第二阶段第一轮未打开 `nt_memevo_gate`、replay、support verification 或真实 actor；这些应等 no-memory reward 可解释后再迁移。

下一步建议：

1. 先完成运行环境修正与正式复验：在 `conda activate rm` 下执行 `pip install -e ".[dev]"`，确认 `python -m ntmemevo.experiments.run_stream ...` 不再报 `ModuleNotFoundError`。
2. 正式复验六条命令后，再用真实 tau-bench retail export 替换 phase-two fixture，先跑 `max_tasks=1` 的 no-memory。
3. 对比本地 `evaluation_details` 与官方 reward / state diff / policy violation，逐项补工具语义或 evaluator schema。
4. 在 no-memory 失败可解释后，再跑同一真实 export 的 `raw_trace_rag`，只验证 memory 日志和 token 成本。
5. 真实 actor 和 `nt_memevo_gate` 应作为第二阶段第二轮或第一轮后的附加 smoke，不作为本轮主验收。

## 第二阶段第二轮方向（更新）

第二阶段第二轮应以“真实 tau-retail export 小批量语义对齐”为主，但前置条件是第二阶段第一轮 run_stream 命令在目标环境中完成正式复验。

前置修正：

1. 确认运行环境为 `conda activate rm`，而不是 `(base)`。
2. 在目标环境执行 `pip install -e ".[dev]"`。
3. 重新运行 `python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_nomem.yaml` 和 `configs/tau_retail_phase2_state_raw_trace_rag.yaml`，确认 artifacts 是本次生成。
4. 若临时不安装包，则所有实验命令统一加 `PYTHONPATH=src`，但正式实验仍建议使用 editable install。

第二轮建议编码/实验范围：

1. 准备真实 tau-bench retail task/data export，按 `docs/tau_retail_export_schema.md` 对齐字段，先只取 `max_tasks=1`。
2. 新增或复制配置为真实 export 专用，例如 `configs/tau_retail_phase2_real_nomem.yaml` 和 `configs/tau_retail_phase2_real_raw_trace_rag.yaml`；不要覆盖现有本地 fixture 配置。
3. 在真实 export 上运行 no-memory，重点检查 `runs.jsonl.evaluation_details` 是否能解释 reward：action mismatch、state diff mismatch、policy violation、tool semantic error 或 actor 工具调用错误。
4. 若失败来自缺失 tool semantic，优先补 `TauBenchEnv` 的对应 retail tool；若失败来自 expected outcome schema 不兼容，优先扩展 loader/evaluator schema。
5. no-memory reward 可解释后，再跑同一真实 export 的 raw-trace-rag，只验证 memory 写入/检索、token 成本和 evaluator 语义不变。
6. 暂不把 `nt_memevo_gate`、support verification、scope refinement 或真实 actor 作为第二轮主线；这些等真实 export 的 evaluator/state 语义稳定后再迁移。

第二轮验收标准：

1. `python -m pytest` 全量通过。
2. 第二阶段第一轮本地 fixture 的 no-memory/raw-trace-rag 命令在目标环境正式通过。
3. 真实 export `max_tasks=1` 至少能生成 `tasks.jsonl`、`runs.jsonl`、`trace_events.jsonl` 和 `metrics.json`。
4. 若真实 export 任务失败，失败原因必须能归入明确类别，并记录最小复现 task/data 片段。
5. 同一真实 export 的 raw-trace-rag 能写入 memory 与 retrieve 日志，不改变 evaluator 解释链路。

## 2026-05-03 第二阶段第二轮

目标：进入“真实 tau-retail export 小批量语义对齐”，按用户要求克隆官方真实数据，并把实验配置从本地 phase-two fixture 推进到官方 `tau2-bench` retail 任务/DB 文件；同时修正官方任务在当前 mock actor 下没有已知 no-memory 反事实时的负迁移误标风险。

官方数据准备：

1. 已克隆旧版官方仓库 `https://github.com/sierra-research/tau-bench.git` 到 `data/external/tau-bench/`，commit 为 `59a200c6d575d595120f1cb70fea53cef0632f6b`。
2. 旧版 `tau-bench` README 明确提示任务文件已过期，并指向 `https://github.com/sierra-research/tau2-bench` 作为更新后的 tau-three 数据源。
3. 已克隆更新官方仓库 `https://github.com/sierra-research/tau2-bench.git` 到 `data/external/tau2-bench/`，commit 为 `2be691669909439cf88dedc13decf94b7664d262`。
4. `tau2-bench` retail 官方数据路径为 `data/external/tau2-bench/data/tau2/domains/retail/`，包含 `tasks.json`、`split_tasks.json`、`db.json`、`policy.md`、`tasks_voice.json`、audio difficulty 与 task issue 文件。
5. 本轮统计官方 retail 数据：`tasks.json` 共 114 条任务，split 为 `train=74`、`test=40`、`base=114`；`db.json` 包含 `products=50`、`users=500`、`orders=1000`。
6. 已将 `data/external/` 加入 `.gitignore`，避免把完整外部仓库纳入项目版本控制；后续智能体可在同一路径复用已克隆数据，若目录缺失按 README 命令重新克隆。

已完成：

1. 扩展 `TauBenchEnv`，支持直接读取官方 tau2 嵌套 task 结构：`user_scenario.instructions` 会被合成为项目内 `Task.instruction`，`evaluation_criteria.actions` 会转换为 `metadata.expected_actions`。
2. 新增官方 split 过滤：`benchmark.task_split_file` 可指向 `split_tasks.json`，`benchmark.task_split` 支持 `base/train/test`，`benchmark.task_ids` 支持最小任务 id 子集调试。
3. 官方 tau2 task metadata 保留 `source_format=tau2_official`、原始 `evaluation_criteria`、`user_scenario`、`tool_names` 和推断 intent，便于 `tasks.jsonl` 审计。
4. 修正负迁移代理默认值：官方 tau2 任务缺少本项目 no-memory 反事实结果时，默认 `no_memory_success=false`；只有导出文件显式提供该字段时才使用 true，避免 raw-trace 失败被误记为 negative transfer。
5. 扩展 retail tool wrapper，新增/补齐 `get_item_details`、`modify_user_address`、`new_item_ids`、`payment_method_id`、官方 address 字段和 item variant 查询的最小兼容语义。
6. 扩展 `MockLLMClient` 的工具名解析，支持 `get_item_details`、`modify_user_address`，并将 exchange 的 replacement 参数改为官方常见的 `new_item_ids`。
7. 新增官方 tau2 配置 `configs/tau_retail_phase2_official_tau2_nomem.yaml`，默认读取官方 base split 前 3 条任务，使用 `official_like`、`compare_action_args=true`。
8. 新增官方 tau2 配置 `configs/tau_retail_phase2_official_tau2_raw_trace_rag.yaml`，在同一官方任务/DB 上启用 Raw Trace RAG，验证 memory 写入与逐轮检索。
9. 扩展 `tests/test_tau_bench_adapter.py`，新增官方嵌套 task 格式、split 过滤、`official_like` action args 评估与 no-memory baseline 默认值测试。
10. 更新 `README.md` 与 `docs/tau_retail_export_schema.md`，写明官方仓库克隆命令、tau2 数据路径、`task_split_file` / `task_ids` 配置、支持工具和当前边界。

验证记录：

1. `PYTHONPATH=src python -m pytest tests/test_tau_bench_adapter.py -q` 通过，结果为 `16 passed in 0.09s`。
2. `PYTHONPATH=src python -m pytest -q` 通过，结果为 `31 passed in 0.12s`。
3. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_nomem.yaml` 通过：`success_rate=0.6666666666666666`、`state_diff_passed_count=1`、`expected_actions_matched_count=3`、`policy_violation_count=1`。
4. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_raw_trace_rag.yaml` 通过：`success_rate=0.6666666666666666`、`memory_policy=raw_trace_rag`、`memory_size=3`、`policy_violation_count=1`。
5. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_nomem.yaml` 成功生成官方 tau2 no-memory artifacts：`num_tasks=3`、`success_rate=0.0`、`evaluation_modes={"official_like": 3}`、`expected_actions_evaluated_count=3`、`expected_actions_matched_count=0`、`policy_violation_count=0`、`tool_semantic_error_count=0`、`negative_transfer_rate=0.0`。
6. no-memory 官方任务失败是预期且可解释的：当前 mock actor 不是完整对话 agent，前 3 条官方 base 任务需要 5/5/11 步 expected actions，而 mock 只会做 0-1 次工具调用；`runs.jsonl.evaluation_details.action_mismatches` 明确给出 `action_count_mismatch`、`tool_name_mismatch` 和 `missing_actual_action`。
7. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_raw_trace_rag.yaml` 成功：`num_tasks=3`、`success_rate=0.0`、`memory_policy=raw_trace_rag`、`memory_size=3`、`memory_top_k=2`、`expected_actions_failed_count=3`、`negative_transfer_rate=0.0`。
8. 官方 raw-trace-rag 抽查确认逐轮检索正常：第 1 轮空检索，第 2 轮检索 `raw_000001_0`，第 3 轮检索 `raw_000002_1` 和 `raw_000001_0`。
9. 第一阶段核心回归仍通过：`tiny_nt_memevo_gate_refine.yaml` 保持 `memory_refinement_count=1`、`memory_split_count=1`、`support_replay_helpful_count=2`、`support_replay_harmful_count=2`；`tiny_nt_memevo_gate_unsafe_polluted.yaml` 保持 `negative_transfer_rate=1.0`、`replay_harmful_count=1`、`quarantined_memory_count=1`。
10. 修正前官方 raw-trace 由于默认 `no_memory_success=true` 曾把第 2/3 条失败误计为 `negative_transfer_rate=0.666666...`；修正后同一配置为 `negative_transfer_rate=0.0`，符合“未知 no-memory 反事实不做负迁移归因”的第二阶段口径。

用户正式复验记录：

1. 用户在 Linux 机器 `BNUZ`、交互式 conda 环境 `(rm)` 下运行 `python -m pytest`，环境为 Python 3.12.13、pytest 9.0.3、pluggy 1.6.0，结果为 `31 passed in 0.10s`。
2. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_nomem.yaml`，结果为 `num_tasks=3`、`success_rate=0.6666666666666666`、`avg_prompt_tokens=1011.3333333333334`、`evaluation_modes={"official_like": 3}`、`state_diff_passed_count=1`、`expected_actions_matched_count=3`、`policy_violation_count=1`、`tool_semantic_error_count=1`、`memory_policy=none`。
3. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_raw_trace_rag.yaml`，结果为 `success_rate=0.6666666666666666`、`avg_prompt_tokens=1354.6666666666667`、`memory_policy=raw_trace_rag`、`memory_size=3`、`memory_top_k=2`、`policy_violation_count=1`、`negative_transfer_rate=0.0`。
4. 用户抽查 `runs/tau_retail_phase2_state_nomem_seed1/runs.jsonl`，确认 read 任务成功、cancel 任务 `state_diff_passed=true`、pending return 任务按预期触发 `error_type=policy_violation`。
5. 用户抽查 `runs/tau_retail_phase2_state_nomem_seed1/trace_events.jsonl`，确认 `get_order_details` 与 `cancel_pending_order` 为 `ok=true`，`return_delivered_order_items` 对 pending order 为 `ok=false`。
6. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_nomem.yaml`，结果为 `num_tasks=3`、`success_rate=0.0`、`avg_prompt_tokens=988.0`、`expected_actions_matched_count=0`、`expected_actions_failed_count=3`、`evaluator_error_types={"expected_action_sequence_mismatch": 1, "expected_tool_name_mismatch": 2}`、`negative_transfer_rate=0.0`。
7. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_raw_trace_rag.yaml`，结果为 `num_tasks=3`、`success_rate=0.0`、`avg_prompt_tokens=1279.6666666666667`、`memory_policy=raw_trace_rag`、`memory_size=3`、`memory_top_k=2`、`expected_actions_failed_count=3`、`negative_transfer_rate=0.0`。
8. 用户抽查官方 no-memory `runs.jsonl`，确认 task `0` 和 `1` 当前 mock actor 只调用 1 次 `exchange_delivered_order_items`，而 expected action sequence 分别需要 5 步；task `2` 当前无工具调用，而 expected action sequence 需要 11 步。
9. 用户抽查官方 raw-trace-rag `memories.jsonl`，确认 3 条失败轨迹被保存；抽查 `memory_updates.jsonl`，确认第 1 轮空检索、第 2 轮检索 `raw_000001_0`、第 3 轮检索 `raw_000002_1` 和 `raw_000001_0`。
10. 用户确认官方数据版本：`data/external/tau-bench` commit 为 `59a200c6d575d595120f1cb70fea53cef0632f6b`，`data/external/tau2-bench` commit 为 `2be691669909439cf88dedc13decf94b7664d262`；tau2 retail 数据规模为 `tasks=114`、split `train=74/test=40/base=114`、DB `products=50/users=500/orders=1000`。

当前边界：

1. 本轮已正确链接并运行官方 tau2 retail 真实 task/DB，但 actor 仍是 deterministic mock，不具备完成官方多轮任务的能力，因此成功率为 0.0 不代表方法失效。
2. `official_like` 仍是本项目本地可解释 evaluator，不等价于 tau2 官方 evaluator；本轮重点是任务/DB 加载、action mismatch 分类、memory 日志和负迁移代理口径。
3. 官方 tau2 task 的 `communicate_info` / `nl_assertions` 尚未完整映射为自然语言评估，当前主要依赖 `evaluation_criteria.actions` 做可解释 action-sequence 评估。
4. 官方 state diff / policy evaluator 对齐、真实 user/agent actor、完整多轮对话、support pool、gate/replay/verification 仍属于第二阶段后续轮次。

用户复验建议命令：

```bash
conda activate rm
pip install -e ".[dev]"
python -m pytest

# 如果 data/external 下缺少官方仓库，先克隆：
git clone https://github.com/sierra-research/tau-bench.git data/external/tau-bench
git clone https://github.com/sierra-research/tau2-bench.git data/external/tau2-bench

# 第二阶段第一轮正式补验
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_raw_trace_rag.yaml

# 第二阶段第二轮官方 tau2 real-data 小批量复验
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_raw_trace_rag.yaml

cat runs/tau_retail_phase2_official_tau2_nomem_seed1/metrics.json
tail -n 3 runs/tau_retail_phase2_official_tau2_nomem_seed1/runs.jsonl
grep '"event_type": "tool_call"' runs/tau_retail_phase2_official_tau2_nomem_seed1/trace_events.jsonl

cat runs/tau_retail_phase2_official_tau2_raw_trace_rag_seed1/metrics.json
head -n 3 runs/tau_retail_phase2_official_tau2_raw_trace_rag_seed1/memories.jsonl
grep '"event_type": "retrieve"' runs/tau_retail_phase2_official_tau2_raw_trace_rag_seed1/memory_updates.jsonl
```

实验日志更新状态：

1. `docs/experiment_log.md` 已补齐第二阶段第一轮在 `(rm)` 环境下的正式复验结果，记录 state fixture 的 no-memory/raw-trace-rag 指标、policy violation 和 raw trace 检索。
2. `docs/experiment_log.md` 已新增 `tau_retail_phase2_official_tau2_seed1` 实验条目，记录官方 repo commit、官方 retail 数据规模、两组配置指标和 action mismatch 分类。
3. 官方 no-memory/raw-trace 成功率为 0.0 的原因已记录为 actor 能力边界：mock actor 只能验证 adapter/evaluator 日志，不是官方 benchmark actor。
4. raw-trace-rag 的 `memory_size=3`、逐轮 retrieve、token 成本增加和 `negative_transfer_rate=0.0` 修正口径已写入实验日志。

下一步建议：

1. 在官方 tau2 task 上接入一个可多步完成 expected actions 的 actor 或 action-replay oracle，用于把 adapter/evaluator 和真实模型能力解耦。
2. 逐步对齐 tau2 官方 evaluator 的 `communicate_info`、`nl_assertions`、DB 终态和 policy violation，而不只依赖 action sequence。
3. 针对官方前 3 条 exchange/return 任务继续补 mutation semantics，尤其是 `new_item_ids`、payment history、refund/exchange 状态字段与官方工具返回结构。
4. 当 no-memory 官方小批量 reward 可解释且 actor 不再是主要 blocker 后，再迁移 `nt_memevo_gate`、support verification 和 scope refinement。

## 第二阶段第三轮方向（更新）

优先方向：实现官方 tau2 action-replay oracle / scripted expected-action actor，并补齐官方前 3 条 retail 任务需要的 tool/evaluator 语义。理由是第二阶段第二轮已经证明官方 task/DB loader、Raw Trace RAG 日志和 action mismatch 分类可运行；当前主要 blocker 是 mock actor 只能执行 0-1 步，无法验证官方多步 expected actions、DB state mutation 和自然语言断言。

第三轮建议范围：

1. 新增 `action_replay` 或 `scripted_expected_actions` actor/provider：从 `metadata.expected_actions` 逐步执行官方工具调用，生成可评估 trace，用来把 adapter/evaluator 问题和真实模型策略能力解耦。
2. 在官方 tau2 前 3 条 base 任务上建立最小 oracle 配置，例如 `configs/tau_retail_phase2_official_tau2_action_replay.yaml`，默认 `max_tasks=3`，只用于语义对齐，不作为方法收益实验。
3. 补齐官方 exchange 任务链路：`find_user_id_by_name_zip -> get_order_details -> get_product_details -> get_product_details -> exchange_delivered_order_items`，重点检查 `item_ids`、`new_item_ids`、product variant、替换商品选择和 order state update。
4. 补齐官方 return/count 任务链路：多次 `get_order_details`、`get_product_details`、tshirt option count、`return_delivered_order_items`，重点检查返回 item 选择、订单状态、商品过滤和最终信息表达。
5. 扩展 `official_like` evaluator：在 action sequence 之外开始映射 `communicate_info` / `nl_assertions`，并为 DB state mismatch、natural-language assertion mismatch、unsupported official criterion 分别记录 error type。
6. 在 `runs.jsonl.evaluation_details` 中保留 expected-vs-actual action 对齐表、state diff summary、未支持 evaluator criterion 列表和官方原始 task id，避免后续真实 actor 失败只能看到笼统 `success=false`。
7. 新增测试覆盖 tau2 nested action replay、官方 tool 参数规范化、exchange/return mutation state update、unsupported criterion 的可解释降级，以及第二阶段第二轮四个配置不回归。
8. 第三轮暂不建议迁移 `nt_memevo_gate`、support verification、scope refinement 或真实 LLM actor；只有当 action-replay/oracle 能让官方小批量任务通过或输出明确 state/assertion mismatch 后，再进入真实 actor smoke。

第三轮验收标准：

1. `python -m pytest` 全量通过。
2. `tau_retail_phase2_state_nomem.yaml` 和 `tau_retail_phase2_state_raw_trace_rag.yaml` 维持当前 `success_rate=0.6666666666666666` 和可解释 policy violation。
3. `tau_retail_phase2_official_tau2_nomem.yaml` 与 `tau_retail_phase2_official_tau2_raw_trace_rag.yaml` 继续稳定生成 action mismatch 与 memory 日志，`negative_transfer_rate=0.0`。
4. 新增 action-replay/oracle 配置至少能完整执行官方前 3 条任务的 expected action sequence；若 reward 仍失败，失败必须落到 state diff、natural-language assertion、unsupported criterion 或 tool semantic mismatch。
5. 官方 tau2 artifacts 中每个失败任务都能在 `evaluation_details` 中解释“是 actor 少做/错做动作，还是工具语义/evaluator 尚未对齐”。

## 2026-05-05 第二阶段第三轮

目标：实现官方 tau2 action-replay oracle / scripted expected-action actor，并补齐官方前 3 条 retail 任务所需的最小 tool/evaluator 语义，使官方多步任务失败不再被 mock actor 能力阻塞，而能归因到工具语义、自然语言断言或 unsupported criterion。

已完成：

1. 新增 `src/ntmemevo/agents/action_replay_agent.py`，实现 `ActionReplayAgent`，按 `Task.metadata.expected_actions` 顺序执行官方工具调用，并记录 `scripted_action` 与 `tool_call` trace 事件。
2. 修改 `run_stream`，支持 `agent.type=action_replay_agent` / `action_replay` / `scripted_expected_actions`；该路径不创建 LLM client，prompt/completion token 成本为 0，用于 adapter/evaluator oracle 对齐。
3. 修改 `RunLogger.log_run()`，将 `runs.jsonl.agent` 从硬编码 `react_tool_agent` 改为按实际 agent 类型记录。
4. 扩展 tau2 official task loader：保留 `evaluation_criteria.actions` 的 `action_id` / `info`，并把 `communicate_info`、`nl_assertions`、`reward_basis` 写入 task metadata。
5. 修正 official DB 用户姓名解析，支持 tau2 `user.name={first_name,last_name}` 结构，使 `find_user_id_by_name_zip` 可在官方 DB 上找到 Yusuf Rossi。
6. 补齐官方 exchange / return mutation 的关键字段：`status="exchange requested"` / `status="return requested"`、`exchange_items`、`exchange_new_items`、`exchange_payment_method_id`、`exchange_price_difference`、`return_items` 和 `return_payment_method_id`；增加 payment method 与 variant/product consistency 检查。
7. 扩展 `official_like` evaluator：在 action/state/answer 之外开始检查 `communicate_info` 与可确定映射的 `nl_assertions`，并记录 `communicate_info_*`、`nl_assertion_*` 与 `unsupported_official_criteria` 细节。
8. `runs.jsonl.evaluation_details` 新增 `expected_actual_action_alignment`，逐步保留 expected action id、expected/actual tool name、args、actual ok 与 mismatch reasons。
9. `metrics.json` 新增 `communicate_info_evaluated_count`、`communicate_info_passed_count`、`communicate_info_failed_count`、`nl_assertion_evaluated_count`、`nl_assertion_passed_count`、`nl_assertion_failed_count` 和 `unsupported_official_criteria_count`。
10. 新增配置 `configs/tau_retail_phase2_official_tau2_action_replay.yaml`，默认读取官方 tau2 retail base split 前 3 条任务，使用 action replay oracle 与 `official_like` evaluator。
11. 新增/更新测试：action replay 执行 nested tau2 expected actions、`communicate_info` / `nl_assertions` 通过、unsupported criterion 可解释降级、official exchange/return mutation 状态更新、官方姓名结构解析，以及第二阶段前两轮配置不回归。
12. 更新 `README.md`，加入 action-replay 命令、第三轮新增 evaluator detail 字段、metrics 字段和下一轮方向。

关键实现说明：

1. `ActionReplayAgent` 不是方法收益实验 actor，不代表真实 LLM 能力；它只用于把 expected action sequence 完整送进环境，从而检查 adapter、tool semantics 和 evaluator。
2. `official_like` 对 `nl_assertions` 只做确定性可解释映射：当前支持数字与简单 “there are N ... available” 形态；无法确定映射的 assertion 会进入 `unsupported_official_criteria`，不会静默当作通过。
3. 对 official tau2 前 3 条任务，action replay 已经消除 actor action mismatch；剩余失败来自 task `2` 的 `get_product_details(product_id=6086499569)` 在当前官方 DB 中找不到对应 product，属于明确的 `tool_semantic_error`。
4. 本轮仍不迁移 `nt_memevo_gate`、support verification、scope refinement 或真实 LLM actor；这些应等 official oracle/evaluator 语义进一步对齐后再进入主线。

验证记录：

1. `PYTHONPATH=src python -m pytest tests/test_tau_bench_adapter.py -q` 通过，结果为 `19 passed in 0.11s`。
2. `PYTHONPATH=src python -m pytest -q` 通过，结果为 `34 passed in 0.13s`。
3. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_nomem.yaml` 通过：`success_rate=0.6666666666666666`、`expected_actions_matched_count=3`、`state_diff_passed_count=1`、`policy_violation_count=1`。
4. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_raw_trace_rag.yaml` 通过：`success_rate=0.6666666666666666`、`memory_policy=raw_trace_rag`、`memory_size=3`、`policy_violation_count=1`。
5. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_nomem.yaml` 通过：`success_rate=0.0`、`expected_actions_matched_count=0`、`expected_actions_failed_count=3`、`negative_transfer_rate=0.0`；新增 `communicate_info_failed_count=1` 和 `nl_assertion_failed_count=1`，说明 mock actor 未表达 task 2 的官方 NL 要求。
6. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_raw_trace_rag.yaml` 通过：`success_rate=0.0`、`memory_policy=raw_trace_rag`、`memory_size=3`、`expected_actions_failed_count=3`、`negative_transfer_rate=0.0`。
7. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_action_replay.yaml` 通过：`num_tasks=3`、`success_rate=0.6666666666666666`、`avg_tool_calls=7.0`、`avg_prompt_tokens=0.0`、`expected_actions_matched_count=3`、`expected_actions_failed_count=0`、`communicate_info_passed_count=1`、`nl_assertion_passed_count=1`、`tool_semantic_error_count=1`、`evaluator_error_types={"tool_semantic_error": 1}`。
8. 抽查 `runs/tau_retail_phase2_official_tau2_action_replay_seed1/runs.jsonl`：task `0` 与 `1` 成功；task `2` 完整执行 11 步 expected actions，`expected_actions_matched=true`，但 `get_product_details({"product_id":"6086499569"})` 返回 `ok=false`，因此 `error_type=tool_semantic_error`。

用户复验建议命令：

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

实验日志填写建议：

1. 新增 `tau_retail_phase2_official_tau2_action_replay_seed1` 条目，记录官方 repo commit、官方数据规模、action-replay 配置和本轮 action-replay 指标。
2. 重点记录 action-replay 与 mock no-memory 的差异：mock 配置 `expected_actions_matched_count=0`，action-replay 配置 `expected_actions_matched_count=3`。
3. 重点记录 task `2` 的失败原因：actor 已完整执行 expected actions，NL assertion 已通过，剩余失败是 `get_product_details(product_id=6086499569)` 在当前 official DB 中找不到 product，归类为 `tool_semantic_error`。
4. 本轮结果只用于 adapter/evaluator 对齐，不用于报告 NT-MemEvo 方法收益。

当前边界：

1. `official_like` 仍不是官方 tau2 evaluator，只是本地可解释近似。
2. `nl_assertions` 仍是确定性启发式映射，不支持需要复杂语义判断的自然语言断言。
3. 官方 task `2` 的 `6086499569` product semantic gap 需要下一轮继续对齐官方 evaluator/DB/tool 版本或记录为官方数据兼容 blocker。
4. 真实 LLM actor、多轮 user simulator、官方 reward、`nt_memevo_gate`、support verification 和 scope refinement 仍未迁移到官方 tau2 主实验。

下一步建议：

1. 追踪 `6086499569` 在当前 tau2 官方 DB 中缺失的原因：确认是 task/data 版本错配、官方 evaluator 对该 action 的特殊处理，还是 adapter 应兼容 item/product id fallback。
2. 对齐官方 tau2 evaluator 的 `communicate_info`、`nl_assertions` 和 DB reward 规则，优先把 action-replay 的失败从 `tool_semantic_error` 推进到官方一致口径。
3. 当 action-replay 前 3 条任务全部通过或每个失败都有官方一致解释后，再接真实 LLM actor 的 `max_tasks=1/3` smoke。
4. 在真实 actor no-memory reward 可解释后，再迁移 `raw_trace_rag` 以外的 NT-MemEvo gate/replay/verification 机制。

用户正式复验记录（2026-05-05）：

1. 用户在 Linux 机器 `BNUZ`、交互式 conda 环境 `(rm)` 下运行 `python -m pytest`，环境为 Python 3.12.13、pytest 9.0.3、pluggy 1.6.0，结果为 `34 passed in 0.11s`。
2. 用户确认官方数据版本：`data/external/tau-bench` commit 为 `59a200c6d575d595120f1cb70fea53cef0632f6b`，`data/external/tau2-bench` commit 为 `2be691669909439cf88dedc13decf94b7664d262`。
3. `tau_retail_phase2_state_nomem.yaml` 复验通过：`num_tasks=3`、`success_rate=0.6666666666666666`、`state_diff_passed_count=1`、`expected_actions_matched_count=3`、`policy_violation_count=1`、`tool_semantic_error_count=1`、`memory_policy=none`。
4. `tau_retail_phase2_state_raw_trace_rag.yaml` 复验通过：`success_rate=0.6666666666666666`、`memory_policy=raw_trace_rag`、`memory_size=3`、`memory_top_k=2`、`negative_transfer_rate=0.0`；与 no-memory 的 evaluator 结论一致。
5. `tau_retail_phase2_official_tau2_nomem.yaml` 复验通过并按预期失败：`success_rate=0.0`、`expected_actions_matched_count=0`、`expected_actions_failed_count=3`、`communicate_info_failed_count=1`、`nl_assertion_failed_count=1`、`negative_transfer_rate=0.0`。
6. `tau_retail_phase2_official_tau2_raw_trace_rag.yaml` 复验通过并按预期失败：`success_rate=0.0`、`memory_policy=raw_trace_rag`、`memory_size=3`、`memory_top_k=2`、`expected_actions_failed_count=3`、`negative_transfer_rate=0.0`。
7. `tau_retail_phase2_official_tau2_action_replay.yaml` 复验通过：`num_tasks=3`、`success_rate=0.6666666666666666`、`avg_steps=8.0`、`avg_tool_calls=7.0`、`avg_prompt_tokens=0.0`、`expected_actions_matched_count=3`、`expected_actions_failed_count=0`、`communicate_info_passed_count=1`、`nl_assertion_passed_count=1`、`tool_semantic_error_count=1`、`evaluator_error_types={"tool_semantic_error": 1}`。
8. 用户抽查 action-replay `runs.jsonl`：task `0` 与 task `1` 成功；task `2` 完整执行 11 步 expected actions，且 `communicate_info` / `nl_assertion` 均通过，但 `get_product_details({"product_id":"6086499569"})` 返回 `Product 6086499569 was not found.`，因此当前失败落到 `tool_semantic_error`。
9. 用户抽查 action-replay `trace_events.jsonl`：`6086499569` 同时写入 `scripted_action` 与 `tool_call`，其中 `tool_call.ok=false`；所有 `scripted_action` 均来自 `metadata.expected_actions`，说明 actor mismatch 已被 oracle 消除。

当前结果分析：

1. 第二阶段第三轮的编码目标已经完成：action-replay oracle 能完整执行官方 tau2 前 3 条 base 任务的 expected action sequence，`expected_actions_matched_count=3` 消除了第二阶段第二轮 `expected_actions_matched_count=0` 的 actor mismatch。
2. 官方 mock no-memory/raw-trace-rag 的 `success_rate=0.0` 仍是可解释 actor 能力边界；第三轮新增的 `communicate_info_failed_count=1` 与 `nl_assertion_failed_count=1` 进一步说明 mock actor 没有表达 task `2` 的自然语言要求。
3. action-replay 的 `success_rate=0.6666666666666666` 不代表 NT-MemEvo 方法收益，只说明 adapter/tool/evaluator 对齐层可以绕过 actor 能力限制进行诊断。
4. 当前唯一剩余失败集中在 `6086499569`：expected action 已执行且 action args 匹配，但当前 tau2 retail DB 查询不到该 product。初步本地检索显示该 id 出现在 tau2 `tasks.json`、`task_issues` 和 legacy tau-bench expected actions 中，但没有出现在当前 tau2 retail `db.json` product 记录中。
5. 下一轮不能直接把 `ok=false` 统一解释为 fatal tool semantic error；需要区分 expected action 中允许的负向观察、官方数据兼容问题和真正的 adapter/tool 语义错误。

实验日志更新状态：

1. `docs/experiment_log.md` 已将 `tau_retail_phase2_official_tau2_action_replay_seed1` 从待填模板更新为正式实验记录。
2. 实验日志已记录本轮 `34 passed` 测试结果、官方 repo commit、五组配置对照指标、action-replay 抽查结论和 `6086499569` 失败分析。
3. 实验日志已把下一轮方向从“建设 action-replay oracle”推进到“官方 tau2 数据/工具/evaluator 口径对齐”。

## 第二阶段第四轮方向（更新）

优先方向：对齐官方 tau2 数据、工具 observation 和 evaluator reward 口径，特别是 expected action 中工具返回 `ok=false` 的处理方式。理由是第三轮已经证明 action-replay 可以完整执行官方 expected actions；当前 blocker 不再是 actor 少做/错做动作，而是 `get_product_details(product_id=6086499569)` 这种“expected action matched 但工具 observation 为 not found”的语义应如何计入 reward。

第四轮建议范围：

1. 追踪 `6086499569` 的来源与官方语义，确认它是 task/data 版本错配、官方已知 issue、expected negative lookup，还是 adapter 应补的兼容映射。
2. 扩展 `official_like` evaluator 的工具失败分类：区分 expected negative observation、policy/precondition violation、adapter/tool semantic error 和 unsupported official criterion。
3. 对比 tau2 官方结果文件、`task_issues`、official action checks 与当前本地 evaluator，明确 action match、tool `ok`、DB check、communicate check、nl assertion 之间的 reward 组合关系。
4. 为 `get_product_details(product_id=6086499569)` 建立最小测试，确保后续不会把官方允许的负向查询误报成 adapter 回归，也不会掩盖真正工具语义错误。
5. 继续保持 `runs.jsonl.evaluation_details` 的可解释输出：每个失败任务都必须能同时看到 expected-vs-actual action alignment、tool observation、state diff summary、communicate/nl assertion 和 unsupported criterion。
6. action-replay 前 3 条任务全部通过或失败均有官方一致解释后，再接真实 LLM actor 的 `max_tasks=1/3` smoke；真实 actor 先只做 no-memory 可解释性，不做方法收益结论。
7. 第四轮暂不迁移 `nt_memevo_gate`、support verification、scope refinement 或大规模 raw-trace-rag；这些等官方 no-memory/actor/evaluator 口径稳定后再进入主线。

第四轮验收标准：

1. `python -m pytest` 全量通过。
2. 第二阶段第三轮五组复验命令继续可运行，并稳定生成 `tasks.jsonl`、`runs.jsonl`、`trace_events.jsonl`、`metrics.json` 及 memory artifacts。
3. `tau_retail_phase2_official_tau2_action_replay.yaml` 对 task `2` 的 `6086499569` 给出官方一致解释：通过、unsupported known issue、expected negative observation，或明确 adapter/tool semantic bug。
4. `tool_semantic_error_count` 不再混合 expected negative lookup 和真正工具语义错误。
5. 若新增真实 LLM actor smoke，必须先在 no-memory 上输出可解释 failure taxonomy；不得把 raw-trace-rag、gate/replay/verification 结果提前作为 NT-MemEvo 方法收益。

## 2026-05-05 第二阶段第四轮

目标：对齐官方 tau2 数据、工具 observation 和 evaluator reward 口径，重点处理 expected action 中工具返回 `ok=false` 的场景，避免把官方 expected read lookup 的负向 observation 误归为 adapter/tool semantic bug。

官方口径对照：

1. 本地已存在官方数据仓库，无需本轮重新克隆：`data/external/tau-bench` commit 为 `59a200c6d575d595120f1cb70fea53cef0632f6b`，`data/external/tau2-bench` commit 为 `2be691669909439cf88dedc13decf94b7664d262`。
2. 检查 `data/external/tau2-bench/src/tau2/evaluator/evaluator_action.py` 后确认：官方 action evaluator 只检查 expected tool call 是否出现在轨迹中以及参数是否匹配，不检查工具返回 `ok/error`。
3. 检查 `data/external/tau2-bench/src/tau2/evaluator/evaluator_env.py` 后确认：官方 environment evaluator 会 replay golden actions；golden action 抛异常时记录 warning 并继续 DB hash 比较，因此 read-only gold action 查不到对象不应直接等价于 fatal reward failure。
4. `6086499569` 仍只出现在 tau2 retail `tasks.json`、`task_issues`、legacy tau-bench task/trajectory 和工具文档示例中，没有出现在当前 tau2 retail `db.json` 的 products 中；第四轮将其解释为 matched expected read action 的 negative observation，而不是当前 adapter 的工具语义错误。

已完成编码：

1. 修改 `src/ntmemevo/envs/tau_bench.py`，新增 `_classify_tool_observations()`，将所有 `ok=false` 工具结果先归入 `tool_observation_errors`，再细分为 `expected_negative_observation`、`policy_violation` 和 `tool_semantic_error`。
2. 对 matched expected read-only tool action 且 `actual_ok=false` 的情况，新增 `expected_negative_observations` 记录；当前覆盖 `find_user_id_by_name_zip`、`find_user_id_by_email`、`get_user_details`、`get_order_details`、`get_product_details`、`get_item_details`、`list_all_product_types` 和 `lookup_policy`。
3. mutation/precondition 类工具失败继续归入 `policy_violations`，不再混入 `tool_semantic_errors`；当前覆盖 pending order mutation、cancel、return、exchange 和 `modify_user_address`。
4. `tool_semantic_errors` 现在只保留非 policy、非 expected-negative 的剩余工具语义错误；`official_like` success 判定只把 unexpected policy violation、真正 tool semantic error 和 unsupported criterion 当作 fatal。
5. `runs.jsonl.evaluation_details.expected_actual_action_alignment` 新增 `actual_observation`，使每个 expected-vs-actual action row 同时能看到 tool name、args、`actual_ok` 和 observation 文本。
6. `runs.jsonl.evaluation_details` 新增 `tool_observation_error_count`、`tool_observation_errors`、`expected_negative_observation_count`、`expected_negative_observations`；保留 `policy_violation_count` 和新的严格 `tool_semantic_error_count`。
7. 修改 `src/ntmemevo/evaluation/metrics.py`，聚合新增 `tool_observation_error_count` 与 `expected_negative_observation_count`。
8. 更新 `README.md` 的 artifact/metrics 字段说明，明确 `tool_observation_error_count` 是所有 `ok=false`，`expected_negative_observation_count` 是 official expected read lookup 的负向观察，`tool_semantic_error_count` 只表示剩余非 policy、非 expected 的工具失败。
9. 新增回归测试 `test_tau2_expected_read_tool_error_is_classified_as_negative_observation`：构造 expected `get_product_details(product_id=6086499569)` 的 action-replay 任务，验证 success 保持为 true、`expected_negative_observation_count=1`、`tool_semantic_error_count=0`。
10. 新增回归测试 `test_tau2_unexpected_read_tool_error_remains_tool_semantic_error`：验证非 expected 的 read lookup failure 仍然失败，并归类为 `tool_semantic_error`。
11. 更新 phase2 state fixture 测试：pending return 仍然是 `policy_violation`，但 `tool_semantic_error_count` 从旧口径的 `1` 调整为 `0`，对应新字段 `tool_observation_error_count=1`。

本轮本地验证：

1. `PYTHONPATH=src python -m pytest tests/test_tau_bench_adapter.py -q` 通过：`21 passed in 0.11s`。
2. `PYTHONPATH=src python -m pytest -q` 通过：`36 passed in 0.13s`。
3. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_nomem.yaml` 通过：`success_rate=0.6666666666666666`、`expected_actions_matched_count=3`、`policy_violation_count=1`、`tool_observation_error_count=1`、`expected_negative_observation_count=0`、`tool_semantic_error_count=0`。
4. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_raw_trace_rag.yaml` 通过：`success_rate=0.6666666666666666`、`memory_policy=raw_trace_rag`、`memory_size=3`、`tool_observation_error_count=1`、`tool_semantic_error_count=0`、`negative_transfer_rate=0.0`。
5. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_nomem.yaml` 通过并按预期失败：`success_rate=0.0`、`expected_actions_matched_count=0`、`expected_actions_failed_count=3`、`tool_observation_error_count=0`、`negative_transfer_rate=0.0`。
6. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_raw_trace_rag.yaml` 通过并按预期失败：`success_rate=0.0`、`memory_policy=raw_trace_rag`、`memory_size=3`、`expected_actions_failed_count=3`、`tool_observation_error_count=0`、`negative_transfer_rate=0.0`。
7. `PYTHONPATH=src python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_action_replay.yaml` 通过：`success_rate=1.0`、`expected_actions_matched_count=3`、`expected_actions_failed_count=0`、`communicate_info_passed_count=1`、`nl_assertion_passed_count=1`、`tool_observation_error_count=1`、`expected_negative_observation_count=1`、`tool_semantic_error_count=0`、`evaluator_error_types={}`。
8. 抽查 `runs/tau_retail_phase2_official_tau2_action_replay_seed1/runs.jsonl`：task `2` 中 `get_product_details({"product_id":"6086499569"})` 仍返回 `Product 6086499569 was not found.`，但对应 alignment row 为 `matched=true`、`actual_ok=false`，并进入 `expected_negative_observations`，不再导致 run failure。

结果分析：

1. 第三轮 action-replay 剩余的唯一失败已按官方 action/env evaluator 口径解释为 expected read negative observation；官方 tau2 前 3 条 base task 的 action-replay 本地近似 evaluator 现在全部通过。
2. 本轮没有改变 mock no-memory/raw-trace-rag 的 actor 能力边界：官方 mock 任务仍因 expected action sequence mismatch 失败，不能被解释为 memory 方法失败。
3. 本轮修改了工具失败统计口径：`tool_observation_error_count` 是总观察错误计数；`policy_violation_count` 与 `expected_negative_observation_count` 是可解释子类；`tool_semantic_error_count` 只代表剩余真正工具语义错误。历史日志中 phase2 state 的 `tool_semantic_error_count=1` 在新口径下应读作 `tool_observation_error_count=1` 且 `policy_violation_count=1`。
4. `official_like` 仍是本项目本地可解释 evaluator，不等价于官方 tau2 evaluator；但它与官方 action/env reward 组合的关键差异已进一步缩小。

用户复验建议命令：

```bash
conda activate rm
pip install -e ".[dev]"
python -m pytest

# 如果 data/external 下缺少官方仓库，先克隆：
git clone https://github.com/sierra-research/tau-bench.git data/external/tau-bench
git clone https://github.com/sierra-research/tau2-bench.git data/external/tau2-bench

git -C data/external/tau-bench rev-parse HEAD
git -C data/external/tau2-bench rev-parse HEAD

python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_state_raw_trace_rag.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_nomem.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_raw_trace_rag.yaml
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_action_replay.yaml

cat runs/tau_retail_phase2_official_tau2_action_replay_seed1/metrics.json
grep '6086499569' runs/tau_retail_phase2_official_tau2_action_replay_seed1/runs.jsonl
grep '"expected_negative_observations"' runs/tau_retail_phase2_official_tau2_action_replay_seed1/runs.jsonl
grep '"tool_semantic_errors": \[\]' runs/tau_retail_phase2_official_tau2_action_replay_seed1/runs.jsonl
```

实验日志填写建议：

1. 用户正式复验后再更新 `docs/experiment_log.md`，建议新增 `tau_retail_phase2_official_tau2_action_replay_seed1_round4_observation_taxonomy` 或在原 action-replay 条目下追加第四轮复验小节。
2. 重点记录 action-replay 指标变化：第三轮 `success_rate=0.6666666666666666`、`tool_semantic_error_count=1`；第四轮新口径下 `success_rate=1.0`、`tool_observation_error_count=1`、`expected_negative_observation_count=1`、`tool_semantic_error_count=0`。
3. 重点记录 state fixture 指标口径变化：pending return 仍是 policy violation，但不再算作 `tool_semantic_error`；应记录为 `tool_observation_error_count=1`、`policy_violation_count=1`、`tool_semantic_error_count=0`。
4. 本轮仍只用于 official adapter/evaluator 对齐，不用于报告 NT-MemEvo 方法收益。

下一步建议：

1. 在官方 action-replay 前 3 条全部通过后，可以进入真实 LLM actor `max_tasks=1/3` no-memory smoke，但必须先保留 failure taxonomy，不做 memory 收益结论。
2. 继续对齐 official reward basis：区分 DB、ACTION、COMMUNICATE、NL_ASSERTION 是否进入最终 reward，而不是只作为 detail 记录。
3. 对官方更多 task 的 read negative observation、mutation policy failure 和 unsupported criterion 做批量扫描，形成 official compatibility report。
4. 真实 no-memory actor 失败类型稳定后，再迁移 `raw_trace_rag` 对照；`nt_memevo_gate`、support verification 和 scope refinement 仍暂缓。

用户正式复验记录：

1. 用户在 Linux 机器 `BNUZ`、交互式 conda 环境 `(rm)` 下运行 `python -m pytest`，环境为 Python 3.12.13、pytest 9.0.3、pluggy 1.6.0，结果为 `36 passed in 0.11s`。
2. 用户确认官方仓库版本：`data/external/tau-bench` commit 为 `59a200c6d575d595120f1cb70fea53cef0632f6b`，`data/external/tau2-bench` commit 为 `2be691669909439cf88dedc13decf94b7664d262`。
3. `tau_retail_phase2_state_nomem.yaml` 复验通过：`success_rate=0.6666666666666666`、`expected_actions_matched_count=3`、`state_diff_passed_count=1`、`policy_violation_count=1`、`tool_observation_error_count=1`、`expected_negative_observation_count=0`、`tool_semantic_error_count=0`、`memory_policy=none`。
4. `tau_retail_phase2_state_raw_trace_rag.yaml` 复验通过：`success_rate=0.6666666666666666`、`memory_policy=raw_trace_rag`、`memory_size=3`、`memory_top_k=2`、`policy_violation_count=1`、`tool_observation_error_count=1`、`tool_semantic_error_count=0`、`negative_transfer_rate=0.0`。
5. `tau_retail_phase2_official_tau2_nomem.yaml` 复验通过并按预期失败：`success_rate=0.0`、`expected_actions_matched_count=0`、`expected_actions_failed_count=3`、`communicate_info_failed_count=1`、`nl_assertion_failed_count=1`、`tool_observation_error_count=0`、`tool_semantic_error_count=0`、`negative_transfer_rate=0.0`。
6. `tau_retail_phase2_official_tau2_raw_trace_rag.yaml` 复验通过并按预期失败：`success_rate=0.0`、`memory_policy=raw_trace_rag`、`memory_size=3`、`memory_top_k=2`、`expected_actions_failed_count=3`、`communicate_info_failed_count=1`、`nl_assertion_failed_count=1`、`tool_observation_error_count=0`、`negative_transfer_rate=0.0`。
7. `tau_retail_phase2_official_tau2_action_replay.yaml` 复验通过：`success_rate=1.0`、`avg_steps=8.0`、`avg_tool_calls=7.0`、`avg_prompt_tokens=0.0`、`expected_actions_matched_count=3`、`expected_actions_failed_count=0`、`communicate_info_passed_count=1`、`nl_assertion_passed_count=1`、`tool_observation_error_count=1`、`expected_negative_observation_count=1`、`tool_semantic_error_count=0`、`evaluator_error_types={}`。
8. 用户抽查 `runs/tau_retail_phase2_official_tau2_action_replay_seed1/runs.jsonl`，确认 task `2` 的 `get_product_details({"product_id": "6086499569"})` 仍返回 `Product 6086499569 was not found.`，但该 action 在 expected-vs-actual alignment 中 `matched=true`、`actual_ok=false`，并被归入 `expected_negative_observations`。
9. 用户用 `grep '"expected_negative_observations"'` 确认 task `2` 记录包含 expected negative observation；用 `grep '"tool_semantic_errors": []'` 确认三条 action-replay 任务均无剩余 tool semantic error。

复验结论：

1. 第二阶段第四轮 observation taxonomy 已通过目标环境复验。第三轮 action-replay 的剩余失败从 `tool_semantic_error` 被正确重分类为 `expected_negative_observation`，官方 tau2 前 3 条 base task 在 action-replay oracle 下全部通过。
2. 本轮 evaluator 口径变化不改变 mock actor 的能力边界：官方 no-memory/raw-trace-rag 仍因 action sequence mismatch 与自然语言断言缺失失败，不能解释为 memory 方法失败或负迁移。
3. 当前日志口径已经能同时区分 `tool_observation_error_count`、`policy_violation_count`、`expected_negative_observation_count` 和严格意义的 `tool_semantic_error_count`。后续实验必须按新口径解读历史 phase2 state 结果。
4. `docs/experiment_log.md` 已新增第四轮 observation taxonomy 复验补充；`docs/tau_retail_export_schema.md` 已同步 evaluator detail 字段说明。

## 第二阶段第五轮方向（基于第四轮复验）

优先方向：官方 tau2 真实 actor no-memory 小批量 smoke 与 reward-basis 兼容性报告。理由是第四轮已经让 action-replay oracle 在官方前 3 条 base task 上全部通过，adapter/evaluator 对 expected negative observation 的口径也稳定；下一步应验证真实 actor 在官方 tau2 retail 上的失败是否能被同一套 taxonomy 解释，而不是继续扩 action-replay 的方法链路。

第五轮建议范围：

1. 新增或整理真实 actor no-memory 配置，例如 `configs/tau_retail_phase2_official_tau2_real_actor_nomem.yaml`，默认 `max_tasks=1/3`、`evaluation=official_like`、`compare_action_args=true`、temperature 固定为 `0.0`，输出独立 run 目录。
2. 若当前环境没有可用真实 LLM API key，则先做 action-replay compatibility scan：把官方 base split 从前 3 条扩到 `max_tasks=10/20`，只统计 read negative observation、policy/precondition violation、unsupported criterion、state diff mismatch 和 communicate/nl assertion 覆盖情况。
3. 明确 reward basis 报告字段：ACTION、DB/state、COMMUNICATE、NL_ASSERTION、unsupported criteria、tool observation taxonomy 分别通过/失败多少次，以及哪些字段进入本地 `official_like.success` 的 fatal 判定。
4. 对真实 actor no-memory 结果只报告可解释失败类型和日志完整性，不报告 NT-MemEvo 方法收益；只有 no-memory 失败 taxonomy 稳定后，才迁移 `raw_trace_rag`。
5. 保持第四轮五组配置不回归，尤其是 action-replay 的 `success_rate=1.0`、`expected_negative_observation_count=1`、`tool_semantic_error_count=0`，以及官方 mock no-memory/raw-trace-rag 的 `negative_transfer_rate=0.0`。
6. 暂缓 `nt_memevo_gate`、support verification、scope refinement 和更大规模 memory 方法对照；这些需要等真实 actor no-memory 与 raw-trace-rag failure taxonomy 稳定后再进入主线。

第五轮验收标准：

1. `python -m pytest` 全量通过。
2. 第四轮五组复验命令继续可运行，metrics 字段口径不回退。
3. 真实 actor no-memory smoke 至少完成 `max_tasks=1`；若运行到 `max_tasks=3`，每条失败必须在 `runs.jsonl.evaluation_details` 中给出 action/state/communicate/nl/tool taxonomy。
4. 若真实 actor 不可用，action-replay compatibility scan 至少覆盖官方 base 前 10 条，并产出可写入 `docs/experiment_log.md` 的 compatibility summary。
5. `docs/experiment_log.md` 新增第五轮实验记录，明确当前仍处于 official adapter/evaluator/actor 对齐阶段，不进入 memory 方法收益结论。

## 2026-05-05 第二阶段第五轮

目标：在第四轮 action-replay oracle 与 observation taxonomy 稳定后，进入官方 tau2 真实 actor no-memory 小批量 smoke 的准备工作；同时按用户要求把真实 actor 调用策略从 OpenAI API 优先迁移为本地 `/home/fyk/models/Qwen/Qwen3.5-9B` + vLLM OpenAI-compatible 服务，并保留 action-replay scan10 作为真实 actor 暂不可用时的兼容性报告路径。

环境检查：

1. 当前 `conda run -n rm python` 为 Python 3.12.13。
2. 当前 `rm` 环境未安装 `vllm` 和 `openai` 包；因此本轮没有尝试直接启动真实 vLLM 服务。
3. 本地模型目录 `/home/fyk/models/Qwen/Qwen3.5-9B` 存在，大小约 19G，包含 tokenizer、chat template、config 和 4 个 safetensors 分片。
4. 官方数据仓库仍已在 `data/external/` 下准备好，本轮无需重新克隆真实数据。

已完成编码：

1. 修改 `src/ntmemevo/llm/client.py`，新增 `OpenAICompatibleChatClient`，使用 Python 标准库直接请求 OpenAI-compatible `/v1/chat/completions`，不依赖 OpenAI SDK。
2. `create_llm_client()` 新增 `provider=vllm` / `provider=local_vllm` / `provider=openai_compatible`，支持 `base_url_env`、`base_url`、`api_key`、`api_key_env`、`timeout_seconds`、`request_retries`、`retry_sleep_seconds`、`healthcheck`、`disable_response_format`、`strip_thinking`、`extract_json_object` 和 `extra_body`。
3. vLLM client 默认访问 `/v1/models` 做健康检查；如果服务未启动，会给出明确提示：先运行 `bash scripts/start_vllm_qwen35_9b.sh`，或在干跑配置时设置 `healthcheck=false`。
4. 针对本地 Qwen 可能输出 `<think>...</think>`、Markdown code fence 或 JSON 外文本的情况，client 支持在 `response_format={"type":"json_object"}` 时抽取首个 JSON object，降低真实 actor 因格式噪声直接 `invalid_json_response` 的概率。
5. 新增 `scripts/start_vllm_qwen35_9b.sh`，默认以 `served_model_name=qwen3.5-9b` 启动 `/home/fyk/models/Qwen/Qwen3.5-9B`，监听 `127.0.0.1:8000`，并支持 `CUDA_VISIBLE_DEVICES`、`PORT`、`GPU_MEMORY_UTILIZATION`、`MAX_MODEL_LEN`、`DTYPE`、`TENSOR_PARALLEL_SIZE` 等调度参数。
6. `pyproject.toml` 新增可选 extra `vllm`，用于目标服务器安装 `pip install -e ".[dev,vllm]"`；实验 client 本身仍不依赖该包，只有服务端启动脚本需要 vLLM。
7. 新增 `configs/tau_retail_phase2_official_tau2_real_actor_nomem.yaml`，默认运行官方 tau2 retail base split 前 1 条任务，`agent.type=react_tool_agent`，`models.actor.provider=vllm`，`model=qwen3.5-9b`，`base_url_env=VLLM_BASE_URL`，输出到 `runs/tau_retail_phase2_official_tau2_real_actor_nomem_seed1/`。
8. 新增 `configs/tau_retail_phase2_official_tau2_action_replay_scan10.yaml`，默认使用 action-replay oracle 扫描官方 base 前 10 条任务，作为真实 actor/GPU 调度不可用时的 reward-basis / observation taxonomy 兼容性报告。
9. 新增 `tests/test_llm_client.py`，用 mock `urllib.request.urlopen` 覆盖 vLLM/OpenAI-compatible client 的 healthcheck、chat completion payload、`response_format` 传递、Qwen thinking 清理、JSON 抽取和 usage 解析。
10. 更新 `README.md`，加入本地 vLLM 启动命令、GPU/端口调度方式、真实 actor 配置、scan10 fallback 命令和 vLLM actor 配置字段说明。

本轮本地验证：

1. `conda run -n rm python -m py_compile src/ntmemevo/llm/client.py tests/test_llm_client.py` 通过。
2. `conda run -n rm python -m pytest tests/test_llm_client.py -q` 通过：`1 passed in 0.02s`。
3. `conda run -n rm python -m pytest -q` 通过：`37 passed in 0.18s`。
4. `conda run -n rm python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_action_replay_scan10.yaml` 通过。
5. scan10 fallback 结果：`num_tasks=10`、`success_rate=1.0`、`avg_steps=8.5`、`avg_tool_calls=7.5`、`expected_actions_matched_count=10`、`expected_actions_failed_count=0`、`tool_observation_error_count=3`、`expected_negative_observation_count=3`、`tool_semantic_error_count=0`、`communicate_info_passed_count=3`、`nl_assertion_passed_count=3`、`unsupported_official_criteria_count=0`、`negative_transfer_rate=0.0`。
6. 未运行 `configs/tau_retail_phase2_official_tau2_real_actor_nomem.yaml`，原因是当前 `rm` 环境未安装 vLLM，且本轮不应在编码阶段占用 GPU 启动长驻服务。

用户复验建议命令：

```bash
conda activate rm
pip install -e ".[dev]"
python -m pytest

# 如需启动本地 Qwen/vLLM 服务，先在独立终端安装并启动：
pip install -e ".[dev,vllm]"
CUDA_VISIBLE_DEVICES=0 bash scripts/start_vllm_qwen35_9b.sh

# 另一个终端确认服务可用：
curl http://127.0.0.1:8000/v1/models

# 如果改用非默认端口，例如 PORT=8001，实验前同步设置：
export VLLM_BASE_URL=http://127.0.0.1:8001/v1

# 官方 action-replay compatibility fallback：
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_action_replay_scan10.yaml
cat runs/tau_retail_phase2_official_tau2_action_replay_scan10_seed1/metrics.json
grep '"expected_negative_observations"' runs/tau_retail_phase2_official_tau2_action_replay_scan10_seed1/runs.jsonl

# 本地 Qwen/vLLM real actor no-memory smoke，默认只跑 base 前 1 条：
python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_real_actor_nomem.yaml
cat runs/tau_retail_phase2_official_tau2_real_actor_nomem_seed1/metrics.json
tail -n 1 runs/tau_retail_phase2_official_tau2_real_actor_nomem_seed1/runs.jsonl
grep '"event_type": "model_parse_error"' runs/tau_retail_phase2_official_tau2_real_actor_nomem_seed1/trace_events.jsonl || true
```

实验日志填写建议：

1. vLLM 服务启动后，记录 `CUDA_VISIBLE_DEVICES`、`PORT`、`MODEL_PATH`、`SERVED_MODEL_NAME`、`MAX_MODEL_LEN`、`GPU_MEMORY_UTILIZATION` 和 vLLM 版本。
2. 真实 actor no-memory 默认先记录 `max_tasks=1`，若通过或失败可解释，再手动把配置中的 `benchmark.max_tasks` 改为 `3` 复验。
3. 对每条失败记录 `error_type`、`expected_actions_matched`、`state_diff_passed`、`communicate_info_passed`、`nl_assertions_passed`、`tool_observation_error_count`、`expected_negative_observation_count`、`policy_violation_count`、`tool_semantic_error_count` 和 `unsupported_official_criteria_count`。
4. 若 vLLM/GPU 暂不可用，则先把 scan10 的 compatibility summary 写入实验日志，明确这是 action-replay oracle 兼容性报告，不是真实 actor 或 memory 方法收益实验。

当前边界：

1. 本轮完成真实 actor 的本地 vLLM 调用链路和配置，但没有在当前编码环境启动 vLLM 服务，也没有产生真实 Qwen actor 结果。
2. `provider=vllm` 依赖外部长驻服务；推荐手动启动并固定 `CUDA_VISIBLE_DEVICES` / `PORT`，避免多实验抢同一 GPU 或端口。
3. scan10 action-replay 结果只说明官方前 10 条 expected actions、communicate/nl assertion 和 observation taxonomy 在 oracle 下可解释，不代表真实 actor 能力。
4. 第五轮仍处于 official adapter/evaluator/actor 对齐阶段，不报告 NT-MemEvo memory 方法收益。

下一步建议：

1. 在目标服务器启动 vLLM 后，先运行 `tau_retail_phase2_official_tau2_real_actor_nomem.yaml` 的 `max_tasks=1` smoke，检查是否存在 JSON 格式噪声、工具调用循环或 action mismatch。
2. 若 `max_tasks=1` 可解释，再扩到 `max_tasks=3`，并与第四轮 action-replay 前 3 条的 taxonomy 对齐。
3. 真实 no-memory actor 的 failure taxonomy 稳定后，再新增 `real_actor_raw_trace_rag` 小样本配置；`nt_memevo_gate`、support verification 和 scope refinement 继续暂缓。

用户正式复验记录（本地 Qwen/vLLM real actor）：

1. 用户在 Linux 机器 `BNUZ`、交互式 conda 环境 `(rm)` 下设置 `VLLM_BASE_URL=http://127.0.0.1:8000/v1`，运行 `python -m pytest`，结果为 `37 passed in 0.12s`。
2. 用户运行 `python -m ntmemevo.experiments.run_stream --config configs/tau_retail_phase2_official_tau2_real_actor_nomem.yaml`，真实 actor no-memory smoke 完成 `max_tasks=1`。
3. 真实 actor 指标：`num_tasks=1`、`success_rate=0.0`、`avg_reward=0.0`、`avg_steps=2.0`、`avg_prompt_tokens=1177.0`、`avg_completion_tokens=127.0`、`avg_tool_calls=1.0`、`expected_actions_matched_count=0`、`expected_actions_failed_count=1`、`evaluator_error_types={"unsupported_action": 1}`、`negative_transfer_rate=0.0`。
4. 抽查 `runs.jsonl`：task `0` 第一轮工具调用 `find_user_id_by_name_zip({"first_name":"Yusuf","last_name":"Rossi","zip":"19122"})` 与 official expected action 第一步匹配，tool observation 为 `user_id=yusuf_rossi_9620; name=Yusuf Rossi; zip=19122`。
5. 抽查 `trace_events.jsonl`：第二轮 model decision 的 thought 表示模型知道应继续查询 `get_order_details(order #W2378156)`，但解析后 `action=""`、`tool_name=null`，agent 因此返回 `Unsupported action: `。
6. 本轮没有 `model_parse_error`、没有 tool observation error、没有 expected negative observation、没有 policy violation、没有 tool semantic error，也没有 unsupported official criteria；失败完全落在真实 actor 输出协议/动作序列能力，而不是 adapter/tool/evaluator 语义或 memory 负迁移。
7. 用户单卡启动 vLLM 时遇到 24G 显存 OOM；脚本已补充 `TENSOR_PARALLEL_SIZE`，推荐双卡命令为 `CUDA_VISIBLE_DEVICES=0,1 TENSOR_PARALLEL_SIZE=2 GPU_MEMORY_UTILIZATION=0.85 MAX_MODEL_LEN=4096 bash scripts/start_vllm_qwen35_9b.sh`，若仍 OOM 可降到 `MAX_MODEL_LEN=2048`。

第五轮收口判断：

1. 第五轮目标已经完成：本地 Qwen/vLLM 服务链路、真实 actor 配置、official-like evaluator taxonomy 和日志输出均已在目标机器通过最小 `max_tasks=1` smoke。
2. 当前不应直接扩大到 `max_tasks=3`，因为第一条任务已经暴露真实 actor 输出协议问题；扩大样本只会重复收集 `unsupported_action`，不会推进 adapter/evaluator 对齐。
3. 本轮仍不报告 NT-MemEvo memory 方法收益；真实 actor no-memory 尚未稳定完成多步工具协议，raw-trace-rag / gate / replay / verification 都应继续暂缓。

## 第二阶段第六轮方向

优先方向：真实 actor 输出协议加固与可审计 raw model response 日志。理由是第五轮已经证明本地 Qwen/vLLM actor 能连通并正确执行第一步工具调用，但第二步出现“模型意图正确、输出协议不合格”的 `unsupported_action`；下一轮应先把真实 actor 的输出格式、修复路径和原始响应诊断稳定下来，再扩大官方 tau2 样本。

第六轮建议范围：

1. 在 `ReActToolAgent` 中为所有 model decision 增加可控 raw response 日志，尤其是成功 JSON 解析但 `action` 不在 `{tool, final}` 时，记录 `raw_response`、parsed decision、repair status 和 failure reason。
2. 强化 prompt 协议：明确每轮只能返回一个 JSON object，且必须包含 `action`；调用工具时必须包含 `tool_name` 和 `args`；不得只写 thought 或漏写 action。
3. 实现保守 action repair：若模型输出包含可识别 `tool_name`/`tool` 和 dict 类型 `args`/`arguments`，但漏写 `action`，可修复为 `action=tool`，并写入 `model_action_repair` trace event；不能修复时继续 `unsupported_action`。
4. 增加单元测试覆盖：合法 tool action 不变、缺失 action 但含 tool_name 可修复、缺失 action 且无工具名不可修复、raw response 日志按预期写出。
5. 复验 `tau_retail_phase2_official_tau2_real_actor_nomem.yaml` 的 `max_tasks=1`；若不再停在第二步 `unsupported_action`，再考虑扩到 `max_tasks=3`。
6. 保持 action-replay scan10 和全部 tiny/tau adapter 回归测试不变，确保真实 actor parser 加固不影响 mock/action-replay 路径。

第六轮验收标准：

1. `python -m pytest` 全量通过。
2. 真实 actor `max_tasks=1` 不再因“漏写 action 但有明确工具意图”直接丢失原始响应；要么被可审计 repair，要么在 trace 中保留 raw response 和不可修复原因。
3. 若 repair 后 task 0 继续推进到 `get_order_details` 或更深工具链，记录新的 failure taxonomy；若仍失败，必须能从日志看到原始模型输出。
4. 不扩大到 memory 方法收益实验；第六轮仍只服务于 official real actor 输出协议和 failure taxonomy 稳定。
