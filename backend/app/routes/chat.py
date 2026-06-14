from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from app.schemas.agent_output import AgentOutput
from app.schemas.chat_input_output import ChatRequest, ChatResponse
from app.schemas.runtime_snapshot import RuntimeSessionSnapshot
from app.schemas.task_input_output import (
    TaskCancelResponse,
    TaskLogsResponse,
    TaskStatusResponse,
    TaskSubmitRequest,
    TaskSubmitResponse,
)
from app.services.chat_service import chat_service
from app.schemas.transcript_response import TranscriptEntryResponse
from app.schemas.session_response import SessionResponse



router = APIRouter(tags=["chat"])


def _runtime_snapshot_from_output(agent_output: AgentOutput) -> RuntimeSessionSnapshot | None:
    meta = agent_output.metadata or {}
    rs = meta.get("runtime_session")
    if rs is None:
        return None
    return RuntimeSessionSnapshot.from_runtime_session(rs)


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    # Strip once and reuse to keep backend/frontend validation behavior aligned.
    message = payload.message.strip()
    if not message:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "BAD_REQUEST", "message": "message不能为空"}},
        )
    if len(message) > 2000:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "BAD_REQUEST", "message": "message长度不能超过2000"}},
        )
    agent_output, session_id = chat_service.chat(
        message=message, session_id=payload.session_id
    )
    if hasattr(chat_service, "build_chat_payload"):
        payload_dict = chat_service.build_chat_payload(agent_output, session_id)
        payload_dict.pop("success", None)
        payload_dict.pop("error_message", None)
        return ChatResponse(**payload_dict)
    snapshot = _runtime_snapshot_from_output(agent_output)
    if not agent_output.success:
        return ChatResponse(
            reply=agent_output.error_message or "",
            session_id=session_id,
            timestamp=datetime.now(timezone.utc),
            runtime_session=snapshot,
        )
    return ChatResponse(
        reply=agent_output.content,
        session_id=session_id,
        timestamp=datetime.now(timezone.utc),
        runtime_session=snapshot,
    )

@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions() -> list[SessionResponse]:
    return chat_service.list_sessions()


@router.get(
    "/sessions/{session_id}/transcript", response_model=list[TranscriptEntryResponse]
)
def get_session_transcript(session_id: str) -> list[TranscriptEntryResponse]:
    return chat_service.get_transcript(session_id=session_id)


@router.post("/tasks", response_model=TaskSubmitResponse)
def submit_task(payload: TaskSubmitRequest) -> TaskSubmitResponse:
    message = payload.message.strip()
    if not message:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "BAD_REQUEST", "message": "message不能为空"}},
        )
    if len(message) > 2000:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "BAD_REQUEST", "message": "message长度不能超过2000"}},
        )
    task = chat_service.submit_chat_task(message=message, session_id=payload.session_id)
    return TaskSubmitResponse(**task)


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str) -> TaskStatusResponse:
    task = chat_service.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "task不存在"}},
        )
    return TaskStatusResponse(**task)


@router.get("/tasks/{task_id}/logs", response_model=TaskLogsResponse)
def get_task_logs(task_id: str) -> TaskLogsResponse:
    payload = chat_service.get_task_logs(task_id)
    if payload is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "task不存在"}},
        )
    return TaskLogsResponse(**payload)


@router.post("/tasks/{task_id}/cancel", response_model=TaskCancelResponse)
def cancel_task(task_id: str) -> TaskCancelResponse:
    payload = chat_service.cancel_task(task_id)
    if payload is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "task不存在"}},
        )
    return TaskCancelResponse(**payload)


@router.get(
    "/tasks/{task_id}/transcript", response_model=list[TranscriptEntryResponse]
)
def get_task_transcript(task_id: str) -> list[TranscriptEntryResponse]:
    entries = chat_service.get_task_transcript(task_id)
    if entries is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "task不存在"}},
        )
    return entries

