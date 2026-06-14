from app.runtime.runtime_session import RuntimeSession
from app.runtime.transcript_entry import TranscriptEntry


runtime_session = RuntimeSession(session_id="session-1", user_input="你好")
runtime_session.planner_result = {"action": "model"}
runtime_session.add_tool_call(
    tool_name="time_tool",
    success=True,
    output="2026-04-09 10:00:00",
    error=None,
)
runtime_session.add_model_call(
    prompt="你好",
    success=True,
    output="你好呀",
    error=None,
)
runtime_session.add_workflow_step_trace(
    step_name="generate_reply",
    action="model",
    success=True,
    output="你好呀",
    input_summary="prompt=你好",
    output_summary="你好呀",
    error=None,
)
runtime_session.final_output = "你好呀"
runtime_session.add_error("mock warning")

entry = TranscriptEntry(
    type="agent",
    user_input="你好",
    final_output="你好呀",
    success=True,
    runtime_session=runtime_session,
    timestamp="2026-04-09T10:10:00",
)

entry_dict = entry.to_dict()

assert entry_dict["type"] == "agent"
assert entry_dict["user_input"] == "你好"
assert entry_dict["final_output"] == "你好呀"
assert entry_dict["success"] is True
assert entry_dict["timestamp"] == "2026-04-09T10:10:00"

runtime_session_dict = entry_dict["runtime_session"]
assert isinstance(runtime_session_dict, dict)
assert runtime_session_dict["session_id"] == "session-1"
assert runtime_session_dict["user_input"] == "你好"
assert runtime_session_dict["planner_result"] == {"action": "model"}
assert len(runtime_session_dict["tool_calls"]) == 1
assert runtime_session_dict["tool_calls"][0]["tool_name"] == "time_tool"
assert len(runtime_session_dict["model_calls"]) == 1
assert runtime_session_dict["model_calls"][0]["prompt"] == "你好"
assert len(runtime_session_dict["workflow_trace"]) == 1
assert runtime_session_dict["workflow_trace"][0]["step_name"] == "generate_reply"
assert runtime_session_dict.get("collaboration_trace") == []
assert runtime_session_dict.get("deliverables") == []
assert runtime_session_dict["final_output"] == "你好呀"
assert runtime_session_dict["errors"] == ["mock warning"]

print("transcript entry tests passed")
