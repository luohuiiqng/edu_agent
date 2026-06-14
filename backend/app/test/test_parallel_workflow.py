"""并行扇出 + 扇入工作流测试。"""

from app.models.mock_model import MockModel
from app.workflows.agent_executor import AgentExecutor
from app.workflows.parallel_workflow import ParallelSequentialWorkflow
from app.workflows.workflow_steps import flatten_steps_for_trace


def test_parallel_then_merge_three_modules():
    model = MockModel(response_text="out")
    executor = AgentExecutor(model=model, tool_registry=None)
    wf = ParallelSequentialWorkflow()

    raw_steps = [
        {
            "parallel": [
                {
                    "step_name": "a",
                    "action": "model",
                    "agent_role": "A",
                    "prompt": "hello a",
                },
                {
                    "step_name": "b",
                    "action": "model",
                    "agent_role": "B",
                    "prompt": "hello b",
                },
            ]
        },
        {
            "step_name": "merge",
            "action": "model",
            "prompt_template": "m:{a}!{b}!",
            "use_step_result_keys": ["a", "b"],
        },
    ]

    out = wf.run(steps=raw_steps, executor=executor, context={})
    assert out["success"] is True
    assert len(out["results"]) == 3

    flat = flatten_steps_for_trace(raw_steps)
    assert len(flat) == 3
    names = [s.get("step_name") for s in flat]
    assert "a" in names and "b" in names and "merge" in names

    ra = next(r for r in out["results"] if r["step_name"] == "a")
    rb = next(r for r in out["results"] if r["step_name"] == "b")
    merge = next(r for r in out["results"] if r["step_name"] == "merge")
    assert ra.get("parallel_fan_out") is True
    assert rb.get("parallel_fan_out") is True
    assert merge.get("parallel_fan_out") is not True
    assert merge["success"] is True
    assert "out:" in merge["output"]
