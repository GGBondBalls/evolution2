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
