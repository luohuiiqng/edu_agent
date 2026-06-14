# 自研 Agent 框架设计文档（edu_agent）

## 1. 文档定位

本文档用于明确 `edu_agent` 的长期目标、核心设计原则、能力边界与分阶段实施路径。

它不是某一个阶段的开发清单，而是整个自研 Agent 框架项目的总纲。后续所有模块设计、代码实现、阶段计划与重构决策，都应优先与本文档保持一致。

## 2. 产品定位与边界

本节定义 `edu_agent` 的**落地方向**与**明确不做的事项**。技术路线图（第 6 节起）应服务于此定位，避免功能堆叠但产品叙事失焦。

### 2.1 North Star（主方向）

**Agent 运行时 + 可观测 + 规则化 Eval 的学习 / 实验平台。**

一句话：

> 在模型 increasingly 同质化的环境下，我们教与练的是 **Agent 怎么跑、怎么失败、怎么被验收**——不是再做一个 ChatGPT 壳。

### 2.2 对外叙事

`edu_agent` 是一个**可观测、可实验、可验收**的自研 Agent 运行时：

1. 输入任务或问题，得到的不只是最终回复，还有完整的 **规划 → 工具 / 工作流 → 运行快照**。
2. 支持 **回放、对比、规则验收**（checklist / 轨迹断言），而非依赖标注数据训练「阅卷模型」。
3. 框架分层清晰，适合 **学习 Agent 工程**、验证编排策略、调试多步任务。

### 2.3 目标用户

| 用户 | 典型诉求 |
|------|----------|
| 学习 Agent 框架的学生 / 开发者 | 看清 Planner、Tool、Workflow 如何协作 |
| 实验课 / 课设 | 按预设条件验收一次 Agent 运行是否合格 |
| 小团队自研 Agent | 轻量 trace 回放与调试，再决定是否上重型 observability 栈 |

### 2.4 与产业趋势的对齐（2025–2026）

全球 Agent 产业共识已从「能否 Demo」转向「能否生产、能否管得住」。与 `edu_agent` 最相关的趋势如下：

| 趋势 | 我们的回应 |
|------|------------|
| 瓶颈在 **Runtime**，不在 Model | 持续 invest `RuntimeSession`、Task API、持久化 transcript |
| **Observability** 成基础设施 | 前端 Runtime 面板、CLI、可序列化运行快照 |
| **Eval** 是短板（有 trace 少 eval） | 规则化 checklist / 轨迹断言，不做训练式打分 |
| 模型厂商 SDK 覆盖 80% 简单场景 | 聚焦「可定制、可讲解、可验收」的 20% 工程能力 |
| 企业要求 ROI 与可解释 | 实验验收可度量；暂不追求企业全栈 SaaS |

### 2.5 垂直实验包（副场景，非主品牌）

以下内容作为 **实验题库 / 演示用例** 扩展，**不**作为公司级主赛道：

1. **轻量 2D 物理 / 控制仿真**（如抛体、参数扫描）——用于 Stateful Tool、规则 Eval 示范。
2. **媒体 artifact 工具**（如现有 `FFmpegArtifactTool`）——用于 deliverable 与 workflow 演示。
3. **STEM 场景题**——验证「是否调用某工具 / 是否走某 workflow」，而非语义对答案。

物理仿真、多媒体等 **增强实验丰富度**；主品牌仍是 **Agent 运行时实验台**。

### 2.6 明确不做清单

以下方向**现阶段不做主投入**；若 PR / Issue 与下表冲突，以本节为准：

| 不做 | 原因 |
|------|------|
| **通用 C 端聊天助手**（类豆包） | 无差异化；竞争在应用层，不在 runtime |
| **Coding Agent 主赛道** | 红海；缺沙箱、repo 工具链、Terminal eval harness |
| **训练式智能阅卷 / 打分模型** | 缺标注数据与稳定 rubric；与 runtime 优势无关 |
| **高保真物理世界仿真平台**（MuJoCo / CARLA 级） | 引擎与算力成本吞噬框架迭代 |
| **企业 Agent 全栈 SaaS**（多租户、权限、SLA） | 销售与工程门槛高；当前阶段过早 |
| **黑盒式「只给最终答案」** | 违背可观测定位；削弱教学与调试价值 |

