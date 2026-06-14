"""CLI 用的最小 HTTP 客户端（标准库 urllib，无额外依赖）。"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


def default_api_base() -> str:
    return os.environ.get(
        "LEARNCHAIN_API_BASE", "http://127.0.0.1:8000/agent_api"
    )


def resolve_origin(api_base: str, origin_override: str | None) -> str:
    if origin_override:
        return origin_override.rstrip("/")
    env_origin = os.environ.get("LEARNCHAIN_ORIGIN")
    if env_origin:
        return env_origin.rstrip("/")
    b = api_base.rstrip("/")
    if b.endswith("/agent_api"):
        root = b[: -len("/agent_api")]
        return root.rstrip("/") if root else "http://127.0.0.1:8000"
    return "http://127.0.0.1:8000"


@dataclass(frozen=True)
class ApiContext:
    api_base: str
    origin: str


def get_json(url: str, *, timeout: float = 60.0) -> Any:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8")
            detail: Any = json.loads(err_body)
        except json.JSONDecodeError:
            detail = err_body or str(e)
        raise SystemExit(f"HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise SystemExit(f"请求失败 {url}：{e.reason}") from e


def post_json(url: str, payload: dict[str, Any], *, timeout: float = 600.0) -> Any:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8")
            detail: Any = json.loads(err_body)
        except json.JSONDecodeError:
            detail = err_body or str(e)
        raise SystemExit(f"HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise SystemExit(
            f"无法连接 {url}：{e.reason}\n"
            "请先在本机启动后端（例如 uvicorn app.main:app --port 8000）。"
        ) from e
