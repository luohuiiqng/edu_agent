"""多代理协作与成果交付 — 稳定字段名，便于 transcript / API 与后续多进程扩展。"""

from __future__ import annotations

from typing import Any, Literal

# 用户可见「成果」类型（后续可接语音合成、文生图、ffmpeg、脚手架仓库等）
ArtifactKind = Literal[
    "text",
    "audio",
    "image",
    "video",
    "web_project",
    "other",
]


def deliverable_dict(
    kind: ArtifactKind,
    *,
    title: str = "",
    uri: str = "",
    summary: str = "",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """构造写入 ``RuntimeSession.deliverables`` 的一条记录。"""
    return {
        "kind": kind,
        "title": title,
        "uri": uri,
        "summary": summary,
        "meta": meta or {},
    }
