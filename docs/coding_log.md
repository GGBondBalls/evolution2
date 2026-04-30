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
