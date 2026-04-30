# 负迁移感知的 Agent 自进化记忆系统：研究方案与实验路线图

本文档面向从零编码、实验和论文写作，目标是把“带负迁移检测的自进化记忆系统”落成一个可复现、可扩展、可投稿 CCF-A 方向会议的研究项目。

建议暂定论文题目：

**NT-MemEvo: Negative-Transfer-Aware Memory Evolution for Self-Improving LLM Agents**

中文可称为：

**负迁移感知的自进化 Agent 记忆系统**

## 1. 核心判断

Agent 自进化不应只等同于“让模型反思一次并把反思追加到 prompt”。近期趋势已经从 Reflexion 式 episodic memory，发展到 ReasoningBank 式 reasoning memory、G-Memory 式层次图记忆、MemoryOS 式长短期记忆管理。它们共同说明：外部记忆是无需更新模型权重即可实现 agent 行为进化的关键路径。

但当前记忆型自进化有一个明显缺口：**记忆不是天然有益的**。错误经验、过度泛化的策略、过期规则、不适用任务域、LLM 自我总结偏差，都会导致 negative transfer。现有方法通常强调“如何存更多经验、如何检索相似经验、如何总结成功失败”，但较少系统回答：

1. 一条记忆到底在什么条件下有用？
2. 它是否曾经伤害过相似任务？
3. 检索到的记忆是否应该被注入当前 agent 上下文？
4. 记忆何时应该被降权、拆分、合并、隔离或删除？
5. 自进化过程中如何防止“学坏”和 regression？

本项目的核心创新点就是把 agent memory 从“经验仓库”升级为“可验证、可度量、可回滚的进化对象”。

## 2. 研究问题

### 2.1 问题定义

设 agent 在任务流 \(\mathcal{D} = \{x_1, x_2, ..., x_T\}\) 上运行。基础 agent 为：

\[
A_0 = (M_\theta, P, T, \pi)
\]

其中 \(M_\theta\) 是大模型，\(P\) 是 prompt，\(T\) 是工具集，\(\pi\) 是决策策略。加入记忆后：

\[
A_B = (M_\theta, P, T, \pi, B)
\]

\(B\) 是随任务流不断更新的记忆库。

传统 memory agent 目标是：

\[
\max_B \mathbb{E}_{x \sim \mathcal{D}}[R(A_B, x)]
\]

但该目标不区分有益记忆和有害记忆。本文应引入负迁移约束：

\[
\max_B \mathbb{E}_{x \sim \mathcal{D}}[R(A_B, x) - \lambda C(A_B, x)]
\]

subject to:

\[
\Pr[R(A_B, x) < R(A_{\emptyset}, x) - \epsilon] \leq \delta
\]

其中 \(C\) 是 token、工具调用、时间等成本；\(\epsilon\) 是允许波动阈值；\(\delta\) 是最大可接受负迁移率。

### 2.2 负迁移定义

对单条记忆 \(m\)，如果 agent 使用该记忆后的结果比不使用该记忆更差，则认为该记忆在任务 \(x\) 上造成负迁移：

\[
NT(m,x)=\mathbb{I}[R(A_{B_m},x)<R(A_{B\setminus m},x)-\epsilon]
\]

实际实验中，不可能对每条记忆、每个任务都完整反事实重跑，所以需要近似估计：

1. 在线估计：根据“记忆被使用后的任务结果”更新 utility。
2. 局部反事实：只对 top-k 高影响记忆做 leave-one-memory-out replay。
3. 支持集验证：新记忆进入主库前，在相似任务 replay set 上测试。
4. 风险惩罚：对高不确定性、低证据、过期或跨域记忆降低检索权重。

## 3. 论文主张

### 3.1 核心假设

本文可以围绕四个可验证假设展开。

**H1：记忆的负迁移是 agent 自进化中的真实瓶颈。**

相比无记忆 agent，普通 memory agent 在平均成功率上可能提高，但会在部分任务上显著失败。这类失败可通过“with-memory fail, no-memory success”的反事实对比测量。

**H2：带适用范围和反例证据的记忆，比普通自然语言反思更稳健。**

只保存“下次应该怎样做”的经验不够，还应保存“什么时候适用、什么时候不适用、曾在哪些任务上失败”。

**H3：将记忆选择建模为 contextual bandit，可以降低有害记忆注入概率。**

每条记忆的效用不是常数，而依赖任务上下文。应根据任务特征和历史反馈动态估计。

**H4：加入验证门控和回滚机制后，agent 的 lifelong learning curve 更稳定。**

自进化系统不只要最终成功率高，还要减少 regression、降低 token 成本、提升跨任务泛化。

### 3.2 预期贡献

建议论文 contribution 写成三点：

1. 提出一种负迁移感知的 agent memory 表示，每条记忆包含适用条件、正证据、反例证据、置信度、生命周期和风险估计。
2. 提出 memory utility learning 与 verification-gated consolidation 机制，把记忆检索和记忆写入都变成可学习、可验证、可回滚的过程。
3. 在交互式工具任务、代码修复任务和长程环境任务上证明该机制相比 Reflexion、Raw Trace RAG、success-only memory、ReasoningBank-like memory 和 MemoryOS-like hierarchy 更高效、更稳健、更少负迁移。

## 4. 相关工作定位

### 4.1 Reflexion

