# Agent 实验手册

`edu_agent` 内置一组 **规则化 Eval 实验**：跑一遍 Agent，再按 checklist 自动验收运行轨迹，**不需要标注数据或训练模型**。

## 快速开始

在 `backend` 目录下：

```bash
# 列出实验
python -m app.cli experiment list

# 运行 exp_001（问时间 → 必须调 time_tool）
python -m app.cli experiment run exp_001_time_tool

# JSON 输出（含 eval 明细与 runtime_session）
python -m app.cli experiment run exp_001_time_tool --json
```

也可用 pytest：

```bash
pytest app/test/test_eval_checklist.py app/test/test_experiment_exp_001.py -q
```

## 实验目录

| ID | 说明 | 验收要点 |
|----|------|----------|
| `exp_001_time_tool` | 用户问「现在几点了？」 | 必须调用 `time_tool`，planner 走 tool 分支 |
| `exp_002_time_reply_workflow` | 「现在几点了，回复我一句」 | 走 workflow + time_tool；含 control 对照与自动 Diff |
| `exp_003_ffmpeg_deliverable` | ffmpeg 演示短视频 | 调用 `ffmpeg_artifact_tool` 且登记 deliverable（需本机 ffmpeg） |

配置文件位于 `backend/app/experiments/`，清单见 `manifest.yaml`。

### 对照组与批量运行

```bash
python -m app.cli experiment run exp_002_time_reply_workflow
python -m app.cli experiment run-all --skip-ffmpeg
python -m app.cli experiment run exp_001_time_tool --no-control
```

## Checklist 规则

| 规则 | 含义 |
|------|------|
| `must_call_tool` | 至少有一次成功的指定工具调用 |
| `must_not_call_tool` | 不得成功调用指定工具 |
| `planner_action` | `tool` / `model` / `workflow` |
| `min_workflow_steps` | `workflow_trace` 最少步数 |
| `min_deliverables` | `deliverables` 最少条数 |
| `no_errors` | `errors` 为空 |
| `require_final_output` | 有非空 `final_output` |

## 新增实验

1. 在 `backend/app/experiments/` 新增 `exp_xxx.yaml`
2. 将 id 登记到 `manifest.yaml`
3. 补充 `app/test/test_experiment_exp_xxx.py`（推荐）

示例：

```yaml
id: exp_001_time_tool
title: 问时间必须调用 time_tool
message: 现在几点了？
session_id: exp-001-time-tool
checklist:
  must_call_tool: time_tool
  planner_action: tool
  no_errors: true
```

## 与产品定位的关系

实验 Eval 对应 [`agent-framework-design.md`](agent-framework-design.md) §2 的 **规则化 Eval 实验台**，用于验证「Agent 是否按预期跑」，而非语义对答案。

前端 **RuntimeInspector** 在 transcript ≥ 2 轮时提供 Run Diff 面板，可选取两轮对比。

## Run Diff

对比同一会话中两次 transcript 的 runtime 快照（planner、tool_calls、workflow_trace 等）。

**HTTP API**

```text
GET /agent_api/sessions/{session_id}/transcript/diff?base=0&compare=1
```

**CLI**（需后端已启动）

```bash
python -m app.cli diff <session_id> --base 0 --compare 1
python -m app.cli diff <session_id> --json
```

**本地单元测试**

```bash
pytest app/test/test_runtime_diff.py app/test/test_transcript_diff.py -q
```
