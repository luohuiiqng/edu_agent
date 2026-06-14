from app.workflows.workflow_runner_registry import (
    get_workflow_runner,
    list_registered_workflow_kinds,
)
from app.workflows.sequential_workflow import SequentialWorkflow
from app.workflows.parallel_workflow import ParallelSequentialWorkflow


assert get_workflow_runner(None).__class__ is SequentialWorkflow
assert get_workflow_runner("sequential").__class__ is SequentialWorkflow
assert get_workflow_runner("parallel_sequential").__class__ is ParallelSequentialWorkflow
assert get_workflow_runner("unknown_kind_defaults").__class__ is SequentialWorkflow

kinds = list_registered_workflow_kinds()
assert "parallel_sequential" in kinds and "sequential" in kinds

print("workflow runner registry tests passed")