Reflexion 将环境反馈转成自然语言反思，并写入 episodic memory，在后续尝试中作为上下文使用。它的价值是证明“不更新模型权重也能通过语言反馈实现行为改进”。但它的问题是记忆通常较粗粒度，缺少适用范围、反例和生命周期控制。

### 4.2 ReasoningBank

ReasoningBank 将成功和失败经验蒸馏成 generalizable reasoning strategies，并在测试时检索使用。它非常接近本课题，但其重点是 experience scaling 和 reasoning memory 的收益，而不是系统地检测 harmful memory、negative transfer 和 regression。

### 4.3 G-Memory

G-Memory 面向多智能体系统，将交互轨迹组织成 insight、query、interaction 三层图结构。它说明长期轨迹不能只用扁平文本存储。但它主要处理多智能体协作记忆，并不直接解决单条记忆何时伤害当前任务的问题。

### 4.4 MemoryOS

MemoryOS 从操作系统视角管理 short-term、mid-term、long-term memory，有明确的存储、更新、检索和生成模块。它适合作为系统架构启发或 baseline，但其目标更偏个性化对话记忆，不是 agent task-solving 中的负迁移控制。

### 4.5 本文差异

本文不单纯提出一种新的 memory store，而是提出一个闭环：

\[
Trace \rightarrow Candidate Memory \rightarrow Verification \rightarrow Utility Update \rightarrow Risk-aware Retrieval \rightarrow Regression Guard
\]

这使得记忆成为可进化对象，而不是无限追加的文本缓冲区。

## 5. 方法设计

### 5.1 总体架构

系统由八个模块组成：

1. `EnvAdapter`：封装不同 benchmark 的任务加载、环境交互、reward 计算。
2. `AgentRunner`：执行 ReAct / tool-use / coding agent，记录完整 trace。
3. `TraceLogger`：统一存储 action、observation、tool call、memory usage、reward、cost。
4. `MemoryExtractor`：从成功和失败轨迹中抽取候选记忆。
5. `MemoryStore`：管理记忆单元、embedding、证据、效用、状态。
6. `RetrieverGate`：根据语义相似度、适用条件、效用和风险选择记忆。
7. `MemoryVerifier`：对候选记忆或高风险记忆做 replay / counterfactual 验证。
8. `ExperimentScheduler`：控制串行迭代、baseline、消融、随机种子和预算。

### 5.2 记忆单元设计

不要只存一句自然语言经验。推荐每条记忆使用结构化 JSON：

```json
{
  "memory_id": "mem_000001",
  "type": "strategy | warning | constraint | tool_usage | bug_pattern | user_policy",
  "claim": "When the user asks to exchange an item, first verify the original order status and whether the replacement item is in stock.",
  "scope": {
    "benchmark": "tau-bench",
    "domain": "retail",
    "intent": "exchange_item",
    "tool_names": ["get_order_details", "get_product_details", "exchange_delivered_order_items"],
    "preconditions": [
      "user request involves item exchange",
      "order_id is known or can be asked",
      "policy document is available"
    ]
  },
  "action_hint": "Collect order_id, check delivered status, check replacement availability, then call exchange tool.",
  "avoid_hint": "Do not call exchange tool before checking eligibility and replacement stock.",
  "positive_evidence": ["run_001", "run_017"],
  "negative_evidence": ["run_029"],
  "utility": {
    "alpha": 3.0,
    "beta": 2.0,
    "mean_delta_reward": 0.12,
    "lcb_delta_reward": -0.03,
    "num_used": 5,
    "num_helpful": 3,
    "num_harmful": 1
  },
  "lifecycle": {
    "status": "candidate | active | quarantined | retired",
    "created_iter": 4,
    "last_used_iter": 9,
    "ttl": 50
  },
  "source": {
    "created_from": ["run_001", "run_002"],
    "extractor_model": "configured_model_name",
    "prompt_hash": "sha256..."
  }
}
```

关键点：

1. `claim` 是可读的规则。
2. `scope` 控制适用范围，避免过度泛化。
3. `positive_evidence` 和 `negative_evidence` 同时保留。
4. `utility` 用于在线学习。
5. `status` 支持隔离和回滚。

### 5.3 记忆检索公式

传统 RAG 通常只按 embedding similarity 排序：

\[
Score(m,x)=sim(m,x)
\]

本文应改为风险感知检索：

\[
Score(m,x) =
w_s \cdot Sim(m,x)
+ w_p \cdot Precond(m,x)
+ w_u \cdot U(m,x)
- w_r \cdot Risk(m,x)
- w_a \cdot Age(m)
- w_c \cdot Cost(m)
\]

其中：

1. `Sim(m,x)`：语义相似度。
2. `Precond(m,x)`：适用条件匹配度，可由规则匹配或 LLM classifier 判断。
3. `U(m,x)`：上下文相关效用估计。
4. `Risk(m,x)`：负迁移风险。
5. `Age(m)`：过期惩罚。
6. `Cost(m)`：注入上下文的 token 成本。

初版可以实现为线性打分，论文后期可升级为 learned ranker。

### 5.4 记忆效用更新

每次 agent 运行结束后，记录本轮注入了哪些记忆：

\[
M_x = \{m_1, m_2, ..., m_k\}
\]

如果任务成功，所有被用到的记忆不应都简单加分；因为成功可能来自模型本身、工具调用、其他记忆或任务简单。初版可以使用三种 credit 估计：

**Level 1：Outcome update**

简单稳定，适合快速跑通。

