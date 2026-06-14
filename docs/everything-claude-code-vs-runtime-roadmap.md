# `everything-claude-code` 与 `edu_agent` Runtime 路线对照

## 1. 文档目的

这份文档用于把我们当前的：

- `RuntimeSession`
- `ChatAgent`
- `Workflow`
- `Executor`

与 [`student/everything-claude-code`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/everything-claude-code) 中最值得借鉴的 runtime 设计放到同一张图里。

目标不是照搬对方，而是回答三个问题：

1. 我们现在 runtime 已经走到哪一步了。
2. 对方在 runtime / session / control-plane 方面比我们强在哪里。
3. 我们后续应该按什么顺序演进，既不跳太快，也不失去方向。

---

## 2. 先给结论

如果只用一句话概括：

- `everything-claude-code` 已经在思考 **session adapter + canonical snapshot + runtime/control-plane**
- `edu_agent` 当前更接近 **内部运行对象 + 最小执行主链**

也就是说：

### 我们现在已经有的

1. 单轮运行快照对象：`RuntimeSession`
2. Agent 主链接入：`ChatAgent + RuntimeSession`
3. 规划层：`Planner`
4. 执行层：`Workflow + Executor`

### 对方比我们更成熟的地方

1. Session adapter 归一化思路
2. Canonical snapshot 契约
3. 更清晰的 runtime / state / control-plane 演进视角
4. 更产品化的 workflow surface 与 orchestration policy

---

## 3. 当前两边 runtime 关注点对照

## 3.1 `edu_agent`

我们当前的 runtime 主要在做：

1. 记录一轮输入是什么
2. 记录 planner 怎么决策
3. 记录工具或模型调用
4. 记录最终输出
5. 让这些信息跟随 `AgentOutput` 返回

一句话就是：

## 我们现在更像“单轮运行快照”

---

## 3.2 `everything-claude-code`

它更进一步在做：

1. 多来源 session 的归一化
2. 面向持久化与控制层的标准快照协议
3. worker 级状态聚合
4. aggregate 统计
5. 未来 UI / TUI / daemon / state store 的统一输入

一句话就是：

## 它更像“控制平面可消费的标准运行快照”

---

## 4. 最值得我们借鉴的 runtime 设计

## 4.1 内部运行对象 vs 对外标准快照协议分层

这是我认为最值得我们借鉴的一点。

### 我们现在

`RuntimeSession` 既是：

- 内部运行对象
- 也是当前对外调试时能看到的快照

这在当前阶段是对的，而且足够轻。

### 对方提醒我们的未来方向

后面很自然会分成两层：

1. **内部运行对象**
   适合在 `ChatAgent`、`Workflow`、`Executor` 里边跑边写。
2. **标准快照协议**
   适合拿去：
   - 持久化
   - 回放
   - UI 展示
   - 控制层消费

### 对我们的启发

当前不要急着分层实现，但在设计上要明确：

## `RuntimeSession` 不是最终形态，它更像 future canonical snapshot 的前置层

---

## 4.2 Session Adapter 思维

在 `everything-claude-code` 里，不同来源的 session 会先被 adapter 归一化，再输出成统一 snapshot。

### 这点为什么重要

因为运行信息的来源未来可能不止一种：

1. `ChatAgent` 单轮执行
2. `Workflow` 多步执行
3. 历史记录回放
4. 未来多 Agent 协作 session

如果没有 adapter 思维，后面很容易变成：

- 每种来源一种结构
- 上层 UI / store / monitor 都要写很多兼容代码

### 对我们的启发

当前阶段先不用实现 adapter，但可以开始在文档里统一约束：

1. `RuntimeSession` 负责内部收集
2. 后续如果进入持久化/回放/UI，再通过 adapter 或 serializer 转成统一快照

---

## 4.3 Canonical Snapshot Contract

`everything-claude-code` 通过 `SESSION-ADAPTER-CONTRACT` 做了一件很工程化的事：

## 先把“快照长什么样”定义成契约，再让实现去符合它

这个设计特别适合我们以后做：

- `TranscriptStore`
- `SessionStore`
- `Runtime monitor`
- 可视化调试页

### 对我们的启发

我们后面可以逐步思考：

1. `schemaVersion`
2. `session`
3. `steps/workers`
4. `aggregates`
5. `artifacts`

这些字段是否也需要进入我们的“标准 runtime 快照”定义。

当前还不用实现，但这个方向值得提前记住。

---

## 4.4 Runtime / Control-plane 演进思维

`everything-claude-code` 的参考架构把系统往：

- TUI Layer
- Runtime Layer
- Daemon Layer

方向拆开。

