# `student/claw-code-main` Agent/Harness 架构学习说明

## 1. 文档目的

本文档基于对 [`student/claw-code-main`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main) 本地代码的阅读整理而成，目标不是逐文件翻译，而是帮助后续学习时快速理解：

1. 这个项目到底是什么类型的系统。
2. 它的主入口、运行时、命令/工具表面、会话与执行链路如何组织。
3. 它和我们当前 `edu_agent` 自研 Agent 框架有什么相似点与差异点。
4. 哪些设计值得借鉴，哪些只是该项目在“clean-room port / harness 研究”场景下的特殊产物。

## 2. 先给结论：这不是一个传统“业务 Agent”，更像一个 Harness Runtime / 镜像运行时

从当前 Python `src/` 实现看，`claw-code-main` 的核心目标不是直接做一个“聊天 Agent 产品”，而是：

1. 复刻并整理一个 **agent harness / runtime** 的结构认知。
2. 把命令、工具、运行时上下文、会话、权限、转录、CLI 入口组织成一个可运行的研究型 Python 工作区。
3. 提供一个“镜像执行面”：
   - 可以列出命令和工具表面
   - 可以做 prompt routing
   - 可以模拟 turn loop
   - 可以持久化 session
   - 可以生成 runtime report / parity report

因此，它当前更像：

- 一个 **带 CLI 的 agent runtime 原型**
- 一个 **命令/工具镜像与编排研究工程**
- 一个 **harness 结构学习项目**

而不是我们现在这种：

- `ChatAgent + Planner + Workflow + Tool + Memory`
- 面向“后续真正做复杂 Agent 框架”的逐层抽象

## 3. 顶层目录结构怎么理解

项目关键目录如下：

```text
student/claw-code-main/
  README.md
  CLAUDE.md
  src/                # 当前 Python 主实现
  tests/              # Python 侧验证
  rust/               # Rust 版运行时 / CLI 正在推进
  assets/             # README / 说明用素材
```

### 3.1 `src/`

这是当前最核心的 Python 实现工作区，重点不是做某一个“聊天机器人”，而是把运行时相关概念拆成多个模块：

- 入口与 CLI：[`src/main.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/main.py)
- 运行时：[`src/runtime.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/runtime.py)
- 查询引擎 / 会话循环：[`src/query_engine.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/query_engine.py)
- 命令表面：[`src/commands.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/commands.py)
- 工具表面：[`src/tools.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/tools.py)
- 执行注册表：[`src/execution_registry.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/execution_registry.py)
- 会话持久化：[`src/session_store.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/session_store.py)
- 转录与历史：[`src/transcript.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/transcript.py), [`src/history.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/history.py)
- 运行上下文：[`src/context.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/context.py)
- 权限：[`src/permissions.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/permissions.py)
- 清单与镜像元数据：[`src/port_manifest.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/port_manifest.py), [`src/models.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/models.py)

### 3.2 `rust/`

`README` 和 `CLAUDE.md` 都说明了 Rust 版正在推进，而且被视为未来更正式的 runtime/CLI 实现。  
这说明该项目的 Python `src/` 更像是：

- 研究工作区
- 原型运行时
- porting / parity 学习层

而 Rust 版则更偏：

- 正式 CLI/runtime 产品化方向

## 4. 入口层：`main.py` 是一个总控 CLI

[`src/main.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/main.py) 是整个 Python 工作区最重要的入口。

它的特点很鲜明：

1. **不是 HTTP API 入口**
2. **不是单一聊天入口**
3. **而是一个多命令 CLI 总控台**

### 4.1 它暴露了很多运行模式

例如：

- `summary`
- `manifest`
- `parity-audit`
- `commands`
- `tools`
- `route`
- `bootstrap`
- `turn-loop`
- `flush-transcript`
- `load-session`
- `remote-mode`
- `ssh-mode`
- `teleport-mode`
- `show-command`
- `show-tool`
- `exec-command`
- `exec-tool`

这说明它的设计思路是：

## 用 CLI 暴露 runtime/harness 的不同观察和执行面

也就是说，`main.py` 并不只是“运行模型”，而是在统一暴露：

- 清单视图
- 路由视图
- 执行视图
- 会话视图
- 远程模式视图

这种设计很适合研究型 harness 项目。

## 5. 运行时层：`PortRuntime`

