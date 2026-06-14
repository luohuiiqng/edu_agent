from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from app.eval.checklist import EvalChecklist

AgentProfile = Literal["time_only", "lab_full"]

DEFAULT_EXPERIMENTS_DIR = Path(__file__).resolve().parents[1] / "experiments"


@dataclass
class ExperimentControl:
    message: str
    checklist: EvalChecklist


@dataclass
class ExperimentDefinition:
    id: str
    title: str
    message: str
    session_id: str
    checklist: EvalChecklist
    agent_profile: AgentProfile = "time_only"
    use_mock_model: bool = True
    control: ExperimentControl | None = None
    raw: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperimentDefinition":
        exp_id = str(data["id"])
        agent = data.get("agent") or {}
        control_raw = data.get("control")
        control = None
        if isinstance(control_raw, dict) and control_raw.get("message"):
            control = ExperimentControl(
                message=str(control_raw["message"]),
                checklist=EvalChecklist.from_dict(control_raw),
            )
        profile = str(agent.get("profile", "time_only"))
        if profile not in ("time_only", "lab_full"):
            profile = "time_only"
        return cls(
            id=exp_id,
            title=str(data.get("title", exp_id)),
            message=str(data["message"]),
            session_id=str(data.get("session_id", exp_id)),
            checklist=EvalChecklist.from_dict(data),
            agent_profile=profile,  # type: ignore[arg-type]
            use_mock_model=bool(agent.get("use_mock_model", True)),
            control=control,
            raw=data,
        )


def experiments_dir() -> Path:
    return DEFAULT_EXPERIMENTS_DIR


def load_manifest(path: Path | None = None) -> list[str]:
    manifest_path = path or (experiments_dir() / "manifest.yaml")
    with manifest_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    experiments = data.get("experiments") or []
    return [str(item) for item in experiments]


def load_experiment(experiment_id: str, base_dir: Path | None = None) -> ExperimentDefinition:
    root = base_dir or experiments_dir()
    path = root / f"{experiment_id}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"experiment not found: {experiment_id} ({path})")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return ExperimentDefinition.from_dict(data)


def list_experiments(base_dir: Path | None = None) -> list[ExperimentDefinition]:
    root = base_dir or experiments_dir()
    manifest = load_manifest(root / "manifest.yaml")
    return [load_experiment(exp_id, root) for exp_id in manifest]
