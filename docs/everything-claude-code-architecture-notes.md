# `student/everything-claude-code` 架构学习说明

## 1. 文档目的

本文档用于记录对 [`student/everything-claude-code`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/everything-claude-code) 的第一轮学习结论，重点回答：

1. 这个项目本质上是什么类型的系统。
2. 它最值得我们借鉴的架构优点有哪些。
3. 它和我们当前 `edu_agent` 的差异在哪里。
4. 哪些设计值得进入我们后续的 Runtime / Observability 规划。

本文档不是逐文件翻译，而是后续学习和借鉴的“第一张地图”。

## 2. 先给结论：这不是单一 Agent 项目，而是一个跨 Harness 的 Agentic Workflow 资产平台

从项目顶层结构和核心文档看，`everything-claude-code` 更像：

1. 一个跨 `Claude Code / Codex / Cursor / OpenCode` 的 agentic workflow 发行版。
2. 一个多 agent、多 skill、多 command、多 rules 的能力资产仓库。
3. 一个带安装体系、兼容层、session adapter、runtime 规范和持续演进能力的平台化工程。

它的核心重心不是：

- 定义一个 `BaseAgent`
- 实现一个 `ChatAgent`
- 把模型、工具、记忆、规划串起来

而是：

- 如何让大量 workflow 资产在不同 harness 里可安装、可兼容、可复用
- 如何让 session / runtime / adapter / state store 有统一契约
- 如何让 agent orchestration policy 变成一套默认工作方法

一句更直白的话：

- 我们当前更像“从内核往上搭 Agent Framework”
- 它更像“从资产和运行表面往下搭 Agentic Operating System”

## 3. 顶层结构体现出的产品定位

这个仓库最显眼的目录不是某个 `src/agent/`，而是：

```text
agents/
skills/
commands/
rules/
hooks/
scripts/
mcp-configs/
docs/
ecc2/
```

这说明它的产品重心不是单点运行逻辑，而是：

1. `agents/`
   提供大量专门职责的子代理说明。
2. `skills/`
   提供面向任务流的技能资产。
3. `commands/`
   提供兼容层和历史工作流入口。
4. `rules/`
   提供语言和场景级约束。
5. `hooks/`
   提供自动化触发机制。
6. `scripts/`
   提供跨平台安装、状态、适配器和工具脚本。
7. `ecc2/`
   预示更正式的 runtime / TUI / control-plane 演进方向。

## 4. 最值得学习的 4 个优点

## 4.1 Skills-first 工作流表面

在 [`AGENTS.md`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/everything-claude-code/AGENTS.md) 中，它明确提出：

- `skills/` 是 canonical workflow surface
- `commands/` 是 legacy compatibility surface

这有两个很重要的设计价值：

1. 将“能力资产”与“触发方式”分层
   也就是说，真正长期稳定的东西是 skill/workflow，而不是某条命令名字。
2. 让系统具备更好的跨 harness 迁移性
   因为 command 很可能是某个平台的语法壳，而 skill 才是可迁移的工作流能力。

### 对我们的启发

我们现在更偏：

- Prompt / Tool / Planner / Workflow / Executor 的内核抽象

后面如果要往上长，就很适合思考：

1. 哪些能力将来应该成为“工作流表面”
2. 哪些入口只是兼容壳，不应成为核心抽象

## 4.2 Agent-first orchestration policy

`everything-claude-code` 不是只“有很多 agents”，而是明确写了：

- 复杂功能 -> `planner`
- 写完代码 -> `code-reviewer`
- 新功能/修复 -> `tdd-guide`
- 安全敏感 -> `security-reviewer`

这意味着它把：

## “什么时候调哪个 agent”

也做成了系统默认规则，而不只是文档建议。

### 对我们的启发

后续如果我们做多 Agent，不应该停在：

- 再定义几个 `BaseAgent` 子类

而应该继续思考：

1. 触发规则
2. 路由时机
3. 默认协作顺序
4. 哪些 agent 是主干 agent，哪些是 review/verify/support agent

## 4.3 Canonical Session Snapshot / Session Adapter Contract

[`docs/SESSION-ADAPTER-CONTRACT.md`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/everything-claude-code/docs/SESSION-ADAPTER-CONTRACT.md) 是这个项目最值得我们借鉴的一份文档之一。

它做的事情不是“保存一个 session 对象”，而是定义：

## 一个跨多种 session 来源的统一快照协议

文档里的核心思想包括：

1. 不同来源的 session 先通过 adapter 归一化。
2. 归一化后的 snapshot 必须符合固定 schema。
3. UI、持久化、控制平面、消费者都依赖这份统一 snapshot，而不是依赖某个 harness 私有结构。

