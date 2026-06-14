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


client = TestClient(app)


def test_list_experiments():
    response = client.get("/agent_api/experiments")
    assert response.status_code == 200
    body = response.json()
    ids = {item["id"] for item in body["experiments"]}
    assert "exp_001_time_tool" in ids
    assert "exp_004_parallel_pillar" in ids
    assert "exp_005_model_fallback" in ids


def test_run_experiment_not_found():
    response = client.post("/agent_api/experiments/missing_exp/run")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_run_experiment_exp_005():
    response = client.post(
        "/agent_api/experiments/exp_005_model_fallback/run",
        params={"include_control": False},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["passed"] is True
    assert body["eval"]["passed"] is True


def test_run_all_experiments_skip_ffmpeg():
    response = client.post(
        "/agent_api/experiments/run-all",
        params={"skip_ffmpeg": True, "compact": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 5
    assert body["passed_count"] == body["total"]
    assert body["passed"] is True
    for item in body["results"]:
        if "main" in item:
            assert item["main"].get("runtime_session") is None
        else:
            assert item.get("runtime_session") is None
