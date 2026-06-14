import pytest
from app.workflows.sequential_workflow import SequentialWorkflow
from app.workflows.agent_executor import AgentExecutor
from app.models.mock_model import MockModel
from app.tools.tool_registry import ToolRegistry
from app.tools.time_tool import TimeTool


def test_sequential_workflow_execution():
    """测试顺序工作流的执行功能"""
    # 初始化工具注册表和工具
    tool_registry = ToolRegistry()
    time_tool = TimeTool()
    tool_registry.register_tool(time_tool)
    
    # 初始化模型
    model = MockModel()
    
    # 创建工作流和执行器
    sequential_workflow = SequentialWorkflow()
    agent_executor = AgentExecutor(model=model, tool_registry=tool_registry)
    
    # 定义工作流步骤
    steps = [
        {"action": "tool", "tool_name": "time_tool", "tool_input": {"content": "现在几点了？"}, "step_name": "get_time"},
        {
            "action": "model",
            "prompt_template": "当前时间是 {step_output}，请生成一句话回复用户",
            "use_step_result": "get_time",
            "step_name": "generate_reply",
        }
    ]
    
    # 执行工作流
    context = {}
    workflow_output = sequential_workflow.run(steps=steps, executor=agent_executor, context=context)
    
    # 验证工作流执行结果
    assert workflow_output is not None
    assert isinstance(workflow_output, dict)
    assert "success" in workflow_output
    assert workflow_output["success"] == True
    assert "results" in workflow_output
    assert isinstance(workflow_output["results"], list)
    
    # 验证时间工具的执行结果
    get_time_result = None
    generate_reply_result = None
    
    for result in workflow_output["results"]:
        if result["step_name"] == "get_time":
            get_time_result = result
        elif result["step_name"] == "generate_reply":
            generate_reply_result = result
    
    assert get_time_result is not None
    assert get_time_result["success"] == True
    assert get_time_result["output"] is not None
    assert isinstance(get_time_result["output"], str)
    
    assert generate_reply_result is not None
    assert generate_reply_result["success"] == True
    assert generate_reply_result["output"] is not None
    assert isinstance(generate_reply_result["output"], str)



