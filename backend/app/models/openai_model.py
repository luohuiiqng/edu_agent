from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.models.base_model import BaseModel
from app.schemas.model_request import ModelRequest
from app.schemas.model_response import ModelResponse


class OpenAIModel(BaseModel):
    def __init__(
        self,
        model_name: str,
        api_key: str,
        base_url: str | None = None,
        organization: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model_name=model_name, api_key=api_key, **kwargs)
        self._base_url = base_url
        self._organization = organization
        self._client = OpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            organization=self._organization,
        )

    def validate_config(self) -> None:
        super().validate_config()
        if not self._api_key:
            raise ValueError("api_key is empty")

    def generate(self, input_data: ModelRequest, **kwargs: Any) -> ModelResponse:
        messages = input_data.effective_messages()
        if not messages:
            return ModelResponse(
                content=None,
                success=False,
                error_message="messages 或 prompt 不能为空",
                metadata={"model_name": self._model_name},
            )
        try:
            params: dict[str, Any] = {
                "model": self._model_name,
                "messages": messages,
            }
            if input_data.tools:
                params["tools"] = input_data.tools
                if input_data.tool_choice:
                    params["tool_choice"] = input_data.tool_choice
            if input_data.temperature is not None:
                params["temperature"] = input_data.temperature
            if input_data.response_format:
                params["response_format"] = input_data.response_format

            response = self._client.chat.completions.create(**params)
            message = response.choices[0].message
            tool_calls = self._parse_tool_calls(message.tool_calls)
            content = message.content or ""
            return ModelResponse(
                content=content if content else None,
                success=True,
                tool_calls=tool_calls,
                metadata={
                    "model_name": self._model_name,
                    "finish_reason": response.choices[0].finish_reason,
                },
            )
        except Exception as exc:
            return ModelResponse(
                content=None,
                success=False,
                error_message=str(exc),
                metadata={"model_name": self._model_name},
            )

    @staticmethod
    def _parse_tool_calls(raw_calls: Any) -> list[dict[str, Any]]:
        if not raw_calls:
            return []
        parsed: list[dict[str, Any]] = []
        for call in raw_calls:
            function = getattr(call, "function", None)
            name = getattr(function, "name", "") if function else ""
            arguments = getattr(function, "arguments", "") if function else ""
            parsed.append(
                {
                    "id": getattr(call, "id", ""),
                    "name": name,
                    "arguments": arguments,
                }
            )
        return parsed
