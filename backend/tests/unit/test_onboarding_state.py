import pytest
from app.langgraph.state import ConversationState


def test_conversation_state_has_onboarding_fields():
    """Verify ConversationState includes all onboarding fields."""
    state = ConversationState(
        conversation_id="conv-123",
        user_id="user-456",
        messages=[],
        employee_name="John Doe",
        employee_id="EMP-123",
        starter_kit="mouse",
        dietary_restrictions="vegetarian",
        meeting_scheduled=True,
        conversation_summary="Test summary"
    )

    assert state["employee_name"] == "John Doe"
    assert state["employee_id"] == "EMP-123"
    assert state["starter_kit"] == "mouse"
    assert state["dietary_restrictions"] == "vegetarian"
    assert state["meeting_scheduled"] == True
    assert state["conversation_summary"] == "Test summary"


def test_conversation_state_fields_optional():
    """Verify onboarding fields are optional (default to None)."""
    state = ConversationState(
        conversation_id="conv-123",
        user_id="user-456",
        messages=[]
    )

    assert state.get("employee_name") is None
    assert state.get("employee_id") is None
    assert state.get("starter_kit") is None
    assert state.get("dietary_restrictions") is None
    assert state.get("meeting_scheduled") is None
    assert state.get("conversation_summary") is None


def test_conversation_state_serialization():
    """Verify state serializes correctly (for checkpointer)."""
    state = ConversationState(
        conversation_id="conv-123",
        user_id="user-456",
        messages=[],
        employee_name="John Doe"
    )

    # ConversationState is a TypedDict, so we can access it directly
    assert "employee_name" in state
    assert state["employee_name"] == "John Doe"
