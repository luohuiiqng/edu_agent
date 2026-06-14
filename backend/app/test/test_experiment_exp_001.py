from app.eval.experiment_runner import run_experiment
from app.eval.loader import list_experiments, load_experiment


def test_load_exp_001():
    exp = load_experiment("exp_001_time_tool")
    assert exp.id == "exp_001_time_tool"
    assert exp.checklist.must_call_tool == "time_tool"
    assert exp.checklist.planner_action == "tool"


def test_list_experiments_manifest():
    experiments = list_experiments()
    assert len(experiments) >= 1
    assert experiments[0].id == "exp_001_time_tool"


def test_run_exp_001_time_tool():
    result = run_experiment("exp_001_time_tool")
    assert result.agent_success is True
    assert result.eval_result.passed is True
    assert result.passed is True
    assert result.runtime_session is not None
    assert result.runtime_session.tool_calls[0]["tool_name"] == "time_tool"