\[
\alpha_m \leftarrow \alpha_m + R
\]

\[
\beta_m \leftarrow \beta_m + (1-R)
\]

**Level 2：Leave-one-memory-out replay**

对 top-k 记忆重跑一次去除实验：

\[
\Delta_m = R(A_{M_x},x) - R(A_{M_x \setminus m},x)
\]

如果 \(\Delta_m > 0\)，说明该记忆有帮助；如果 \(\Delta_m < 0\)，说明可能造成负迁移。

**Level 3：Matched replay**

在相似任务集合 \(S_m\) 上验证：

\[
\hat{U}(m) = \frac{1}{|S_m|}\sum_{x\in S_m}[R(A_{+m},x)-R(A_{-m},x)]
\]

初始实现建议使用 Level 1 + 少量 Level 2。正式实验和消融再加入 Level 3。

### 5.5 候选记忆生成

MemoryExtractor 输入：

1. 任务 instruction。
2. agent trace。
3. final reward。
4. evaluator feedback。
5. 使用过的工具和失败信息。
6. 当前已有相似记忆。

输出候选记忆，必须是结构化 JSON。生成 prompt 应强制模型区分：

1. 可泛化策略。
2. 任务特定事实。
3. 失败警告。
4. 工具使用约束。
5. 不应写入记忆的偶然细节。

候选记忆不直接进入 active memory，而是进入 candidate pool。

### 5.6 验证门控

候选记忆 \(m\) 被接受前，需要经过验证：

1. 找到与其 `scope` 匹配的 support tasks。
2. 对 support tasks 分别运行 `with m` 和 `without m`。
3. 计算平均收益、负迁移率和置信下界。
4. 若通过阈值，进入 active memory；否则 quarantine。

接受条件可设为：

\[
LCB(\Delta_m) > \tau_u
\]

\[
NTR(m) < \tau_{nt}
\]

其中 \(LCB\) 是收益置信下界，\(NTR\) 是 negative transfer rate。

工程上，如果 replay 成本太高，可以先只对高频候选记忆和高风险候选记忆验证。

### 5.7 生命周期管理

记忆状态机：

```text
candidate -> active -> quarantined -> retired
             active -> retired
             quarantined -> active
```

状态转换规则：

1. `candidate -> active`：验证通过。
2. `active -> quarantined`：连续造成负迁移或风险过高。
3. `quarantined -> active`：在新验证集上恢复正收益。
4. `active -> retired`：长期未使用、过期、被更高质量记忆替代。
5. `candidate -> retired`：验证失败且无修复价值。

### 5.8 记忆合并与拆分

自进化记忆库会膨胀，必须控制规模。

合并规则：

1. claim 高相似。
2. scope 高重叠。
3. evidence 不冲突。
4. 合并后 token 更少。

拆分规则：

1. 同一记忆在 domain A 有益，在 domain B 有害。
2. negative evidence 聚集在某个 intent 或 tool 上。
3. claim 太宽泛，例如“always ask user for confirmation”。

拆分示例：

原记忆：

```text
Always ask the user for confirmation before changing an order.
```

拆分后：

```text
For retail returns, ask for confirmation before initiating refund if policy requires explicit consent.
```

```text
For airline rebooking, do not ask redundant confirmation after user has already confirmed the new itinerary and price difference.
```

这类拆分正是论文亮点：负迁移不是简单删除记忆，而是收窄适用范围。

## 6. 推荐 Benchmark

### 6.1 首选：τ-bench / tau2-bench

推荐作为主 benchmark。

理由：

1. 任务是多轮用户-工具交互，符合 agent 设定。
2. 有 domain-specific policy，记忆可以学习规则和工具调用顺序。
3. final evaluation 可通过数据库状态和目标状态自动判断，减少 LLM judge 偏差。
4. 原论文提出 pass^k，用于评价多次试验下的 agent 可靠性，适合测记忆是否提升稳定性。
5. 相比 WebArena，工程成本低；相比 HumanEval，记忆迁移意义更强。

当前 Sierra 维护的仓库已有 tau2/tau3 相关更新。论文实验必须固定 commit 或 release tag，避免 benchmark 漂移。

建议任务组织：

1. `retail` 作为开发和主实验域。
2. `airline` 作为跨域泛化域。
3. 如果使用新版 tau2/tau3，可加入 `banking_knowledge` 作为带检索知识的附加实验，但不要让主结果依赖过新且不稳定的 benchmark。

### 6.2 第二选择：SWE-bench Lite / Verified

适合作为强说服力的代码 agent 实验。

优点：

1. 真实 GitHub issue。
2. Docker 可复现测试。
3. 代码修复任务有明确 pass/fail。
4. 记忆可学习 debugging pattern、repo navigation strategy、test failure pattern。

缺点：

1. 环境成本高。
2. 单次运行成本高。
3. 任务之间迁移不一定稳定。
4. 如果只跑很小子集，说服力有限。

建议路线：

1. 先跑 30-50 个实例验证方法。
2. 后续扩到 SWE-bench Lite 300 个实例。
3. 如果时间充足，使用 SWE-Bench-CL 或自己按 repo/time 构造 continual split，突出 lifelong learning。

### 6.3 第三选择：ALFWorld

适合快速验证交互式长程决策。

优点：

1. 安装成本低于 WebArena。
2. 任务有明确成功失败。
3. 有相似任务类型，适合测试经验记忆迁移。

缺点：

