import sys
import types

from fastapi.testclient import TestClient

fake_openai_module = types.ModuleType("openai")


class FakeOpenAI:
    def __init__(self, *args, **kwargs) -> None:
        pass


fake_openai_module.OpenAI = FakeOpenAI
sys.modules.setdefault("openai", fake_openai_module)

from app.main import app
from app.routes import chat as chat_route


class StubTaskChatService:
    def submit_chat_task(self, message: str, session_id: str | None = None):
        return {
            "task_id": "t-1",
            "status": "pending",
            "created_at": "2026-05-09T00:00:00+00:00",
            "session_id": session_id,
        }

    def get_task(self, task_id: str):
        if task_id == "missing":
            return None
        return {
            "task_id": task_id,
            "status": "succeeded",
            "message": "hello",
            "session_id": "s-1",
            "created_at": "2026-05-09T00:00:00+00:00",
            "updated_at": "2026-05-09T00:00:01+00:00",
            "started_at": "2026-05-09T00:00:00+00:00",
            "finished_at": "2026-05-09T00:00:01+00:00",
            "error_message": None,
            "result": {
                "reply": "ok",
                "session_id": "s-1",
                "timestamp": "2026-05-09T00:00:01+00:00",
                "runtime_session": None,
            },
        }

    def get_task_logs(self, task_id: str):
        if task_id == "missing":
            return None
        return {"task_id": task_id, "status": "succeeded", "logs": ["a", "b"]}

    def cancel_task(self, task_id: str):
        if task_id == "missing":
            return None
        return {"task_id": task_id, "status": "cancelling", "cancelled": True}

    def get_task_transcript(self, task_id: str):
        if task_id == "missing":
            return None
        return [
            {
                "type": "agent",
                "user_input": "u",
                "final_output": "a",
                "success": True,
                "timestamp": "2026-05-09T00:00:02+00:00",
                "runtime_session": {
                    "session_id": "s-1",
                    "task_id": task_id,
                    "user_input": "u",
                    "planner_result": None,
                    "workflow_result": None,
                    "tool_calls": [],
                    "model_calls": [],
                    "workflow_trace": [],
                    "collaboration_trace": [],
                    "deliverables": [],
                    "final_output": "a",
                    "errors": [],
                },
            }
        ]


client = TestClient(app)
origin = chat_route.chat_service
try:
    chat_route.chat_service = StubTaskChatService()

    r = client.post("/agent_api/tasks", json={"message": "hello", "session_id": "s-1"})
    assert r.status_code == 200
    assert r.json()["task_id"] == "t-1"

    r2 = client.get("/agent_api/tasks/t-1")
    assert r2.status_code == 200
    assert r2.json()["status"] == "succeeded"
    assert r2.json()["result"]["reply"] == "ok"

    r3 = client.get("/agent_api/tasks/t-1/logs")
    assert r3.status_code == 200
    assert len(r3.json()["logs"]) == 2

    r4 = client.post("/agent_api/tasks/t-1/cancel", json={})
    assert r4.status_code == 200
    assert r4.json()["cancelled"] is True

    r5 = client.get("/agent_api/tasks/missing")
    assert r5.status_code == 404

    r6 = client.get("/agent_api/tasks/t-1/transcript")
    assert r6.status_code == 200
    assert len(r6.json()) == 1
    assert r6.json()[0]["runtime_session"]["task_id"] == "t-1"
finally:
    chat_route.chat_service = origin

print("task route tests passed")

