from app.planners.rule_planner import RULE_PLAN_ATTEMPT_ORDER, RulePlanner
from app.schemas.agent_input import AgentInput
from app.tools.tool_router import ToolRouter


tool_router = ToolRouter()
tool_router.add_rule(
    tool_name="time_tool",
    keywords=["时间", "现在时间", "当前时间", "几点", "现在几点"],
)

planner = RulePlanner(tool_router=tool_router)

assert len(RULE_PLAN_ATTEMPT_ORDER) == len(planner._plan_attempt_chain())

workflow_plan = planner.plan(
    AgentInput(message="现在几点了，回复我一句", session_id="planner-session")
)
assert workflow_plan["action"] == "workflow"
assert len(workflow_plan["steps"]) == 2
assert workflow_plan["steps"][0]["step_name"] == "get_time"
assert workflow_plan["steps"][0]["action"] == "tool"
assert workflow_plan["steps"][0]["tool_name"] == "time_tool"
assert workflow_plan["steps"][1]["step_name"] == "generate_reply"
assert workflow_plan["steps"][1]["action"] == "model"
assert workflow_plan["steps"][1]["use_step_result"] == "get_time"
assert workflow_plan["context"] == {}

tool_plan = planner.plan(AgentInput(message="现在几点了？", session_id="planner-session"))
assert tool_plan["action"] == "tool"
assert tool_plan["tool_name"] == "time_tool"

research_plan = planner.plan(
    AgentInput(message="请帮我做一个关于强化学习的课题综述", session_id="planner-session")
)
assert research_plan["action"] == "workflow"
assert research_plan["workflow_name"] == "research_team_workflow"
assert len(research_plan["steps"]) == 3
assert research_plan["steps"][0]["agent_role"] == "拆解员"
assert research_plan["steps"][1]["agent_role"] == "调研员"
assert research_plan["steps"][2]["agent_role"] == "撰稿员"

pillar_plan = planner.plan(
    AgentInput(
        message="库存中心三线并行，基建业务数据一起设计",
        session_id="planner-session",
    )
)
assert pillar_plan["action"] == "workflow"
assert pillar_plan["workflow_name"] == "parallel_pillar_workflow"
assert pillar_plan.get("final_step_name") == "merge_pillar"
assert len(pillar_plan["steps"]) == 2
assert len(pillar_plan["steps"][0]["parallel"]) == 3

pillar_ffmpeg_plan = planner.plan(
    AgentInput(
        message="数据中台三线并行规划，并导出视频样例演示",
        session_id="planner-session",
    )
)
assert pillar_ffmpeg_plan["workflow_name"] == "parallel_pillar_ffmpeg_workflow"
assert pillar_ffmpeg_plan["steps"][-1]["step_name"] == "ffmpeg_pack"

parallel_plan = planner.plan(
    AgentInput(
        message="做一个记账应用，前后端模块并行分工交付",
        session_id="planner-session",
    )
)
assert parallel_plan["action"] == "workflow"
assert parallel_plan["workflow_kind"] == "parallel_sequential"
assert parallel_plan["workflow_name"] == "multi_module_parallel_workflow"
assert parallel_plan.get("final_step_name") == "merge_coordination"
assert len(parallel_plan["steps"]) == 2
assert "parallel" in parallel_plan["steps"][0]
assert len(parallel_plan["steps"][0]["parallel"]) == 3

parallel_ffmpeg_plan = planner.plan(
    AgentInput(
        message="记账应用前后端模块并行分工，并导出视频样例演示",
        session_id="planner-session",
    )
)
assert parallel_ffmpeg_plan["action"] == "workflow"
assert parallel_ffmpeg_plan["workflow_name"] == "multi_module_parallel_ffmpeg_workflow"
assert parallel_ffmpeg_plan.get("final_step_name") == "merge_coordination"
assert len(parallel_ffmpeg_plan["steps"]) == 3
assert parallel_ffmpeg_plan["steps"][-1]["step_name"] == "ffmpeg_pack"

research_ffmpeg_plan = planner.plan(
    AgentInput(
        message="调研深度学习框架对比并导出视频样例用于演示",
        session_id="planner-session",
    )
)
assert research_ffmpeg_plan["action"] == "workflow"
assert research_ffmpeg_plan["workflow_name"] == "research_team_ffmpeg_workflow"
assert research_ffmpeg_plan.get("final_step_name") == "writeup"
assert len(research_ffmpeg_plan["steps"]) == 4
assert research_ffmpeg_plan["steps"][-1]["step_name"] == "ffmpeg_pack"
assert research_ffmpeg_plan["steps"][-1]["tool_name"] == "ffmpeg_artifact_tool"

model_plan = planner.plan(AgentInput(message="你好", session_id="planner-session"))
assert model_plan["action"] == "model"
assert model_plan.get("tool_name") is None

invalid_plan = planner.plan(AgentInput(message="   ", session_id="planner-session"))
assert invalid_plan["action"] == "model"
assert invalid_plan["reason"] == "输入数据不合法，无法规划工具调用"

planner_info = planner.get_planner_info()
assert planner_info["planner_class"] == "RulePlanner"

print("rule planner tests passed")
