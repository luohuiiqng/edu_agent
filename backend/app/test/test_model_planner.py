from app.agent.chat_agent import ChatAgent
from app.config.settings import Settings
from app.memory.in_memory_memory import InMemoryMemory
from app.models.mock_model import MockModel
from app.planners.hybrid_planner import HybridPlanner
from app.planners.model_planner import ModelPlanner
from app.planners.plan_parser import parse_plan_json
from app.planners.planner_factory import create_planner
from app.planners.rule_planner import RulePlanner
from app.runtime.in_memory_session_store import InMemorySessionStore
from app.runtime.in_memory_transcript_store import InMemoryTranscriptStore
from app.runtime.runtime_manager import RuntimeManager
from app.schemas.agent_input import AgentInput
from app.tools.time_tool import TimeTool
from app.tools.tool_registry import ToolRegistry
from app.tools.tool_router import ToolRouter


def _settings(mode: str) -> Settings:
    return Settings(
        openai_api_key="mock",
        openai_model="mock",
        openai_base_url=None,
        openai_organization=None,
        store_backend="memory",
        runtime_db_path=None,
        model_provider="mock",
        planner_mode=mode,
    )


def _build_agent(planner_mode: str = "hybrid") -> ChatAgent:
    registry = ToolRegistry()
    registry.register_tool(TimeTool())
    router = ToolRouter()
    router.add_rule("time_tool", ["时间", "几点", "现在几点"])
    model = MockModel()
    planner = create_planner(
        _settings(planner_mode),
        model=model,
        tool_registry=registry,
        tool_router=router,
    )
    return ChatAgent(
        runtime_manager=RuntimeManager(
            session_store=InMemorySessionStore(),
            transcript_store=InMemoryTranscriptStore(),
        ),
        model=model,
        memory=InMemoryMemory(),
        planner=planner,
        tool_registry=registry,
        model_enable_tool_calling=False,
    )


def test_parse_plan_json_with_fence():
    parsed = parse_plan_json(
        '说明\n```json\n{"action":"tool","tool_name":"time_tool","reason":"x"}\n```'
    )
    assert parsed is not None
    assert parsed["action"] == "tool"


def test_model_planner_selects_tool():
    registry = ToolRegistry()
    registry.register_tool(TimeTool())
    model = MockModel()
    planner = ModelPlanner(model=model, tool_registry=registry)
    plan = planner.plan(AgentInput(message="现在几点了？", session_id="s1"))
    assert plan["action"] == "tool"
    assert plan["tool_name"] == "time_tool"
    assert plan["planner_source"] == "model"
    assert plan["planning_trace"]["parsed"]["action"] == "tool"
    assert model._last_input is not None
    assert model._last_input.response_format == {"type": "json_object"}


def test_model_planner_selects_workflow():
    registry = ToolRegistry()
    model = MockModel()
    planner = ModelPlanner(model=model, tool_registry=registry)
    plan = planner.plan(
        AgentInput(
            message="基建、业务、数据三线并行规划登录",
            session_id="s1",
        )
    )
    assert plan["action"] == "workflow"
    assert plan["workflow_name"] == "parallel_pillar_workflow"


def test_hybrid_keeps_rule_workflow():
    agent = _build_agent("hybrid")
    output = agent.run(
        AgentInput(message="现在几点了，回复我一句", session_id="hybrid-wf")
    )
    assert output.success is True
    plan = output.metadata["runtime_session"].planner_result
    assert plan["action"] == "workflow"
    assert plan["planner_source"] == "rule"


def test_hybrid_uses_model_when_rule_falls_back():
    agent = _build_agent("hybrid")
    output = agent.run(AgentInput(message="你好", session_id="hybrid-model"))
    assert output.success is True
    plan = output.metadata["runtime_session"].planner_result
    assert plan["action"] == "model"
    assert plan["planner_source"] == "model"
    assert plan.get("rule_fallback_reason")


def test_planner_factory_modes():
    registry = ToolRegistry()
    router = ToolRouter()
    model = MockModel()
    assert isinstance(
        create_planner(_settings("rule"), model=model, tool_registry=registry, tool_router=router),
        RulePlanner,
    )
    assert isinstance(
        create_planner(_settings("model"), model=model, tool_registry=registry, tool_router=router),
        ModelPlanner,
    )
    assert isinstance(
        create_planner(_settings("hybrid"), model=model, tool_registry=registry, tool_router=router),
        HybridPlanner,
    )
