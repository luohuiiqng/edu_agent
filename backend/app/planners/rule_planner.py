"""基于关键词的规则规划器。

规划顺序由 ``RULE_PLAN_ATTEMPT_ORDER`` 列出；新增场景时优先增加对应的 ``_try_*``，
并在元组中插入合适优先级（越靠前越先匹配）。"""
from __future__ import annotations

from typing import Any, Callable

from app.planners.base_planner import BasePlanner
from app.tools.tool_router import ToolRouter

from app.planners import rule_step_builders as steps


# 文档与运行时自检：与 RulePlanner._plan_attempt_chain 中顺序保持一致
RULE_PLAN_ATTEMPT_ORDER: tuple[str, ...] = (
    "time_reply_workflow",
    "parallel_pillar_ffmpeg",
    "parallel_pillar",
    "parallel_modules_ffmpeg",
    "parallel_modules",
    "research_ffmpeg",
    "research_team",
    "tool_route",
    "fallback_model",
)


class RulePlanner(BasePlanner):
    def __init__(self, tool_router: ToolRouter = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._tool_router = tool_router

    def _should_use_workflow(self, message: Any) -> bool:
        """根据输入内容判断是否需要使用workflow进行规划，默认根据message内容是否包含特定关键词进行判断，可以在子类中重写实现更复杂的逻辑"""
        rule_time_tool_str = ["时间", "几点", "现在几点", "当前时间"]
        has_time_intent = False
        for rule in rule_time_tool_str:
            if rule in str(message):
                has_time_intent = True
                break
        rule_workflow_str = ["回复", "说一句", "生成一句", "告诉我一句"]
        has_workflow_intent = False
        for rule in rule_workflow_str:
            if rule in str(message):
                has_workflow_intent = True
                break
        return has_time_intent and has_workflow_intent

    def _should_use_research_workflow(self, message: Any) -> bool:
        """课题 / 调研类意图：顺序多角色模型步骤（教学演示桩，后续可换真多进程 Agent）。"""
        keywords = (
            "研究",
            "课题",
            "调研",
            "综述",
            "研究报告",
            "协作研究",
            "多智能体",
            "多代理",
        )
        text = str(message)
        return any(k in text for k in keywords)

    def _has_ffmpeg_route_hint(self, message: Any) -> bool:
        text = str(message)
        return any(h in text for h in steps.FFMPEG_ROUTE_HINTS)

    def _should_use_parallel_pillar_workflow(self, message: Any) -> bool:
        """基建 / 业务 / 数据三线并行（与前后端质量并行互为补充）。"""
        text = str(message)
        if any(k in text for k in ("三线并行", "三条线并行", "基建业务数据")):
            return True
        return all(k in text for k in ("基建", "业务", "数据"))

    def _should_use_parallel_pillar_ffmpeg_workflow(self, message: Any) -> bool:
        return self._should_use_parallel_pillar_workflow(
            message
        ) and self._has_ffmpeg_route_hint(message)

    def _should_use_parallel_modules_workflow(self, message: Any) -> bool:
        """多模块并行：后端 / 前端 / 质量等代理同时出稿，再由协调代理合并。"""
        text = str(message)
        if any(
            k in text
            for k in ("多模块并行", "并行模块", "模块分工", "分工协作", "同时开发多模块")
        ):
            return True
        if "模块" in text and any(
            k in text for k in ("并行", "同时", "一起", "分工", "各负责")
        ):
            return True
        return False

    def _should_use_parallel_modules_ffmpeg_workflow(self, message: Any) -> bool:
        """多模块并行合并后，再导出本地 ffmpeg 演示短视频。"""
        return self._should_use_parallel_modules_workflow(
            message
        ) and self._has_ffmpeg_route_hint(message)

    def _should_use_research_ffmpeg_workflow(self, message: Any) -> bool:
        """研究类意图 + 明确要本地 ffmpeg / 视频样例时，在综述后追加演示导出步骤。"""
        if not self._should_use_research_workflow(message):
            return False
        return self._has_ffmpeg_route_hint(message)

    # --- 规则链：返回完整 plan 或 None（未命中则尝试下一规则） ---

    def _try_time_reply_workflow(self, msg: str, raw_message: Any) -> dict[str, Any] | None:
        if not self._should_use_workflow(raw_message):
            return None
        return {
            "action": "workflow",
            "workflow_kind": "sequential",
            "reason": "同时命中时间意图和自然回复意图，选择workflow",
            "tool_name": None,
            "workflow_name": "time_reply_workflow",
            "steps": [
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
            "context": {},
        }

    def _try_parallel_pillar_ffmpeg(self, msg: str, raw_message: Any) -> dict[str, Any] | None:
        if not self._should_use_parallel_pillar_ffmpeg_workflow(raw_message):
            return None
        return {
            "action": "workflow",
            "workflow_kind": "parallel_sequential",
            "reason": "三线并行（基建/业务/数据）合并后追加 ffmpeg 演示视频",
            "tool_name": None,
            "workflow_name": "parallel_pillar_ffmpeg_workflow",
            "steps": steps.parallel_pillar_steps_with_ffmpeg(msg),
            "context": {},
            "final_step_name": "merge_pillar",
        }

    def _try_parallel_pillar(self, msg: str, raw_message: Any) -> dict[str, Any] | None:
        if not self._should_use_parallel_pillar_workflow(raw_message):
            return None
        return {
            "action": "workflow",
            "workflow_kind": "parallel_sequential",
            "reason": "命中三线并行意图：基建/业务/数据并行产出后合并",
            "tool_name": None,
            "workflow_name": "parallel_pillar_workflow",
            "steps": steps.parallel_pillar_steps(msg),
            "context": {},
            "final_step_name": "merge_pillar",
        }

    def _try_parallel_modules_ffmpeg(self, msg: str, raw_message: Any) -> dict[str, Any] | None:
        if not self._should_use_parallel_modules_ffmpeg_workflow(raw_message):
            return None
        return {
            "action": "workflow",
            "workflow_kind": "parallel_sequential",
            "reason": "多模块并行合并后追加本地 ffmpeg 演示视频导出",
            "tool_name": None,
            "workflow_name": "multi_module_parallel_ffmpeg_workflow",
            "steps": steps.parallel_module_steps_with_ffmpeg(msg),
            "context": {},
            "final_step_name": "merge_coordination",
        }

    def _try_parallel_modules(self, msg: str, raw_message: Any) -> dict[str, Any] | None:
        if not self._should_use_parallel_modules_workflow(raw_message):
            return None
        return {
            "action": "workflow",
            "workflow_kind": "parallel_sequential",
            "reason": "命中多模块并行意图：后端/前端/测试质量并行产出后由协调代理合并",
            "tool_name": None,
            "workflow_name": "multi_module_parallel_workflow",
            "steps": steps.parallel_module_steps(msg),
            "context": {},
            "final_step_name": "merge_coordination",
        }

    def _try_research_ffmpeg(self, msg: str, raw_message: Any) -> dict[str, Any] | None:
        if not self._should_use_research_ffmpeg_workflow(raw_message):
            return None
        return {
            "action": "workflow",
            "workflow_kind": "sequential",
            "reason": "研究类意图且包含 ffmpeg/视频样例诉求，综述后追加本地 ffmpeg 导出",
            "tool_name": None,
            "workflow_name": "research_team_ffmpeg_workflow",
            "steps": steps.research_team_ffmpeg_steps(msg),
            "context": {},
            "final_step_name": "writeup",
        }

    def _try_research_team(self, msg: str, raw_message: Any) -> dict[str, Any] | None:
        if not self._should_use_research_workflow(raw_message):
            return None
        return {
            "action": "workflow",
            "workflow_kind": "sequential",
            "reason": "命中研究/课题类意图，触发多角色顺序工作流（演示桩）",
            "tool_name": None,
            "workflow_name": "research_team_workflow",
            "steps": steps.research_team_steps(msg),
            "context": {},
        }

    def _try_tool_route(self, msg: str, raw_message: Any) -> dict[str, Any] | None:
        tool_name = (
            self._tool_router.route(raw_message) if self._tool_router else None
        )
        if tool_name is None:
            return None
        return {
            "action": "tool",
            "reason": "命中工具路由规则",
            "tool_name": tool_name,
            "workflow_name": None,
            "steps": [],
            "context": {},
        }

    def _try_fallback_model(self, msg: str, raw_message: Any) -> dict[str, Any] | None:
        return {
            "action": "model",
            "reason": "未命中workflow或tool规则，回退到模型",
            "tool_name": None,
            "workflow_name": None,
            "steps": [],
            "context": {},
        }

    def _plan_attempt_chain(
        self,
    ) -> tuple[Callable[[str, Any], dict[str, Any] | None], ...]:
        """按优先级排列的规则尝试函数（与 RULE_PLAN_ATTEMPT_ORDER 对齐）。"""
        return (
            self._try_time_reply_workflow,
            self._try_parallel_pillar_ffmpeg,
            self._try_parallel_pillar,
            self._try_parallel_modules_ffmpeg,
            self._try_parallel_modules,
            self._try_research_ffmpeg,
            self._try_research_team,
            self._try_tool_route,
            self._try_fallback_model,
        )

    def plan(self, input_data: Any, context: Any = None) -> dict[str, Any]:
        """根据输入内容生成最小规则计划结果。"""
        if not self.validate_input(input_data):
            return {
                "action": "model",
                "reason": "输入数据不合法，无法规划工具调用",
                "tool_name": None,
                "workflow_name": None,
                "steps": [],
                "context": {},
            }
        msg = str(input_data.message).strip()
        raw = input_data.message

        for attempt in self._plan_attempt_chain():
            plan = attempt(msg, raw)
            if plan is not None:
                return plan

        raise RuntimeError("plan: unreachable — fallback_model must always return a dict")
