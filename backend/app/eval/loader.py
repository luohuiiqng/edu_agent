from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.eval.checklist import EvalChecklist

DEFAULT_EXPERIMENTS_DIR = Path(__file__).resolve().parents[1] / "experiments"


@dataclass
class ExperimentDefinition:
    id: str
    title: str
    message: str
    session_id: str
    checklist: EvalChecklist
    use_mock_model: bool = True
    raw: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperimentDefinition":
        exp_id = str(data["id"])
        agent = data.get("agent") or {}
        return cls(
            id=exp_id,
            title=str(data.get("title", exp_id)),
            message=str(data["message"]),
            session_id=str(data.get("session_id", exp_id)),
            checklist=EvalChecklist.from_dict(data),
            use_mock_model=bool(agent.get("use_mock_model", True)),
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
    definition = ExperimentDefinition.from_dict(data)
    if definition.id != experiment_id and not str(path.stem).startswith(experiment_id):
        pass
    return definition


def list_experiments(base_dir: Path | None = None) -> list[ExperimentDefinition]:
    root = base_dir or experiments_dir()
    manifest = load_manifest(root / "manifest.yaml")
    return [load_experiment(exp_id, root) for exp_id in manifest]
