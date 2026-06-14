from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.chat_input_output import ChatResponse


class TaskSubmitRequest(BaseModel):
    message: str = Field(..., description="Task message")
    session_id: Optional[str] = Field(default=None, description="Conversation session id")


class TaskSubmitResponse(BaseModel):
    task_id: str
    status: str
    created_at: str
    session_id: Optional[str] = None


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    message: str
    session_id: Optional[str] = None
    created_at: str
    updated_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error_message: Optional[str] = None
    result: Optional[ChatResponse] = None


class TaskLogsResponse(BaseModel):
    task_id: str
    status: str
    logs: list[str]


class TaskCancelResponse(BaseModel):
    task_id: str
    status: str
    cancelled: bool

