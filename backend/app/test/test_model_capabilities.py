from app.agent.chat_agent import ChatAgent
from app.memory.in_memory_memory import InMemoryMemory
from app.models.mock_model import MockModel
from app.models.openai_model import OpenAIModel
from app.prompts.prompt_builder import PromptBuilder
from app.runtime.in_memory_session_store import InMemorySessionStore
from app.runtime.in_memory_transcript_store import InMemoryTranscriptStore
from app.runtime.runtime_manager import RuntimeManager
from app.schemas.agent_input import AgentInput
from app.schemas.model_request import ModelRequest
from app.tools.openai_tool_adapter import build_openai_tool_schemas
from app.tools.time_tool import TimeTool
from app.tools.tool_registry import ToolRegistry


def test_model_request_effective_messages_with_system():
    request = ModelRequest(
        messages=[{"role": "user", "content": "你好"}],
        system="你是助手",
    )
    messages = request.effective_messages()
    assert messages[0]["role"] == "system"
    assert messages[1]["content"] == "你好"


def test_prompt_builder_chat_messages_dedupes_current():
    builder = PromptBuilder()
    messages = builder.build_chat_messages(
        [{"role": "user", "content": "你好"}],
        current_input="你好",
    )
    assert len(messages) == 1


def test_build_openai_tool_schemas():
    registry = ToolRegistry()
    registry.register_tool(TimeTool())
    schemas = build_openai_tool_schemas(registry)
    assert schemas[0]["function"]["name"] == "time_tool"


def test_mock_model_simulates_tool_call_then_text():
    registry = ToolRegistry()
    registry.register_tool(TimeTool())
    model = MockModel(simulate_tool_calls=True)
    tools = build_openai_tool_schemas(registry)

    first = model.generate(
        ModelRequest(
            messages=[{"role": "user", "content": "请告诉我现在几点"}],
            tools=tools,
        )
    )
    assert first.has_tool_calls
    assert first.tool_calls[0]["name"] == "time_tool"

    second = model.generate(
        ModelRequest(
            messages=[
                {"role": "user", "content": "请告诉我现在几点"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": first.tool_calls,
                },
                {"role": "tool", "tool_call_id": "mock-call-1", "content": "12:00:00"},
            ],
            tools=tools,
        )
    )
    assert not second.has_tool_calls
    assert second.content


def test_chat_agent_model_branch_executes_model_tool_call():
    registry = ToolRegistry()
    registry.register_tool(TimeTool())
    runtime_manager = RuntimeManager(
        session_store=InMemorySessionStore(),
        transcript_store=InMemoryTranscriptStore(),
    )
    agent = ChatAgent(
        runtime_manager=runtime_manager,
        model=MockModel(simulate_tool_calls=True, response_text="好的"),
        memory=InMemoryMemory(),
        planner=None,
        tool_registry=registry,
        model_enable_tool_calling=True,
        model_max_tool_rounds=1,
    )
    output = agent.run(
        AgentInput(message="帮我看看现在几点了", session_id="model-tool-session")
    )
    assert output.success is True
    runtime_session = output.metadata["runtime_session"]
    assert len(runtime_session.tool_calls) == 1
    assert runtime_session.tool_calls[0]["tool_name"] == "time_tool"
    assert len(runtime_session.model_calls) >= 1
    assert runtime_session.model_calls[0]["metadata"]["tool_calls"]


def test_openai_model_parses_tool_calls(monkeypatch):
    class FakeFunction:
        name = "time_tool"
        arguments = "{}"

    class FakeToolCall:
        id = "call-1"
        function = FakeFunction()

    class FakeMessage:
        content = ""
        tool_calls = [FakeToolCall()]

    class FakeChoice:
        message = FakeMessage()
        finish_reason = "tool_calls"

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeCompletions:
        def create(self, **kwargs):
            assert kwargs["messages"][0]["role"] == "system"
            assert kwargs.get("tools")
            return FakeResponse()

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    model = OpenAIModel(model_name="test", api_key="k")
    model._client = FakeClient()
    response = model.generate(
        ModelRequest(
            messages=[{"role": "user", "content": "几点了"}],
            system="sys",
            tools=[{"type": "function", "function": {"name": "time_tool"}}],
        )
    )
    assert response.success is True
    assert response.tool_calls[0]["name"] == "time_tool"


def test_openai_model_supports_json_response_format():
    class FakeMessage:
        content = '{"action":"model","reason":"ok"}'
        tool_calls = None

    class FakeChoice:
        message = FakeMessage()
        finish_reason = "stop"

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeCompletions:
        def create(self, **kwargs):
            assert kwargs.get("response_format") == {"type": "json_object"}
            return FakeResponse()

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    model = OpenAIModel(model_name="test", api_key="k")
    model._client = FakeClient()
    response = model.generate(
        ModelRequest(
            messages=[{"role": "user", "content": "plan"}],
            response_format={"type": "json_object"},
        )
    )
    assert response.success is True
    assert response.content == '{"action":"model","reason":"ok"}'
