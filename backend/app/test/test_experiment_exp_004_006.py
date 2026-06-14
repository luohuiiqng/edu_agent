from app.eval.experiment_runner import ExperimentPairResult, run_experiment


def test_run_exp_004_parallel_pillar_with_control():
    result = run_experiment("exp_004_parallel_pillar")
    assert isinstance(result, ExperimentPairResult)
    assert result.main.passed is True
    assert result.main.runtime_session is not None
    assert result.main.runtime_session.planner_result["action"] == "workflow"
    parallel_steps = [
        step
        for step in result.main.runtime_session.workflow_trace
        if step.get("parallel_fan_out")
    ]
    assert len(parallel_steps) >= 3
    assert result.control is not None
    assert result.control.passed is True
    assert result.diff is not None
    assert result.diff.changed is True
    assert result.passed is True


def test_run_exp_005_model_fallback():
    result = run_experiment("exp_005_model_fallback", include_control=False)
    assert result.passed is True
    assert result.runtime_session is not None
    assert result.runtime_session.planner_result["action"] == "model"
    assert len(result.runtime_session.tool_calls) == 0
    assert len(result.runtime_session.model_calls) >= 1


def test_run_exp_006_multi_module_parallel():
    result = run_experiment("exp_006_multi_module_parallel", include_control=False)
    assert result.passed is True
    assert result.runtime_session is not None
    assert result.runtime_session.planner_result["action"] == "workflow"
    parallel_steps = [
        step
        for step in result.runtime_session.workflow_trace
        if step.get("parallel_fan_out")
    ]
    assert len(parallel_steps) >= 3
