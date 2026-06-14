from typing import Any

from app.agent.chat_agent import ChatAgent
from app.memory.in_memory_memory import InMemoryMemory
from app.models.mock_model import MockModel
from app.planners.base_planner import BasePlanner
from app.planners.rule_planner import RulePlanner
from app.runtime.in_memory_session_store import InMemorySessionStore
from app.runtime.in_memory_transcript_store import InMemoryTranscriptStore
from app.runtime.runtime_manager import RuntimeManager
from app.runtime.runtime_session import RuntimeSession
from app.runtime.transcript_entry import TranscriptEntry
from app.schemas.agent_input import AgentInput
from app.tools.time_tool import TimeTool
from app.tools.tool_registry import ToolRegistry
from app.tools.tool_router import ToolRouter


class WorkflowPlanner(BasePlanner):
    def plan(self, input_data: Any, context: Any = None) -> dict[str, Any]:
        return {
            "action": "workflow",
            "steps": [
                {
                    "action": "tool",
                    "tool_name": "time_tool",
                    "tool_input": {"content": input_data.message},
                    "step_name": "get_time",
                },
                {
                    "action": "model",
                    "prompt_template": "当前时间是 {step_output}，请生成一句话回复用户",
                    "use_step_result": "get_time",
                    "step_name": "generate_reply",
                },
            ],
            "context": {},
        }


def assert_transcript_entry_shape(
    entry: TranscriptEntry,
    expected_user_input: str,
    expected_output: str,
) -> RuntimeSession:
    assert isinstance(entry, TranscriptEntry)
    assert entry.type == "agent"
    assert entry.user_input == expected_user_input
    assert entry.final_output == expected_output
    assert isinstance(entry.success, bool)
    assert entry.timestamp
    runtime_session = entry.runtime_session
    assert isinstance(runtime_session, RuntimeSession)
    assert runtime_session.user_input == expected_user_input
    assert runtime_session.final_output == expected_output
    return runtime_session


tool_registry = ToolRegistry()
tool_registry.register_tool(TimeTool())

transcript_store = InMemoryTranscriptStore()
session_store = InMemorySessionStore()
runtime_manager = RuntimeManager(
    session_store=session_store,
    transcript_store=transcript_store,
)
memory = InMemoryMemory()
model = MockModel(response_text="mock transcript response")

tool_router = ToolRouter()
tool_router.add_rule(
    tool_name="time_tool",
    keywords=["时间", "现在时间", "当前时间", "几点", "现在几点"],
)
rule_planner = RulePlanner(tool_router=tool_router)

rule_agent = ChatAgent(
    runtime_manager=runtime_manager,
    model=model,
    tool_registry=tool_registry,
    memory=memory,
    planner=rule_planner,
)

session_id = "transcript-rule-session"

tool_output = rule_agent.run(AgentInput(message="现在几点了？", session_id=session_id))
model_output = rule_agent.run(AgentInput(message="你好", session_id=session_id))

rule_entries = transcript_store.get_entries(session_id)
assert len(rule_entries) == 2

tool_entry_runtime = assert_transcript_entry_shape(
    rule_entries[0],
    expected_user_input="现在几点了？",
    expected_output=tool_output.content or "",
)
assert tool_entry_runtime.planner_result["action"] == "tool"
assert tool_entry_runtime.planner_result["tool_name"] == "time_tool"
assert len(tool_entry_runtime.tool_calls) == 1
assert tool_entry_runtime.model_calls == []

model_entry_runtime = assert_transcript_entry_shape(
    rule_entries[1],
    expected_user_input="你好",
    expected_output=model_output.content or "",
)
assert model_entry_runtime.planner_result["action"] == "model"
assert model_entry_runtime.tool_calls == []
assert len(model_entry_runtime.model_calls) == 1

workflow_transcript_store = InMemoryTranscriptStore()
workflow_session_store = InMemorySessionStore()
workflow_runtime_manager = RuntimeManager(
    session_store=workflow_session_store,
    transcript_store=workflow_transcript_store,
)
workflow_model = MockModel(response_text="mock workflow transcript response")
workflow_agent = ChatAgent(
    runtime_manager=workflow_runtime_manager,
    model=workflow_model,
    tool_registry=tool_registry,
    planner=WorkflowPlanner(),
)

workflow_session_id = "transcript-workflow-session"
workflow_output = workflow_agent.run(
    AgentInput(message="现在几点了？", session_id=workflow_session_id)
)

workflow_entries = workflow_transcript_store.get_entries(workflow_session_id)
assert len(workflow_entries) == 1

workflow_runtime = assert_transcript_entry_shape(
    workflow_entries[0],
    expected_user_input="现在几点了？",
    expected_output=workflow_output.content or "",
)
assert workflow_runtime.planner_result["action"] == "workflow"
assert len(workflow_runtime.workflow_trace) == 3
assert workflow_runtime.workflow_trace[0]["step_name"] == "planner"
assert workflow_runtime.workflow_trace[1]["action"] == "tool"
assert workflow_runtime.workflow_trace[2]["action"] == "model"
assert len(workflow_runtime.tool_calls) == 1
assert len(workflow_runtime.model_calls) == 1
assert workflow_runtime.model_calls[0]["prompt"]

print("chat agent transcript store tests passed")
