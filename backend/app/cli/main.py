"""edu_agent CLI：chat / health / sessions / transcript / task。"""

from __future__ import annotations

import argparse
import json
import time
import sys
from typing import Any

from app.cli.chat_format import print_human_chat_summary, read_message_arg
from app.cli.http_api import (
    ApiContext,
    default_api_base,
    get_json,
    post_json,
    resolve_origin,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lcp",
        description="edu_agent 终端客户端（需先启动后端 HTTP API）",
    )
    parser.add_argument(
        "--base-url",
        default=default_api_base(),
        help="Agent API 前缀，默认 http://127.0.0.1:8000/agent_api；可用环境变量 LEARNCHAIN_API_BASE",
    )
    parser.add_argument(
        "--origin",
        default=None,
        help="服务根 URL（用于 /health），默认由 --base-url 推导或 LEARNCHAIN_ORIGIN",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_chat = sub.add_parser("chat", help="发送一条聊天消息（默认打印可读摘要）")
    p_chat.add_argument(
        "message",
        nargs="?",
        help="用户消息（可省略则从标准输入读一行）",
    )
    p_chat.add_argument(
        "-m",
        "--message-opt",
        dest="message_flag",
        help="与位置参数二选一",
    )
    p_chat.add_argument("--session-id", default=None, help="延续同一会话")
    p_chat.add_argument(
        "--json",
        action="store_true",
        help="只输出原始 JSON",
    )
    p_chat.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="只打印助手回复正文",
    )

    sub.add_parser("health", help="GET /health，检查服务是否存活")

    sub.add_parser("sessions", help="列出会话列表 GET /agent_api/sessions")

    p_tr = sub.add_parser(
        "transcript",
        help="拉取某会话的 transcript GET /agent_api/sessions/<id>/transcript",
    )
    p_tr.add_argument("session_id", help="会话 ID")

    p_tr.add_argument(
        "--json",
        action="store_true",
        help="原始 JSON 输出",
    )

    p_task = sub.add_parser("task", help="异步任务相关操作")
    task_sub = p_task.add_subparsers(dest="task_command", required=True)

    p_task_submit = task_sub.add_parser("submit", help="提交异步聊天任务")
    p_task_submit.add_argument("message", nargs="?", help="任务消息")
    p_task_submit.add_argument("-m", "--message-opt", dest="message_flag", help="与位置参数二选一")
    p_task_submit.add_argument("--session-id", default=None, help="延续会话")
    p_task_submit.add_argument("--json", action="store_true", help="原始 JSON 输出")
    p_task_submit.add_argument("--wait", action="store_true", help="提交后等待任务结束")
    p_task_submit.add_argument("--poll-interval", type=float, default=1.0, help="轮询间隔秒")
    p_task_submit.add_argument("--timeout", type=float, default=600.0, help="最长等待秒")

    p_task_status = task_sub.add_parser("status", help="查看任务状态")
    p_task_status.add_argument("task_id")
    p_task_status.add_argument("--json", action="store_true", help="原始 JSON 输出")

    p_task_logs = task_sub.add_parser("logs", help="查看任务日志")
    p_task_logs.add_argument("task_id")
    p_task_logs.add_argument("--json", action="store_true", help="原始 JSON 输出")

    p_task_cancel = task_sub.add_parser("cancel", help="取消任务")
    p_task_cancel.add_argument("task_id")
    p_task_cancel.add_argument("--json", action="store_true", help="原始 JSON 输出")

    p_task_transcript = task_sub.add_parser("transcript", help="按任务查看 transcript")
    p_task_transcript.add_argument("task_id")
    p_task_transcript.add_argument("--json", action="store_true", help="原始 JSON 输出")

    return parser


def _ctx(ns: argparse.Namespace) -> ApiContext:
    api_base = ns.base_url
    origin = resolve_origin(api_base, getattr(ns, "origin", None))
    return ApiContext(api_base=api_base, origin=origin)


def cmd_chat(ns: argparse.Namespace) -> None:
    ctx = _ctx(ns)
    text = read_message_arg(ns.message, ns.message_flag)
    if not text:
        raise SystemExit("消息不能为空")
    url = ctx.api_base.rstrip("/") + "/chat"
    payload: dict[str, Any] = {"message": text}
    if ns.session_id:
        payload["session_id"] = ns.session_id
    data = post_json(url, payload)
    if ns.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print_human_chat_summary(data, quiet=ns.quiet)


