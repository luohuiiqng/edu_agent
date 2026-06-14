from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelResponse:
    """模型统一回复对象"""

    content: str | None = None
    success: bool = True
    error_message: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)
