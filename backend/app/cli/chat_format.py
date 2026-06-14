"""chat 响应的人类可读格式化（与 API 字段对齐）。"""

from __future__ import annotations

import json
import sys
from typing import Any


def print_human_chat_summary(data: dict[str, Any], *, quiet: bool) -> None:
    reply = data.get("reply", "")
    if quiet:
        print(reply)
        return

    print("=== 回复 ===")
    print(reply)
    print()
    print("=== 会话 ID ===")
    print(data.get("session_id", ""))
    ts = data.get("timestamp")
    if ts:
        print(f"时间: {ts}")

    rs = data.get("runtime_session")
    if not rs:
        print()
        print("(本轮无 runtime_session，可能为旧后端或未返回快照)")
        return

    print()
    wt = rs.get("workflow_trace") or []
    print(f"=== Workflow 轨迹 ({len(wt)} 条) ===")
    for i, row in enumerate(wt, 1):
        step = row.get("step_name", "?")
        action = row.get("action", "?")
        role = row.get("agent_role")
        ok = row.get("success")
        line = f"  {i}. [{action}] {step}"
        if role:
            line += f"  @{role}"
        if row.get("parallel_fan_out"):
            line += "  [并行扇出]"
        line += f"  ok={ok}"
        print(line)

    wr = rs.get("workflow_result") or {}
    rc = wr.get("runner_class")
    if rc:
        print()
        print(f"工作流引擎: {rc}")

    collab = rs.get("collaboration_trace") or []
    if collab:
        print()
        print(f"=== 协作轨迹 ({len(collab)} 条) ===")
        for i, ev in enumerate(collab, 1):
            role = ev.get("agent_role", "?")
            summ = str(ev.get("summary", ""))[:300]
            print(f"  {i}. {role}: {summ}")

    dels = rs.get("deliverables") or []
    if dels:
        print()
        print(f"=== 成果交付 ({len(dels)} 条) ===")
        for i, d in enumerate(dels, 1):
            kind = d.get("kind", "?")
            title = d.get("title", "")
            uri = d.get("uri", "")
            print(f"  {i}. [{kind}] {title}")
            if uri:
                print(f"      {uri}")

    errs = rs.get("errors") or []
    if errs:
        print()
        print("=== 错误 ===")
        for e in errs:
            print(f"  - {e}")


def read_message_arg(message: str | None, message_flag: str | None) -> str:
    text = message or message_flag
    if not text:
        text = sys.stdin.readline()
    return (text or "").strip()
