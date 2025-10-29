import pytest
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.langgraph.state import ConversationState
from app.langgraph.graphs.onboarding_graph import inject_system_prompt
from app.langgraph.prompts.onboarding_prompts import ONBOARDING_SYSTEM_PROMPT


def test_inject_system_prompt_adds_message():
    """Test system prompt is added when not present."""
    state = ConversationState(
        conversation_id="conv-123",
        user_id="user-456",
        messages=[
            HumanMessage(content="Hello")
        ]
    )

    result = inject_system_prompt(state)

    # Should return messages dict with system prompt
    assert "messages" in result
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], SystemMessage)
    assert result["messages"][0].content == ONBOARDING_SYSTEM_PROMPT


def test_inject_system_prompt_skips_if_present():
    """Test no duplicate system prompts are added."""
    state = ConversationState(
        conversation_id="conv-123",
        user_id="user-456",
        messages=[
            SystemMessage(content=ONBOARDING_SYSTEM_PROMPT),
            HumanMessage(content="Hello")
        ]
    )

    result = inject_system_prompt(state)

    # Should return empty dict (no update needed)
    assert result == {}


def test_inject_system_prompt_empty_messages():
    """Test system prompt is added when messages list is empty."""
    state = ConversationState(
        conversation_id="conv-123",
        user_id="user-456",
        messages=[]
    )

    result = inject_system_prompt(state)

    # Should add system prompt
    assert "messages" in result
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], SystemMessage)


def test_inject_system_prompt_preserves_content():
    """Test system prompt content matches ONBOARDING_SYSTEM_PROMPT."""
    state = ConversationState(
        conversation_id="conv-123",
        user_id="user-456",
        messages=[HumanMessage(content="Test")]
    )

    result = inject_system_prompt(state)

    system_message = result["messages"][0]
    assert "onboarding assistant for Orbio" in system_message.content
    assert "read_data" in system_message.content
    assert "write_data" in system_message.content
    assert "rag_search" in system_message.content
    assert "export_data" in system_message.content


def test_inject_system_prompt_with_ai_message():
    """Test system prompt is added even if first message is AI message."""
    state = ConversationState(
        conversation_id="conv-123",
        user_id="user-456",
        messages=[
            AIMessage(content="Hello, how can I help?")
        ]
    )

    result = inject_system_prompt(state)

    # Should add system prompt since first message is not SystemMessage
    assert "messages" in result
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], SystemMessage)


def test_inject_system_prompt_with_different_system_message():
    """Test system prompt not added if any SystemMessage exists at start."""
    different_system_prompt = SystemMessage(content="Different system prompt")

    state = ConversationState(
        conversation_id="conv-123",
        user_id="user-456",
        messages=[
            different_system_prompt,
            HumanMessage(content="Hello")
        ]
    )

    result = inject_system_prompt(state)

    # Should skip injection (assumes first SystemMessage is sufficient)
    assert result == {}
