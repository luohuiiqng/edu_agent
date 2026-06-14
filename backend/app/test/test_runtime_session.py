from app.runtime.runtime_session import RuntimeSession


# 设计原则：
# 1. 只测试 RuntimeSession 自己，不把 ChatAgent/Workflow 一起卷进来
# 2. 重点验证默认初始化和可变字段隔离，避免 dataclass 常见坑
# 3. 每个断言都尽量对应一个明确职责，方便失败时快速定位


# 默认初始化场景
runtime_session = RuntimeSession(session_id="session-1", user_input="你好")

assert runtime_session.session_id == "session-1"
assert runtime_session.user_input == "你好"
assert runtime_session.planner_result is None
assert runtime_session.workflow_result is None
assert runtime_session.tool_calls == []
assert runtime_session.model_calls == []
assert runtime_session.final_output is None
assert runtime_session.errors == []
assert runtime_session.workflow_trace == []
assert runtime_session.collaboration_trace == []
assert runtime_session.deliverables == []


# 可变字段隔离场景
runtime_session_a = RuntimeSession(session_id="session-a")
runtime_session_b = RuntimeSession(session_id="session-b")

runtime_session_a.tool_calls.append(
    {
        "tool_name": "time_tool",
        "success": True,
        "output": "2026-04-04 10:00:00",
        "error": None,
    }
)
runtime_session_a.model_calls.append(
    {
        "prompt": "你好",
        "success": True,
        "output": "mock response",
        "error": None,
    }
)
runtime_session_a.errors.append("mock error")

assert len(runtime_session_a.tool_calls) == 1
assert len(runtime_session_a.model_calls) == 1
assert runtime_session_a.errors == ["mock error"]

assert runtime_session_b.tool_calls == []
assert runtime_session_b.model_calls == []
assert runtime_session_b.errors == []

rs_collab = RuntimeSession(session_id="c1", user_input="课题测试")
rs_collab.add_collaboration_event(
    agent_role="调研员",
    phase="gather",
    summary="完成要点摘录",
    step_name="s1",
)
assert len(rs_collab.collaboration_trace) == 1
assert rs_collab.collaboration_trace[0]["agent_role"] == "调研员"

print("runtime session tests passed")
