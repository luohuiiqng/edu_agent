from app.eval.diff import diff_runtime_snapshots
from app.runtime.runtime_session import RuntimeSession


def test_diff_detects_tool_vs_model():
    base = RuntimeSession(session_id="s1", user_input="现在几点了？")
    base.planner_result = {"action": "tool", "tool_name": "time_tool", "reason": "hit"}
    base.add_tool_call("time_tool", True, "12:00", None)
    base.final_output = "12:00"

    compare = RuntimeSession(session_id="s1", user_input="你好")
    compare.planner_result = {"action": "model", "reason": "fallback"}
    compare.add_model_call("你好", True, "mock", None)
    compare.final_output = "mock"

    result = diff_runtime_snapshots(base, compare)
    assert result.changed is True
    changed_fields = {item.field for item in result.items if item.changed}
    assert "planner_result" in changed_fields
    assert "tool_calls" in changed_fields
    assert "final_output" in changed_fields


def test_diff_same_run_unchanged():
    session = RuntimeSession(session_id="s1", user_input="现在几点了？")
    session.planner_result = {"action": "tool", "tool_name": "time_tool"}
    session.add_tool_call("time_tool", True, "12:00", None)
    session.final_output = "12:00"

    result = diff_runtime_snapshots(session, session.to_dict())
    assert result.changed is False