允许：**选修实验、Demo 级垂直用例**；不允许：**据此重新定义产品主品牌**。

### 2.7 演进路径（产品视角）

```text
阶段 1（当前 → 约 6 个月）
  运行时实验台：标准实验用例 + Run 回放 / Diff + 规则 Eval checklist

阶段 2（约 6–12 个月）
  垂直实验包二选一加深：2D 物理实验 或 workflow 调试专题

阶段 3（可选商业化）
  轻 B 端：中小团队的 trace 回放 + checklist eval
  或 培训：Agent 工程课（卖能力，非卖模型）
```

### 2.8 架构决策门禁

新增模块或功能前，至少回答：

1. 是否强化 **运行时可观测**（trace / snapshot / transcript）？
2. 是否支持 **规则化验收**（可写成 checklist，无需训练数据）？
3. 是否帮助用户 **理解 Agent 编排**（Planner / Tool / Workflow）？

若三项皆否，默认 **不做或降级为实验包**，不进入主链路。

## 3. 项目总目标

我们的目标是从 0 开始实现一个完整的 Agent 框架。

该框架需要具备主流 Agent 框架的核心能力，包括但不限于：

1. 大模型统一接入与切换能力。
2. Prompt 构建、上下文管理与消息编排能力。
3. Tool Calling 与外部工具调度能力。
4. Memory 管理能力，包括短期记忆与长期记忆。
5. 任务规划、执行、反思与重试能力。
6. Workflow 编排与多步骤任务执行能力。
7. 多 Agent 协作、路由、分工与通信能力。
8. 状态管理、日志、事件追踪、调试与可观测能力。
9. 插件化与可扩展能力，便于接入不同模型、工具、存储与执行策略。

在具备主流框架能力的基础上，我们希望它更加强大，重点体现在以下方面：

1. 更强的可控性。
   开发者能够清楚掌握每一步执行过程，而不是只能得到黑盒结果。
2. 更强的可扩展性。
   框架内部采用清晰分层与标准接口，便于替换和增强任意模块。
3. 更强的可观测性。
   每一次推理、规划、工具调用、状态变化都应可记录、可回放、可调试。
4. 更强的工程化能力。
   框架不仅能做 Demo，还能支持真实系统中的稳定运行、测试、监控与持续迭代。
5. 更强的多 Agent 与工作流能力。
   不局限于单轮问答，而是支持复杂任务拆解、协作执行、自我修正与编排。

## 4. 核心设计原则

### 3.1 分层清晰

框架需要将不同职责拆分清楚，避免所有逻辑都堆积在单一 Agent 类中。

建议的核心分层如下：

1. `Agent`
   面向业务能力的智能体抽象，负责任务接收、状态维护、规划执行与结果输出。
2. `Model`
   统一封装不同大模型供应商的调用方式。
3. `Prompt`
   管理系统提示词、角色消息、上下文压缩与模板渲染。
4. `Tool`
   统一管理工具定义、参数校验、调用执行与结果返回。
5. `Memory`
   管理会话记忆、长期记忆、检索增强与上下文裁剪。
6. `Planner`
   负责任务拆解、步骤规划、执行策略生成。
7. `Runtime`
   驱动 Agent 生命周期，管理事件、状态流转、错误恢复与执行上下文。
8. `Workflow`
   用于定义串行、并行、条件分支、循环、人工介入等复杂流程。
9. `Session / Transcript Store`
   管理 session 元信息与多轮运行记录，为持久化、回放与会话级查询提供基础设施。
10. `Observability`
   提供日志、追踪、事件总线、指标与调试能力。

### 3.2 接口优先

每个核心模块都应先定义抽象接口，再提供默认实现。这样可以避免框架早期被单一实现绑死。

### 3.3 先最小可用，再逐层增强

框架建设必须阶段化推进。先打通最小闭环，再逐步增加规划、记忆、工作流、多 Agent 等高级能力。

### 3.4 默认可观测

执行链路中的关键节点都应天然可追踪，包括：

