"""Planner 可用的会话上下文（与 Memory 解耦，便于单测）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlanContext:
    recent_user_messages: list[str] = field(default_factory=list)

    @classmethod
    def from_memory_messages(
        cls,
        messages: list[dict[str, Any]],
        *,
        limit: int = 6,
    ) -> PlanContext:
        user_msgs = [
            str(message.get("content", "")).strip()
            for message in messages
            if message.get("role") == "user" and str(message.get("content", "")).strip()
        ]
        return cls(recent_user_messages=user_msgs[-limit:])

    def combined_user_text(self, current_message: str) -> str:
        current = str(current_message).strip()
        prior = [message for message in self.recent_user_messages if message.strip()]
        if prior and prior[-1] == current:
            prior = prior[:-1]
        if not prior:
            return current
        return "\n".join(prior + [current])

    @property
    def has_prior_turns(self) -> bool:
        return len(self.recent_user_messages) > 0