1. 不是当前最热的 web/tool benchmark。
2. 论文说服力弱于 τ-bench 和 SWE-bench。

建议作为早期 debug benchmark 或 appendix。

### 6.4 第四选择：WebArena / WebArena-Verified

适合作为最终增强实验。

优点：

1. 真实 web 环境。
2. 长程、多工具、强 agent 属性。
3. 对 robust memory 很有价值。

缺点：

1. 环境复杂。
2. 成本高。
3. 失败原因多，credit assignment 难。

建议在方法稳定后加入 WebArena-Verified 小规模实验。不要作为第一阶段主战场。

### 6.5 不建议作为主实验：纯 QA 记忆 benchmark

LoCoMo、LongMemEval、HotpotQA、GAIA 可作为辅助实验，但不建议作为主实验。原因是本文关注的是 task-solving agent 的经验负迁移，而不是单纯长对话记忆或知识问答。

## 7. 数据获取与实验数据组织

### 7.1 τ-bench 数据获取

建议使用官方仓库：

```bash
git clone https://github.com/sierra-research/tau-bench
```

或当前维护版本：

```bash
git clone https://github.com/sierra-research/tau2-bench
```

必须记录：

1. 仓库 URL。
2. commit hash。
3. domain。
4. task list。
5. user simulator model。
6. agent model。
7. random seed。
8. policy document版本。

建议先抽样：

```text
retail_train: 100 tasks
retail_dev: 50 tasks
retail_test: full or 100 tasks
airline_transfer_test: 100 tasks
```

如果任务数量不足，采用多 seed repeated trials，并报告 pass^k。

### 7.2 SWE-bench 数据获取

使用 Hugging Face dataset：

```python
from datasets import load_dataset
data = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
```

评估使用官方 Docker harness。必须保存每个 instance 的：

1. `instance_id`
2. `repo`
3. `base_commit`
4. `problem_statement`
5. generated patch
6. test result
7. logs

如果做 continual split，推荐按 repo 分组：

```text
train memory: django, sympy, sklearn subset
dev: same repos later tasks
test-in-domain: same repos unseen tasks
test-cross-repo: flask, astropy, matplotlib subset
```

更严格方案是按时间顺序分割，避免未来经验泄漏到过去任务。

### 7.3 ALFWorld 数据获取

使用官方仓库：

```bash
git clone https://github.com/alfworld/alfworld.git
```

建议先使用 text-only setting。记录：

1. task type。
2. scene id。
3. goal。
4. action sequence。
5. success flag。

记忆可以按 task type 学习，例如 pick-and-place、heat-and-place、clean-and-place。

### 7.4 实验日志格式

建议从第一天开始就统一日志，否则后期无法做消融和统计。

目录结构：

```text
runs/
  exp_2026_04_28_tau_retail_ntmemevo/
    config.yaml
    tasks.jsonl
    runs.jsonl
    trace_events.jsonl
    memories.jsonl
    memory_updates.jsonl
    replay_results.jsonl
    metrics.json
```

`runs.jsonl` 示例：

```json
{
  "run_id": "run_000001",
  "experiment_id": "tau_retail_ntmemevo_seed1",
  "task_id": "retail_042",
  "iteration": 3,
  "agent": "react_tool_agent",
  "memory_policy": "nt_memevo",
  "model": "configured_model_name",
  "seed": 1,
  "success": true,
  "reward": 1.0,
  "num_steps": 8,
  "prompt_tokens": 2310,
  "completion_tokens": 740,
  "tool_calls": 5,
  "used_memory_ids": ["mem_000014", "mem_000021"],
  "latency_sec": 42.7,
  "error_type": null
}
```

`trace_events.jsonl` 示例：

```json
{
  "run_id": "run_000001",
  "step": 4,
  "event_type": "tool_call",
  "thought_summary": "Need to verify order eligibility before exchange.",
  "tool_name": "get_order_details",
  "tool_args_hash": "sha256...",
  "observation_summary": "Order was delivered 3 days ago.",
  "used_memory_ids": ["mem_000014"]
}
```

注意：不建议存完整 chain-of-thought。可以存模型可公开的 action rationale summary、tool call、observation summary 和 prompt hash。

## 8. 模型推理设计

### 8.1 Provider 抽象

从第一版开始实现统一接口：

```python
class LLMClient:
    def complete(self, messages, temperature, max_tokens, response_format=None):
        ...
```

不要把 OpenAI、Anthropic、Gemini、vLLM、Ollama 的调用散落在 agent 代码里。所有模型调用都经过：

1. request hash。
2. cache lookup。
3. rate limit。
4. retry。
5. cost logging。
6. raw response 保存。

### 8.2 模型角色

建议分三类模型调用：

1. `ActorModel`：执行 agent 动作。
2. `MemoryModel`：从轨迹中抽取候选记忆。
3. `VerifierModel`：判断 scope/precondition、合并拆分记忆、生成结构化解释。

初期可三者共用同一个模型，便于控制变量。论文正式实验可测试：

1. 小模型 actor + 小模型 memory。
2. 小模型 actor + 强模型 memory。
3. 强模型 actor + 小模型 memory。

这样可以回答“记忆系统是否能让弱 agent 受益”。

### 8.3 推理参数

主实验建议：

```yaml
actor:
  temperature: 0.0
  max_tokens: 2048
memory_extractor:
  temperature: 0.2
  max_tokens: 2048
verifier:
  temperature: 0.0
  max_tokens: 1024
```