它的 canonical snapshot 顶层结构包含：

- `schemaVersion`
- `adapterId`
- `session`
- `workers`
- `aggregates`

### 对我们的启发

我们现在的 `RuntimeSession` 还是：

- 框架内部的运行快照对象

这完全没问题，而且是当前阶段正确路线。  
但后面如果我们继续往 Runtime / Observability 长，就很自然可以演进成两层：

1. `RuntimeSession`
   框架内部运行对象
2. `Canonical Runtime Snapshot`
   对外持久化、展示、回放、控制平面的统一协议

这条演进路线非常值得保留。

## 4.4 Runtime / Control-plane 思维

[`docs/ECC-2.0-REFERENCE-ARCHITECTURE.md`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/everything-claude-code/docs/ECC-2.0-REFERENCE-ARCHITECTURE.md) 提出了一个更成熟的演进方向：

```text
TUI Layer
Runtime Layer
Daemon Layer
```

这个设计最值得学习的地方不是“TUI”本身，而是它体现出的：

## 把运行时、状态、终端会话、进程管理、持久化和 UI 分层

也就是说，它已经不是简单地在一个 `Agent` 类里处理一切，而是在往：

- control plane
- runtime registry
- persistent daemon
- state persistence

这种方向走。

### 对我们的启发

我们现在完全没必要直接上 TUI/daemon 那么远，但很适合记住这条中间路线：

1. 先有 `RuntimeSession`
2. 再有 `TranscriptStore / SessionStore`
3. 再有更显式的 `Runtime`
4. 更后面才是更完整的控制平面/回放/监控

## 5. 它和我们当前项目的差异

## 5.1 我们当前更强的地方

我们在这些“框架内核层”上其实更清楚：

- `BaseAgent`
- `BasePrompt`
- `BaseTool`
- `BaseMemory`
- `BasePlanner`
- `BaseWorkflow`
- `BaseExecutor`

这意味着我们当前更像：

## 一个从抽象接口和执行主链往上长的 Agent Framework

## 5.2 它当前更强的地方

它更强在这些“运行表面 / 生态 / 控制层”能力上：

1. skill / command / rules / hooks 的产品化组织
2. session adapter 与 canonical snapshot 规范
3. 多 harness 兼容和安装体系
4. agent orchestration policy
5. runtime / state / registry / control-plane 演进意识

也就是说，它更像：

## 一个已经进入分发与运营阶段的 agentic platform

## 6. 对 `edu_agent` 最值得借鉴的设计落点

如果只选当前最适合落到我们项目里的几个点，我会推荐：

## 6.1 继续强化 `RuntimeSession`

当前我们已经有：

- 单轮输入
- planner result
- tool/model calls
- final output
- errors

下一步可以思考：

1. `workflow_result`
2. step trace
3. 未来序列化 shape

## 6.2 设计未来的 canonical runtime snapshot

当前不急着实现，但可以在设计文档里明确：

- `RuntimeSession` 是内部对象
- 后面会有面向持久化/回放/UI 的标准快照协议

## 6.3 为 `TranscriptStore / SessionStore` 预留接口

等 `RuntimeSession` 再稳定一层之后，最自然的下一步就是：

- 让运行轨迹可存
- 让运行轨迹可回放

## 6.4 思考未来的 workflow surface

我们当前已经有：

- Planner
- Workflow
- Executor

后面可以继续想：

- 哪些能力应该成为“工作流表面”
- 哪些只是兼容壳

这正是 `skills-first` 思路能给我们的启发。

## 7. 当前建议的学习顺序

为了避免被这个项目的海量资产淹没，建议后续按这个顺序继续学：

1. 先深读 `SESSION-ADAPTER-CONTRACT.md`
   目标：学它怎么定义统一 snapshot 协议。
2. 再看 session adapter / state store / runtime 相关实现
   目标：学它怎么把文档契约落成代码。
3. 最后再回头看 `skills/`、`commands/`、`agents/`
   目标：理解它的工作流表面和 orchestration policy。

## 8. 一句话总结

`everything-claude-code` 最值得我们当前阶段学习的，不是它海量的 skills，而是：

1. `skills-first` 的工作流表面设计
2. `agent-first` 的协作策略
3. `session adapter + canonical snapshot` 的 runtime 规范
4. `runtime / control-plane` 的演进思维

这些点和我们现在正在做的：

- `RuntimeSession`
- `Workflow`
- `Executor`
- 后续 `TranscriptStore / Runtime`

是天然能接上的。
