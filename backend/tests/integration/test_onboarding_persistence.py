import pytest
from langgraph.types import RunnableConfig
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from app.langgraph.state import ConversationState
from app.langgraph.graphs.streaming_chat_graph import create_streaming_chat_graph
from langchain_core.messages import HumanMessage
from unittest.mock import AsyncMock
from motor.motor_asyncio import AsyncIOMotorClient


@pytest.mark.asyncio
@pytest.mark.integration
async def test_state_changes_persisted_by_checkpointer():
    """Test that state changes are persisted to checkpointer."""
    # Create a temporary MongoDB connection for testing
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["genesis_test_langgraph"]

    # Create checkpointer
    checkpointer = AsyncMongoDBSaver(client, "genesis_test_langgraph")

    # Create mock LLM provider
    mock_llm = AsyncMock()
    mock_llm.bind_tools = AsyncMock(return_value=mock_llm)
    mock_llm.generate = AsyncMock(return_value=HumanMessage(content="Test response"))

    # Create graph with checkpointer
    graph = create_streaming_chat_graph(checkpointer)

    config = RunnableConfig(
        configurable={
            "thread_id": "conv-test-persist",
            "llm_provider": mock_llm,
            "user_id": "user-test"
        }
    )

    initial_state = {
        "messages": [HumanMessage(content="Test message")],
        "conversation_id": "conv-test-persist",
        "user_id": "user-test",
        "employee_name": "Test Employee",
        "employee_id": "EMP-999"
    }

    # Run graph
    await graph.ainvoke(initial_state, config)

    # Retrieve from checkpointer
    retrieved = await graph.aget_state(config)
    final_state = retrieved.values

    # Verify onboarding fields persisted
    assert final_state["employee_name"] == "Test Employee"
    assert final_state["employee_id"] == "EMP-999"

    # Cleanup
    await db.drop_collection("checkpoints")
    client.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_state_retrieval_after_conversation_restart():
    """Test that state is preserved after conversation restart."""
    # Create a temporary MongoDB connection for testing
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["genesis_test_langgraph"]

    # Create checkpointer
    checkpointer = AsyncMongoDBSaver(client, "genesis_test_langgraph")

    # Create mock LLM provider
    mock_llm = AsyncMock()
    mock_llm.bind_tools = AsyncMock(return_value=mock_llm)
    mock_llm.generate = AsyncMock(return_value=HumanMessage(content="Test response"))

    # Create graph with checkpointer
    graph = create_streaming_chat_graph(checkpointer)

    conversation_id = "conv-test-restart"

    config = RunnableConfig(
        configurable={
            "thread_id": conversation_id,
            "llm_provider": mock_llm,
            "user_id": "user-test"
        }
    )

    # First: Write data
    state1 = {
        "messages": [HumanMessage(content="First message")],
        "conversation_id": conversation_id,
        "user_id": "user-test",
        "employee_name": "Jane Doe",
        "starter_kit": "keyboard"
    }

    await graph.ainvoke(state1, config)

    # Second: Retrieve after restart (new invocation)
    state2 = await graph.aget_state(config)

    assert state2.values["employee_name"] == "Jane Doe"
    assert state2.values["starter_kit"] == "keyboard"

    # Cleanup
    await db.drop_collection("checkpoints")
    client.close()
