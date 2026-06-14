from __future__ import annotations

from typing import Any

from app.eval.checklist import EvalChecklist, EvalCheckResult, EvalResult
from app.runtime.runtime_session import RuntimeSession


def _tool_names(session: RuntimeSession | dict[str, Any]) -> list[str]:
    if isinstance(session, RuntimeSession):
        calls = session.tool_calls
    else:
        calls = session.get("tool_calls") or []
    return [str(c.get("tool_name", "")) for c in calls if c.get("success")]


def _planner_action(session: RuntimeSession | dict[str, Any]) -> str | None:
    if isinstance(session, RuntimeSession):
        planner = session.planner_result
    else:
        planner = session.get("planner_result")
    if not isinstance(planner, dict):
        return None
    action = planner.get("action")
    return str(action) if action is not None else None


def _workflow_step_count(session: RuntimeSession | dict[str, Any]) -> int:
    if isinstance(session, RuntimeSession):
        trace = session.workflow_trace
    else:
        trace = session.get("workflow_trace") or []
    return len(trace)


def _deliverable_count(session: RuntimeSession | dict[str, Any]) -> int:
    if isinstance(session, RuntimeSession):
        items = session.deliverables
    else:
        items = session.get("deliverables") or []
    return len(items)


def _errors(session: RuntimeSession | dict[str, Any]) -> list[str]:
    if isinstance(session, RuntimeSession):
        return list(session.errors)
    return list(session.get("errors") or [])


def _final_output(session: RuntimeSession | dict[str, Any]) -> str | None:
    if isinstance(session, RuntimeSession):
        return session.final_output
    value = session.get("final_output")
    return str(value) if value is not None else None


def evaluate_runtime_session(
    session: RuntimeSession | dict[str, Any],
    checklist: EvalChecklist,
    *,
    run_success: bool | None = None,
) -> EvalResult:
    """对 RuntimeSession（或快照 dict）执行 checklist 验收。"""
    checks: list[EvalCheckResult] = []

    if checklist.must_call_tool:
        names = _tool_names(session)
        passed = checklist.must_call_tool in names
        checks.append(
            EvalCheckResult(
                rule="must_call_tool",
                passed=passed,
                message=(
                    f"期望调用工具 `{checklist.must_call_tool}`，"
                    f"实际成功调用: {names or '（无）'}"
                ),
            )
        )

    if checklist.must_not_call_tool:
        names = _tool_names(session)
        passed = checklist.must_not_call_tool not in names
        checks.append(
            EvalCheckResult(
                rule="must_not_call_tool",
                passed=passed,
                message=(
                    f"不应调用工具 `{checklist.must_not_call_tool}`，"
                    f"实际成功调用: {names or '（无）'}"
                ),
            )
        )

    if checklist.planner_action:
        action = _planner_action(session)
        passed = action == checklist.planner_action
        checks.append(
            EvalCheckResult(
                rule="planner_action",
                passed=passed,
                message=(
                    f"期望 planner action `{checklist.planner_action}`，"
                    f"实际: `{action}`"
                ),
            )
        )

    if checklist.min_workflow_steps is not None:
        count = _workflow_step_count(session)
        passed = count >= checklist.min_workflow_steps
        checks.append(
            EvalCheckResult(
                rule="min_workflow_steps",
                passed=passed,
                message=(
                    f"期望 workflow 步骤数 >= {checklist.min_workflow_steps}，"
                    f"实际: {count}"
                ),
            )
        )

    if checklist.min_deliverables is not None:
        count = _deliverable_count(session)
        passed = count >= checklist.min_deliverables
        checks.append(
            EvalCheckResult(
                rule="min_deliverables",
                passed=passed,
                message=(
                    f"期望 deliverable 数量 >= {checklist.min_deliverables}，"
                    f"实际: {count}"
                ),
            )
        )

    if checklist.no_errors:
        errors = _errors(session)
        passed = len(errors) == 0
        checks.append(
            EvalCheckResult(
                rule="no_errors",
                passed=passed,
                message=f"期望 errors 为空，实际: {errors or '（无）'}",
            )
        )

    if checklist.require_final_output:
        output = _final_output(session)
        passed = bool(output and str(output).strip())
        checks.append(
            EvalCheckResult(
                rule="require_final_output",
                passed=passed,
                message=f"期望有 final_output，实际: {output!r}",
            )
        )

    if run_success is not None:
        checks.append(
            EvalCheckResult(
                rule="run_success",
                passed=run_success,
                message=f"期望 Agent 运行 success={run_success}",
            )
        )

    return EvalResult(passed=all(c.passed for c in checks), checks=checks)
