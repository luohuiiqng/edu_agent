from app.runtime.runtime_session import RuntimeSession
from app.runtime.transcript_entry import TranscriptEntry
from app.schemas.runtime_snapshot import RuntimeSessionSnapshot
from app.schemas.transcript_response import TranscriptEntryResponse


runtime_session = RuntimeSession(session_id="session-1", user_input="你好")
runtime_session.planner_result = {"action": "model"}
runtime_session.workflow_result = {"status": "done"}
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
    step_name="reply",
    action="model",
    success=True,
    output="你好呀",
    input_summary="prompt=你好",
    output_summary="你好呀",
    error=None,
)
runtime_session.final_output = "你好呀"
runtime_session.add_error("mock warning")

runtime_snapshot = RuntimeSessionSnapshot.from_runtime_session(runtime_session)

assert runtime_snapshot.session_id == "session-1"
assert runtime_snapshot.user_input == "你好"
assert runtime_snapshot.planner_result == {"action": "model"}
assert runtime_snapshot.workflow_result == {"status": "done"}
assert len(runtime_snapshot.tool_calls) == 1
assert len(runtime_snapshot.model_calls) == 1
assert len(runtime_snapshot.workflow_trace) == 1
assert runtime_snapshot.collaboration_trace == []
assert runtime_snapshot.deliverables == []
assert runtime_snapshot.final_output == "你好呀"
assert runtime_snapshot.errors == ["mock warning"]

entry = TranscriptEntry(
    type="agent",
    user_input="你好",
    final_output="你好呀",
    success=True,
    runtime_session=runtime_session,
    timestamp="2026-04-09T10:10:00",
)

entry_response = TranscriptEntryResponse.from_transcript_entry(entry)

assert entry_response.type == "agent"
assert entry_response.user_input == "你好"
assert entry_response.final_output == "你好呀"
assert entry_response.success is True
assert entry_response.timestamp == "2026-04-09T10:10:00"
assert entry_response.runtime_session.session_id == "session-1"
assert entry_response.runtime_session.final_output == "你好呀"

print("transcript response tests passed")
