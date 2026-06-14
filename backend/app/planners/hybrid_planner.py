"""规则优先、模型补规划的混合 Planner。"""

from __future__ import annotations

from typing import Any

from app.planners.base_planner import BasePlanner
from app.planners.plan_context import PlanContext


class HybridPlanner(BasePlanner):
    """先走 RulePlanner；仅当规则回退到 ``model`` 时，再交给 ModelPlanner。"""

    def __init__(
        self,
        rule_planner: BasePlanner,
        model_planner: BasePlanner,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._rule_planner = rule_planner
        self._model_planner = model_planner

    def plan(
        self,
        input_data: Any,
        context: PlanContext | None = None,
    ) -> dict[str, Any]:
        rule_plan = self._rule_planner.plan(input_data, context=context)
        rule_plan = dict(rule_plan)
        rule_plan["planner_source"] = "rule"

        if rule_plan.get("action") != "model":
            return rule_plan

        model_plan = self._model_planner.plan(input_data, context=context)
        model_plan = dict(model_plan)
        model_plan["rule_fallback_reason"] = rule_plan.get("reason")
        return model_plan

    def get_planner_info(self) -> dict[str, Any]:
        return {
            "planner_class": self.__class__.__name__,
            "config": self._config,
            "rule_planner": self._rule_planner.get_planner_info(),
            "model_planner": self._model_planner.get_planner_info(),
        }