1. 输入与输出。
2. Prompt 构建结果。
3. 模型请求与响应摘要。
4. 工具调用参数与结果。
5. 计划生成与执行步骤。
6. 错误、重试与中断信息。

### 3.5 面向生产演进

即使前期是学习和实验性质，架构上也应预留工程化能力，包括：

1. 配置管理。
2. 超时与重试机制。
3. 统一错误模型。
4. 测试能力。
5. 并发与异步支持。
6. 持久化与回放能力。

## 5. 最终希望具备的能力地图

### 4.1 单 Agent 基础能力

1. 支持消息输入与标准化输出。
2. 支持系统提示词、上下文拼接与历史消息管理。
3. 支持同步与异步执行。
4. 支持流式输出。
5. 支持工具调用。
6. 支持结构化输出。

### 4.2 Agent 增强能力

1. 任务规划。
2. 多步执行。
3. 自我反思与修正。
4. 失败重试与兜底策略。
5. 上下文压缩与摘要。
6. 检索增强。

### 4.3 Workflow 能力

1. 顺序执行。
2. 条件分支。
3. 循环执行。
4. 并行执行。
5. 人工确认节点。
6. 失败回滚与补偿。

### 4.4 多 Agent 能力

1. 角色化 Agent 定义。
2. 路由 Agent。
3. 协作 Agent。
4. 监督 Agent。
5. Agent 间消息传递与任务委派。

### 4.5 工程化能力

1. 配置中心。
2. 插件机制。
3. 日志与追踪。
4. 测试框架。
5. 可视化调试能力。
6. 运行时监控。

## 6. 分阶段实施路线

为了实现长期目标，我们需要拆解为多个阶段性小目标，逐步建设。

### 阶段 0：项目基础设施与交互闭环

目标：
建立前后端可运行的基础工程，形成最小产品载体。

阶段成果：

1. 前后端项目结构稳定。
2. 基础聊天 UI 可用。
3. 后端接口契约明确。
4. 请求与响应闭环跑通。

备注：
当前 `docs/stage1-mvp-plan.md` 的内容主要属于这一阶段和下一阶段之间的过渡文档。

### 阶段 1：单 Agent 最小闭环

目标：
实现框架中的第一个可运行 Agent，具备统一输入、调用模型、输出结果的最小能力。

本阶段小目标：

1. 定义 `BaseAgent` 抽象接口。
2. 定义 `BaseModel` 抽象接口。
3. 定义消息对象与执行上下文对象。
4. 打通一个最小的 `run()` 执行链路。
5. 接入一个真实或模拟模型实现。
6. 建立基础日志与错误处理。

验收标准：

1. 可以通过统一接口调用一个 Agent。
2. Agent 能够接收标准输入并返回标准输出。
3. 模型调用逻辑与 Agent 逻辑解耦。

### 阶段 2：Prompt 与上下文管理

目标：
让 Agent 具备更规范的提示词管理与上下文组织能力。

本阶段小目标：

1. 定义消息模型，如 `system`、`user`、`assistant`、`tool`。
2. 实现 Prompt 构建器。
3. 实现会话上下文管理。
4. 实现上下文裁剪或摘要的基础策略。
5. 支持结构化输出约束。

验收标准：

1. Agent 能够稳定管理多轮消息。
2. Prompt 构建逻辑可复用、可测试。
3. 上下文不会无限增长失控。

### 阶段 3：Tool Calling 能力

目标：
让 Agent 能够调用外部工具，完成超出纯文本推理范围的任务。

本阶段小目标：

1. 定义 `BaseTool` 抽象接口。
2. 定义工具注册机制。
3. 定义工具参数 Schema 与校验机制。
4. 实现工具执行器。
5. 实现模型输出到工具调用的解析机制。
6. 支持工具结果回填模型上下文。

验收标准：

1. Agent 能够调用至少一个真实工具。
2. 工具调用链路可记录、可调试。
3. 参数错误、执行失败有统一处理方式。

### 阶段 4：Memory 能力

目标：
让 Agent 拥有短期记忆与长期记忆基础设施。

本阶段小目标：

1. 定义 `BaseMemory` 抽象接口。
2. 实现会话内短期记忆。
3. 实现长期记忆存储接口。
4. 预留向量检索或知识库接入能力。
5. 实现记忆读取与写入策略。