[`src/runtime.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/runtime.py) 可以理解成 Python 工作区里的“运行时总协调器”。

它不是一个聊天 Agent，而更像一个：

## runtime façade / orchestration coordinator

### 5.1 它负责的核心事情

1. 将 prompt 路由到命令和工具表面
2. 构造 session 运行报告
3. 管理 turn loop
4. 组装 setup/context/system init/history/session persistence

### 5.2 关键接口

#### `route_prompt(prompt, limit=5)`
职责：
- 将用户 prompt token 化
- 在 `PORTED_COMMANDS` 与 `PORTED_TOOLS` 中做简单匹配
- 返回一组 `RoutedMatch`

#### `bootstrap_session(prompt, limit=5)`
职责：
- 构建上下文
- 运行 setup
- 路由 prompt
- 建立 execution registry
- 收集 command/tool execution message
- 调用 query engine 产出 turn result
- 持久化 session
- 返回完整的 `RuntimeSession`

#### `run_turn_loop(prompt, ...)`
职责：
- 模拟多轮 turn loop
- 多次调用 `QueryEnginePort.submit_message(...)`

### 5.3 `RuntimeSession`

`RuntimeSession` 是这个项目里一个很关键的聚合对象。  
它把一次 runtime 运行中涉及的很多维度都包在一起：

- prompt
- context
- setup/setup_report
- system init message
- history
- routed matches
- turn result
- command/tool execution messages
- stream events
- persisted session path

这说明这个项目非常重视：

## “一次运行到底发生了什么”的可观测汇总

这一点和我们自己后面想做的 `Observability` 非常像。

## 6. Query Engine：会话循环与输出组织层

[`src/query_engine.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/query_engine.py) 是另一个核心模块。

它更像：

## 一个极简的 turn engine / session engine

### 6.1 关键数据结构

#### `QueryEngineConfig`
定义：
- `max_turns`
- `max_budget_tokens`
- `compact_after_turns`
- `structured_output`
- `structured_retry_limit`

这说明它虽然不是一个真正接 LLM API 的完整推理引擎，但已经开始有：

- 回合限制
- token 预算
- transcript compact
- structured output retry

这些典型 runtime concerns。

#### `TurnResult`
职责：
- 承载一次 turn 的输出
- 记录 matched commands/tools、permission denials、usage、stop_reason

### 6.2 `QueryEnginePort` 做了什么

#### `submit_message(...)`
职责：
- 做最大 turn 限制判断
- 组织 summary_lines
- 生成 output
- 更新 usage
- 记录 transcript
- 累计 permission denials
- 必要时 compact 消息

注意：  
当前 Python 版更像是在**模拟一个带预算和状态的 turn engine**，而不是直接调用真实大模型。

#### `stream_submit_message(...)`
职责：
- 生成类似 SSE/streaming 的事件序列
- 包括：
  - `message_start`
  - `command_match`
  - `tool_match`
  - `permission_denial`
  - `message_delta`
  - `message_stop`

这说明作者对“runtime streaming surface”是有明确建模意识的。

#### `persist_session()`
职责：
- 通过 [`session_store.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/session_store.py) 落盘保存会话

## 7. 命令与工具层：不是“真实业务工具”，而是“镜像表面”

[`src/commands.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/commands.py) 和 [`src/tools.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/tools.py) 很值得注意。

这两层的关键点不是“实现了很多真实工具逻辑”，而是：

## 它们基于 snapshot/reference_data 构造了一个镜像化的命令/工具清单

### 7.1 关键特征

1. 从 JSON snapshot 加载 `PortingModule`
2. 提供：
   - `get_*`
   - `find_*`
   - `render_*_index`
   - `execute_*`
3. `execute_command` / `execute_tool` 当前更多是：
   - 返回“哪个镜像命令/工具会处理这个输入”的 message

这说明当前 Python 版重点在：

- mirror the surface
- build the registry/index
- simulate the execution contract

而不是立即把每个 command/tool 的真实业务逻辑全部补完。

这和我们当前项目的差别很大：

- 我们是“先做可运行的最小真实 tool”
- 它是“先做命令/工具表面的镜像与运行时组织”

## 8. 执行注册表：Execution Registry

[`src/execution_registry.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/execution_registry.py) 的作用非常清楚：

## 它是命令/工具执行对象的查找中心

里面定义了：

- `MirroredCommand`
- `MirroredTool`
- `ExecutionRegistry`

