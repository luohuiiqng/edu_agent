from typing import Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RuntimeSession:
    """一次运行过程中的核心聚合快照"""

    session_id: str = ""
    task_id: str | None = None
    user_input: str = ""
    planner_result: dict[str, Any] | None = None
    workflow_result: dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    model_calls: list[dict[str, Any]] = field(default_factory=list)
    workflow_trace: list[dict[str, Any]] = field(default_factory=list)
    # 多角色协作时间线（与 workflow 步骤对应，便于 UI 展示「谁做了什么」）
    collaboration_trace: list[dict[str, Any]] = field(default_factory=list)
    # 结构化成果引用（路径/URL/摘要）；完整文件由后续 Tool 写入并登记在此
    deliverables: list[dict[str, Any]] = field(default_factory=list)
    final_output: str | None = None
    errors: list[str] = field(default_factory=list)

    def add_tool_call(
        self, tool_name: str, success: bool, output: Any, error: str | None
    ) -> None:
        timestamp = datetime.now().isoformat()
        self.tool_calls.append(
            {
                "tool_name": tool_name,
                "success": success,
                "output": output,
                "error": error,
                "timestamp": timestamp,
            }
        )

    def add_model_call(
        self,
        prompt: str,
        success: bool,
        output: Any,
        error: str | None,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        timestamp = datetime.now().isoformat()
        row: dict[str, Any] = {
            "prompt": prompt,
            "success": success,
            "output": output,
            "error": error,
            "timestamp": timestamp,
        }
        if metadata:
            row["metadata"] = metadata
        self.model_calls.append(row)

    def add_workflow_step_trace(
        self,
        step_name: str,
        action: str,
        success: bool,
        output: Any,
        input_summary: str,
        output_summary: str,
        error: str | None,
        agent_role: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        timestamp = datetime.now().isoformat()
        row: dict[str, Any] = {
            "step_name": step_name,
            "action": action,
            "success": success,
            "output": output,
            "error": error,
            "input_summary": input_summary,
            "output_summary": output_summary,
            "timestamp": timestamp,
        }
        if agent_role:
            row["agent_role"] = agent_role
        if extra:
            row.update(extra)
        self.workflow_trace.append(row)

    def add_collaboration_event(
        self,
        *,
        agent_role: str,
        phase: str,
        summary: str,
        step_name: str | None = None,
    ) -> None:
        """记录一次「代理交接」，便于终端/UI 展示协同过程。"""
        timestamp = datetime.now().isoformat()
        self.collaboration_trace.append(
            {
                "agent_role": agent_role,
                "phase": phase,
                "step_name": step_name,
                "summary": summary,
                "timestamp": timestamp,
            }
        )

    def add_deliverable(self, record: dict[str, Any]) -> None:
        """登记一条成果元数据（见 ``schemas.collaboration.deliverable_dict``）。"""
        self.deliverables.append(dict(record))
    def add_error(self, error_message: str) -> None:
        text = str(error_message or "").strip()
        if not text:
            return
        self.errors.append(text)

    def update_planner_trace_outcome(
        self,
        *,
        success: bool,
        error: str | None = None,
    ) -> None:
        """根据本轮实际执行结果，回写 planner 步骤 trace。"""
        for row in reversed(self.workflow_trace):
            if row.get("step_name") == "planner":
                row["success"] = success
                if error:
                    row["error"] = error
                elif success:
                    row["error"] = None
                return

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "task_id": self.task_id,
            "user_input": self.user_input,
            "planner_result": self.planner_result,
            "workflow_result": self.workflow_result,
            "tool_calls": self.tool_calls,
            "model_calls": self.model_calls,
            "workflow_trace": self.workflow_trace,
            "collaboration_trace": self.collaboration_trace,
            "deliverables": self.deliverables,
            "final_output": self.final_output,
            "errors": self.errors,
        }
