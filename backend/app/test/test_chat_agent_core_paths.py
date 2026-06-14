from app.agent.chat_agent import ChatAgent
from app.memory.in_memory_memory import InMemoryMemory
from app.models.mock_model import MockModel
from app.planners.base_planner import BasePlanner
from app.planners.plan_context import PlanContext
from app.planners.rule_planner import RulePlanner
from app.runtime.in_memory_session_store import InMemorySessionStore
from app.runtime.in_memory_transcript_store import InMemoryTranscriptStore
from app.runtime.runtime_manager import RuntimeManager
from app.schemas.agent_input import AgentInput
from app.tools.time_tool import TimeTool
from app.tools.tool_registry import ToolRegistry
from app.tools.tool_router import ToolRouter


def _build_agent(
    *,
    model: MockModel | None = None,
    planner: BasePlanner | None = None,
    memory: InMemoryMemory | None = None,
    tool_registry: ToolRegistry | None = None,
) -> ChatAgent:
    runtime_manager = RuntimeManager(
        session_store=InMemorySessionStore(),
        transcript_store=InMemoryTranscriptStore(),
    )
    return ChatAgent(
        runtime_manager=runtime_manager,
        model=model or MockModel(),
        memory=memory or InMemoryMemory(),
        planner=planner,
        tool_registry=tool_registry,
    )


def _lab_planner() -> RulePlanner:
    tool_router = ToolRouter()
    tool_router.add_rule(
        tool_name="time_tool",
        keywords=["时间", "现在时间", "当前时间", "几点", "现在几点"],
    )
    return RulePlanner(tool_router=tool_router)


def test_empty_message_returns_structured_failure():
    agent = _build_agent(planner=_lab_planner())
    output = agent.run(AgentInput(message="   ", session_id="s-empty"))
    assert output.success is False
    assert "输入不合法" in (output.error_message or "")


def test_multi_turn_greeting_then_time_tool():
    registry = ToolRegistry()
    registry.register_tool(TimeTool())
    agent = _build_agent(
        planner=_lab_planner(),
        tool_registry=registry,
    )
    session_id = "multi-greet-time"

    greet = agent.run(AgentInput(message="你好", session_id=session_id))
    assert greet.success is True

    time_out = agent.run(AgentInput(message="现在几点了？", session_id=session_id))
    assert time_out.success is True
    runtime_session = time_out.metadata["runtime_session"]
    assert runtime_session.planner_result["action"] == "tool"
    assert runtime_session.tool_calls[-1]["tool_name"] == "time_tool"
    assert runtime_session.tool_calls[-1]["success"] is True


def test_multi_turn_time_followup_uses_context():
    registry = ToolRegistry()
    registry.register_tool(TimeTool())
    agent = _build_agent(
        planner=_lab_planner(),
        tool_registry=registry,
    )
    session_id = "multi-followup"

    agent.run(AgentInput(message="现在几点了？", session_id=session_id))
    followup = agent.run(AgentInput(message="再查一次", session_id=session_id))

    assert followup.success is True
    runtime_session = followup.metadata["runtime_session"]
    assert runtime_session.planner_result["action"] == "tool"
    assert runtime_session.tool_calls[-1]["tool_name"] == "time_tool"
    assert "多轮跟进" in runtime_session.planner_result.get("reason", "")


def test_model_failure_is_recorded_in_runtime_session():
    agent = _build_agent(
        model=MockModel(should_fail=True, fail_message="upstream unavailable"),
        planner=_lab_planner(),
    )
    output = agent.run(AgentInput(message="你好", session_id="s-model-fail"))
    assert output.success is False
    runtime_session = output.metadata["runtime_session"]
    assert any("model call error" in err for err in runtime_session.errors)
    assert runtime_session.model_calls[-1]["success"] is False


def test_missing_tool_records_error_and_fails():
    registry = ToolRegistry()

    class ToolOnlyPlanner(BasePlanner):
        def plan(self, input_data, context=None):
            return {
                "action": "tool",
                "tool_name": "missing_tool",
                "reason": "force missing tool",
                "workflow_name": None,
                "steps": [],
                "context": {},
            }

    agent = _build_agent(planner=ToolOnlyPlanner(), tool_registry=registry)
    output = agent.run(AgentInput(message="触发工具", session_id="s-missing-tool"))
    assert output.success is False
    runtime_session = output.metadata["runtime_session"]
    assert any("tool call error" in err for err in runtime_session.errors)


