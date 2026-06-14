# edu_agent

`edu_agent` 是一个面向 Agent 学习与实践的自研 Agent 框架项目，包含 Vue3 前端调试台、FastAPI 后端与可扩展的运行时主链。项目从最小可运行原型起步，逐步演进到具备规划、工作流、异步任务与运行轨迹可观测的完整 Agent 运行时。

## 产品定位

**主方向：** Agent 运行时 + 可观测 + 规则化 Eval 的学习 / 实验平台。

我们关注 Agent **怎么跑、怎么失败、怎么被验收**，而不是再做一个通用聊天壳。垂直场景（如轻量物理实验、媒体 artifact）仅作为**实验题库**，不定义主品牌。

**现阶段不做：** 通用 C 端聊天、Coding Agent 主赛道、训练式智能阅卷、高保真物理仿真平台、企业全栈 Agent SaaS。

完整说明见 [`docs/agent-framework-design.md` §2 产品定位与边界](docs/agent-framework-design.md#2-产品定位与边界)。实验与规则 Eval 见 [`docs/experiments.md`](docs/experiments.md)。

当前已具备以下能力：

- Vue3 前端聊天界面与运行时调试面板
- FastAPI 后端聊天接口与异步任务 API（提交 / 查询 / 取消 / 日志）
- 自研 Agent 框架骨架（Agent / Model / Tool / Memory / Planner / Workflow / Runtime）
- `MockModel` 与真实 `OpenAIModel` 接入
- 规则版 `ToolRouter` + `ToolRegistry` + `TimeTool` + `FFmpegArtifactTool`
- `BaseMemory` 与 `InMemoryMemory` 短期记忆实现
- 模型分支可读取最近历史消息参与上下文构建
- `BasePlanner` 与 `RulePlanner` 规则规划能力（含步骤构建器拆分）
- `SequentialWorkflow`、`ParallelWorkflow` 与 `AgentExecutor` 工作流执行能力
- Workflow 支持步骤结果传递，后一步可消费前一步输出
- `RuntimeSession` 运行快照能力，可记录单轮输入、规划、调用轨迹与最终输出
- `BaseTranscriptStore` / `PersistentTranscriptStore`，可按 `session_id` 保存多轮运行记录
- `BaseSessionStore` 与内存 / SQLite 持久化实现，可管理 session 元信息并在主链中自动建 session
- 终端 CLI（`python -m app.cli`）对接 HTTP API，便于本地调试
- 前后端一问一回联调
- Docker 化后端部署
- Nginx 部署前端并代理后端接口

## 当前核心链路

当前项目后端核心调用链路如下：

```text
AgentInput
  -> ChatAgent
  -> 写入 user memory
  -> RulePlanner
     -> ToolRouter 匹配工具
     -> 生成 tool / model / workflow plan
  -> ChatAgent 执行计划
     -> tool plan：ToolRegistry -> Tool
     -> model plan：Memory history -> PromptBuilder -> OpenAIModel / MockModel
     -> workflow plan：SequentialWorkflow -> AgentExecutor
  -> RuntimeSession 聚合本轮输入、计划、步骤轨迹、调用轨迹与最终输出
  -> SessionStore 确保当前 session 存在
  -> TranscriptStore 追加本轮 agent_run 记录
  -> 写入 assistant memory
  -> AgentOutput
```

## 当前架构总览

当前项目可以拆成四层理解：

### 1. 前端展示层

主要职责：

- 提供聊天输入框与消息展示
- 调用后端聊天接口
- 展示模型回复与错误提示

核心文件：

- `frontend/src/components/ChatWindow.vue`
- `frontend/src/services/chatApi.ts`

前端当前统一请求：

```text
/agent_api/chat
```

### 2. 后端 API 层

主要职责：

- 接收前端请求
- 校验输入
- 调用服务层
- 返回统一响应结构

核心文件：

- `backend/app/main.py`
- `backend/app/routes/chat.py`
- `backend/app/schemas/chat_input_output.py`

### 3. 服务层

主要职责：

- 负责把 API 层请求接入 Agent 框架
- 初始化模型与 Agent
- 承接业务调用过程

核心文件：

- `backend/app/services/chat_service.py`

### 4. Agent 框架层

主要职责：

- 定义 Agent 抽象
- 定义 Model 抽象
- 定义 Prompt 抽象与默认 Prompt 构建实现
- 定义 Tool 抽象、工具注册与规则路由
- 定义 Memory 抽象与会话记忆实现
- 定义 Planner 抽象与规则规划实现
- 定义 Runtime 最小运行快照对象
- 定义 Transcript / Session 存储抽象与内存实现
- 定义 Workflow / Executor 抽象与最小顺序执行能力
- 定义统一输入输出协议
- 执行带规则规划、工具调用、短期记忆、运行快照、会话记录与最小工作流的 Agent 推理链路

核心文件：

- `backend/app/agent/base_agent.py`
- `backend/app/agent/chat_agent.py`
- `backend/app/models/base_model.py`
- `backend/app/models/mock_model.py`
- `backend/app/models/openai_model.py`
- `backend/app/tools/base_tool.py`
- `backend/app/tools/time_tool.py`
- `backend/app/tools/tool_registry.py`
- `backend/app/tools/tool_router.py`
- `backend/app/memory/base_memory.py`
- `backend/app/memory/in_memory_memory.py`
- `backend/app/planners/base_planner.py`
- `backend/app/planners/rule_planner.py`
- `backend/app/prompts/base_prompt.py`
- `backend/app/prompts/prompt_builder.py`
- `backend/app/workflows/base_workflow.py`
- `backend/app/workflows/sequential_workflow.py`
- `backend/app/workflows/base_executor.py`
- `backend/app/workflows/agent_executor.py`
- `backend/app/runtime/runtime_session.py`
- `backend/app/runtime/base_transcript_store.py`
- `backend/app/runtime/in_memory_transcript_store.py`
- `backend/app/runtime/base_session_store.py`
- `backend/app/runtime/in_memory_session_store.py`
- `backend/app/schemas/agent_input.py`
- `backend/app/schemas/agent_output.py`
- `backend/app/schemas/agent_context.py`
- `backend/app/schemas/model_request.py`
- `backend/app/schemas/model_response.py`
- `backend/app/schemas/tool_input.py`
- `backend/app/schemas/tool_output.py`

## 当前端到端调用关系

从浏览器输入一条消息开始，当前完整调用链如下：

```text
浏览器页面
  -> chatApi.ts
  -> POST /agent_api/chat
  -> routes/chat.py
  -> services/chat_service.py
  -> ChatAgent.run()
  -> ChatAgent.act()
  -> 写入 user memory
  -> RulePlanner.plan()
     -> ToolRouter.route()
     -> 生成 tool / model / workflow plan
  -> ChatAgent 执行计划
     -> 命中工具：ToolRegistry.get_tool() -> Tool.run()
     -> 未命中：PromptBuilder.build_prompt() -> OpenAIModel.generate() / MockModel.generate()
     -> workflow：SequentialWorkflow.run() -> AgentExecutor.execute_step()
  -> RuntimeSession 记录 planner_result / workflow_trace / tool_calls / model_calls / final_output
  -> SessionStore 确保 session 存在
  -> TranscriptStore 追加本轮 agent_run 记录
  -> 写入 assistant memory
  -> AgentOutput
  -> ChatResponse
  -> 前端渲染消息
```

## 当前项目分层职责说明

为了避免后续扩展时职责混乱，当前建议坚持以下边界：

### `AgentInput / AgentOutput`

职责：

- 描述 Agent 层的输入和输出
- 不直接进入 Model 层

### `ModelRequest / ModelResponse`

职责：

- 描述 Model 层的输入和输出
- 不直接承载 Agent 语义

### `ChatAgent`

职责：

- 作为 Agent、Model、Tool、Memory、Planner 之间的编排层
- 根据 Planner 产出的计划决定走工具分支还是模型分支
- 将 `AgentInput` 转成 `ModelRequest`
- 将 `ToolOutput` / `ModelResponse` 转成 `AgentOutput`
- 在会话维度写入 user / assistant 消息到 Memory

### `BasePrompt / PromptBuilder`

职责：

- `BasePrompt` 定义 Prompt 抽象接口
- `PromptBuilder` 负责把历史消息和当前输入组织成模型可用的 prompt

### `OpenAIModel / MockModel`

职责：

- 作为 `BaseModel` 的具体实现
- 负责真正执行模型调用或模拟模型调用

### `ToolRegistry / ToolRouter / TimeTool`

职责：

- `ToolRegistry` 负责工具注册与查询
- `ToolRouter` 负责将自然语言输入匹配成工具名
- `TimeTool` 作为第一个真实接入 Agent 主流程的工具

### `BaseMemory / InMemoryMemory`

职责：

- 定义短期记忆抽象接口
- 按 `session_id` 保存多轮消息
- 为模型分支提供最近历史消息

### `BasePlanner / RulePlanner`

职责：

- `BasePlanner` 定义规划层抽象接口
- `RulePlanner` 基于 `ToolRouter` 结果生成最小执行计划
- 当前最小计划结果支持：
  - `{"action": "tool", "tool_name": "..."}`
  - `{"action": "model"}`

### `BaseWorkflow / SequentialWorkflow / AgentExecutor`

职责：

- `BaseWorkflow` 定义工作流抽象接口
- `SequentialWorkflow` 负责顺序执行多个步骤并汇总结果
- `BaseExecutor` 定义步骤执行抽象接口
- `AgentExecutor` 负责执行 `tool` / `model` 两类 step
- 当前 workflow 已支持通过 `context["step_results"]` 在步骤之间传递结果

### `RuntimeSession`

职责：

- 记录单轮运行的核心快照
- 聚合 `session_id`、`user_input`、`planner_result`
- 记录 `tool_calls`、`model_calls`、`final_output` 与 `errors`
- 记录 `workflow_trace`
- 作为最小 runtime 观测对象挂入 `AgentOutput.metadata["runtime_session"]`

### `BaseTranscriptStore / InMemoryTranscriptStore`

职责：

- 定义 transcript 存储抽象接口
- 按 `session_id` 保存多轮 `agent_run` 记录
- 为后续运行轨迹回看、调试与回放预留存储层

### `BaseSessionStore / InMemorySessionStore`

职责：

- 定义 session 元信息存储抽象接口
- 管理 session 的 `session_id`、`created_at`、`updated_at` 与 `metadata`
- 在 `ChatAgent` 主链中与 `TranscriptStore` 协同，确保 transcript 落库前 session 已存在

### `routes/chat.py`

职责：

- 保持为“薄路由”
- 不承担复杂业务逻辑

### `chat_service.py`

职责：

- 承接路由层和 Agent 框架之间的业务调用
- 后续适合作为框架集成的主要入口

当前对外聊天接口为：

```text
POST /agent_api/chat
```

## 当前已验证的能力

当前项目已经通过脚本测试验证了以下关键链路：

1. `ToolRouter -> RulePlanner -> ChatAgent`
   职责：验证工具分支与模型分支都能由 Planner 正常决策并执行。
2. `Memory + PromptBuilder + ChatAgent`
   职责：验证会话历史可被读取并参与模型输入构建。
3. `ChatAgent + RuntimeSession`
   职责：验证工具分支与模型分支都能记录单轮运行快照，并保留原始 metadata。
4. `SequentialWorkflow + AgentExecutor`
   职责：验证顺序工作流执行、步骤结果传递与最小执行层联动。
5. `ParallelWorkflow + WorkflowRunnerRegistry`
   职责：验证并行工作流注册、调度与步骤聚合。
6. 异步任务 API + CLI
   职责：验证后台任务提交、状态查询、日志拉取与终端客户端联调。

## 目录结构

```text
edu_agent/
  backend/          # FastAPI 后端与 Agent 框架
  frontend/         # Vue3 前端调试台
  docs/             # 设计与对照文档
  student/          # 参考项目（本地学习用，默认不纳入版本库）
```

## 本地开发

### 1. 启动后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

健康检查：

```text
GET http://127.0.0.1:8000/health
```

### 2. 配置后端环境变量

在 `backend/.env` 中配置（二选一）：

**DeepSeek（推荐，已配置 `DEEPSEEK_API_KEY` 时自动优先）**

```env
DEEPSEEK_API_KEY=你的密钥
DEEPSEEK_API_BASE=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

**OpenAI 或 OpenRouter 等兼容接口**

```env
OPENAI_API_KEY=
OPENAI_MODEL=
OPENAI_BASE_URL=
OPENAI_ORGANIZATION=
```

说明：

- `DEEPSEEK_API_KEY`
  职责：DeepSeek 模型调用认证；存在时覆盖 `OPENAI_*` 配置
- `DEEPSEEK_MODEL`
  职责：常用 `deepseek-chat` 或 `deepseek-reasoner`
- `OPENAI_API_KEY`
  职责：未设置 DeepSeek 时的模型调用认证
- `OPENAI_MODEL`
  职责：指定模型名
- `OPENAI_BASE_URL`
  职责：指定兼容 OpenAI 的第三方接口地址
- `OPENAI_ORGANIZATION`
  职责：可选组织信息

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问：

```text
http://127.0.0.1:5173
```

### 4. 本地前后端联调说明

前端代码统一使用相对路径：

```text
/agent_api/chat
```

本地开发时通过 `frontend/vite.config.ts` 中的代理转发到：

```text
http://127.0.0.1:8000
```

这样可以避免本地开发和线上部署反复改接口地址。

## API 说明

### POST `/agent_api/chat`

请求体：

```json
{
  "message": "你好",
  "session_id": "optional-uuid"
}
```

成功响应：

```json
{
  "reply": "你好，很高兴见到你",
  "session_id": "same-or-generated-uuid",
  "timestamp": "2026-03-29T10:00:00Z"
}
```

错误响应：

```json
{
  "error": {
    "code": "BAD_REQUEST",
    "message": "message不能为空"
  }
}
```

## 后端 Docker 部署

### 1. 构建镜像

后端 Dockerfile 位于：

```text
backend/dockerfile
```

如果本地是 Apple Silicon Mac，而服务器是常见 Linux x86_64，推荐显式构建 `linux/amd64` 镜像：

```bash
docker buildx build \
  --platform linux/amd64 \
  -t edu-agent-backend \
  -f ./backend/dockerfile \
  ./backend \
  --load
```

如果本地和服务器架构一致，也可以直接：

```bash
docker build -t edu-agent-backend -f ./backend/dockerfile ./backend
```

### 2. 导出镜像

```bash
docker save -o edu-agent-backend.tar edu-agent-backend
```

### 3. 上传镜像到服务器

```bash
scp edu-agent-backend.tar root@<server-ip>:/home/hqluo/edu-agent/
```

### 4. 服务器导入镜像

```bash
docker load -i /home/hqluo/edu-agent/edu-agent-backend.tar
```

### 5. 服务器准备 `.env`

服务器上准备：

```text
/home/hqluo/edu-agent/.env
```

内容与本地 `backend/.env` 一致，但不要提交到仓库。

### 6. 启动容器

```bash
docker run -d \
  --name edu-agent-backend \
  --restart unless-stopped \
  --env-file /home/hqluo/edu-agent/.env \
  -p 127.0.0.1:18000:8000 \
  edu-agent-backend
```
### 停止容器：
```bash
docker stop edu-agent-backend
```

说明：

- `127.0.0.1:18000:8000`
  职责：只对服务器本机开放容器服务，再由 Nginx 代理出去
- `--restart unless-stopped`
  职责：服务器重启后自动恢复容器

### 7.进入docker容器
```bash
docker exec -it <容器ID或名称> /bin/bash
```

### 7. 验证后端容器

查看日志：

```bash
docker logs edu-agent-backend
```



健康检查：

```bash
curl http://127.0.0.1:18000/health
```

聊天接口验证：

```bash
curl -X POST http://127.0.0.1:18000/agent_api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"你好"}'
```

## 前端 Nginx 部署

### 1. 本地构建前端

```bash
cd frontend
npm run build
```

构建产物位于：

```text
frontend/dist/
```

### 2. 上传前端构建产物

将 `dist/` 中的内容上传到服务器，例如：

```text
/var/www/html/glodDeer
```

### 3. Vite `base` 配置

如果前端部署在子路径下，例如：

```text
/glodDeer/
```

则 `frontend/vite.config.ts` 中应配置：

```ts
base: "/glodDeer/"
```

否则打包后静态资源路径可能错误，导致 JS/CSS 404。

### 4. Nginx 配置要点

Nginx 需要同时做两件事：

1. 提供前端静态资源
2. 代理后端接口 `/agent_api/`

一个典型思路如下：

```nginx
server {
    listen 80;
    server_name _;

    root /var/www/html/glodDeer;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /agent_api/ {
        proxy_pass http://127.0.0.1:18000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

注意：

- `location /` 中的 `try_files`
  职责：支持前端单页应用路由刷新
- `proxy_pass http://127.0.0.1:18000`
  职责：保留原始路径 `/agent_api/chat`
- 不要写成：

```nginx
proxy_pass http://127.0.0.1:18000/;
```

否则可能把 `/agent_api/` 前缀吃掉，导致后端收到 `/chat`，出现 404。

### 5. 重载 Nginx

先检查配置：

```bash
nginx -t
```

再重载：

```bash
systemctl reload nginx
```

## 常见问题与排查

### 1. 容器启动时报 `No module named 'dotenv'`

原因：

- `requirements.txt` 中缺少 `python-dotenv`

解决：

- 补充依赖
- 重新构建镜像
- 重新导出并上传镜像

### 2. 容器日志出现 `exec format error`

原因：

- 本地构建的是 `arm64` 镜像
- 服务器是 `amd64`

解决：

- 使用 `docker buildx build --platform linux/amd64 ...`
  构建服务器可用镜像

### 3. 前端页面打开，但静态资源 404

原因：

- 前端部署在子路径下
- `vite.config.ts` 中 `base` 没有和部署路径对齐

解决：

- 根据部署路径设置正确的 `base`
- 重新 build 并重新上传 `dist`

### 4. 前端报 `crypto.randomUUID is not a function`

原因：

- 当前浏览器运行环境不支持 `crypto.randomUUID()`

解决：

- 前端代码中增加兼容 fallback，避免直接裸用

### 5. 前端请求 `127.0.0.1:8000` 报错

原因：

- 浏览器中的 `127.0.0.1` 指向用户本机，而不是服务器

解决：

- 前端统一使用相对路径 `/agent_api/chat`
- 本地开发通过 Vite 代理
- 线上部署通过 Nginx 代理

### 6. Nginx 返回 404，但后端容器正常

原因：

- `/agent_api/` 的 `proxy_pass` 写法不对

解决：

- 确保使用：

```nginx
proxy_pass http://127.0.0.1:18000;
```

而不是带尾部 `/` 的写法

## 当前项目状态

当前 `edu_agent` 已经完成：

- 本地前后端一问一回与运行时快照展示
- 真实模型调用验证
- 规则版工具调用链路与 FFmpeg 媒体工具接入
- 短期会话记忆写入与读取
- 历史消息拼接进模型 prompt 的最小多轮上下文能力
- 顺序 / 并行工作流与异步任务 API
- 终端 CLI 与 pytest 测试脚本
- SQLite 持久化 transcript / session 存储
- Docker 化后端部署验证
- Nginx 静态前端 + 反向代理后端验证

## 下一步建议

- 扩展异步任务的流式日志与前端任务面板
- 优化 Memory 读取策略，例如最近 N 轮裁剪与后续摘要机制
- 从规则版 ToolRouter 逐步演进到更灵活的工具决策机制
- 完善协作消息、权限与多 Agent 编排能力

## 上线检查清单

每次发布前，建议至少检查以下内容：

### 后端检查

1. `backend/requirements.txt` 是否包含当前实际使用的依赖
2. `backend/.env` 中的模型配置是否正确
3. 后端本地是否能通过：

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

4. 本地健康检查是否正常：

```bash
curl http://127.0.0.1:8000/health
```

5. 本地聊天接口是否正常：

```bash
curl -X POST http://127.0.0.1:8000/agent_api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"你好"}'
```

### Docker 检查

1. 如果服务器是 `amd64`，镜像是否按 `linux/amd64` 构建
2. 构建后是否重新导出、重新上传、重新加载镜像
3. 容器启动后日志是否正常：

```bash
docker logs edu-agent-backend
```

4. 容器健康检查是否正常：

```bash
curl http://127.0.0.1:18000/health
```

### Nginx 检查

1. `location /agent_api/` 是否正确代理到后端容器
2. `proxy_pass` 是否没有错误地写成带尾部 `/` 的形式
3. 前端静态资源目录是否与 `root` 配置一致
4. 配置修改后是否执行：

```bash
nginx -t
systemctl reload nginx
```

### 前端检查

1. `vite.config.ts` 中的 `base` 是否与部署子路径一致
2. `chatApi.ts` 是否使用相对路径 `/agent_api/chat`
3. 本地开发时 Vite 代理是否正常
4. 重新 build 后是否把最新 `dist/` 上传到服务器
5. 页面打开后浏览器控制台是否无明显报错

### 联调检查

1. 页面是否可以正常打开
2. 首屏静态资源是否没有 404
3. 输入消息后是否能成功返回回复
4. Network 面板中 `/agent_api/chat` 是否返回 200
5. 错误时前端是否能正常显示提示，而不是白屏