原因：

1. Actor 低温保证可复现。
2. Extractor 可有轻微随机性，产生不同候选经验。
3. Verifier 低温保证稳定。

若 benchmark 使用 user simulator，应固定 user simulator 模型和 seed。

### 8.4 Prompt 注入格式

注入记忆时不要直接塞一堆文本。建议格式：

```text
Relevant Verified Memories:

[M1 | type=constraint | confidence=0.82 | scope=retail.exchange_item]
Use this when: user wants to exchange a delivered item.
Do: verify order status and replacement stock before calling exchange tool.
Avoid: calling exchange tool before eligibility checks.
Evidence: helped 5 similar tasks, harmed 0 verified tasks.

[M2 | type=warning | confidence=0.64 | scope=retail.refund]
Use this when: refund request involves payment method mismatch.
Do: check original payment method before promising refund route.
Avoid: assuming store credit is always allowed.
Evidence: helped 2 similar tasks, harmed 1 task; use cautiously.
```

这样 actor 能看到置信度和适用范围，而不是盲从记忆。

## 9. 串行自进化流程

### 9.1 两种评价协议

必须同时区分两种 setting。

**Protocol A：Prequential Online Evaluation**

任务流中，每个任务先评估，再根据结果更新记忆：

```text
for task in stream:
    retrieve memory
    run agent and record reward
    update memory using this task
```

该协议衡量 lifelong learning 的在线收益。第 \(t\) 个任务不能使用第 \(t\) 个任务运行后产生的记忆。

**Protocol B：Train-then-Freeze Transfer Evaluation**

先在训练流中积累记忆，然后冻结，在 held-out test 上评估：

```text
for task in train_stream:
    run agent
    update memory

freeze memory

for task in test_set:
    retrieve memory
    run agent
    do not update memory
```

该协议衡量泛化能力，防止审稿人质疑 test-time contamination。

### 9.2 推荐主流程

每一轮 iteration：

```text
1. Load next batch of tasks.
2. For each task:
   2.1 Build task representation.
   2.2 Retrieve candidate memories.
   2.3 Apply RetrieverGate to select top-k verified memories.
   2.4 Run agent.
   2.5 Save trace and reward.
3. Extract candidate memories from traces.
4. Merge duplicate candidates.
5. Verify high-priority candidates on replay set.
6. Activate, quarantine, split, or retire memories.
7. Run regression probe set.
8. Save metrics and checkpoint memory store.
```

### 9.3 Replay set 构造

Replay set 是防止记忆学坏的关键。

建议维护三类 replay：

1. `support_success_set`：过去成功任务，用于验证记忆不会破坏已有能力。
2. `support_failure_set`：过去失败任务，用于验证记忆是否能修复失败。
3. `near_miss_set`：with-memory 失败但 no-memory 成功的任务，用于检测负迁移。

每轮只抽小样本 replay，控制成本：

```yaml
replay:
  max_tasks_per_iter: 16
  leave_one_memory_out_topk: 3
  candidate_verify_topn: 10
```

## 10. Baseline 设计与复现

### 10.1 Baseline 0：No Memory ReAct

基础 agent，不使用任何长期记忆。

作用：

1. 测量记忆系统的净收益。
2. 计算 negative transfer rate。

### 10.2 Baseline 1：Raw Trace RAG

把过去完整或压缩轨迹存入向量库，按相似度检索 top-k 注入。

作用：

1. 检查“直接存轨迹”是否足够。
2. 通常会暴露 token 成本高、噪声多、负迁移高的问题。

### 10.3 Baseline 2：Reflexion

每次失败或成功后生成自然语言 reflection，后续任务检索或追加 reflection。

复现要点：

1. 保持 reflection 长度上限。
2. 只用文本反馈，不做结构化 utility。
3. 不做负迁移检测。

### 10.4 Baseline 3：Success-only Memory

只从成功轨迹总结经验。

作用：

1. 检查失败经验是否重要。
2. 检查 success-only 是否导致过度自信和负迁移。

### 10.5 Baseline 4：Failure-only Warning Memory

只从失败轨迹总结 warning。

作用：

1. 检查“避错型记忆”是否比“成功策略”更有价值。
2. 对工具交互任务可能很强。

### 10.6 Baseline 5：ReasoningBank-like

从成功和失败经验蒸馏 general reasoning strategy，按相似度检索使用。

如果官方代码不可用，可做 method-level reimplementation，并在论文中明确称为 `ReasoningBank-style`。

### 10.7 Baseline 6：MemoryOS-like Hierarchy

实现 short-term、mid-term、long-term 三层记忆，不加入负迁移检测。

作用：

1. 对比“层次记忆管理”与“负迁移感知管理”的差异。
2. 如果直接使用 MemoryOS 开源代码，应注意它偏对话记忆，可能需要封装成 agent memory backend。

### 10.8 Baseline 7：Random Memory

随机检索同数量记忆。

作用：

1. 验证收益不是来自额外 token 或 prompt 变长。
2. 作为 sanity check。

### 10.9 Upper Bound：Oracle Scope Memory

使用 benchmark label 或人工标签选择同 intent/domain 的记忆。

作用：

1. 给出 memory retrieval 的上限。
2. 证明 RetrieverGate 还有提升空间。

## 11. 主实验设计

### 11.1 实验一：τ-bench 主结果

目标：证明 NT-MemEvo 在工具交互任务上提升成功率、降低负迁移和成本。