我们现在当然还没到那一步，但这给了我们一条非常清楚的演进路线：

### 当前阶段

`ChatAgent + RuntimeSession`

### 下一阶段

`Workflow / Executor + RuntimeSession`

### 再下一阶段

`TranscriptStore / SessionStore`

### 更后面

显式 `Runtime`

### 再更后面

control-plane / replay / monitor / UI

这条路线特别适合我们现在这样一步一步往上搭，而不是一上来就设计一个大而全运行时。

---

## 5. 当前我们最应该怎么演进

结合当前项目状态，我建议按这个顺序走：

## 第一阶段：收稳当前 `RuntimeSession`

目标：

1. 让 `ChatAgent` 里的 runtime 记录结构稳定
2. 测试守住工具分支 / 模型分支
3. 明确哪些字段属于单轮运行快照

## 第二阶段：把 `RuntimeSession` 往 `Workflow / Executor` 深接

目标：

1. 让 runtime 看见 step 级执行
2. 决定 `workflow_result` 怎么存
3. 决定 step 结果要不要进入 runtime trace

## 第三阶段：引入 `TranscriptStore / SessionStore`

目标：

1. 让运行轨迹可存
2. 让 session 元信息与多轮运行记录分层管理
3. 为后续 UI/调试视图做准备
4. 为 replay / session 查询 / 回放能力打基础

## 第四阶段：考虑 canonical snapshot

目标：

1. 把内部 `RuntimeSession` 与对外标准快照分层
2. 让 store / replay / monitor 不直接依赖内部对象

---

## 7. 当前新增进展：planner / executor 解释性增强

最近这一轮我们已经把 runtime 记录链再往前推了一步：

1. `RulePlanner.plan()` 不再只返回松散 action，而是返回稳定的 `planner_result`。
2. `AgentExecutor.execute_step()` 已统一 step result 协议，开始显式输出：
   - `action`
   - `input_summary`
   - `output_summary`
3. `ChatAgent` 已把 planner 决策和 workflow step 摘要一起写进 `RuntimeSession.workflow_trace`。
4. 对应测试已经覆盖：
   - planner trace 会记录完整 `plan`
   - workflow step trace 会记录 step 级摘要

## 8. 当前新增进展：前端调试视图分层

在完成解释性 trace 主链之后，前端调试台也进入了新的分层阶段：

1. 首页不再承载完整 session 调试详情，而是改成轻量 `SessionSidebar`。
2. session 的完整调试信息被迁移到独立 `SessionDetailPage`。
3. 详情页已经能完整消费当前 runtime 数据，包括：
   - `planner_result`
   - `workflow_trace`
   - `tool_calls`
   - `model_calls`
   - `workflow_result`
   - `errors`
4. 详情页支持 transcript 过滤、trace 过滤与 transcript 快捷切换，这说明前端已经不只是“展示存量数据”，而是在逐步形成 runtime 调试 surface。

这一步很重要，因为它说明我们开始把：

- runtime 数据结构
- 调试交互
- 页面分层

作为同一个系统去设计，而不是各自零散演进。

这一步的意义在于：

## 我们现在的 runtime 不只是“能保存”，还开始“会解释”

这对后续前端调试台、持久化回放、失败分析都很关键。

---

## 6. 一个更直白的路线图

```text
今天
  RuntimeSession
    -> 记录单轮输入、规划、调用、输出

下一步
  RuntimeSession + Workflow/Executor
    -> 记录 step 级执行

再下一步
  TranscriptStore / SessionStore
    -> 保存运行轨迹并建立 session 目录层

更后面
  Canonical Runtime Snapshot
    -> 统一持久化 / UI / 回放协议

再更后面
  Runtime / Control Plane
    -> 监控、回放、可视化调试、多会话聚合
```

---

## 7. 现在最重要的取舍

这个对照文档最想帮我们守住的一件事是：

## 不要因为看到了更成熟的 runtime/control-plane 设计，就跳过中间层

也就是说：

- 不要一上来就做大而全 `Runtime`
- 不要跳过 `RuntimeSession -> TranscriptStore -> SessionStore` 这条中间演进路径

## 8. 当前阶段补充说明

截至当前阶段，`edu_agent` 已经不只是“规划 + Workflow + RuntimeSession”：

1. `RuntimeSession` 已能记录单轮输入、规划、`workflow_trace`、工具/模型调用与最终输出。
2. `TranscriptEntry` 已落地，transcript 记录已从松散 dict 收敛为明确的数据对象。
3. `TranscriptStore` 已接入 `ChatAgent` 主链，可按 `session_id` 追加统一结构的 `agent` 记录。
4. `SessionStore` 已接入 `ChatAgent` 主链，可在 transcript 写入前确保 session 已存在。
5. `RuntimeManager` 已开始统一协调 `RuntimeSession`、`TranscriptEntry`、`TranscriptStore` 与 `SessionStore`。