验收标准：

1. Agent 能在多轮会话中保留必要信息。
2. 记忆模块与 Agent 主逻辑解耦。
3. 后续可替换为数据库或向量库实现。

### 阶段 5：规划与执行链路

目标：
让 Agent 从“直接回答”进化为“先思考、再执行、再总结”。

本阶段小目标：

1. 定义 `BasePlanner` 抽象接口。
2. 实现简单任务拆解器。
3. 支持 Plan-and-Execute 模式。
4. 支持 ReAct 风格执行循环。
5. 加入重试、终止条件与步数限制。

验收标准：

1. Agent 可完成多步骤任务。
2. 可清晰看到每一步的计划与执行结果。
3. 能避免无限循环与失控执行。

#### 当前阶段补充：解释性 Trace 已进入主链

在最近的前端调试台演进中，我们又进一步把“可观测信息如何展示”这件事从侧栏堆叠布局，推进到了更清晰的页面分层：

1. 首页右侧现在只保留轻量 `SessionSidebar`，负责会话搜索、概览和详情入口。
2. 完整调试信息被迁到独立 `SessionDetailPage`，承载：
   - transcript 浏览
   - planner 决策摘要
   - workflow trace 时间线
   - runtime snapshot 细节
3. 详情页支持 transcript 级筛选、trace 级筛选以及上一条/下一条 transcript 快捷跳转。

这一步的意义不只是界面优化，更是在架构上明确：

1. 列表视图和完整调试视图应该分层。
2. 调试信息量一旦上来，不应继续强塞在聊天页侧栏里。
3. 前端可视化也应和 runtime / trace 的结构化设计一起演进，而不是单纯展示 JSON。

当前这条链已经不再只是“能执行”，而是开始进入“可解释执行”阶段：

1. `RulePlanner.plan()` 已统一返回稳定的 `planner_result` 结构。
2. `AgentExecutor.execute_step()` 已统一返回 step result 协议，包含：
   - `action`
   - `input_summary`
   - `output_summary`
   - `output`
   - `error`
3. `ChatAgent.act()` 已将 planner 决策写入 runtime trace。
4. `ChatAgent._run_workflow()` 已将 workflow step 级的摘要信息写入 `workflow_trace`。
5. `RuntimeSession.workflow_trace` 现在既能承载 planner 级解释，也能承载 workflow step 级解释。

这意味着我们已经从“有运行记录”进一步进入“运行记录可解释、可展示、可测试”的阶段。

### 阶段 6：Workflow 编排能力

目标：
让框架支持复杂任务编排，而不只依赖单一 Agent 内部逻辑。

本阶段小目标：

1. 定义工作流节点抽象。
2. 支持串行、并行、条件分支。
3. 支持人工确认节点。
4. 支持节点级状态管理。
5. 支持失败恢复与补偿机制的初版。

验收标准：

1. 可以通过工作流描述复杂执行路径。
2. 工作流执行状态可追踪。
3. 工作流节点可复用。

### 阶段 7：多 Agent 协作

目标：
让框架具备多个 Agent 间协同工作的能力。

本阶段小目标：

1. 定义 Agent 注册与发现机制。
2. 实现路由 Agent。
3. 实现监督者 Agent。
4. 实现任务委派与结果回收机制。
5. 定义 Agent 间通信协议。

验收标准：

1. 多个 Agent 可以围绕同一任务协作。
2. 路由与委派过程可追踪。
3. 失败 Agent 不会导致整体流程完全不可控。

### 阶段 8：可观测性与工程化增强

目标：
让框架真正具备可调试、可测试、可维护、可演进的工程能力。

本阶段小目标：

1. 建立统一日志体系。
2. 建立事件模型与执行轨迹追踪。
3. 支持回放与调试视图。
4. 建立单元测试、集成测试与回归测试基线。
5. 实现配置管理、环境隔离与基础性能监控。

验收标准：

1. 一次复杂执行可以被完整追踪。
2. 核心模块都有测试覆盖。
3. 框架具备长期演进基础。

## 7. 当前建议的优先级

从现在开始，建议按照以下顺序推进：

