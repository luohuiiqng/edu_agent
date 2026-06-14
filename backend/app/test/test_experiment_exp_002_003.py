import shutil
import tempfile
from pathlib import Path

import pytest

from app.eval.experiment_runner import (
    ExperimentPairResult,
    ffmpeg_available,
    run_experiment,
)


def test_run_exp_002_workflow_with_control():
    with tempfile.TemporaryDirectory() as tmp:
        result = run_experiment(
            "exp_002_time_reply_workflow",
            artifacts_root=Path(tmp),
        )
    assert isinstance(result, ExperimentPairResult)
    assert result.main.passed is True
    assert result.main.runtime_session is not None
    assert result.main.runtime_session.planner_result["action"] == "workflow"
    assert result.control is not None
    assert result.control.passed is True
    assert result.diff is not None
    assert result.diff.changed is True
    assert result.passed is True


@pytest.mark.skipif(not ffmpeg_available(), reason="需要本机安装 ffmpeg")
def test_run_exp_003_ffmpeg_deliverable():
    with tempfile.TemporaryDirectory() as tmp:
        result = run_experiment(
            "exp_003_ffmpeg_deliverable",
            artifacts_root=Path(tmp),
            include_control=False,
        )
    assert result.passed is True
    assert result.runtime_session is not None
    assert len(result.runtime_session.deliverables) >= 1
