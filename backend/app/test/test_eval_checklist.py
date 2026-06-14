from app.eval.checklist import EvalChecklist
from app.eval.runner import evaluate_runtime_session
from app.runtime.runtime_session import RuntimeSession


def test_eval_must_call_tool_pass():
    session = RuntimeSession(session_id="s1", user_input="现在几点了？")
    session.add_tool_call("time_tool", True, "2026-01-01 12:00:00", None)
    session.planner_result = {"action": "tool", "tool_name": "time_tool"}
    session.final_output = "2026-01-01 12:00:00"

    result = evaluate_runtime_session(
        session,
        EvalChecklist(
            must_call_tool="time_tool",
            planner_action="tool",
            no_errors=True,
            require_final_output=True,
        ),
        run_success=True,
    )
    assert result.passed is True
    assert all(c.passed for c in result.checks)


def test_eval_must_call_tool_fail():
    session = RuntimeSession(session_id="s1", user_input="你好")
    session.planner_result = {"action": "model"}
    session.final_output = "mock"

    result = evaluate_runtime_session(
        session,
        EvalChecklist(must_call_tool="time_tool", planner_action="tool"),
    )
    assert result.passed is False
    failed_rules = {c.rule for c in result.checks if not c.passed}
    assert "must_call_tool" in failed_rules
    assert "planner_action" in failed_rules


def test_eval_from_snapshot_dict():
    snapshot = {
        "tool_calls": [{"tool_name": "time_tool", "success": True}],
        "planner_result": {"action": "tool"},
        "workflow_trace": [{"step_name": "planner"}],
        "errors": [],
        "final_output": "ok",
        "deliverables": [],
    }
    result = evaluate_runtime_session(
        snapshot,
        EvalChecklist(
            must_call_tool="time_tool",
            min_workflow_steps=1,
            no_errors=True,
        ),
    )
    assert result.passed is True
