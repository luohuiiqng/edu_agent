"""工作流步骤展开 — 支持 ``{"parallel": [...]}`` 嵌套结构。"""

from __future__ import annotations

from typing import Any


def flatten_steps_for_trace(steps: list[Any]) -> list[dict[str, Any]]:
    """将规划中的步骤列表展平为单个步骤字典列表，供轨迹 / transcript 关联。"""
    out: list[dict[str, Any]] = []
    for item in steps:
        if isinstance(item, dict) and "parallel" in item:
            subs = item.get("parallel")
            if isinstance(subs, list):
                for s in subs:
                    if isinstance(s, dict):
                        out.append(s)
        elif isinstance(item, dict):
            out.append(item)
    return out
