from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4
from app.schemas.agent_input import AgentInput
from app.schemas.agent_output import AgentOutput
from app.services.agent_factory import AgentFactory
from app.schemas.runtime_snapshot import RuntimeSessionSnapshot
from app.schemas.transcript_response import TranscriptEntryResponse
from app.schemas.session_response import SessionResponse
from app.config.settings import Settings


def ensure_session_id(session_id: str | None) -> str:
    return session_id or str(uuid4())


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ChatTaskRecord:
    task_id: str
    message: str
    session_id: str | None
    status: str
    created_at: str
    updated_at: str
    started_at: str | None = None
    finished_at: str | None = None
    error_message: str | None = None
    result: dict[str, Any] | None = None
    logs: list[str] = field(default_factory=list)


class ChatService:
    def __init__(
        self,
        settings: Settings,
        agent_factory: AgentFactory | None = None,
    ) -> None:
        self._settings = settings or Settings.from_env()
        self._agent_factory = agent_factory or AgentFactory(
            store_backend=self._settings.store_backend,
            db_path=self._settings.runtime_db_path,
        )
        self._agent = self._agent_factory.create_chat_agent(settings=self._settings)
        self._session_store = self._agent_factory.get_session_store()
        self._transcript_store = self._agent_factory.get_transcript_store()
        self._task_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="chat-task")
        self._task_lock = Lock()
        self._tasks: dict[str, ChatTaskRecord] = {}
        self._task_futures: dict[str, Future[None]] = {}

    def chat(
        self, message: str, session_id: str | None = None, task_id: str | None = None
    ) -> tuple[AgentOutput, str]:
        resolved_session_id = ensure_session_id(session_id=session_id)
        metadata: dict[str, Any] = {}
        if task_id:
            metadata["task_id"] = task_id
        agent_input = AgentInput(
            message=message, session_id=resolved_session_id, metadata=metadata
        )
        agent_output = self._agent.run(agent_input)
        return agent_output, resolved_session_id

    def build_chat_payload(self, agent_output: AgentOutput, session_id: str) -> dict[str, Any]:
        runtime_snapshot = None
        meta = agent_output.metadata or {}
        rs = meta.get("runtime_session")
        if rs is not None:
            snap = RuntimeSessionSnapshot.from_runtime_session(rs)
            if hasattr(snap, "model_dump"):
                runtime_snapshot = snap.model_dump()
            else:
                runtime_snapshot = snap.dict()
        return {
            "reply": agent_output.content if agent_output.success else (agent_output.error_message or ""),
            "session_id": session_id,
            "timestamp": _utc_iso_now(),
            "runtime_session": runtime_snapshot,
            "success": agent_output.success,
            "error_message": agent_output.error_message,
        }

    def _append_task_log(self, task_id: str, message: str) -> None:
        with self._task_lock:
            task = self._tasks.get(task_id)
            if task is None:
                return
            task.logs.append(f"{_utc_iso_now()} {message}")
            task.updated_at = _utc_iso_now()

    def submit_chat_task(self, message: str, session_id: str | None = None) -> dict[str, Any]:
        task_id = str(uuid4())
        now = _utc_iso_now()
        record = ChatTaskRecord(
            task_id=task_id,
            message=message,
            session_id=session_id,
            status="pending",
            created_at=now,
            updated_at=now,
            logs=[f"{now} task created"],
        )
        with self._task_lock:
            self._tasks[task_id] = record

        def _runner() -> None:
            with self._task_lock:
                task = self._tasks[task_id]
                task.status = "running"
                task.started_at = _utc_iso_now()
                task.updated_at = task.started_at
                task.logs.append(f"{task.started_at} task started")
            try:
                output, resolved_session_id = self.chat(
                    message=message, session_id=session_id, task_id=task_id
                )
                payload = self.build_chat_payload(output, resolved_session_id)
                with self._task_lock:
                    task = self._tasks[task_id]
                    if task.status == "cancelling":
                        task.status = "cancelled"
                        task.logs.append(f"{_utc_iso_now()} task cancelled while running")
                    else:
                        task.status = "succeeded" if output.success else "failed"
                    task.result = payload
                    task.session_id = resolved_session_id
                    task.finished_at = _utc_iso_now()
                    task.updated_at = task.finished_at
                    task.error_message = output.error_message
                    task.logs.append(f"{task.finished_at} task finished with status={task.status}")
            except Exception as e:  # pragma: no cover
                with self._task_lock:
                    task = self._tasks[task_id]
                    task.status = "failed"
                    task.error_message = str(e)
                    task.finished_at = _utc_iso_now()
                    task.updated_at = task.finished_at
                    task.logs.append(f"{task.finished_at} task failed: {e}")

        future = self._task_pool.submit(_runner)
        with self._task_lock:
            self._task_futures[task_id] = future
        return {"task_id": task_id, "status": "pending", "created_at": now, "session_id": session_id}

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._task_lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            return {
                "task_id": task.task_id,
                "status": task.status,
                "message": task.message,
                "session_id": task.session_id,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "started_at": task.started_at,
                "finished_at": task.finished_at,
                "error_message": task.error_message,
                "result": task.result,
            }

    def get_task_logs(self, task_id: str) -> dict[str, Any] | None:
        with self._task_lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            return {
                "task_id": task.task_id,
                "status": task.status,
                "logs": list(task.logs),
            }

    def get_task_transcript(self, task_id: str) -> list[TranscriptEntryResponse] | None:
        with self._task_lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            session_id = task.session_id
        if not session_id:
            return []
        return self.get_transcript(session_id)

    def cancel_task(self, task_id: str) -> dict[str, Any] | None:
        with self._task_lock:
            task = self._tasks.get(task_id)
            future = self._task_futures.get(task_id)
            if task is None or future is None:
                return None
            if task.status in ("succeeded", "failed", "cancelled"):
                return {"task_id": task_id, "status": task.status, "cancelled": False}
            if future.cancel():
                task.status = "cancelled"
                task.finished_at = _utc_iso_now()
                task.updated_at = task.finished_at
                task.logs.append(f"{task.finished_at} task cancelled before start")
                return {"task_id": task_id, "status": task.status, "cancelled": True}
            task.status = "cancelling"
            task.updated_at = _utc_iso_now()
            task.logs.append(f"{task.updated_at} cancel requested (running)")
            return {"task_id": task_id, "status": task.status, "cancelled": True}

    def list_sessions(self) -> list[SessionResponse]:
        sessions = self._session_store.list_sessions()
        return [SessionResponse.from_session_dict(session) for session in sessions]

    def get_transcript(self, session_id: str) -> list[TranscriptEntryResponse]:
        if not session_id:
            return []
        entries = self._transcript_store.get_entries(session_id)
        return [
            TranscriptEntryResponse.from_transcript_entry(entry) for entry in entries
        ]

    def diff_transcript(
        self,
        session_id: str,
        base_index: int,
        compare_index: int,
    ) -> dict[str, Any]:
        from app.eval.diff import diff_runtime_snapshots

        entries = self.get_transcript(session_id)
        if not entries:
            raise ValueError("transcript 为空")
        if base_index < 0 or base_index >= len(entries):
            raise ValueError(f"base_index 越界: {base_index}")
        if compare_index < 0 or compare_index >= len(entries):
            raise ValueError(f"compare_index 越界: {compare_index}")

        base_entry = entries[base_index]
        compare_entry = entries[compare_index]
        diff = diff_runtime_snapshots(
            base_entry.runtime_session,
            compare_entry.runtime_session,
            base_label=f"index:{base_index}",
            compare_label=f"index:{compare_index}",
        )
        return {
            "session_id": session_id,
            "base_index": base_index,
            "compare_index": compare_index,
            "base_timestamp": base_entry.timestamp,
            "compare_timestamp": compare_entry.timestamp,
            "changed": diff.changed,
            "items": [item.to_dict() for item in diff.items],
        }

settings = Settings.from_env()
chat_service = ChatService(settings=settings)
