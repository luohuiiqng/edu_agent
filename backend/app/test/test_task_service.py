import time
import os
import sys
import types

from app.config.settings import Settings
from app.schemas.agent_output import AgentOutput

os.environ.setdefault("OPENAI_API_KEY", "test-api-key")
fake_openai_module = types.ModuleType("openai")


class FakeOpenAI:
    def __init__(self, *args, **kwargs) -> None:
        pass


fake_openai_module.OpenAI = FakeOpenAI
sys.modules.setdefault("openai", fake_openai_module)

from app.services.chat_service import ChatService


class StubAgent:
    def __init__(self, delay_s: float = 0.01) -> None:
        self.delay_s = delay_s

    def run(self, agent_input):
        time.sleep(self.delay_s)
        return AgentOutput(
            content=f"ok:{agent_input.message}",
            success=True,
            metadata={},
        )


class StubSessionStore:
    def list_sessions(self):
        return []


class StubTranscriptStore:
    def get_entries(self, session_id: str):
        return []


class StubFactory:
    def __init__(self) -> None:
        self._agent = StubAgent()
        self._session_store = StubSessionStore()
        self._transcript_store = StubTranscriptStore()

    def create_chat_agent(self, settings=None):
        return self._agent

    def get_session_store(self):
        return self._session_store

    def get_transcript_store(self):
        return self._transcript_store


settings = Settings.from_env()
service = ChatService(settings=settings, agent_factory=StubFactory())

task = service.submit_chat_task("hello task", None)
task_id = task["task_id"]
assert task["status"] == "pending"

terminal = {"succeeded", "failed", "cancelled"}
status = None
for _ in range(50):
    status = service.get_task(task_id)
    assert status is not None
    if status["status"] in terminal:
        break
    time.sleep(0.02)

assert status is not None
assert status["status"] == "succeeded"
assert status["session_id"]
assert isinstance(status.get("result"), dict)
assert str(status["result"].get("reply", "")).startswith("ok:hello task")

logs = service.get_task_logs(task_id)
assert logs is not None
assert len(logs["logs"]) >= 2

task_transcript = service.get_task_transcript(task_id)
assert isinstance(task_transcript, list)

cancel_result = service.cancel_task(task_id)
assert cancel_result is not None
assert cancel_result["cancelled"] is False

print("task service tests passed")

