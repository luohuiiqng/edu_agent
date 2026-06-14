from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from app.eval.experiment_runner import (
    ExperimentPairResult,
    ExperimentRunResult,
    ffmpeg_available,
    run_all_experiments,
    run_experiment,
)
from app.eval.loader import list_experiments, load_experiment

router = APIRouter(tags=["experiments"])


@router.get("/experiments")
def list_builtin_experiments() -> dict:
    experiments = list_experiments()
    return {
        "experiments": [
            {
                "id": exp.id,
                "title": exp.title,
                "message": exp.message,
                "agent_profile": exp.agent_profile,
                "has_control": exp.control is not None,
            }
            for exp in experiments
        ]
    }


@router.post("/experiments/{experiment_id}/run")
def run_builtin_experiment(
    experiment_id: str,
    include_control: bool = Query(default=True),
) -> dict:
    try:
        definition = load_experiment(experiment_id)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": str(exc)}},
        ) from exc

    if (
        definition.id == "exp_003_ffmpeg_deliverable"
        and not ffmpeg_available()
    ):
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": "FFMPEG_UNAVAILABLE",
                    "message": "本机未安装 ffmpeg，无法运行 exp_003",
                }
            },
        )

    if definition.agent_profile == "lab_full":
        with tempfile.TemporaryDirectory() as tmp:
            result = run_experiment(
                definition,
                include_control=include_control,
                artifacts_root=Path(tmp),
            )
            return _serialize_result(result)

    result = run_experiment(definition, include_control=include_control)
    return _serialize_result(result)


@router.post("/experiments/run-all")
def run_all_builtin_experiments(
    skip_ffmpeg: bool = Query(default=False),
    include_control: bool = Query(default=True),
    compact: bool = Query(default=True),
) -> dict:
    results = run_all_experiments(skip_ffmpeg=skip_ffmpeg)
    serialized = [
        _serialize_result(result, compact=compact) for result in results
    ]
    passed_count = sum(1 for result in results if result.passed)
    return {
        "passed": all(result.passed for result in results),
        "total": len(results),
        "passed_count": passed_count,
        "skip_ffmpeg": skip_ffmpeg,
        "ffmpeg_available": ffmpeg_available(),
        "results": serialized,
    }


def _serialize_result(
    result: ExperimentRunResult | ExperimentPairResult,
    *,
    compact: bool = False,
) -> dict:
    payload = result.to_dict()
    if compact:
        payload = _compact_payload(payload)
    return payload


def _compact_payload(payload: dict) -> dict:
    compact = dict(payload)
    if "runtime_session" in compact:
        compact["runtime_session"] = None
    main = compact.get("main")
    if isinstance(main, dict):
        compact["main"] = _compact_run_payload(main)
    control = compact.get("control")
    if isinstance(control, dict):
        compact["control"] = _compact_run_payload(control)
    return compact


def _compact_run_payload(payload: dict) -> dict:
    compact = dict(payload)
    compact["runtime_session"] = None
    compact.pop("agent_output", None)
    return compact
