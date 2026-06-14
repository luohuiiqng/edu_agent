from __future__ import annotations

import json
from typing import Any

from app.schemas.tool_input import ToolInput
from app.tools.base_tool import BaseTool
from app.tools.tool_registry import ToolRegistry


def build_openai_tool_schemas(registry: ToolRegistry) -> list[dict[str, Any]]:
    """将 ToolRegistry 转为 OpenAI Chat Completions ``tools`` 参数。"""
    schemas: list[dict[str, Any]] = []
    for name in registry.list_tools():
        tool = registry.get_tool(name)
        if tool is None:
            continue
        info = tool.get_tool_info()
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": info.get("name", name),
                    "description": info.get("description") or f"Tool {name}",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": True,
                    },
                },
            }
        )
    return schemas


def parse_tool_arguments(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    text = str(raw).strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def run_tool_call(
    registry: ToolRegistry,
    tool_call: dict[str, Any],
) -> tuple[str, Any, bool, str | None, dict[str, Any] | None]:
    """执行单次 model 发起的 tool_call，返回 (name, content, success, error, metadata)。"""
    tool_name = str(tool_call.get("name") or "")
    tool = registry.get_tool(tool_name)
    if tool is None:
        return tool_name, "", False, f"tool not found: {tool_name}", None
    params = parse_tool_arguments(tool_call.get("arguments"))
    output = tool.run(ToolInput(params=params))
    return (
        tool_name,
        output.content or "",
        output.success,
        output.error_message,
        output.metadata,
    )
