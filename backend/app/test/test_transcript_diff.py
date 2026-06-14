import os
import sys
import types

os.environ.setdefault("OPENAI_API_KEY", "test-api-key")

fake_openai_module = types.ModuleType("openai")


class FakeOpenAI:
    def __init__(self, *args, **kwargs) -> None:
        pass


fake_openai_module.OpenAI = FakeOpenAI
sys.modules.setdefault("openai", fake_openai_module)

from app.eval.experiment_runner import build_lab_chat_agent, run_experiment
from app.schemas.agent_input import AgentInput
from app.schemas.transcript_response import TranscriptEntryResponse
from app.schemas.runtime_snapshot import RuntimeSessionSnapshot
from app.services.chat_service import ChatService
from app.config.settings import Settings
from app.runtime.runtime_session import RuntimeSession
from app.eval.diff import diff_runtime_snapshots


def _entry(session: RuntimeSession, *, user_input: str, final_output: str) -> TranscriptEntryResponse:
    session.user_input = user_input
    session.final_output = final_output
    return TranscriptEntryResponse(
        type="agent",
        user_input=user_input,
        final_output=final_output,
        success=True,
        timestamp="2026-06-14T12:00:00",
        runtime_session=RuntimeSessionSnapshot.from_runtime_session(session),
    )


def test_chat_service_diff_transcript():
    rs_tool = RuntimeSession(session_id="s1", user_input="现在几点了？")
    rs_tool.planner_result = {"action": "tool", "tool_name": "time_tool"}
    rs_tool.add_tool_call("time_tool", True, "12:00", None)

    rs_model = RuntimeSession(session_id="s1", user_input="你好")
    rs_model.planner_result = {"action": "model", "reason": "fallback"}
    rs_model.add_model_call("你好", True, "mock", None)

    service = ChatService(settings=Settings.from_env())
    service.get_transcript = lambda session_id: [
        _entry(rs_tool, user_input="现在几点了？", final_output="12:00"),
        _entry(rs_model, user_input="你好", final_output="mock"),
    ]

    payload = service.diff_transcript("s1", base_index=0, compare_index=1)
    assert payload["changed"] is True
    changed = {item["field"] for item in payload["items"] if item["changed"]}
    assert "planner_result" in changed
    assert "tool_calls" in changed


def test_run_experiment_twice_then_diff_via_snapshots():
    agent = build_lab_chat_agent()
    r1 = run_experiment("exp_001_time_tool", chat_agent=agent)
    r2 = agent.run(AgentInput(message="你好", session_id="exp-diff"))
    diff = diff_runtime_snapshots(
        r1.runtime_session,
        r2.metadata.get("runtime_session"),
    )
    assert diff.changed is True