def cmd_health(ns: argparse.Namespace) -> None:
    ctx = _ctx(ns)
    url = ctx.origin.rstrip("/") + "/health"
    data = get_json(url)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_sessions(ns: argparse.Namespace) -> None:
    ctx = _ctx(ns)
    url = ctx.api_base.rstrip("/") + "/sessions"
    data = get_json(url)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_transcript(ns: argparse.Namespace) -> None:
    ctx = _ctx(ns)
    sid = ns.session_id.strip()
    url = ctx.api_base.rstrip("/") + f"/sessions/{sid}/transcript"
    data = get_json(url)
    if ns.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    entries = data if isinstance(data, list) else []
    print(f"会话 {sid} — 共 {len(entries)} 条 transcript")
    for i, entry in enumerate(entries, 1):
        et = entry.get("type", "?")
        ui = str(entry.get("user_input", ""))[:120]
        fo = entry.get("final_output")
        ok = entry.get("success")
        ts = entry.get("timestamp", "")
        print(f"\n--- {i}. [{et}] {ts} ok={ok} ---")
        print(f"用户: {ui}")
        if fo is not None:
            out_preview = str(fo)[:500]
            print(f"助手: {out_preview}{'…' if len(str(fo)) > 500 else ''}")


def _task_url(ctx: ApiContext, suffix: str = "") -> str:
    return ctx.api_base.rstrip("/") + "/tasks" + suffix


def cmd_task_submit(ns: argparse.Namespace) -> None:
    ctx = _ctx(ns)
    text = read_message_arg(ns.message, ns.message_flag)
    if not text:
        raise SystemExit("消息不能为空")
    payload: dict[str, Any] = {"message": text}
    if ns.session_id:
        payload["session_id"] = ns.session_id
    data = post_json(_task_url(ctx), payload)
    if ns.json and not ns.wait:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    task_id = str(data.get("task_id", ""))
    print(f"任务已提交: {task_id} status={data.get('status')}")
    if not ns.wait:
        return
    deadline = time.time() + ns.timeout
    terminal = {"succeeded", "failed", "cancelled"}
    while True:
        status_payload = get_json(_task_url(ctx, f"/{task_id}"))
        status = str(status_payload.get("status", "unknown"))
        if status in terminal:
            if ns.json:
                print(json.dumps(status_payload, ensure_ascii=False, indent=2))
                return
            print(f"任务结束: {task_id} status={status}")
            result = status_payload.get("result")
            if isinstance(result, dict):
                print_human_chat_summary(result, quiet=False)
            elif status_payload.get("error_message"):
                print(f"错误: {status_payload.get('error_message')}")
            return
        if time.time() >= deadline:
            raise SystemExit(f"等待超时: task_id={task_id} status={status}")
        time.sleep(max(ns.poll_interval, 0.1))


def cmd_task_status(ns: argparse.Namespace) -> None:
    ctx = _ctx(ns)
    data = get_json(_task_url(ctx, f"/{ns.task_id}"))
    if ns.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print(
        f"task_id={data.get('task_id')} status={data.get('status')} "
        f"created={data.get('created_at')} updated={data.get('updated_at')}"
    )
    if data.get("error_message"):
        print(f"error={data.get('error_message')}")


def cmd_task_logs(ns: argparse.Namespace) -> None:
    ctx = _ctx(ns)
    data = get_json(_task_url(ctx, f"/{ns.task_id}/logs"))
    if ns.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print(f"task_id={data.get('task_id')} status={data.get('status')}")
    for row in data.get("logs", []):
        print(f"- {row}")


def cmd_task_cancel(ns: argparse.Namespace) -> None:
    ctx = _ctx(ns)
    data = post_json(_task_url(ctx, f"/{ns.task_id}/cancel"), {})
    if ns.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print(
        f"task_id={data.get('task_id')} status={data.get('status')} "
        f"cancelled={data.get('cancelled')}"
    )


def cmd_task_transcript(ns: argparse.Namespace) -> None:
    ctx = _ctx(ns)
    data = get_json(_task_url(ctx, f"/{ns.task_id}/transcript"))
    if ns.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    entries = data if isinstance(data, list) else []
    print(f"task_id={ns.task_id} transcript entries={len(entries)}")
    for i, entry in enumerate(entries, 1):
        ts = entry.get("timestamp", "")
        ui = str(entry.get("user_input", ""))[:120]
        fo = entry.get("final_output")
        print(f"\n--- {i}. {ts} ---")
        print(f"用户: {ui}")
        if fo is not None:
            out_preview = str(fo)[:500]
            print(f"助手: {out_preview}{'…' if len(str(fo)) > 500 else ''}")


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    ns = parser.parse_args(argv)

    if ns.command == "chat":
        cmd_chat(ns)
    elif ns.command == "health":
        cmd_health(ns)
    elif ns.command == "sessions":
        cmd_sessions(ns)
    elif ns.command == "transcript":
        cmd_transcript(ns)
    elif ns.command == "task":
        if ns.task_command == "submit":
            cmd_task_submit(ns)
        elif ns.task_command == "status":
            cmd_task_status(ns)
        elif ns.task_command == "logs":
            cmd_task_logs(ns)
        elif ns.task_command == "cancel":
            cmd_task_cancel(ns)
        elif ns.task_command == "transcript":
            cmd_task_transcript(ns)
        else:
            parser.error(f"未知 task 子命令: {ns.task_command}")
    else:
        parser.error(f"未知子命令: {ns.command}")


if __name__ == "__main__":
    main()