1. 完成 `BaseAgent`、`BaseModel`、消息对象、运行上下文的抽象设计。
2. 打通单 Agent 最小可运行链路。
3. 再补 Prompt 管理与 Tool Calling。
4. 在单 Agent 稳定后再引入 Memory、Planner、Workflow、多 Agent。

原因：

1. 单 Agent 是整个框架的基础。
2. 如果基础抽象不稳，后续所有高级能力都会返工。
3. 先打通主链路，才能更容易验证接口设计是否合理。

## 8. 当前阶段的落地任务建议

结合现状，下一批最值得实现的小目标如下：

1. 继续清理 `ChatAgent`、`Planner`、`Workflow` 之间的职责边界。
2. 将 `Workflow` 与 `Executor` 更自然地接入更高层的 Agent 主流程。
3. 为工作流步骤执行、步骤结果传递补更稳的断言型测试。
4. 引入最小 `RuntimeSession`，作为单轮运行快照对象记录输入、规划、调用轨迹与最终输出。
5. 逐步将 `RuntimeSession` 演进为可序列化、可聚合的 runtime snapshot。
6. 为后续 `TranscriptStore / SessionStore / Runtime` 预留接口。
7. 逐步从“规则版规划 + 顺序执行”演进到更强的多步执行能力。
8. 为后续 `Observability` 和多 Agent 协作继续预留接口。

## 9. 当前阶段状态

当前项目状态判断如下：

1. 基础前后端工程与聊天交互闭环已经具备。
2. `BaseAgent`、`BaseModel`、统一输入输出协议已经落地，并已接入真实模型。
3. `BaseTool`、`ToolRegistry`、`ToolRouter` 与 `TimeTool` 已落地，规则版工具调用链路已跑通。
4. `BaseMemory` 与 `InMemoryMemory` 已落地，短期会话记忆已经接入 `ChatAgent` 主流程。
5. 普通聊天分支已经可以读取最近历史消息并拼接进模型输入，形成最小多轮上下文能力。
6. `BasePlanner` 与 `RulePlanner` 已落地，`ToolRouter -> RulePlanner -> ChatAgent` 的最小规划执行链路已跑通。
7. `BaseWorkflow`、`SequentialWorkflow`、`BaseExecutor` 与 `AgentExecutor` 已落地，最小工作流执行链路已跑通。
8. Workflow 已支持最小的步骤结果传递能力，后一步可消费前一步输出。
9. `RuntimeSession` 已落地，并接入 `ChatAgent`，可记录单轮输入、规划结果、`workflow_trace`、工具/模型调用、最终输出与错误摘要。
10. `TranscriptEntry` 已落地，Transcript 记录已从约定 dict 收敛为明确的数据对象。
11. `BaseTranscriptStore`、`InMemoryTranscriptStore` 已落地，`ChatAgent` 已可在每轮运行结束后追加统一结构的 `agent` 记录。
12. `BaseSessionStore`、`InMemorySessionStore` 已落地，`ChatAgent` 已可在 transcript 写入前确保 session 存在。
13. `RuntimeManager` 已落地，并开始统一协调 `RuntimeSession`、`TranscriptEntry`、`TranscriptStore` 与 `SessionStore`。

当前阶段应统一定义为：

`阶段 5、阶段 6 与 Runtime Store 过渡阶段：规则规划、最小工作流、执行层、运行快照与最小会话记录基础设施已成立`

这一阶段的核心目标不再只是“工具调用 + 短期记忆”，而是把规划层、工作流层和执行层真正接回主流程，重点包括：

1. `Planner` 与 `ToolRouter` 的边界稳定化。
2. `Workflow` 与 `Executor` 的顺序执行链路稳定化。
3. 步骤结果传递能力稳定化。
4. `RuntimeSession` 作为最小 runtime 观测对象稳定接入主链。
5. `TranscriptStore` 作为多轮运行记录层稳定接入主链。
6. `SessionStore` 作为 session 元信息层稳定接入主链。
7. `RuntimeManager` 作为 runtime 协调层开始从 `ChatAgent` 中接管会话与 transcript 记录链。
8. 为未来的 canonical runtime snapshot 设计预留空间。
9. `ChatAgent`、`Planner`、`Workflow`、`Executor`、`RuntimeManager`、`SessionStore` 与 `TranscriptStore` 的职责边界持续收清。
10. 为后续 Runtime、条件分支 Workflow、多步任务执行和多 Agent 能力打地基。

