import pytest
from app.langgraph.state import ConversationState
from app.langgraph.tools.write_data import write_data


@pytest.mark.asyncio
async def test_write_data_employee_name_success():
    """Test writing valid employee name."""
    state = ConversationState(
        conversation_id="conv-123",
        user_id="user-456",
        messages=[]
    )

    result = await write_data(
        state=state,
        field_name="employee_name",
        value="John Doe"
    )

    assert result["status"] == "success"
    assert state["employee_name"] == "John Doe"
    assert result["value"] == "John Doe"


@pytest.mark.asyncio
async def test_write_data_starter_kit_valid():
    """Test writing valid starter kit option."""
    state = ConversationState(
        conversation_id="conv-123",
        user_id="user-456",
        messages=[]
    )

    result = await write_data(
        state=state,
        field_name="starter_kit",
        value="mouse"
    )

    assert result["status"] == "success"
    assert state["starter_kit"] == "mouse"


@pytest.mark.asyncio
async def test_write_data_starter_kit_case_insensitive():
    """Test starter kit validation is case-insensitive."""
    state = ConversationState(
        conversation_id="conv-123",
        user_id="user-456",
        messages=[]
    )

    result = await write_data(
        state=state,
        field_name="starter_kit",
        value="KEYBOARD"
    )

    assert result["status"] == "success"
    assert state["starter_kit"] == "keyboard"


@pytest.mark.asyncio
async def test_write_data_starter_kit_invalid():
    """Test validation error for invalid starter kit."""
    state = ConversationState(
        conversation_id="conv-123",
        user_id="user-456",
        messages=[]
    )

    result = await write_data(
        state=state,
        field_name="starter_kit",
        value="invalid_option"
    )

    assert result["status"] == "error"
    assert "Invalid starter_kit value" in result["message"]
    assert "valid_values" in result


@pytest.mark.asyncio
async def test_write_data_meeting_scheduled_boolean():
    """Test writing boolean meeting_scheduled."""
    state = ConversationState(
        conversation_id="conv-123",
        user_id="user-456",
        messages=[]
    )

    result = await write_data(
        state=state,
        field_name="meeting_scheduled",
        value=True
    )

    assert result["status"] == "success"
    assert state["meeting_scheduled"] == True


@pytest.mark.asyncio
async def test_write_data_unknown_field():
    """Test error for unknown field."""
    state = ConversationState(
        conversation_id="conv-123",
        user_id="user-456",
        messages=[]
    )

    result = await write_data(
        state=state,
        field_name="unknown_field",
        value="value"
    )

    assert result["status"] == "error"
    assert "Unknown field" in result["message"]
