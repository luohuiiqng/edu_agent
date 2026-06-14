"""规则化 Eval：对 RuntimeSession 做 checklist 验收（无需训练数据）。"""

from app.eval.checklist import EvalChecklist, EvalCheckResult, EvalResult
from app.eval.diff import DiffItem, RuntimeDiffResult, diff_runtime_snapshots
from app.eval.runner import evaluate_runtime_session

__all__ = [
    "DiffItem",
    "EvalChecklist",
    "EvalCheckResult",
    "EvalResult",
    "RuntimeDiffResult",
    "diff_runtime_snapshots",
    "evaluate_runtime_session",
]