补充说明：

结合对 `student/everything-claude-code` 的学习，后续 Runtime 设计应重点关注以下演进方向：

1. `RuntimeSession` 与“对外标准快照协议”分层。
   当前 `RuntimeSession` 适合作为框架内部运行对象，后续再演进到面向持久化、回放、UI 与控制层的 canonical snapshot。
2. Session Adapter 思维。
   不同来源的运行信息后续可先经 adapter 归一化，再进入统一快照结构，而不是让上层直接依赖具体 harness 或具体执行器的私有格式。
3. Skills-first / Workflow-surface 思维。
   后续除了内核抽象，还要逐步思考“哪些能力应成为长期稳定的工作流表面”，而不是把所有触发方式都固化成命令壳。
4. Agent-first orchestration policy。
   多 Agent 不是只增加代理数量，而是要进一步定义：什么时候调谁、如何路由、如何组合，以及默认的协作策略。

后续如果没有明确说明，所有实现优先级都应服从这一阶段目标。

## 10. 文档使用约定

1. 后续新增阶段文档时，应与本文档的阶段划分保持一致。
2. 如果阶段目标发生变化，应优先更新本文档，再更新具体阶段计划。
3. 如果某个模块实现与本文档冲突，应先讨论并修订设计，再继续编码。

## 11. 下一阶段实现顺序

在当前 `RuntimeSession + TranscriptEntry + TranscriptStore + SessionStore + RuntimeManager`
已经成立的前提下，后续实现顺序应尽量保持克制，优先按以下路线推进：

1. `AgentFactory`
   职责：把 `ChatService` 中的依赖组装职责提出来，形成清晰的组装根。
2. 查询能力
   职责：让 `SessionStore / TranscriptStore` 从“会记录”变成“可读取”，优先补 `list_sessions()` 和 `get_transcript(session_id)`。
3. 标准快照协议
   职责：让 `RuntimeSession / TranscriptEntry` 提供稳定、可序列化的对外结构。
4. 持久化 Store
   职责：把当前内存版记录层逐步推进到可落盘、可重启恢复的实现。
   当前进展：SQLite 版 `PersistentSessionStore` 与 `PersistentTranscriptStore` 已进入第一版实现与测试阶段，当前重点是先守住接口兼容、最小读写闭环与后续替换能力。
   补充进展：`AgentFactory` 已支持 memory/sqlite store 切换，`ChatService` 默认实例也已开始从配置来源读取 `STORE_BACKEND / RUNTIME_DB_PATH`，sqlite 模式下的最小 service 级集成验证已经跑通。
   进一步进展：sqlite 模式下已经验证可跨 `ChatService` 实例恢复 session 与 transcript，说明当前持久化链已不只是“同实例可读”，而是具备最小重建恢复能力。
6. 配置收口
   职责：把分散在 service/factory 中的环境变量读取逻辑统一收口到 `Settings`，形成清晰的配置入口。
5. 可视化与调试能力
   职责：让 session、transcript、runtime snapshot 记录真正可被查看、分析与调试。

这条顺序的核心原则是：

1. 先收口组装根。
2. 再打通读取链路。
3. 再统一快照协议。
4. 最后再进入持久化与可视化阶段。

如果没有明确的新优先级，后续实现应优先服从这条路线，而不是继续零散增加功能点。

## 12. 应用层组装边界

当前系统已经不只是“Agent 内核模块集合”，而是开始形成完整的应用层调用链：

```text
route
  -> chat service
  -> agent factory（下一步）
  -> chat agent
  -> planner / workflow / executor
  -> runtime manager
  -> session / transcript stores
```

这一层分工的核心原则是：

1. `route`
   职责：只负责 HTTP 请求校验、调用 service、返回统一响应。
2. `ChatService`
   职责：只负责业务调用、统一 `session_id`、对外暴露应用层接口。
