"""CLI 模块载入与参数解析烟测（不发真实 HTTP）。"""

from app.cli.main import _build_parser
from app.cli.http_api import resolve_origin


def test_parser_subcommands():
    p = _build_parser()
    ns = p.parse_args(["chat", "hello"])
    assert ns.command == "chat"
    assert ns.message == "hello"
    ns_task = p.parse_args(["task", "status", "task-1"])
    assert ns_task.command == "task"
    assert ns_task.task_command == "status"
    assert ns_task.task_id == "task-1"
    ns_task_tr = p.parse_args(["task", "transcript", "task-1"])
    assert ns_task_tr.command == "task"
    assert ns_task_tr.task_command == "transcript"
    ns_exp = p.parse_args(["experiment", "list"])
    assert ns_exp.command == "experiment"
    assert ns_exp.exp_command == "list"
    ns_exp_run = p.parse_args(["experiment", "run", "exp_001_time_tool"])
    assert ns_exp_run.exp_command == "run"
    assert ns_exp_run.experiment_id == "exp_001_time_tool"
    ns_diff = p.parse_args(["diff", "session-1", "--base", "0", "--compare", "1"])
    assert ns_diff.command == "diff"
    assert ns_diff.session_id == "session-1"
    assert ns_diff.base == 0
    assert ns_diff.compare == 1


def test_resolve_origin_from_api_base():
    o = resolve_origin("http://127.0.0.1:8000/agent_api", None)
    assert o == "http://127.0.0.1:8000"


def test_resolve_origin_override():
    o = resolve_origin("http://x/agent_api", "http://custom:9000")
    assert o == "http://custom:9000"