### 它的设计价值

把：
- “有哪些命令/工具”
- “怎么按名字找到可执行对象”

单独收成了一层。

这和我们自己项目里的：
- `ToolRegistry`
- 未来可能的 `CommandRegistry`

有很强的相似性。

## 9. 上下文、历史、转录、会话存储

这块是 `claw-code-main` 很值得学习的地方，因为它对 runtime supporting structures 的拆分很清楚。

### 9.1 `context.py`

[`src/context.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/context.py) 定义了 `PortContext`：

- `source_root`
- `tests_root`
- `assets_root`
- `archive_root`
- `python_file_count`
- `test_file_count`
- `asset_file_count`
- `archive_available`

这说明它的 context 不是“会话上下文”，而更像：

## 工作区 / 运行环境上下文

也就是：
- 当前源码树在哪
- 资源在哪
- 是否存在 archive
- 当前工作区规模如何

### 9.2 `history.py`

[`src/history.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/history.py) 维护了 `HistoryLog`：

- 用事件列表记录关键运行节点
- 可以渲染成 markdown

这说明作者很重视：

## “把运行过程变成可回看的历史记录”

### 9.3 `transcript.py`

[`src/transcript.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/transcript.py) 的 `TranscriptStore` 很轻，但职责非常清楚：

- append
- compact
- replay
- flush

也就是：

## 记录会话文本轨迹，并支持压缩与重放

### 9.4 `session_store.py`

[`src/session_store.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/session_store.py) 用 JSON 文件保存：

- `session_id`
- `messages`
- `input_tokens`
- `output_tokens`

它体现的是：

## 最小持久化会话层

不是复杂数据库，但已经足够支撑：
- save / load session
- 基础 replay
- usage tracking

## 10. 权限层：ToolPermissionContext