这意味着我们当前正处于：

## `RuntimeSession + Workflow/Executor + TranscriptStore/SessionStore` 的过渡阶段

这一阶段的意义是：

- 先把“单轮快照”
- 扩展成“多轮记录”
- 再扩展成“有 session 容器的运行记录系统”

后面如果继续演进到 canonical snapshot / runtime control-plane，就会顺很多。
- 不要一上来就做复杂 session schema
- 不要一上来就做控制平面

我们现在最稳的推进方式仍然是：

1. 先把内部运行对象收稳
2. 再让它覆盖更多执行层
3. 再考虑序列化与持久化
4. 最后再上升到控制层

这也是我们一路把：

- Prompt
- Planner
- Workflow
- Executor
- RuntimeSession

做顺的原因。

---

## 8. 一句话总结

`everything-claude-code` 给我们最大的启发不是“再加更多 skill”，而是：

## Runtime 最终应该演进成：
- 有内部运行对象
- 有标准快照协议
- 有 adapter
- 有 transcript/store
- 有 control-plane 视角

而我们现在最正确的做法，是继续沿着这条路线一步一步长，不要跳级。

---

## 9. 后续路线

结合当前项目状态，后续推进不应再按“零散功能点”思考，而应按以下阶段稳定推进：

### 第一阶段：收口组装根

优先目标：

1. 引入 `AgentFactory`，把 `ChatService` 中的组装职责提出来。
2. 明确 `route -> service -> factory -> agent framework` 的分层关系。
3. 让 `ChatService` 更聚焦于业务调用与 session 统一，而不是底层依赖构造。

### 第二阶段：打通查询能力

优先目标：

1. 为 `ChatService` 增加最小查询接口，例如：
   - `list_sessions()`
   - `get_transcript(session_id)`
2. 为 route 增加最小查询 API，例如：
   - `GET /sessions`
   - `GET /sessions/{session_id}/transcript`
3. 让 `SessionStore / TranscriptStore` 从“会保存”走向“可读取、可观察”。

### 第三阶段：建立标准快照协议

优先目标：

1. 让 `RuntimeSession` 提供 `to_dict()` 或 `to_snapshot()`。
2. 让 `TranscriptEntry` 提供 `to_dict()`。
3. 统一 session / transcript / runtime 的对外序列化结构。
4. 将当前内部 Python 对象逐步收敛为稳定、可序列化、可持久化的快照协议。

### 第四阶段：引入持久化 Store

优先目标：

1. 提供持久化版 `SessionStore`。
2. 提供持久化版 `TranscriptStore`。
3. 第一版优先 SQLite 或文件落盘，不急着做复杂数据库设计。
4. 让 session / transcript 能跨进程与重启保留。
5. 当前可先接受“SQLite store 作为 runtime 层另一种实现”的形态，不必过早引入 ORM、repository 或独立 database 层。
6. 当前阶段还应优先验证：默认应用实例能否通过配置切到 sqlite，以及 sqlite 模式下最小 chat -> session/transcript 查询闭环是否成立。
7. 随着配置项增加，应把 `STORE_BACKEND / RUNTIME_DB_PATH / OPENAI_*` 等读取逻辑收口到统一 `Settings`，避免 service/factory 各自读取环境变量。
8. 在进入更重的 route/UI 验证前，应先确认 sqlite 数据能跨 service 实例保留；这条最小恢复验证当前已成立。

### 第五阶段：把记录层做成可视化与可调试能力

优先目标：

1. 增加 session 列表查看能力。
2. 增加 transcript 查看能力。
3. 增加 runtime snapshot 查看能力。
4. 为后续 replay、observability、调试面板打基础。

### 第六阶段：进入复杂 workflow 与多 agent 地基

优先目标：

1. 引入条件分支 workflow。
2. 增强 workflow context 和步骤控制能力。
3. 为多 agent orchestration 预留 role、route、policy 与 runtime 记录结构。

---

## 10. 执行顺序建议

如果只看最近的一段实现节奏，建议按下面顺序推进：

1. `AgentFactory`
2. 查询能力
3. 快照协议
4. 持久化 Store
5. 可视化查看
6. Replay / Observability

这条顺序的核心原则是：

- 先让系统“会运行”
- 再让系统“会记录”
- 再让系统“可读取”
- 再让系统“可持久化”
- 最后再让系统“可观察、可回放、可扩展”
