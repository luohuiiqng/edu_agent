from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.agent.chat_agent import ChatAgent
from app.eval.checklist import EvalResult
from app.eval.diff import RuntimeDiffResult, diff_runtime_snapshots
from app.eval.loader import ExperimentDefinition, load_experiment
from app.eval.runner import evaluate_runtime_session
from app.memory.in_memory_memory import InMemoryMemory
from app.models.mock_model import MockModel
from app.planners.rule_planner import RulePlanner
from app.runtime.in_memory_session_store import InMemorySessionStore
from app.runtime.in_memory_transcript_store import InMemoryTranscriptStore
from app.runtime.runtime_manager import RuntimeManager
from app.runtime.runtime_session import RuntimeSession
from app.schemas.agent_input import AgentInput
from app.schemas.agent_output import AgentOutput
from app.tools.ffmpeg_artifact_tool import FfmpegArtifactTool
from app.tools.time_tool import TimeTool
from app.tools.tool_registry import ToolRegistry
from app.tools.tool_router import ToolRouter


def build_lab_chat_agent(
    *,
    mock_response: str = "mock response",
    profile: str = "time_only",
    artifacts_root: Path | None = None,
) -> ChatAgent:
    """实验用 Agent：MockModel + 可配置 Tool / Planner。"""
    tool_router = ToolRouter()
    tool_registry = ToolRegistry()
    tool_registry.register_tool(TimeTool())
    tool_router.add_rule(
        tool_name="time_tool",
        keywords=["时间", "现在时间", "当前时间", "几点", "现在几点"],
    )

    if profile == "lab_full":
        ffmpeg_root = artifacts_root
        tool_registry.register_tool(FfmpegArtifactTool(artifacts_root=ffmpeg_root))
        tool_router.add_rule(
            tool_name="ffmpeg_artifact_tool",
            keywords=[
                "ffmpeg样例",
                "静音视频样例",
                "演示短视频",
                "ffmpeg演示",
            ],
        )

    runtime_manager = RuntimeManager(
        session_store=InMemorySessionStore(),
        transcript_store=InMemoryTranscriptStore(),
    )
    return ChatAgent(
        runtime_manager=runtime_manager,
        model=MockModel(model_name="eval-mock", response_text=mock_response),
        tool_registry=tool_registry,
        memory=InMemoryMemory(),
        planner=RulePlanner(tool_router=tool_router),
    )


@dataclass
class ExperimentRunResult:
    experiment_id: str
    title: str
    message: str
    agent_success: bool
    eval_result: EvalResult
    runtime_session: RuntimeSession | None
    agent_output: AgentOutput | None

    @property
    def passed(self) -> bool:
        return self.agent_success and self.eval_result.passed

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "title": self.title,
            "message": self.message,
            "passed": self.passed,
            "agent_success": self.agent_success,
            "eval": self.eval_result.to_dict(),
            "runtime_session": (
                self.runtime_session.to_dict() if self.runtime_session else None
            ),
        }


@dataclass
class ExperimentPairResult:
    main: ExperimentRunResult
    control: ExperimentRunResult | None
    diff: RuntimeDiffResult | None

    @property
    def passed(self) -> bool:
        if not self.main.passed:
            return False
        if self.control is not None and not self.control.passed:
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "main": self.main.to_dict(),
            "control": self.control.to_dict() if self.control else None,
            "diff": self.diff.to_dict() if self.diff else None,
        }


def _run_single(
    definition: ExperimentDefinition,
    agent: ChatAgent,
    *,
    message: str,
    session_id: str,
    checklist,
) -> ExperimentRunResult:
    output = agent.run(AgentInput(message=message, session_id=session_id))
    runtime_session = output.metadata.get("runtime_session")
    if not isinstance(runtime_session, RuntimeSession):
        runtime_session = None
    eval_result = evaluate_runtime_session(
        runtime_session or {},
        checklist,
        run_success=output.success,
    )
    return ExperimentRunResult(
        experiment_id=definition.id,
        title=definition.title,
        message=message,
        agent_success=output.success,
        eval_result=eval_result,
        runtime_session=runtime_session,
        agent_output=output,
    )


def run_experiment(
    experiment: ExperimentDefinition | str,
    *,
    chat_agent: ChatAgent | None = None,
    include_control: bool = True,
    artifacts_root: Path | None = None,
) -> ExperimentRunResult | ExperimentPairResult:
    definition = (
        experiment
        if isinstance(experiment, ExperimentDefinition)
        else load_experiment(experiment)
    )
    agent = chat_agent or build_lab_chat_agent(
        profile=definition.agent_profile,
        artifacts_root=artifacts_root,
    )
    main = _run_single(
        definition,
        agent,
        message=definition.message,
        session_id=definition.session_id,
        checklist=definition.checklist,
    )

    if not include_control or definition.control is None:
        return main

    control = _run_single(
        definition,
        agent,
        message=definition.control.message,
        session_id=f"{definition.session_id}-control",
        checklist=definition.control.checklist,
    )
    diff = None
    if main.runtime_session and control.runtime_session:
        diff = diff_runtime_snapshots(
            main.runtime_session,
            control.runtime_session,
            base_label="main",
            compare_label="control",
        )
    return ExperimentPairResult(main=main, control=control, diff=diff)


def run_all_experiments(
    *,
    artifacts_root: Path | None = None,
    skip_ffmpeg: bool = False,
) -> list[ExperimentRunResult | ExperimentPairResult]:
    from app.eval.loader import list_experiments

    results: list[ExperimentRunResult | ExperimentPairResult] = []
    for definition in list_experiments():
        if skip_ffmpeg and definition.id == "exp_003_ffmpeg_deliverable":
            continue
        if definition.agent_profile == "lab_full" and artifacts_root is None:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                results.append(
                    run_experiment(definition, artifacts_root=root)
                )
        else:
            results.append(
                run_experiment(definition, artifacts_root=artifacts_root)
            )
    return results


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None
