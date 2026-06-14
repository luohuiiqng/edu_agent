from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.runtime_snapshot import RuntimeSessionSnapshot


class ChatRequest(BaseModel):
    message: str = Field(..., description="User input text")
    session_id: Optional[str] = Field(default=None, description="Conversation session id")


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    timestamp: datetime
    # 本轮完整运行态（含 collaboration_trace / deliverables），无则省略
    runtime_session: Optional[RuntimeSessionSnapshot] = None


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
