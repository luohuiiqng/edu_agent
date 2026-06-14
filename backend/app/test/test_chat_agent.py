import pytest
from dotenv import load_dotenv
load_dotenv()
import os
from app.agent.chat_agent import ChatAgent
from app.schemas.agent_input import AgentInput
from app.models.mock_model import MockModel
from app.models.openai_model import OpenAIModel
from app.runtime.runtime_manager import RuntimeManager
from app.runtime.in_memory_session_store import InMemorySessionStore
from app.runtime.in_memory_transcript_store import InMemoryTranscriptStore


def test_chat_agent_with_mock_model():
    """测试 ChatAgent 使用 MockModel 的基本功能"""
    # 创建存储和运行时管理器
    session_store = InMemorySessionStore()
    transcript_store = InMemoryTranscriptStore()
    runtime_manager = RuntimeManager(session_store=session_store, transcript_store=transcript_store)
    
    # 创建模型和Agent
    model = MockModel()
    chat_agent = ChatAgent(runtime_manager=runtime_manager, model=model)
    
    # 测试基本功能
    input_data = AgentInput(message="今天是几号呢？")
    output = chat_agent.run(input_data=input_data)
    
    assert output.success == True
    assert output.content is not None
    assert isinstance(output.content, str)
    assert len(output.content) > 0


def test_chat_agent_with_session_id():
    """测试带会话ID的情况"""
    # 创建存储和运行时管理器
    session_store = InMemorySessionStore()
    transcript_store = InMemoryTranscriptStore()
    runtime_manager = RuntimeManager(session_store=session_store, transcript_store=transcript_store)
    
    # 创建模型和Agent
    model = MockModel()
    chat_agent = ChatAgent(runtime_manager=runtime_manager, model=model)
    
    # 测试带会话ID的情况
    session_id = "test-session-123"
    input_data = AgentInput(message="今天天气怎么样？", session_id=session_id)
    output = chat_agent.run(input_data=input_data)
    
    assert output.success == True
    assert output.content is not None


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="需要OpenAI API密钥")
def test_chat_agent_with_openai_model():
    """测试 ChatAgent 使用 OpenAIModel 的功能"""
    # 创建存储和运行时管理器
    session_store = InMemorySessionStore()
    transcript_store = InMemoryTranscriptStore()
    runtime_manager = RuntimeManager(session_store=session_store, transcript_store=transcript_store)
    
    # 创建OpenAI模型
    api_key = os.getenv("OPENAI_API_KEY")
    model_name = os.getenv("OPENAI_MODEL", "gpt-5.4")
    base_url = os.getenv("OPENAI_BASE_URL")
    organization = os.getenv("OPENAI_ORGANIZATION")
    
    model = OpenAIModel(
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        organization=organization
    )
    
    # 创建Agent
    chat_agent = ChatAgent(runtime_manager=runtime_manager, model=model)
    
    # 测试基本功能
    input_data = AgentInput(message="今天是几号呢？")
    output = chat_agent.run(input_data=input_data)
    
    assert output.success == True
    assert output.content is not None
    assert isinstance(output.content, str)
    assert len(output.content) > 0
