"""使用大模型输出结构化 JSON 进行规划。"""

from __future__ import annotations

from typing import Any

from app.models.base_model import BaseModel
from app.planners.base_planner import BasePlanner
from app.planners.plan_catalog import (
    build_model_plan,
    list_tool_descriptions,
    list_workflow_descriptions,
    materialize_model_decision,
)
from app.planners.plan_context import PlanContext
from app.planners.plan_parser import parse_plan_json
from app.schemas.model_request import ModelRequest
from app.tools.tool_registry import ToolRegistry

MODEL_PLANNER_SYSTEM = """你是 edu_agent 的规划器（Planner），只负责为当前用户输入选择执行策略，不要直接回答用户问题。

你必须只输出一个 JSON 对象，不要输出 Markdown 或其它说明。JSON 格式如下：
{
  "action": "tool" | "workflow" | "model",
  "tool_name": "当 action 为 tool 时必填",
  "workflow_name": "当 action 为 workflow 时必填",
  "reason": "简短中文理由"
}

选择原则：
1. 用户仅询问当前时间/几点 → action=tool, tool_name=time_tool
2. 用户既要时间又要自然语言回复 → action=workflow, workflow_name=time_reply_workflow
3. 用户提到基建/业务/数据三线并行 → action=workflow, workflow_name=parallel_pillar_workflow
4. 用户提到多模块/前后端/质量并行 → action=workflow, workflow_name=multi_module_parallel_workflow
5. 用户提到研究/课题/调研/综述 → action=workflow, workflow_name=research_team_workflow
6. 用户要 ffmpeg/视频样例且已有并行或研究诉求 → 选择带 ffmpeg 的 workflow 变体
7. 普通问候或闲聊 → action=model
"""


class ModelPlanner(BasePlanner):
    def __init__(
        self,
        model: BaseModel,
        tool_registry: ToolRegistry | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._model = model
        self._tool_registry = tool_registry

    def _capability_summary(self) -> str:
        tool_lines = [
            f"- {item['tool_name']}: {item['description']}"
            for item in list_tool_descriptions(self._tool_registry)
        ]
        workflow_lines = [
            f"- {item['workflow_name']}: {item['description']}"
            for item in list_workflow_descriptions()
        ]
        return (
            "可用工具:\n"
            + ("\n".join(tool_lines) if tool_lines else "- （无）")
            + "\n\n可用工作流:\n"
            + ("\n".join(workflow_lines) if workflow_lines else "- （无）")
        )

    def _build_planning_messages(
        self,
        input_data: Any,
        context: PlanContext | None,
    ) -> list[dict[str, str]]:
        msg = str(input_data.message).strip()
        sections = [self._capability_summary()]
        if context and context.has_prior_turns:
            prior = "\n".join(context.recent_user_messages)
            sections.append(f"近期用户消息:\n{prior}")
        sections.append(f"当前用户输入:\n{msg}")
        sections.append("请输出规划 JSON。")
        return [{"role": "user", "content": "\n\n".join(sections)}]

    def plan(
        self,
        input_data: Any,
        context: PlanContext | None = None,
    ) -> dict[str, Any]:
        if not self.validate_input(input_data):
            plan = build_model_plan(reason="输入数据不合法，无法规划")
            plan["planner_source"] = "model"
            return plan

        message = str(input_data.message).strip()
        response = self._model.generate(
            ModelRequest(
                messages=self._build_planning_messages(input_data, context),
                system=MODEL_PLANNER_SYSTEM,
                response_format={"type": "json_object"},
                metadata={
                    "mode": "planning",
                    "current_message": message,
                },
            )
        )

        planning_trace = {
            "raw_output": response.content,
            "success": response.success,
            "error": response.error_message,
        }

        if not response.success:
            plan = build_model_plan(
                reason=f"model planner 调用失败: {response.error_message}"
            )
            plan["planner_source"] = "model"
            plan["planning_trace"] = planning_trace
            return plan

        decision = parse_plan_json(response.content)
        if decision is None:
            plan = build_model_plan(reason="model planner 未能解析 JSON，回退 model")
            plan["planner_source"] = "model"
            plan["planning_trace"] = planning_trace
            return plan

        materialized = materialize_model_decision(
            decision,
            message,
            self._tool_registry,
        )
        if materialized is None:
            plan = build_model_plan(reason="model planner 决策无效，回退 model")
            plan["planner_source"] = "model"
            plan["planning_trace"] = {**planning_trace, "parsed": decision}
            return plan

        materialized["planner_source"] = "model"
        materialized["planning_trace"] = {**planning_trace, "parsed": decision}
        return materialized