def test_unknown_planner_action_falls_back_to_model_with_error():
    class UnknownActionPlanner(BasePlanner):
        def plan(self, input_data, context=None):
            return {
                "action": "magic",
                "reason": "unknown branch",
                "tool_name": None,
                "workflow_name": None,
                "steps": [],
                "context": {},
            }

    agent = _build_agent(planner=UnknownActionPlanner())
    output = agent.run(AgentInput(message="测试未知分支", session_id="s-unknown"))
    assert output.success is True
    runtime_session = output.metadata["runtime_session"]
    assert any("unknown planner action" in err for err in runtime_session.errors)
    assert len(runtime_session.model_calls) == 1


def test_multi_turn_greeting_after_time_stays_model():
    registry = ToolRegistry()
    registry.register_tool(TimeTool())
    agent = _build_agent(
        planner=_lab_planner(),
        tool_registry=registry,
    )
    session_id = "multi-greet-after-time"

    agent.run(AgentInput(message="现在几点了？", session_id=session_id))
    greet = agent.run(AgentInput(message="你好", session_id=session_id))

    assert greet.success is True
    runtime_session = greet.metadata["runtime_session"]
    assert runtime_session.planner_result["action"] == "model"
    assert runtime_session.tool_calls == []


def test_rule_planner_contextual_time_followup():
    planner = _lab_planner()
    plan = planner.plan(
        AgentInput(message="再查一次", session_id="s1"),
        context=PlanContext(recent_user_messages=["现在几点了？"]),
    )
    assert plan["action"] == "tool"
    assert plan["tool_name"] == "time_tool"


def test_rule_planner_contextual_workflow_followup():
    planner = _lab_planner()
    plan = planner.plan(
        AgentInput(message="再并行一遍", session_id="s1"),
        context=PlanContext(
            recent_user_messages=["基建、业务、数据三线并行规划用户登录"],
        ),
    )
    assert plan["action"] == "workflow"
    assert plan["workflow_name"] == "parallel_pillar_workflow"
    assert "workflow 跟进" in plan.get("reason", "")


def test_multi_turn_workflow_followup_runs_parallel_again():
    agent = _build_agent(planner=_lab_planner())
    session_id = "multi-workflow-followup"

    first = agent.run(
        AgentInput(
            message="基建、业务、数据三线并行规划用户登录",
            session_id=session_id,
        )
    )
    assert first.success is True
    assert first.metadata["runtime_session"].planner_result["action"] == "workflow"

    second = agent.run(AgentInput(message="按刚才方案再并行一遍", session_id=session_id))
    assert second.success is True
    runtime_session = second.metadata["runtime_session"]
    assert runtime_session.planner_result["action"] == "workflow"
    assert runtime_session.planner_result["workflow_name"] == "parallel_pillar_workflow"
    planner_trace = next(
        row for row in runtime_session.workflow_trace if row["step_name"] == "planner"
    )
    assert planner_trace["success"] is True


def test_workflow_failure_marks_planner_trace():
    class SingleModelWorkflowPlanner(BasePlanner):
        def plan(self, input_data, context=None):
            return {
                "action": "workflow",
                "workflow_kind": "sequential",
                "workflow_name": "fail_demo",
                "reason": "单步 model workflow 测试",
                "tool_name": None,
                "steps": [
                    {
                        "step_name": "only_model",
                        "action": "model",
                        "prompt": "please fail",
                    }
                ],
                "context": {},
            }

    agent = _build_agent(
        model=MockModel(should_fail=True, fail_message="model step failed"),
        planner=SingleModelWorkflowPlanner(),
    )
    output = agent.run(AgentInput(message="触发失败 workflow", session_id="s-wf-fail"))
    assert output.success is False
    runtime_session = output.metadata["runtime_session"]
    planner_trace = next(
        row for row in runtime_session.workflow_trace if row["step_name"] == "planner"
    )
    assert planner_trace["success"] is False
    assert planner_trace["error"] == output.error_message
    assert planner_trace["error"]