[`src/permissions.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/permissions.py) 提供了 `ToolPermissionContext`。

它的职责是：

- 根据 deny names / deny prefixes
- 判断某个 tool 是否被阻止

这个设计点很值得学习，因为它说明作者没有把“工具是否可用”写死在工具执行逻辑里，而是：

## 把工具权限上下文单独抽成一层

这和未来我们要做的：
- sandbox
- permission gating
- policy enforcement

非常接近。

## 11. `port_manifest.py` / `models.py`：元数据与清单层

这两层的作用是：

### `models.py`
提供整个 Python 工作区很多共享数据结构，比如：

- `Subsystem`
- `PortingModule`
- `PermissionDenial`
- `UsageSummary`
- `PortingBacklog`

### `port_manifest.py`
负责扫描当前 `src/` 树，构造 `PortManifest`，并输出 markdown 说明。

这说明该项目并不只是“跑一下代码”，而是在有意识地维护：

## 对代码工作区本身的可描述性与可视化能力

## 12. 它的高层架构可以怎么理解

可以把当前 Python 版大致理解成下面这条链：

```text
CLI(main.py)
  -> PortRuntime
     -> build context / setup / system init
     -> route prompt to mirrored command/tool surface
     -> build execution registry
     -> collect command/tool execution messages
     -> QueryEnginePort submit / stream submit
     -> update transcript / usage / permission denials
     -> persist session
     -> render runtime session report
```

如果从职责角度再压缩一下，可以理解成 6 层：

1. **CLI/Entrypoint 层**
   - `main.py`
2. **Runtime Orchestration 层**
   - `runtime.py`
3. **Turn / Session Engine 层**
   - `query_engine.py`
4. **Registry / Surface 层**
   - `commands.py`
   - `tools.py`
   - `execution_registry.py`
5. **State / Context / Persistence 层**
   - `context.py`
   - `history.py`
   - `transcript.py`
   - `session_store.py`
6. **Metadata / Manifest / Snapshot 层**
   - `models.py`
   - `port_manifest.py`
   - `reference_data/*`

## 13. 和我们当前 `edu_agent` 的关键差异

### 13.1 它更偏“runtime/harness 研究工程”

我们当前项目的主线是：

- Agent
- Tool
- Memory
- Prompt
- Planner
- Workflow
- Executor

是从“可运行 Agent 框架”往上长。

而 `claw-code-main` 当前 Python 版更偏：

- CLI runtime
- mirrored command/tool inventories
- session/reporting/persistence
- runtime orchestration study

它更像：

## “把 Claude Code 类 harness 的外壳、运行面、命令/工具表面和会话机制研究清楚”

### 13.2 它当前弱于我们的地方

从 Agent 框架角度看，它当前 Python 版并没有像我们这样明确落地：

- `BaseAgent`
- `BaseTool` 真执行链
- `BaseMemory`/`InMemoryMemory`
- `BasePlanner`
- `BaseWorkflow`
- `BaseExecutor`

也就是说，它当前 Python 版更多是：

## 镜像与组织
而我们当前则更偏：

## 抽象与最小真实执行链

### 13.3 它强于我们的地方

它在以下方面有更强的“runtime/harness 气质”：

1. CLI surface 很完整
2. 会话持久化、usage、turn limits、structured output retry 这些 runtime concerns 建模得更早
3. context / history / transcript / session persistence 分得很清楚
4. 命令/工具 inventory + registry + routing 这套镜像 runtime 组织得更明显

## 14. 值得我们借鉴的设计点

### 14.1 RuntimeSession 这种“单次运行总报告对象”
很值得学。

我们后面如果做：
- Observability
- 回放
- 调试面板

完全可以借鉴这种思路：

## 把一次运行的上下文、路由、执行、输出、session path 汇总成一个对象

### 14.2 QueryEngineConfig 这种“turn/budget/structured output”配置面
很值得学。

它提醒我们，真正的 runtime 迟早要关心：

- 最大轮数
- token 预算
- transcript compact
- structured output retry

### 14.3 ExecutionRegistry / ToolPermissionContext
很值得学。

一个是：
- “按名字找执行对象”的中心

另一个是：
- “按策略决定哪些工具能不能用”的权限层

这两块都很适合我们后续演进。

### 14.4 TranscriptStore / SessionStore / HistoryLog 三层分开
也很值。

因为它们其实分别处理：

- 会话文本轨迹
- 会话持久化
- 运行历史事件

这和我们以后可能做的：
- transcript
- runtime event log
- persisted session

是可以一一对应的。

## 15. 不要直接照搬的地方

### 15.1 不要把“镜像表面工程”误当成“完整 Agent 框架”
`claw-code-main` 当前 Python 版很有研究价值，但它的中心不完全等于我们当前项目的中心。

我们更需要的是：

- 真正的 Agent 抽象
- Tool/Planner/Workflow/Executor 主链

而不是优先把所有 CLI surface 和 snapshot inventory 都补满。

### 15.2 不要过早为了“像 runtime”而牺牲主链路简洁性
它很多模块是为了镜像和研究 Claude Code harness 的形态，这很有价值。  
但如果我们当前直接全盘模仿，可能会让自己的项目过早变重。

## 16. 对我们后续学习最有帮助的阅读顺序

如果后面你想继续系统学习这个项目，我建议按下面顺序看：

1. [`README.md`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/README.md)
   职责：理解项目定位，不要误判成普通聊天 Agent。
2. [`src/main.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/main.py)
   职责：看清 CLI surface 和主入口。
3. [`src/runtime.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/runtime.py)
   职责：理解高层 orchestration。
4. [`src/query_engine.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/query_engine.py)
   职责：理解 turn/session/usage/structured output 这一层。
5. [`src/commands.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/tools.py) 与 [`src/tools.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/tools.py)
   职责：理解 mirrored command/tool surface。
6. [`src/execution_registry.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/execution_registry.py)
   职责：理解 registry 设计。
7. [`src/context.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/history.py)、[`src/transcript.py`](/Users/hqluo/Dev/AgentWorkSpace/edu_agent/student/claw-code-main/src/session_store.py)
   职责：理解 supporting state 层。

## 17. 一句话总结

`student/claw-code-main` 当前 Python `src/` 更像一个 **CLI 驱动的 harness/runtime 镜像研究工程**，核心优势在于：

- 运行时入口清楚
- 命令/工具表面组织清楚
- 会话、转录、历史、权限、usage 建模较早
- 一次运行的可观测性比较强

而我们当前 `edu_agent` 更偏 **自研 Agent 框架主链**，已经在：

- Agent
- Tool
- Memory
- Prompt
- Planner
- Workflow
- Executor

这些抽象上走得更深。

所以后续最好的学习方式不是照搬，而是：

## 借鉴它的 runtime / observability / session / registry 设计，
## 再继续沿我们自己的 Agent 主链往前推。
