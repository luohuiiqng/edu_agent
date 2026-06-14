from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _snapshot_dict(session: dict[str, Any] | Any) -> dict[str, Any]:
    if hasattr(session, "to_dict"):
        return session.to_dict()
    if hasattr(session, "model_dump"):
        return session.model_dump()
    return dict(session)


def _tool_call_summary(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "tool_name": c.get("tool_name"),
            "success": c.get("success"),
            "output": c.get("output"),
        }
        for c in calls
    ]


def _workflow_summary(trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "step_name": row.get("step_name"),
            "action": row.get("action"),
            "success": row.get("success"),
        }
        for row in trace
    ]


def _planner_summary(planner: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(planner, dict):
        return None
    return {
        "action": planner.get("action"),
        "tool_name": planner.get("tool_name"),
        "reason": planner.get("reason"),
    }


@dataclass
class DiffItem:
    field: str
    base: Any
    compare: Any
    changed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "base": self.base,
            "compare": self.compare,
            "changed": self.changed,
        }


@dataclass
class RuntimeDiffResult:
    base_label: str
    compare_label: str
    changed: bool
    items: list[DiffItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_label": self.base_label,
            "compare_label": self.compare_label,
            "changed": self.changed,
            "items": [item.to_dict() for item in self.items],
        }


def _add_item(items: list[DiffItem], field: str, base: Any, compare: Any) -> None:
    changed = base != compare
    items.append(DiffItem(field=field, base=base, compare=compare, changed=changed))


def diff_runtime_snapshots(
    base: dict[str, Any] | Any,
    compare: dict[str, Any] | Any,
    *,
    base_label: str = "base",
    compare_label: str = "compare",
) -> RuntimeDiffResult:
    """对比两次运行的 runtime 快照（planner / tools / workflow / 输出）。"""
    base_dict = _snapshot_dict(base)
    compare_dict = _snapshot_dict(compare)
    items: list[DiffItem] = []

    _add_item(items, "user_input", base_dict.get("user_input"), compare_dict.get("user_input"))
    _add_item(
        items,
        "planner_result",
        _planner_summary(base_dict.get("planner_result")),
        _planner_summary(compare_dict.get("planner_result")),
    )
    _add_item(
        items,
        "tool_calls",
        _tool_call_summary(base_dict.get("tool_calls") or []),
        _tool_call_summary(compare_dict.get("tool_calls") or []),
    )
    _add_item(
        items,
        "model_call_count",
        len(base_dict.get("model_calls") or []),
        len(compare_dict.get("model_calls") or []),
    )
    _add_item(
        items,
        "workflow_trace",
        _workflow_summary(base_dict.get("workflow_trace") or []),
        _workflow_summary(compare_dict.get("workflow_trace") or []),
    )
    _add_item(
        items,
        "deliverable_count",
        len(base_dict.get("deliverables") or []),
        len(compare_dict.get("deliverables") or []),
    )
    _add_item(items, "errors", base_dict.get("errors") or [], compare_dict.get("errors") or [])
    _add_item(items, "final_output", base_dict.get("final_output"), compare_dict.get("final_output"))

    changed = any(item.changed for item in items)
    return RuntimeDiffResult(
        base_label=base_label,
        compare_label=compare_label,
        changed=changed,
        items=items,
    )
