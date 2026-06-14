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

    p_tr_diff = sub.add_parser(
        "diff",
        help="对比同一会话 transcript 中两次运行的 runtime 快照",
    )
    p_tr_diff.add_argument("session_id", help="会话 ID")
    p_tr_diff.add_argument("--base", type=int, default=0, help="基准条目索引（默认 0）")
    p_tr_diff.add_argument("--compare", type=int, default=1, help="对比条目索引（默认 1）")
    p_tr_diff.add_argument("--json", action="store_true", help="原始 JSON 输出")

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

    p_exp = sub.add_parser("experiment", help="内置 Agent 实验（本地 in-process + 规则 Eval）")
    exp_sub = p_exp.add_subparsers(dest="exp_command", required=True)
    p_exp_list = exp_sub.add_parser("list", help="列出 manifest 中的实验")
    p_exp_list.add_argument("--json", action="store_true", help="原始 JSON 输出")
    p_exp_run = exp_sub.add_parser("run", help="运行指定实验并输出 Eval 结果")
    p_exp_run.add_argument("experiment_id", help="实验 ID，如 exp_001_time_tool")
    p_exp_run.add_argument("--json", action="store_true", help="原始 JSON 输出")
    p_exp_run.add_argument(
        "--no-control",
        action="store_true",
        help="不运行 yaml 中定义的 control 对照组",
    )
    p_exp_run_all = exp_sub.add_parser("run-all", help="运行 manifest 中全部实验")
    p_exp_run_all.add_argument("--json", action="store_true", help="原始 JSON 输出")
    p_exp_run_all.add_argument(
        "--skip-ffmpeg",
        action="store_true",
        help="跳过 exp_003（ffmpeg 依赖）",
    )

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


def cmd_diff(ns: argparse.Namespace) -> None:
    ctx = _ctx(ns)
    sid = ns.session_id.strip()
    url = (
        ctx.api_base.rstrip("/")
        + f"/sessions/{sid}/transcript/diff?base={ns.base}&compare={ns.compare}"
    )
    data = get_json(url)
    if ns.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    changed = data.get("changed")
    status = "CHANGED" if changed else "SAME"
    print(
        f"[{status}] session={sid} "
        f"base[{data.get('base_index')}] vs compare[{data.get('compare_index')}]"
    )
    for item in data.get("items", []):
        if not item.get("changed"):
            continue
        print(f"\n* {item.get('field')}")
        print(f"  base:    {item.get('base')}")
        print(f"  compare: {item.get('compare')}")


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


def cmd_experiment_list(ns: argparse.Namespace) -> None:
    from app.eval.loader import list_experiments

    experiments = list_experiments()
    if getattr(ns, "json", False):
        payload = [
            {"id": e.id, "title": e.title, "message": e.message}
            for e in experiments
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(f"共 {len(experiments)} 个实验：")
    for exp in experiments:
        print(f"- {exp.id}: {exp.title}")
        print(f"  message: {exp.message}")


def cmd_experiment_run(ns: argparse.Namespace) -> None:
    from app.eval.experiment_runner import ExperimentPairResult, run_experiment

    result = run_experiment(
        ns.experiment_id,
        include_control=not getattr(ns, "no_control", False),
    )
    if ns.json:
        payload = result.to_dict() if isinstance(result, ExperimentPairResult) else result.to_dict()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if isinstance(result, ExperimentPairResult):
        _print_experiment_run(result.main)
        if result.control:
            print("\n--- control ---")
            _print_experiment_run(result.control)
        if result.diff:
            print("\n--- diff (main vs control) ---")
            print(f"changed: {result.diff.changed}")
            for check in result.diff.items:
                if check.changed:
                    print(f"  * {check.field}")
                    print(f"    main:    {check.base}")
                    print(f"    control: {check.compare}")
        if not result.passed:
            raise SystemExit(1)
        return

    _print_experiment_run(result)
    if not result.passed:
        raise SystemExit(1)


def _print_experiment_run(result) -> None:
    status = "PASS" if result.passed else "FAIL"
    print(f"[{status}] {result.experiment_id} — {result.title}")
    print(f"message: {result.message}")
    print(f"agent_success: {result.agent_success}")
    for check in result.eval_result.checks:
        mark = "ok" if check.passed else "FAIL"
        print(f"  - [{mark}] {check.rule}: {check.message}")


def cmd_experiment_run_all(ns: argparse.Namespace) -> None:
    from app.eval.experiment_runner import ExperimentPairResult, ffmpeg_available, run_all_experiments

    skip_ffmpeg = getattr(ns, "skip_ffmpeg", False) or not ffmpeg_available()
    results = run_all_experiments(skip_ffmpeg=skip_ffmpeg)
    if ns.json:
        payload = [
            r.to_dict() if isinstance(r, ExperimentPairResult) else r.to_dict()
            for r in results
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    passed = 0
    for result in results:
        if isinstance(result, ExperimentPairResult):
            _print_experiment_run(result.main)
            ok = result.passed
        else:
            _print_experiment_run(result)
            ok = result.passed
        print()
        if ok:
            passed += 1
    print(f"合计: {passed}/{len(results)} 通过")
    if skip_ffmpeg:
        print("(已跳过 exp_003：本机无 ffmpeg)")
    if passed != len(results):
        raise SystemExit(1)


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
    elif ns.command == "diff":
        cmd_diff(ns)
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
    elif ns.command == "experiment":
        if ns.exp_command == "list":
            cmd_experiment_list(ns)
        elif ns.exp_command == "run":
            cmd_experiment_run(ns)
        elif ns.exp_command == "run-all":
            cmd_experiment_run_all(ns)
        else:
            parser.error(f"未知 experiment 子命令: {ns.exp_command}")
    else:
        parser.error(f"未知子命令: {ns.command}")


if __name__ == "__main__":
    main()