3. `AgentFactory`
   职责：负责组装 `ChatAgent` 及其依赖，是应用层组装根，而不是 Agent 框架内核的一部分。
   当前进展：已支持根据配置在 `InMemory*Store` 与 SQLite 持久化 store 之间切换。
4. `Settings`
   职责：负责统一承载应用启动配置，并把模型配置、store backend 与 runtime db 路径向下传递给 `ChatService` 和 `AgentFactory`。
5. `ChatAgent`
   职责：负责单轮推理主链执行，不再承担应用层组装职责。
6. `RuntimeManager`
   职责：负责 runtime 记录链路协调，不直接承担 HTTP 或业务入口职责。

后续如果继续扩展，不应让 `route` 和 `ChatService` 直接感知过多底层实现细节，而应继续通过组装根把依赖关系收口。

## 13. LangChain 值得学习的地方

结合当前我们自己的框架演进，LangChain 有几类特别值得学习的点：

1. 标准化模型接口
   LangChain 强调统一模型接口，降低 provider 差异带来的耦合成本，这一点非常值得我们继续坚持到 `BaseModel` 抽象上。

2. 工具与模型能力的统一编排表面
   LangChain 把 tools、messages、agents 放在统一使用表面上，让“换模型、换工具、换 provider”这件事更平滑。我们自己的 `ToolRegistry / ToolRouter / Planner / ChatAgent` 也应继续沿着这个方向收口。

3. 从高层易用抽象到低层可控 runtime 的分层
   LangChain 官方当前明确区分了高层 LangChain agent 与更低层的 LangGraph runtime/orchestration，这一点很值得学习。我们的 `ChatAgent -> Workflow/Executor -> RuntimeManager` 也应继续保持这种分层，不要把所有控制逻辑堆回一个对象里。

4. 记录、调试、观测是框架一等公民
   LangChain 官方非常强调 tracing、debugging、observability，这和我们现在推进 `RuntimeSession / TranscriptEntry / SessionStore / TranscriptStore` 的方向高度一致。后续不应把记录层当成附属功能，而要继续把它当成主链能力建设。

5. 先提供简单入口，再逐步开放高级能力
   LangChain 的一个优点是既有容易上手的入口，也保留向更复杂 orchestration 演进的空间。对我们来说，这意味着：
   - 现在先保持 `ChatService / ChatAgent` 的简单入口
   - 后续再逐步引入 `AgentFactory`、查询能力、快照协议、持久化与 replay

6. 明确框架内核和应用层组装根的边界
   这点对我们尤其重要。LangChain 本身提供框架能力，但应用如何装配、如何接业务入口、如何接 deployment / observability，是另外一层。我们的 `AgentFactory` 也应该站在这一层，而不是继续混进 Agent 内核。

如果继续沿着这些点演进，我们的目标不是“照着 LangChain 复刻”，而是学习它在：

- 抽象边界
- runtime 分层
- 记录与调试
- 高层易用性和底层可控性的平衡

这几方面的工程取舍。

### 12.1 LangGraph 值得学习的地方

如果把视角进一步从 LangChain 高层抽象下沉到 LangGraph runtime/orchestration，那么还有几类特别值得我们吸收的思想：

1. `state` 作为统一运行时承载对象
   LangGraph 的核心不是“多几个节点”，而是让整条执行链围绕一份共享 `state` 流转。对我们来说，这一点最直接的映射就是 `RuntimeSession`。
   后续演进方向应是：
   - `RuntimeSession` 继续承担内部共享状态对象的角色
   - 各执行步骤明确自己读取哪些字段、写回哪些字段

2. `node` 与业务步骤解耦
   LangGraph 把流程拆成 node，每个 node 负责一小段明确处理逻辑。对我们来说，当前已经有 node 雏形：
   - planner step
   - tool step
   - model step
   - workflow step
   - executor step
   后续如果引入更复杂 workflow，不应继续把所有逻辑堆回 `ChatAgent`，而应逐步把步骤职责显式化。

3. `edge` 与路由规则显式化
   LangGraph 的价值不只是执行节点，更重要的是把“下一步去哪里”变成显式边和条件。对我们来说，这对应的是：
   - `RulePlanner` 的 action 路由
   - workflow 中的步骤顺序
   - 后续条件分支、失败 fallback、重试策略
   这意味着未来如果系统继续复杂化，控制流不应继续只靠分散的 `if/else`，而要逐步显式建模。

