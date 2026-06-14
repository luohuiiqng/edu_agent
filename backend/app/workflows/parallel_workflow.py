"""扇出 / 扇入：一组步骤可包含并行桶（同桶内多代理同时执行），桶之间仍顺序执行。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.workflows.agent_executor import AgentExecutor
from app.workflows.base_workflow import BaseWorkflow


class ParallelSequentialWorkflow(BaseWorkflow):
    """步骤列表中每一项可以是普通步骤 dict，或 ``{"parallel": [dict, ...]}`` 并行桶。"""

    def run(
        self,
        steps: list[Any],
        executor: AgentExecutor | None = None,
        context: Any = None,
    ) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        if context is None:
            context = {}
        if context.get("step_results") is None:
            context["step_results"] = {}

        for item in steps:
            if isinstance(item, dict) and "parallel" in item:
                subs = item.get("parallel")
                if not isinstance(subs, list) or not subs:
                    return {
                        "success": False,
                        "error": "parallel 组为空或格式错误",
                        "results": results,
                    }
                sorted_subs = sorted(subs, key=lambda s: s.get("step_name", ""))
                max_workers = min(8, len(sorted_subs))
                local: dict[str, dict[str, Any]] = {}
                with ThreadPoolExecutor(max_workers=max_workers) as pool:
                    future_map = {
                        pool.submit(executor.execute_step, st, context): st
                        for st in sorted_subs
                    }
                    try:
                        for fut in as_completed(future_map):
                            st = future_map[fut]
                            nm = st.get("step_name", "unknown")
                            sr = fut.result()
                            sr["parallel_fan_out"] = True
                            local[nm] = sr
                            if not sr.get("success", False):
                                for k in sorted(local.keys()):
                                    results.append(local[k])
                                return {
                                    "success": False,
                                    "error": f"并行步骤失败: {nm}",
                                    "results": results,
                                }
                    except Exception as e:
                        return {
                            "success": False,
                            "error": f"并行步骤异常: {e}",
                            "results": results,
                        }
                for nm in sorted(local.keys()):
                    sr = local[nm]
                    results.append(sr)
                    context["step_results"][nm] = sr
            elif isinstance(item, dict):
                step_result = executor.execute_step(item, context=context)
                step_name = item.get("step_name", "unknown")
                results.append(step_result)
                context["step_results"][step_name] = step_result
                if not step_result.get("success", False):
                    return {
                        "success": False,
                        "error": f"Step {step_name} failed",
                        "results": results,
                    }
            else:
                return {
                    "success": False,
                    "error": f"未知步骤类型: {type(item).__name__}",
                    "results": results,
                }

        return {"success": True, "results": results}
