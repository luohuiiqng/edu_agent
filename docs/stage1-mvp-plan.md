# 阶段1详细规划文档（文本聊天 MVP）

## 1. 文档信息
- 项目名称：edu_agent
- 阶段名称：阶段1（文本输入 + 文本输出）
- 前端技术：Vue3 + Vite + TypeScript
- 后端技术：Python + FastAPI + LangChain（占位接入）
- 文档日期：2026-03-25

## 2. 阶段目标
1. 完成前后端通信闭环：前端发送文本，后端返回文本。
2. 完成可演示的基础聊天界面：消息展示、输入、发送、错误提示。
3. 建立可扩展的后端结构，为阶段2接入真实大模型与流式返回做准备。

## 3. 范围定义

### 3.1 本阶段包含
1. 文本消息发送与接收。
2. 用户/助手消息展示。
3. 发送中状态与基础交互反馈。
4. 前后端异常处理（参数错误、网络错误、服务错误）。
5. 界面美观与用户友好设计（清晰层级、舒适配色、易读排版、直观反馈）。
6. 基础接口文档与启动说明。

### 3.2 本阶段不包含
1. 语音输入输出。
2. 图片/文件上传。
3. 用户登录、权限、多租户。
4. 多端同步与历史消息持久化。
5. 大模型流式输出（SSE/WebSocket）。

## 4. 总体架构
1. 前端（Vue3）：负责用户交互、消息渲染、调用后端 API。
2. 后端（FastAPI）：负责请求校验、对话处理、返回结构化响应。
3. LangChain：阶段1仅保留服务层接入点，先使用回显或规则回复逻辑。
4. 通信协议：HTTP + JSON。

## 5. 接口契约（冻结）

### 5.1 健康检查
- 方法：`GET /health`
- 响应：

```json
{
  "status": "ok"
}
```

### 5.2 聊天接口
- 方法：`POST /api/chat`
- 请求：

```json
{
  "message": "你好",
  "session_id": "optional-uuid"
}
```

- 成功响应：

```json
{
  "reply": "你好，我收到了：你好",
  "session_id": "same-or-generated-uuid",
  "timestamp": "2026-03-25T10:00:00Z"
}
```

- 错误响应：

```json
{
  "error": {
    "code": "BAD_REQUEST",
    "message": "message不能为空"
  }
}
```

### 5.3 约束规则
1. `message` 必填，去除首尾空格后不能为空。
2. `message` 最大长度建议 2000 字符。
3. `session_id` 可选；为空时后端生成并返回。
4. 时间统一 ISO 8601 格式（UTC）。

## 6. 项目结构建议

```text
edu_agent/
  frontend/
    src/
      components/
        ChatWindow.vue
        MessageList.vue
        MessageInput.vue
      services/
        chatApi.ts
      types/
        chat.ts
      App.vue
      main.ts
  backend/
    app/
      routes/
        chat.py
      services/
        chat_service.py
      main.py
      schemas.py
    requirements.txt
  docs/
    stage1-mvp-plan.md
```

## 7. 前端详细任务
1. 初始化 Vue3 + Vite + TypeScript 工程。
2. 实现页面布局：消息列表区域、输入框区域、发送按钮。
3. 增加 UI/UX 设计要求：整体视觉简洁美观、重点操作突出、文字对比度充足、移动端可用。
4. 定义消息类型（role/content/timestamp/status）。
5. 封装 API 调用模块 `chatApi.ts`。
6. 完成发送流程（插入用户消息、发送中、回包渲染、失败提示）。
7. 输入校验：空文本拦截、超长拦截（>2000）。
8. 可用性细节：禁用重复提交、自动滚动、错误提示文案。

## 8. 后端详细任务
1. 初始化 FastAPI 项目并配置 CORS。
2. 定义 Pydantic 模型：`ChatRequest`、`ChatResponse`、`ErrorResponse`。
3. 实现 `GET /health`。
4. 实现 `POST /api/chat`（参数校验、session_id、timestamp）。
5. 服务层 `chat_service.py` 先用回显策略，预留 LangChain 替换入口。
6. 统一异常处理和错误码。

## 9. 里程碑与排期（3天）
1. Day 1：后端骨架、接口联调工具验证。
2. Day 2：前端聊天 UI + API 接入联调。
3. Day 3：异常场景测试、README、验收演示。

## 10. 验收标准（DoD）
1. 连续发送 5 条消息均可收到回复。
2. 消息顺序正确且角色展示正确。
3. 前端和后端均有空消息兜底。
4. 后端异常时前端有可理解提示。
5. 界面视觉统一、信息层级清晰，首次使用用户可在 30 秒内完成一次消息发送。
6. 新成员可在 10 分钟内按 README 启动。

## 11. 测试用例（最小集）
1. 正常发送与回复。
2. 连续发送顺序验证。
3. 空输入拦截。
4. 超长输入拦截。
5. 后端 400 标准错误。
6. 后端 500 提示。
7. 断网/服务不可用提示。

## 12. 风险与应对
1. 跨域失败：提前配置 CORS 白名单。
2. 接口字段漂移：冻结契约并统一维护 schema。
3. 状态错乱：发送逻辑单入口与按钮节流。
4. 后续改造成本：路由层与服务层解耦。

## 13. 阶段交付物
1. 可运行的前后端代码。
2. 接口契约文档。
3. README（安装、运行、联调）。
4. 阶段复盘与阶段2计划。

## 14. 阶段2预留点
1. 回显服务替换为 LangChain + LLM。
2. 增加流式输出（SSE/WebSocket）。
3. 引入会话记忆和持久化。
4. 增加安全策略（输入过滤、限流）。