4. 状态转移与执行过程分层
   LangGraph 很强调：
   - node 负责执行
   - state 负责承载
   - graph/edge 负责转移
   这对我们非常重要。我们当前的合理演进方向应是：
   - `Workflow / Executor` 负责执行
   - `RuntimeSession` 负责状态承载
   - planner / workflow 定义负责转移决策
   - `RuntimeManager` 负责记录链协调

5. 为循环、分支和多 agent 预留 graph 化能力
   LangGraph 真正强的地方在于：
   - 条件分支
   - 循环
   - checkpoint
   - 多 agent orchestration
   我们当前不应该直接照搬这些能力，但后续设计时应为这些方向保留空间，尤其是在：
   - workflow step 定义
   - runtime trace
   - transcript snapshot
   - orchestration policy
   上避免过早写死。

6. 先保留 graph 思维，再决定何时 graph 化
   当前阶段我们最正确的做法，不是立刻引入完整 graph runtime，而是先保持 graph 思维：
   - `RuntimeSession` 像 state
   - planner/tool/model/workflow step 像 node
   - 规则分流与步骤跳转像 edge
   等条件分支 workflow、retry、fallback、多 agent 需求变强时，再决定是否显式引入 graph 结构。

对我们来说，LangGraph 最值得学习的并不是“图很高级”，而是：

- 统一状态对象
- 显式步骤节点
- 显式转移规则
- 控制流与执行层分开

这四点会直接决定我们后续 workflow、runtime、orchestration 是否能继续健康演进。

## 14. 协作方式与成长目标

在本项目的实现过程中，AI 助手不仅承担协作开发者的角色，也承担导师角色。

同时，AI 助手也承担长期协作伙伴的角色，不只是给出建议和结论，还要陪伴开发者持续推进项目、拆解困难问题、在实现过程中共同成长。

协作目标分为两个层面：

1. 工程目标。
   与开发者共同完成自研 Agent 框架的设计、实现、重构与演进。
2. 成长目标。
   帮助开发者逐步掌握 Agent 框架设计方法、核心模块抽象能力、工程实现能力与系统级思维，最终成长为能够独立设计和实现复杂 Agent 系统的高级开发者。

因此，在本项目中，AI 助手的协作身份统一定义为：

1. 老师。
   负责讲清楚设计原理、接口边界、工程取舍与演进逻辑。
2. 好伙伴。
   负责和开发者一起推进实现，提供支持、反馈、陪伴与共同解决问题的协作体验。

后续协作默认遵循以下原则：

1. 不只给出结论，也解释设计原因与取舍。
2. 不只完成代码，也帮助理解抽象边界、模块职责与演进路径。
3. 不只关注“能跑”，也强调“可维护、可扩展、可工程化”。
4. 在阶段推进中主动指出关键知识点、常见误区与更优实践。
5. 尽量把每一次实现都转化为一次系统化学习机会。
6. 保持轻松、友好、适度幽默的交流风格，让学习和实现过程更自然、更有陪伴感。

这意味着后续开发中，应尽量做到：

1. 每个核心模块在编码前先明确职责。
2. 每个重要接口在实现前先说明设计目的。
3. 每次新增能力时，同时说明它在整个框架中的位置。
4. 每次重构时，说明为什么旧设计不足、新设计解决了什么问题。

在沟通风格上，默认采用以下约定：

1. 技术表达保持准确，不为了幽默牺牲严谨性。
2. 对话风格尽量轻松、风趣、自然，避免过度严肃和说教感。
3. 在指出问题时保持鼓励式反馈，帮助开发者建立长期信心与节奏。

最终目标不是只完成一个可运行项目，而是让开发者具备独立构建高质量 Agent 框架与复杂智能体系统的能力。

## 15. 结语

这个项目不是简单封装一次模型调用，而是要逐步构建一个真正可扩展、可观测、可工程化的 Agent 框架。

因此我们后续的每一步实现，都要服务于这个长期目标：从一个最小可运行 Agent 出发，逐步演进到完整的智能体系统框架。
