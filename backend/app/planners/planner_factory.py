from __future__ import annotations

from app.config.settings import Settings
from app.models.base_model import BaseModel
from app.planners.base_planner import BasePlanner
from app.planners.hybrid_planner import HybridPlanner
from app.planners.model_planner import ModelPlanner
from app.planners.rule_planner import RulePlanner
from app.tools.tool_registry import ToolRegistry
from app.tools.tool_router import ToolRouter


def create_planner(
    settings: Settings,
    *,
    model: BaseModel,
    tool_registry: ToolRegistry,
    tool_router: ToolRouter,
) -> BasePlanner:
    rule_planner = RulePlanner(tool_router=tool_router)
    mode = (settings.planner_mode or "hybrid").strip().lower()

    if mode == "rule":
        return rule_planner

    model_planner = ModelPlanner(model=model, tool_registry=tool_registry)
    if mode == "model":
        return model_planner

    return HybridPlanner(rule_planner=rule_planner, model_planner=model_planner)
