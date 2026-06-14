from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelRequest:
    """模型统一输入对象。

    - ``prompt``：兼容旧路径（单轮字符串）
    - ``messages``：Chat Completions 原生多轮消息
    - ``tools``：OpenAI function tools schema
    """

    prompt: str = ""
    messages: list[dict[str, Any]] = field(default_factory=list)
    system: str | None = None
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | None = "auto"
    temperature: float | None = None
    response_format: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def effective_messages(self) -> list[dict[str, Any]]:
        if self.messages:
            payload = list(self.messages)
        elif self.prompt.strip():
            payload = [{"role": "user", "content": self.prompt.strip()}]
        else:
            payload = []

        if self.system and not any(message.get("role") == "system" for message in payload):
            return [{"role": "system", "content": self.system}, *payload]
        return payload

    def has_content(self) -> bool:
        return bool(self.effective_messages())