设置：

```text
Benchmark: τ-bench retail + airline
Evaluation: pass^1, pass^k, database-state success
Agent: ReAct tool agent
Models: 固定 actor model，固定 user simulator
Memory budget: top-k = 3 or 5
Iterations: 5-10
Seeds: 3
```

对比：

1. No Memory。
2. Raw Trace RAG。
3. Reflexion。
4. Success-only Memory。
5. ReasoningBank-like。
6. NT-MemEvo。

报告：

1. final success rate。
2. learning curve。
3. pass^k。
4. average steps。
5. token cost。
6. negative transfer rate。

### 11.2 实验二：跨域泛化

目标：证明记忆不是过拟合 retail，而能迁移或正确拒绝迁移。

设置：

```text
Train memory: retail
Test: airline
```

或：

```text
Train memory: airline
Test: retail
```

关键不是一定要跨域大幅提升，而是证明：

1. 有用的通用记忆可以迁移。
2. 不适用记忆会被 RetrieverGate 拒绝。
3. 普通相似度检索更容易产生负迁移。

### 11.3 实验三：SWE-bench 小规模验证

目标：证明方法不仅适用于 customer-service tools，也适用于代码 agent。

设置：

```text
Benchmark: SWE-bench Lite subset
Subset size: 30 -> 100 -> 300
Agent: simple coding agent or SWE-agent wrapper
Reward: resolved / not resolved
Memory type: bug_pattern, repo_navigation, test_debugging, patch_warning
```

建议第一版不要自己写完整代码 agent，可封装现有 SWE-agent 或简化 agent：

1. 查看 issue。
2. 搜索相关文件。
3. 修改代码。
4. 运行测试。
5. 根据失败反馈迭代。

记忆示例：

```text
For Django migration-related failures, inspect tests and release notes before changing model fields; avoid broad changes to migration autodetector unless failing tests directly target it.
```

### 11.4 实验四：记忆污染鲁棒性

目标：突出负迁移检测价值。

构造污染记忆：

1. 错误规则。
2. 过度泛化规则。
3. 跨域不适用规则。
4. 从失败轨迹错误总结出的规则。

比较不同方法在污染率 0%、10%、20%、40% 下的性能下降。

指标：

1. success rate drop。
2. harmful memory usage rate。
3. quarantine precision。
4. recovery speed。

这是非常有论文辨识度的实验。

### 11.5 实验五：长期学习曲线

目标：证明自进化不是单次 prompt trick。

设置：

```text
Task stream length: 200-500
Evaluation window: every 25 tasks
Report: cumulative reward and moving average success
```

关注：

1. 是否越学越好。
2. 是否出现性能崩塌。
3. 是否 memory size 失控。
4. 是否 token cost 随时间增长。

## 12. 消融实验

必须做以下消融，否则论文说服力不足。

### 12.1 去掉 negative evidence

只保留正证据，删除 `negative_evidence`。

预期：成功率可能略升或持平，但负迁移率上升。

### 12.2 去掉 scope/precondition

所有记忆只按 embedding similarity 检索。

预期：跨域泛化下降，污染实验中性能明显下降。

### 12.3 去掉 verification gate

候选记忆直接进入 active。

预期：早期提升快，但长期 regression 更严重。

### 12.4 去掉 lifecycle quarantine

有害记忆不隔离，只更新分数。

预期：重复失败更多，恢复速度慢。

### 12.5 去掉 memory splitting

过宽记忆不能拆分，只能保留或删除。

预期：要么保留导致负迁移，要么删除导致遗忘。

### 12.6 不同 top-k

测试 top-k = 1, 3, 5, 10。

预期：普通 RAG 随 top-k 增加更易噪声污染；NT-MemEvo 更稳定。

### 12.7 不同 replay budget

测试 replay budget = 0, 4, 8, 16, 32。

预期：存在成本-收益拐点。该实验可支撑“预算感知”的分析。

## 13. 指标体系

### 13.1 任务成功指标

```text
Success Rate = #success / #tasks
```

τ-bench 使用：

```text
pass^1, pass^k
```

SWE-bench 使用：

```text
resolved rate
```

### 13.2 成本指标

```text
Average Prompt Tokens
Average Completion Tokens
Average Tool Calls
Average Steps
Average Wall-clock Time
```

### 13.3 负迁移指标

定义 no-memory agent 成功、with-memory agent 失败的比例：

\[
NTR = \frac{|\{x: R(A_0,x)=1 \land R(A_B,x)=0\}|}{|\{x: R(A_0,x)=1\}|}
\]

也可定义 reward delta：

\[
\Delta R = R(A_B,x)-R(A_0,x)
\]

报告：

1. average \(\Delta R\)。
2. fraction of \(\Delta R < 0\)。
3. severe negative transfer rate。

### 13.4 记忆质量指标

```text
Memory Precision = helpful used memories / used memories
Memory Harm Rate = harmful used memories / used memories
Memory Coverage = tasks using at least one active memory / all tasks
Quarantine Precision = truly harmful quarantined memories / quarantined memories
Active Memory Size
Average Memory Age
```

### 13.5 稳定性指标

```text
Regression Rate = tasks solved in previous window but failed after memory update
Recovery Steps = iterations needed to recover after memory pollution
Learning Curve AUC = area under moving average success curve
```

### 13.6 统计检验

建议：

