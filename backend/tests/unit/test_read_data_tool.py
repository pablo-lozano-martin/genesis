import pytest
from app.langgraph.state import ConversationState
from app.langgraph.tools.read_data import read_data


@pytest.mark.asyncio
async def test_read_data_all_fields():
    """Test reading all onboarding fields."""
    state = ConversationState(
        conversation_id="conv-123",
        user_id="user-456",
        messages=[],
        employee_name="John Doe",
        employee_id="EMP-123",
        starter_kit="mouse"
    )

    result = await read_data(state=state, field_names=None)

    assert result["status"] == "success"
    assert result["employee_name"] == "John Doe"
    assert result["employee_id"] == "EMP-123"
    assert result["starter_kit"] == "mouse"
    assert result["dietary_restrictions"] is None


@pytest.mark.asyncio
async def test_read_data_specific_fields():
    """Test reading specific fields."""
    state = ConversationState(
        conversation_id="conv-123",
        user_id="user-456",
        messages=[],
        employee_name="John Doe",
        starter_kit="keyboard"
    )

    result = await read_data(
        state=state,
        field_names=["employee_name", "starter_kit"]
    )

    assert result["status"] == "success"
    assert "employee_name" in result
    assert "starter_kit" in result
    assert "employee_id" not in result


@pytest.mark.asyncio
async def test_read_data_invalid_field():
    """Test error when reading invalid field."""
    state = ConversationState(
        conversation_id="conv-123",
        user_id="user-456",
        messages=[]
    )

    result = await read_data(
        state=state,
        field_names=["invalid_field"]
    )

    assert result["status"] == "error"
    assert "Invalid field" in result["message"]
