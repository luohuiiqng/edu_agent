from typing import Any
from app.prompts.base_prompt import BasePrompt

DEFAULT_AGENT_SYSTEM_PROMPT = (
    "你是 edu_agent 的运行时助手。"
    "当用户需要当前时间、日期或本地 ffmpeg 演示样例时，优先调用可用工具；"
    "其余问题用简洁中文直接回答。"
)


class PromptBuilder(BasePrompt):
    def __init__(self, system_prompt: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._system_prompt = system_prompt or DEFAULT_AGENT_SYSTEM_PROMPT

    def get_system_prompt(self) -> str:
        return self._system_prompt

    def format_history(self, messages: list[dict[str, Any]]) -> str:
        if not messages:
            return ""

        lines = []
        for message in messages:
            role = message.get("role", "unknown")
            content = message.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def build_chat_messages(
        self,
        messages: list[dict[str, Any]],
        *,
        current_input: str | None = None,
    ) -> list[dict[str, str]]:
        """将 Memory 消息转为 Chat Completions ``messages``（不含 system）。"""
        chat_messages: list[dict[str, str]] = []
        for message in messages:
            role = str(message.get("role") or "user")
            if role not in ("user", "assistant", "system"):
                role = "user"
            content = str(message.get("content") or "")
            if content:
                chat_messages.append({"role": role, "content": content})

        if current_input and current_input.strip():
            if not chat_messages or chat_messages[-1].get("content") != current_input.strip():
                chat_messages.append({"role": "user", "content": current_input.strip()})

        return chat_messages

    def build_prompt(
            self,
            messages: list[dict[str, Any]],
            current_input: str | None = None,
    ) -> str:
        """兼容旧路径：仍可用单字符串 prompt。"""
        history_str = self.format_history(messages)
        if history_str and current_input:
            return f"这是与你的用户的对话历史:\n{history_str}\n用户的输入是:\n{current_input}\n你的任务是根据用户的输入生成合适的回复。"
        elif history_str:
            return f"这是与你的用户的对话历史:\n{history_str}\n你的任务是根据用户的输入生成合适的回复。"
        elif current_input:
            return f"用户的输入是:\n{current_input}\n你的任务是根据用户的输入生成合适的回复。"
        else:
            return "你的任务是根据用户的输入生成合适的回复。"