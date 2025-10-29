import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from langgraph.types import RunnableConfig
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from motor.motor_asyncio import AsyncIOMotorClient
from app.langgraph.state import ConversationState
from app.langgraph.graphs.onboarding_graph import create_onboarding_graph
from app.langgraph.tools import read_data, write_data, export_data
from app.langgraph.tools.rag_search import rag_search


@pytest.mark.asyncio
@pytest.mark.integration
async def test_onboarding_graph_injects_system_prompt():
    """Test that onboarding graph injects system prompt on first invocation."""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["genesis_test_langgraph"]

    checkpointer_context = AsyncMongoDBSaver.from_conn_string("mongodb://localhost:27017/genesis_test_langgraph")
    checkpointer = await checkpointer_context.__aenter__()

    # Create mock LLM provider that returns without tool calls
    mock_llm = AsyncMock()
    mock_llm.bind_tools = AsyncMock(return_value=mock_llm)
    mock_llm.generate = AsyncMock(
        return_value=AIMessage(content="Hello! I'm here to help with your onboarding.")
    )

    tools = [read_data, write_data, rag_search, export_data]
    graph = create_onboarding_graph(checkpointer, tools)

    config = RunnableConfig(
        configurable={
            "thread_id": "conv-test-system-prompt",
            "llm_provider": mock_llm,
            "user_id": "user-test"
        }
    )

    initial_state = {
        "messages": [HumanMessage(content="Hello")],
        "conversation_id": "conv-test-system-prompt",
        "user_id": "user-test"
    }

    # Run graph
    result = await graph.ainvoke(initial_state, config)

    # Verify system prompt was injected
    messages = result["messages"]
    assert len(messages) >= 2
    assert isinstance(messages[0], SystemMessage)
    assert "onboarding assistant for Orbio" in messages[0].content

    # Cleanup
    await db.drop_collection("checkpoints")
    await checkpointer_context.__aexit__(None, None, None)
    client.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_onboarding_graph_tool_orchestration():
    """Test multi-tool workflow: read -> write -> read -> export."""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["genesis_test_langgraph"]

    checkpointer_context = AsyncMongoDBSaver.from_conn_string("mongodb://localhost:27017/genesis_test_langgraph")
    checkpointer = await checkpointer_context.__aenter__()

    # Track tool call sequence
    tool_calls_made = []

    # Create mock LLM that simulates tool usage
    mock_llm = AsyncMock()
    mock_llm.bind_tools = AsyncMock(return_value=mock_llm)

    # Simulate: agent calls write_data, then export_data
    call_count = [0]

    async def mock_generate_with_tools(messages):
        call_count[0] += 1

        # First call: write employee_name
        if call_count[0] == 1:
            tool_calls_made.append("write_data")
            return AIMessage(
                content="",
                tool_calls=[{
                    "name": "write_data",
                    "args": {"field_name": "employee_name", "value": "Test User"},
                    "id": "call_1"
                }]
            )
        # Second call: write employee_id
        elif call_count[0] == 2:
            tool_calls_made.append("write_data")
            return AIMessage(
                content="",
                tool_calls=[{
                    "name": "write_data",
                    "args": {"field_name": "employee_id", "value": "EMP-123"},
                    "id": "call_2"
                }]
            )
        # Third call: write starter_kit
        elif call_count[0] == 3:
            tool_calls_made.append("write_data")
            return AIMessage(
                content="",
                tool_calls=[{
                    "name": "write_data",
                    "args": {"field_name": "starter_kit", "value": "mouse"},
                    "id": "call_3"
                }]
            )
        # Final call: no tool calls, just response
        else:
            return AIMessage(content="Data collection complete!")

    mock_llm.generate = mock_generate_with_tools

    tools = [read_data, write_data, rag_search, export_data]
    graph = create_onboarding_graph(checkpointer, tools)

    config = RunnableConfig(
        configurable={
            "thread_id": "conv-test-tools",
            "llm_provider": mock_llm,
            "user_id": "user-test"
        }
    )

    initial_state = {
        "messages": [HumanMessage(content="My name is Test User, ID EMP-123, I want a mouse")],
        "conversation_id": "conv-test-tools",
        "user_id": "user-test"
    }

    # Run graph
    result = await graph.ainvoke(initial_state, config)

    # Verify tools were called
    assert len(tool_calls_made) > 0
    assert "write_data" in tool_calls_made

    # Verify state was updated
    assert result.get("employee_name") == "Test User"
    assert result.get("employee_id") == "EMP-123"
    assert result.get("starter_kit") == "mouse"

    # Cleanup
    await db.drop_collection("checkpoints")
    await checkpointer_context.__aexit__(None, None, None)
    client.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_onboarding_graph_state_persistence():
    """Test state persists via checkpointer throughout conversation."""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["genesis_test_langgraph"]

    checkpointer_context = AsyncMongoDBSaver.from_conn_string("mongodb://localhost:27017/genesis_test_langgraph")
    checkpointer = await checkpointer_context.__aenter__()

    mock_llm = AsyncMock()
    mock_llm.bind_tools = AsyncMock(return_value=mock_llm)
    mock_llm.generate = AsyncMock(
        return_value=AIMessage(content="Got it!")
    )

    tools = [read_data, write_data, rag_search, export_data]
    graph = create_onboarding_graph(checkpointer, tools)

    conversation_id = "conv-test-persist"

    config = RunnableConfig(
        configurable={
            "thread_id": conversation_id,
            "llm_provider": mock_llm,
            "user_id": "user-test"
        }
    )

    # First invocation: set employee_name
    state1 = {
        "messages": [HumanMessage(content="First message")],
        "conversation_id": conversation_id,
        "user_id": "user-test",
        "employee_name": "Alice"
    }

    await graph.ainvoke(state1, config)

    # Retrieve state
    retrieved_state = await graph.aget_state(config)

    # Verify persistence
    assert retrieved_state.values["employee_name"] == "Alice"

    # Cleanup
    await db.drop_collection("checkpoints")
    await checkpointer_context.__aexit__(None, None, None)
    client.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_onboarding_graph_resume_from_checkpoint():
    """Test conversation resumes correctly from checkpoint."""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["genesis_test_langgraph"]

    checkpointer_context = AsyncMongoDBSaver.from_conn_string("mongodb://localhost:27017/genesis_test_langgraph")
    checkpointer = await checkpointer_context.__aenter__()

    mock_llm = AsyncMock()
    mock_llm.bind_tools = AsyncMock(return_value=mock_llm)
    mock_llm.generate = AsyncMock(
        return_value=AIMessage(content="Continuing...")
    )

    tools = [read_data, write_data, rag_search, export_data]
    graph = create_onboarding_graph(checkpointer, tools)

    conversation_id = "conv-test-resume"

    config = RunnableConfig(
        configurable={
            "thread_id": conversation_id,
            "llm_provider": mock_llm,
            "user_id": "user-test"
        }
    )

    # First session: collect partial data
    state1 = {
        "messages": [HumanMessage(content="I'm Bob")],
        "conversation_id": conversation_id,
        "user_id": "user-test",
        "employee_name": "Bob",
        "employee_id": "EMP-456"
    }

    await graph.ainvoke(state1, config)

    # Second session: resume and add more data
    state2 = await graph.aget_state(config)

    assert state2.values["employee_name"] == "Bob"
    assert state2.values["employee_id"] == "EMP-456"

    # Update with new field
    state2.values["starter_kit"] = "keyboard"

    await graph.aupdate_state(config, state2.values)

    # Verify update persisted
    state3 = await graph.aget_state(config)
    assert state3.values["starter_kit"] == "keyboard"

    # Cleanup
    await db.drop_collection("checkpoints")
    await checkpointer_context.__aexit__(None, None, None)
    client.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_onboarding_graph_validation_retry():
    """Test agent handles validation errors and retries."""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["genesis_test_langgraph"]

    checkpointer_context = AsyncMongoDBSaver.from_conn_string("mongodb://localhost:27017/genesis_test_langgraph")
    checkpointer = await checkpointer_context.__aenter__()

    # Track attempts
    attempts = []

    mock_llm = AsyncMock()
    mock_llm.bind_tools = AsyncMock(return_value=mock_llm)

    async def mock_generate_with_retry(messages):
        attempt_num = len(attempts)

        # First attempt: invalid starter_kit
        if attempt_num == 0:
            attempts.append("invalid")
            return AIMessage(
                content="",
                tool_calls=[{
                    "name": "write_data",
                    "args": {"field_name": "starter_kit", "value": "laptop"},
                    "id": "call_invalid"
                }]
            )
        # Second attempt: valid value
        elif attempt_num == 1:
            attempts.append("valid")
            return AIMessage(
                content="",
                tool_calls=[{
                    "name": "write_data",
                    "args": {"field_name": "starter_kit", "value": "mouse"},
                    "id": "call_valid"
                }]
            )
        else:
            return AIMessage(content="Done!")

    mock_llm.generate = mock_generate_with_retry

    tools = [read_data, write_data, rag_search, export_data]
    graph = create_onboarding_graph(checkpointer, tools)

    config = RunnableConfig(
        configurable={
            "thread_id": "conv-test-validation",
            "llm_provider": mock_llm,
            "user_id": "user-test"
        }
    )

    initial_state = {
        "messages": [HumanMessage(content="I want a laptop")],
        "conversation_id": "conv-test-validation",
        "user_id": "user-test"
    }

    # Run graph
    result = await graph.ainvoke(initial_state, config)

    # Verify retry logic worked
    assert len(attempts) == 2
    assert attempts[0] == "invalid"
    assert attempts[1] == "valid"

    # Verify final state has valid value
    assert result.get("starter_kit") == "mouse"

    # Cleanup
    await db.drop_collection("checkpoints")
    await checkpointer_context.__aexit__(None, None, None)
    client.close()