1. 对 success rate 使用 bootstrap 95% CI。
2. 对 paired task results 使用 McNemar test。
3. 对多 seed learning curve 报告均值和标准差。
4. 对成本指标使用 paired t-test 或 Wilcoxon signed-rank。

## 14. 编码路线图

### Week 1：项目骨架

目标：能加载任务、调用模型、保存日志。

实现：

```text
src/
  llm/
    client.py
    cache.py
  envs/
    base.py
    tau_bench.py
  agents/
    react_agent.py
  logging/
    trace_logger.py
  configs/
    tau_retail_nomem.yaml
```

验收：

1. 跑通 5 个 τ-bench task。
2. 生成 `runs.jsonl` 和 `trace_events.jsonl`。
3. 能复现实验结果。

### Week 2：No-memory 和 Raw Trace RAG baseline

目标：建立最基本对照。

实现：

```text
memory/
  raw_trace_store.py
  retriever.py
```

验收：

1. No Memory 跑 50 个 task。
2. Raw Trace RAG 跑 50 个 task。
3. 统计 success、cost、steps。

### Week 3：Reflexion baseline

目标：复现反思记忆。

实现：

```text
memory/
  reflection_memory.py
prompts/
  reflection_extract.md
  reflection_inject.md
```

验收：

1. 失败后生成 reflection。
2. 后续任务可检索 reflection。
3. 与 No Memory 对比。

### Week 4：结构化记忆单元

目标：实现 NT-MemEvo 的 memory schema。

实现：

```text
memory/
  schema.py
  store.py
  extractor.py
```

验收：

1. 从 trace 生成 candidate memory JSON。
2. JSON schema validation 通过。
3. 可写入 candidate pool。

### Week 5：RetrieverGate

目标：实现风险感知检索。

实现：

```text
memory/
  gate.py
  precondition.py
  scoring.py
```

验收：

1. 支持按 similarity + scope + utility + risk 打分。
2. 支持 top-k 注入。
3. 能输出每条记忆为什么被选中或拒绝。

### Week 6：Utility update 和 lifecycle

目标：实现记忆效用在线更新。

实现：

```text
memory/
  utility.py
  lifecycle.py
```

验收：

1. 成功失败后更新 alpha/beta。
2. 低效或有害记忆进入 quarantine。
3. 长期不用记忆 retired。

### Week 7：Verification gate 和 replay

目标：实现候选记忆验证。

实现：

```text
replay/
  replay_buffer.py
  counterfactual.py
  verifier.py
```

验收：

1. 候选记忆进入 active 前可在小 support set 上验证。
2. 支持 leave-one-memory-out replay。
3. 输出 replay_results.jsonl。

### Week 8：主实验初版

目标：完成 τ-bench retail 的主结果。

实验：

```text
No Memory
Raw Trace RAG
Reflexion
Success-only
NT-MemEvo
```

验收：

1. 每个方法至少 100 tasks。
2. 至少 3 seeds。
3. 生成主表格和 learning curve。

### Week 9：消融实验

目标：证明每个模块有贡献。

实验：

```text
- no negative evidence
- no scope
- no verification
- no quarantine
- top-k sensitivity
- replay budget sensitivity
```

验收：

1. 完成核心消融表。
2. 分析负迁移变化。

### Week 10：跨域和污染实验

目标：强化论文创新点。

实验：

```text
retail -> airline
memory pollution 0/10/20/40%
```

验收：

1. 有明确 NTR 降低结果。
2. 有 quarantine precision / recovery curve。

### Week 11：SWE-bench 或 ALFWorld 扩展

目标：证明方法不局限于 τ-bench。

建议优先级：

1. 如果环境和预算允许，做 SWE-bench Lite subset。
2. 否则做 ALFWorld。

验收：

1. 至少一个跨 benchmark 结果。
2. 写清楚方法如何适配不同环境。

### Week 12：论文材料和开源整理

目标：形成投稿材料。

输出：

1. 主实验表。
2. 消融表。
3. learning curve。
4. negative transfer 分析图。
5. memory lifecycle case study。
6. 代码 README。
7. reproducibility checklist。

## 15. 代码结构建议

```text
evolution2/
  README.md
  pyproject.toml
  configs/
    tau_retail_nomem.yaml
    tau_retail_reflexion.yaml
    tau_retail_ntmemevo.yaml
  data/
    task_splits/
  docs/
    negative_transfer_memory_self_evolution_roadmap.md
  src/
    ntmemevo/
      __init__.py
      llm/
        client.py
        cache.py
        cost.py
      envs/
        base.py
        tau_bench.py
        swe_bench.py
        alfworld.py
      agents/
        base.py
        react_tool_agent.py
        coding_agent.py
      memory/
        schema.py
        store.py
        extractor.py
        retriever.py
        gate.py
        utility.py
        lifecycle.py
        consolidation.py
      replay/
        buffer.py
        verifier.py
        counterfactual.py
      evaluation/
        metrics.py
        statistical_tests.py
        plots.py
      logging/
        trace_logger.py
        run_logger.py
      experiments/
        run_stream.py
        run_baseline.py
        run_ablation.py
  tests/
    test_memory_schema.py
    test_retriever_gate.py
    test_lifecycle.py
```

## 16. 最小可运行配置

示例：

