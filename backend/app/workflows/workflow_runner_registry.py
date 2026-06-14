"""按 ``plan["workflow_kind"]`` 解析可执行的工作流实现，支持运行时注册扩展。"""

from __future__ import annotations

from typing import Type

from app.workflows.base_workflow import BaseWorkflow
from app.workflows.parallel_workflow import ParallelSequentialWorkflow
from app.workflows.sequential_workflow import SequentialWorkflow

_REGISTRY: dict[str, Type[BaseWorkflow]] = {
    "sequential": SequentialWorkflow,
    "parallel_sequential": ParallelSequentialWorkflow,
}


def register_workflow_kind(kind: str, workflow_cls: Type[BaseWorkflow]) -> None:
    """注册自定义 ``workflow_kind`` → 工作流类（便于插件或测试替身）。"""
    _REGISTRY[kind] = workflow_cls


def get_workflow_runner(workflow_kind: str | None) -> BaseWorkflow:
    """
    :param workflow_kind: ``sequential``（默认）、``parallel_sequential`` 等；
        ``None`` 视为顺序工作流（兼容旧计划字段不全）。
    """
    key = workflow_kind or "sequential"
    cls = _REGISTRY.get(key, SequentialWorkflow)
    return cls()


def list_registered_workflow_kinds() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY.keys()))
