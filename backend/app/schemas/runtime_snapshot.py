from typing import Any
from pydantic import BaseModel
from app.runtime.runtime_session import RuntimeSession


class RuntimeSessionSnapshot(BaseModel):
    """RuntimeSession对外暴露时的标准快照协议"""

    session_id: str
    task_id: str | None = None
    user_input: str
    planner_result: dict[str, Any] | None
    workflow_result: dict[str, Any] | None
    tool_calls: list[dict[str, Any]]
    model_calls: list[dict[str, Any]]
    workflow_trace: list[dict[str, Any]]
    collaboration_trace: list[dict[str, Any]] = []
    deliverables: list[dict[str, Any]] = []
    final_output: str | None
    errors: list[str]

    @classmethod
    def from_runtime_session(
        cls, runtime_session: RuntimeSession
    ) -> "RuntimeSessionSnapshot":
        return cls(**runtime_session.to_dict())
