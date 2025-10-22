# ABOUTME: Integration tests for LLM tool calling flow with LangGraph
# ABOUTME: Tests complete flow from user input through tool execution to response

import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import AIMessage, ToolMessage
from app.langgraph.graphs.chat_graph import create_chat_graph
from app.langgraph.tools import multiply
from app.core.domain.message import Message, MessageRole
from app.core.domain.conversation import Conversation


@pytest.mark.integration
class TestToolCallingFlow:
    """Integration tests for tool calling flow."""

    @pytest.fixture
    async def mock_repositories(self):
        """Create mock repositories for testing."""
        message_repo = AsyncMock()
        conversation_repo = AsyncMock()

        # Mock conversation exists
        conversation_repo.get_by_id = AsyncMock(
            return_value=Conversation(
                id="test-conv-123",
                user_id="test-user-123",
                title="Test Conversation"
            )
        )

        # Mock message creation
        message_repo.create = AsyncMock(
            side_effect=lambda msg: Message(
                id="mock-msg-id",
                conversation_id=msg.conversation_id,
                role=msg.role,
                content=msg.content,
                metadata=msg.metadata
            )
        )

        # Mock message count increment
        conversation_repo.increment_message_count = AsyncMock()

        return message_repo, conversation_repo

    @pytest.fixture
    def mock_llm_provider(self):
        """Create mock LLM provider that returns tool calls."""
        provider = MagicMock()

        # First call: LLM decides to use multiply tool
        first_response = AIMessage(
            content="",
            tool_calls=[{
                "name": "multiply",
                "args": {"a": 12, "b": 34},
                "id": "call_abc123"
            }]
        )

        # Second call: LLM provides final answer after tool execution
        second_response = AIMessage(
            content="The result of 12 multiplied by 34 is 408."
        )

        # Mock ainvoke to return different responses on consecutive calls
        provider.model.ainvoke = AsyncMock(
            side_effect=[first_response, second_response]
        )

        return provider

    @pytest.mark.asyncio
    async def test_multiply_tool_execution_flow(
        self,
        mock_repositories,
        mock_llm_provider
    ):
        """Test complete tool calling flow with multiply tool."""
        message_repo, conversation_repo = mock_repositories

        # Create chat graph with mocked dependencies
        graph = create_chat_graph(
            llm_provider=mock_llm_provider,
            message_repository=message_repo,
            conversation_repository=conversation_repo
        )

        # Execute graph with user input requesting multiplication
        result = await graph.ainvoke({
            "messages": [],
            "conversation_id": "test-conv-123",
            "user_id": "test-user-123",
            "current_input": "What is 12 times 34?"
        })

        # Verify no errors
        assert result.get("error") is None

        # Verify messages in result
        messages = result["messages"]
        assert len(messages) >= 3  # HumanMessage, AIMessage with tool_calls, ToolMessage, AIMessage

        # Verify tool call was made
        tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
        assert len(tool_messages) == 1
        assert "408" in tool_messages[0].content

        # Verify final AI response
        ai_messages = [m for m in messages if isinstance(m, AIMessage)]
        assert len(ai_messages) == 2  # First with tool call, second with answer
        assert "408" in ai_messages[-1].content

    @pytest.mark.asyncio
    async def test_tool_messages_saved_to_database(
        self,
        mock_repositories,
        mock_llm_provider
    ):
        """Test that tool messages are properly saved to database."""
        message_repo, conversation_repo = mock_repositories

        # Create chat graph
        graph = create_chat_graph(
            llm_provider=mock_llm_provider,
            message_repository=message_repo,
            conversation_repository=conversation_repo
        )

        # Execute graph
        await graph.ainvoke({
            "messages": [],
            "conversation_id": "test-conv-123",
            "user_id": "test-user-123",
            "current_input": "Calculate 5 * 3"
        })

        # Verify message repository create was called
        assert message_repo.create.called

        # Get all created messages
        created_messages = [call.args[0] for call in message_repo.create.call_args_list]

        # Verify we have messages of different roles
        roles = {msg.role for msg in created_messages}
        assert MessageRole.USER in roles
        assert MessageRole.ASSISTANT in roles
        assert MessageRole.TOOL in roles

        # Verify tool message has correct metadata
        tool_messages = [msg for msg in created_messages if msg.role == MessageRole.TOOL]
        assert len(tool_messages) >= 1
        assert tool_messages[0].metadata is not None
        assert "tool_call_id" in tool_messages[0].metadata

    @pytest.mark.asyncio
    async def test_multiply_tool_correctness(self):
        """Test that multiply tool produces correct results."""
        # Test the tool directly
        result = multiply.invoke({"a": 12, "b": 34})
        assert result == 408

        result = multiply.invoke({"a": 7, "b": 8})
        assert result == 56

        result = multiply.invoke({"a": -5, "b": 3})
        assert result == -15

    @pytest.mark.asyncio
    async def test_conversation_without_tools(
        self,
        mock_repositories
    ):
        """Test that normal conversation works without tool calls."""
        message_repo, conversation_repo = mock_repositories

        # Mock LLM that doesn't use tools
        provider = MagicMock()
        provider.model.ainvoke = AsyncMock(
            return_value=AIMessage(content="Hello! How can I help you today?")
        )

        # Create chat graph
        graph = create_chat_graph(
            llm_provider=provider,
            message_repository=message_repo,
            conversation_repository=conversation_repo
        )

        # Execute graph with simple greeting
        result = await graph.ainvoke({
            "messages": [],
            "conversation_id": "test-conv-123",
            "user_id": "test-user-123",
            "current_input": "Hello"
        })

        # Verify no errors
        assert result.get("error") is None

        # Verify no tool messages in result
        messages = result["messages"]
        tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
        assert len(tool_messages) == 0

        # Verify AI response exists
        ai_messages = [m for m in messages if isinstance(m, AIMessage)]
        assert len(ai_messages) >= 1
        assert ai_messages[-1].content != ""

    @pytest.mark.asyncio
    async def test_error_handling_in_graph(
        self,
        mock_repositories
    ):
        """Test error handling when graph encounters issues."""
        message_repo, conversation_repo = mock_repositories

        # Mock LLM that raises an exception
        provider = MagicMock()
        provider.model.ainvoke = AsyncMock(
            side_effect=Exception("LLM API error")
        )

        # Create chat graph
        graph = create_chat_graph(
            llm_provider=provider,
            message_repository=message_repo,
            conversation_repository=conversation_repo
        )

        # Execute graph - should handle error gracefully
        result = await graph.ainvoke({
            "messages": [],
            "conversation_id": "test-conv-123",
            "user_id": "test-user-123",
            "current_input": "Hello"
        })

        # Verify error is captured
        assert result.get("error") is not None
        assert "LLM API error" in result["error"]
