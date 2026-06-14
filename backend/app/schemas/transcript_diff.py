from typing import Any

from pydantic import BaseModel


class DiffItemResponse(BaseModel):
    field: str
    base: Any
    compare: Any
    changed: bool


class TranscriptDiffResponse(BaseModel):
    session_id: str
    base_index: int
    compare_index: int
    base_timestamp: str
    compare_timestamp: str
    changed: bool
    items: list[DiffItemResponse]
