from typing import Any
import json

from app.models.base_model import BaseModel
from app.schemas.model_request import ModelRequest
from app.schemas.model_response import ModelResponse


class MockModel(BaseModel):
    def __init__(
        self,
        model_name: str = "mock-model",
        response_text: str = "mock response",
        prefix: str = "",
        should_fail: bool = False,
        fail_message: str = "mock model failure",
        simulate_tool_calls: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(model_name, api_key="", **kwargs)
        self._response_text = response_text
        self._prefix = prefix
        self._should_fail = should_fail
        self._fail_message = fail_message
        self._simulate_tool_calls = simulate_tool_calls
        self._call_count = 0
        self._last_input: ModelRequest | None = None

    def generate(self, input_data: ModelRequest, **kwargs: Any) -> ModelResponse:
        self._call_count += 1
        self._last_input = input_data

        if self._should_fail:
            return ModelResponse(
                content="",
                success=False,
                error_message=self._fail_message,
            )

        if input_data.metadata.get("mode") == "planning":
            return ModelResponse(
                content=json.dumps(self._planning_decision(input_data), ensure_ascii=False),
                success=True,
            )

        if self._simulate_tool_calls and input_data.tools:
            if not any(
                message.get("role") == "tool"
                for message in input_data.effective_messages()
            ):
                last_user = self._last_user_text(input_data)
                if any(
                    keyword in last_user
                    for keyword in ("时间", "几点", "ffmpeg", "视频样例")
                ):
                    tool_name = (
                        "ffmpeg_artifact_tool"
                        if any(k in last_user for k in ("ffmpeg", "视频样例"))
                        else "time_tool"
                    )
                    if self._tool_available(input_data, tool_name):
                        return ModelResponse(
                            content=None,
                            success=True,
                            tool_calls=[
                                {
                                    "id": "mock-call-1",
                                    "name": tool_name,
                                    "arguments": "{}",
                                }
                            ],
                        )

        prompt = input_data.prompt.strip()
        if not prompt and input_data.messages:
            prompt = self._last_user_text(input_data)

        if self._prefix:
            return ModelResponse(content=f"{self._prefix}:{prompt}")

        return ModelResponse(content=f"{self._response_text}:{prompt}")

    @staticmethod
    def _planning_decision(input_data: ModelRequest) -> dict[str, Any]:
        text = str(input_data.metadata.get("current_message") or "").strip()
        if not text:
            text = MockModel._last_user_text(input_data)
        if all(keyword in text for keyword in ("基建", "业务", "数据")):
            return {
                "action": "workflow",
                "workflow_name": "parallel_pillar_workflow",
                "reason": "mock planner: 三线并行",
            }
        if any(keyword in text for keyword in ("时间", "几点")) and any(
            keyword in text for keyword in ("回复", "一句")
        ):
            return {
                "action": "workflow",
                "workflow_name": "time_reply_workflow",
                "reason": "mock planner: 时间+回复",
            }
        if any(keyword in text for keyword in ("时间", "几点")):
            return {
                "action": "tool",
                "tool_name": "time_tool",
                "reason": "mock planner: 查询时间",
            }
        if any(keyword in text for keyword in ("研究", "课题", "调研")):
            return {
                "action": "workflow",
                "workflow_name": "research_team_workflow",
                "reason": "mock planner: 研究类任务",
            }
        return {"action": "model", "reason": "mock planner: 直接回复"}

    @staticmethod
    def _last_user_text(input_data: ModelRequest) -> str:
        for message in reversed(input_data.effective_messages()):
            if message.get("role") == "user":
                return str(message.get("content") or "")
        return input_data.prompt

    @staticmethod
    def _tool_available(input_data: ModelRequest, tool_name: str) -> bool:
        if not input_data.tools:
            return False
        for tool in input_data.tools:
            function = tool.get("function") or {}
            if function.get("name") == tool_name:
                return True
        return False

    def get_mock_status(self) -> dict[str, Any]:
        return {
            "call_count": self._call_count,
            "last_input": self._last_input,
        }