```yaml
experiment:
  name: tau_retail_ntmemevo_seed1
  seed: 1
  output_dir: runs/tau_retail_ntmemevo_seed1

benchmark:
  name: tau_bench
  domain: retail
  split_file: data/task_splits/tau_retail_train_100.json
  max_tasks: 100

agent:
  type: react_tool_agent
  max_steps: 20
  memory_top_k: 3

models:
  actor:
    provider: configurable
    model: configurable_actor_model
    temperature: 0.0
  memory_extractor:
    provider: configurable
    model: configurable_memory_model
    temperature: 0.2
  verifier:
    provider: configurable
    model: configurable_verifier_model
    temperature: 0.0

memory:
  method: nt_memevo
  store_path: runs/tau_retail_ntmemevo_seed1/memories.jsonl
  embedding_model: configurable_embedding_model
  enable_negative_evidence: true
  enable_scope_gate: true
  enable_verification: true
  enable_quarantine: true
  candidate_verify_topn: 10
  replay_budget_per_iter: 16
  retire_after_unused_iters: 50

retrieval:
  w_similarity: 0.35
  w_precondition: 0.25
  w_utility: 0.25
  w_risk: 0.25
  w_age: 0.05
  w_cost: 0.05

logging:
  save_raw_model_io: true
  save_trace_events: true
  save_costs: true
```

## 17. 论文图表设计

### 17.1 主结果表

列：

```text
Method | Success Rate | pass^k | NTR ↓ | Steps ↓ | Tokens ↓ | Memory Size
```

### 17.2 Learning curve

横轴：task index 或 iteration。

纵轴：

1. moving success rate。
2. cumulative reward。
3. active memory size。

### 17.3 Negative transfer 分析图

展示：

1. 哪些 baseline 的 NTR 高。
2. NT-MemEvo 如何 quarantine harmful memory。
3. 污染率增加时的性能下降曲线。

### 17.4 Case study

选 2-3 条记忆展示生命周期：

```text
candidate -> active -> harmful evidence appears -> split into two scoped memories -> performance recovers
```

这类 case study 对 agent 论文很重要，因为审稿人会关心是否只是 benchmark trick。

## 18. 风险与应对

### 18.1 风险：记忆收益不明显

原因可能是任务之间迁移性弱。应对：

1. 使用 τ-bench 这类规则和工具共享明显的 benchmark。
2. 按 intent/domain 构造 task stream。
3. 增加 repeated trials 和 pass^k。

### 18.2 风险：负迁移难以稳定测量

应对：

1. 固定 actor temperature。
2. 固定 user simulator seed。
3. 使用 paired evaluation。
4. 使用 no-memory reference run。

### 18.3 风险：replay 成本过高

应对：

1. 只验证高频、高风险、高影响记忆。
2. 使用小 support set。
3. 引入 replay budget sensitivity，变成论文分析点。

### 18.4 风险：LLM extractor 输出不稳定

应对：

1. 强制 JSON schema。
2. 失败自动重试。
3. 使用 deterministic verifier。
4. 对候选记忆做去重和合并。

### 18.5 风险：baseline 复现争议

应对：

1. 能用官方代码就用官方代码。
2. 不能用官方代码就明确写 `method-level reimplementation`。
3. 所有 baseline 使用相同 actor model、预算、任务顺序和检索 top-k。

## 19. 最推荐的第一阶段执行顺序

不要一开始碰 SWE-bench 或 WebArena。推荐顺序：

1. 自写一个 tiny tool-use benchmark，10-20 个任务，用于调通 trace、memory、replay。
2. 接入 τ-bench retail，跑 No Memory 和 Raw Trace RAG。
3. 实现 Reflexion baseline。
4. 实现 NT-MemEvo 的结构化 memory 和 RetrieverGate。
5. 加入 utility update 和 quarantine。
6. 加入 candidate verification。
7. 跑 τ-bench retail 主实验。
8. 跑污染实验和跨域实验。
9. 时间允许再扩 SWE-bench Lite subset。

这个顺序能最大限度降低工程风险，同时保证论文创新点逐步可验证。

## 20. 参考资料

1. Reflexion: Language Agents with Verbal Reinforcement Learning, NeurIPS 2023. https://arxiv.org/abs/2303.11366
2. ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory, 2025. https://arxiv.org/abs/2509.25140
3. G-Memory: Tracing Hierarchical Memory for Multi-Agent Systems, NeurIPS 2025. https://arxiv.org/abs/2506.07398
4. Memory OS of AI Agent, EMNLP 2025. https://arxiv.org/abs/2506.06326
5. τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains, 2024. https://arxiv.org/abs/2406.12045
6. τ-bench official repository. https://github.com/sierra-research/tau-bench
7. tau2-bench repository with newer τ-bench updates. https://github.com/sierra-research/tau2-bench
8. SWE-bench: Can Language Models Resolve Real-World GitHub Issues?, ICLR 2024. https://arxiv.org/abs/2310.06770
9. SWE-bench official repository. https://github.com/SWE-bench/SWE-bench
10. SWE-Bench-CL: Continual Learning for Coding Agents, 2025. https://arxiv.org/abs/2507.00014
11. WebArena: A Realistic Web Environment for Building Autonomous Agents, ICLR 2024. https://arxiv.org/abs/2307.13854
12. WebArena-Verified repository. https://github.com/ServiceNow/webarena-verified
13. ALFWorld: Aligning Text and Embodied Environments for Interactive Learning. https://openreview.net/forum?id=0IOX0YcCdTn
14. ALFWorld official repository. https://github.com/alfworld/alfworld

