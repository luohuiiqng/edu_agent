from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

PlannerAction = Literal["tool", "model", "workflow"]


@dataclass
class EvalChecklist:
    """对单次 Agent 运行的规则化验收条件。"""

    must_call_tool: str | None = None
    must_not_call_tool: str | None = None
    planner_action: PlannerAction | None = None
    min_workflow_steps: int | None = None
    min_deliverables: int | None = None
    no_errors: bool = False
    require_final_output: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvalChecklist":
        checklist = data.get("checklist")
        if isinstance(checklist, dict):
            payload = checklist
        else:
            payload = data
        return cls(
            must_call_tool=payload.get("must_call_tool"),
            must_not_call_tool=payload.get("must_not_call_tool"),
            planner_action=payload.get("planner_action"),
            min_workflow_steps=payload.get("min_workflow_steps"),
            min_deliverables=payload.get("min_deliverables"),
            no_errors=bool(payload.get("no_errors", False)),
            require_final_output=bool(payload.get("require_final_output", False)),
        )


@dataclass
class EvalCheckResult:
    rule: str
    passed: bool
    message: str


@dataclass
class EvalResult:
    passed: bool
    checks: list[EvalCheckResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "checks": [
                {"rule": c.rule, "passed": c.passed, "message": c.message}
                for c in self.checks
            ],
        }
