from dotenv import load_dotenv
load_dotenv()
import os
from app.agent.chat_agent import ChatAgent
from app.tools.tool_registry import ToolRegistry
from app.schemas.agent_input import AgentInput
from app.tools.time_tool import TimeTool
from app.models.openai_model import OpenAIModel


api_key = os.getenv("OPENAI_API_KEY")
model_name = os.getenv("OPENAI_MODEL","gpt-5.4")
base_url = os.getenv("OPENAI_BASE_URL")
organization = os.getenv("OPENAI_ORGANIZATION")





time_tool = TimeTool()
tool_registry = ToolRegistry()
tool_registry.register_tool(time_tool)

model = OpenAIModel(
    model_name=model_name,
    api_key=api_key,
    base_url=base_url,
    organization= organization
    )
model_request = AgentInput(message="你好,现在几点了？")

chat_agent = ChatAgent(model = model,tool_registry=tool_registry)

agent_output = chat_agent.run(model_request)
print(f"agent_output:{agent_output}")

model_request = AgentInput(message="你好!")
agent_output = chat_agent.run(model_request)
print(f"agent_output:{agent_output}")