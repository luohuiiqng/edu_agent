from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.agent.chat_agent import ChatAgent
from app.eval.checklist import EvalResult
from app.eval.loader import ExperimentDefinition, load_experiment
from app.eval.runner import evaluate_runtime_session
from app.memory.in_memory_memory import InMemoryMemory
from app.models.mock_model import MockModel
from app.planners.rule_planner import RulePlanner
from app.runtime.in_memory_session_store import InMemorySessionStore
from app.runtime.in_memory_transcript_store import InMemoryTranscriptStore
from app.runtime.runtime_manager import RuntimeManager
from app.runtime.runtime_session import RuntimeSession
from app.schemas.agent_input import AgentInput
from app.schemas.agent_output import AgentOutput
from app.tools.time_tool import TimeTool
from app.tools.tool_registry import ToolRegistry
from app.tools.tool_router import ToolRouter


def build_lab_chat_agent(*, mock_response: str = "mock response") -> ChatAgent:
    """实验用 Agent：MockModel + time_tool 规则路由（含「几点」关键词）。"""
    tool_router = ToolRouter()
    tool_router.add_rule(
        tool_name="time_tool",
        keywords=["时间", "现在时间", "当前时间", "几点", "现在几点"],
    )
    tool_registry = ToolRegistry()
    tool_registry.register_tool(TimeTool())
    runtime_manager = RuntimeManager(
        session_store=InMemorySessionStore(),
        transcript_store=InMemoryTranscriptStore(),
    )
    return ChatAgent(
        runtime_manager=runtime_manager,
        model=MockModel(model_name="eval-mock", response_text=mock_response),
        tool_registry=tool_registry,
        memory=InMemoryMemory(),
        planner=RulePlanner(tool_router=tool_router),
    )


@dataclass
class ExperimentRunResult:
    experiment_id: str
    title: str
    message: str
    agent_success: bool
    eval_result: EvalResult
    runtime_session: RuntimeSession | None
    agent_output: AgentOutput | None

    @property
    def passed(self) -> bool:
        return self.agent_success and self.eval_result.passed

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "title": self.title,
            "message": self.message,
            "passed": self.passed,
            "agent_success": self.agent_success,
            "eval": self.eval_result.to_dict(),
            "runtime_session": (
                self.runtime_session.to_dict() if self.runtime_session else None
            ),
        }


def run_experiment(
    experiment: ExperimentDefinition | str,
    *,
    chat_agent: ChatAgent | None = None,
) -> ExperimentRunResult:
    definition = (
        experiment
        if isinstance(experiment, ExperimentDefinition)
        else load_experiment(experiment)
    )
    agent = chat_agent or build_lab_chat_agent()
    agent_input = AgentInput(
        message=definition.message,
        session_id=definition.session_id,
    )
    output = agent.run(agent_input)
    runtime_session = output.metadata.get("runtime_session")
    if not isinstance(runtime_session, RuntimeSession):
        runtime_session = None
    eval_result = evaluate_runtime_session(
        runtime_session or {},
        definition.checklist,
        run_success=output.success,
    )
    return ExperimentRunResult(
        experiment_id=definition.id,
        title=definition.title,
        message=definition.message,
        agent_success=output.success,
        eval_result=eval_result,
        runtime_session=runtime_session,
        agent_output=output,
    )
