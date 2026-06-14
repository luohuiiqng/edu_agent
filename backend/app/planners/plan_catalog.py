"""内置 workflow / tool 目录：供 ModelPlanner 解析与实例化计划。"""

from __future__ import annotations

from typing import Any, Callable

from app.planners import rule_step_builders as steps
from app.tools.tool_registry import ToolRegistry

WorkflowBuilder = Callable[[str], list[dict[str, Any]]]

WORKFLOW_CATALOG: dict[str, dict[str, Any]] = {
    "time_reply_workflow": {
        "workflow_kind": "sequential",
        "description": "查询当前时间并由模型生成一句自然回复",
        "build_steps": lambda msg: [
            {
                "step_name": "get_time",
                "action": "tool",
                "tool_name": "time_tool",
                "tool_input": {},
            },
            {
                "step_name": "generate_reply",
                "action": "model",
                "prompt_template": "当前时间是{step_output},请生成一句自然回复给用户",
                "use_step_result": "get_time",
            },
        ],
        "final_step_name": None,
    },
    "parallel_pillar_workflow": {
        "workflow_kind": "parallel_sequential",
        "description": "基建/业务/数据三线并行规划后合并",
        "build_steps": steps.parallel_pillar_steps,
        "final_step_name": "merge_pillar",
    },
    "parallel_pillar_ffmpeg_workflow": {
        "workflow_kind": "parallel_sequential",
        "description": "三线并行规划后合并并导出 ffmpeg 演示视频",
        "build_steps": steps.parallel_pillar_steps_with_ffmpeg,
        "final_step_name": "merge_pillar",
    },
    "multi_module_parallel_workflow": {
        "workflow_kind": "parallel_sequential",
        "description": "后端/前端/质量多模块并行开发后合并",
        "build_steps": steps.parallel_module_steps,
        "final_step_name": "merge_coordination",
    },
    "multi_module_parallel_ffmpeg_workflow": {
        "workflow_kind": "parallel_sequential",
        "description": "多模块并行开发后合并并导出 ffmpeg 演示视频",
        "build_steps": steps.parallel_module_steps_with_ffmpeg,
        "final_step_name": "merge_coordination",
    },
    "research_team_workflow": {
        "workflow_kind": "sequential",
        "description": "研究/课题类多角色顺序协作",
        "build_steps": steps.research_team_steps,
        "final_step_name": None,
    },
    "research_team_ffmpeg_workflow": {
        "workflow_kind": "sequential",
        "description": "研究类协作后追加 ffmpeg 演示导出",
        "build_steps": steps.research_team_ffmpeg_steps,
        "final_step_name": "writeup",
    },
}


def list_workflow_descriptions() -> list[dict[str, str]]:
    return [
        {
            "workflow_name": name,
            "description": str(spec.get("description") or ""),
        }
        for name, spec in WORKFLOW_CATALOG.items()
    ]


def list_tool_descriptions(registry: ToolRegistry | None) -> list[dict[str, str]]:
    if registry is None:
        return []
    descriptions: list[dict[str, str]] = []
    for name in registry.list_tools():
        tool = registry.get_tool(name)
        if tool is None:
            continue
        info = tool.get_tool_info()
        descriptions.append(
            {
                "tool_name": str(info.get("name") or name),
                "description": str(info.get("description") or ""),
            }
        )
    return descriptions


def build_workflow_plan(
    workflow_name: str,
    message: str,
    *,
    reason: str,
) -> dict[str, Any] | None:
    spec = WORKFLOW_CATALOG.get(workflow_name)
    if spec is None:
        return None
    builder = spec.get("build_steps")
    if not callable(builder):
        return None
    plan: dict[str, Any] = {
        "action": "workflow",
        "workflow_kind": spec.get("workflow_kind", "sequential"),
        "reason": reason,
        "tool_name": None,
        "workflow_name": workflow_name,
        "steps": builder(message),
        "context": {},
    }
    final_step = spec.get("final_step_name")
    if final_step:
        plan["final_step_name"] = final_step
    return plan


def build_tool_plan(tool_name: str, *, reason: str) -> dict[str, Any]:
    return {
        "action": "tool",
        "reason": reason,
        "tool_name": tool_name,
        "workflow_name": None,
        "steps": [],
        "context": {},
    }


def build_model_plan(*, reason: str) -> dict[str, Any]:
    return {
        "action": "model",
        "reason": reason,
        "tool_name": None,
        "workflow_name": None,
        "steps": [],
        "context": {},
    }


def materialize_model_decision(
    decision: dict[str, Any],
    message: str,
    registry: ToolRegistry | None,
) -> dict[str, Any] | None:
    action = str(decision.get("action") or "").strip().lower()
    reason = str(decision.get("reason") or "model planner decision").strip()

    if action == "tool":
        tool_name = str(decision.get("tool_name") or "").strip()
        if not tool_name:
            return None
        if registry is not None and registry.get_tool(tool_name) is None:
            return None
        return build_tool_plan(tool_name, reason=reason)

    if action == "workflow":
        workflow_name = str(decision.get("workflow_name") or "").strip()
        if not workflow_name:
            return None
        return build_workflow_plan(workflow_name, message, reason=reason)

    if action == "model":
        return build_model_plan(reason=reason)

    return None
