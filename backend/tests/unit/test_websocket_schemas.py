"""Unit tests for WebSocket message schemas."""
import pytest
from pydantic import ValidationError
from app.adapters.inbound.websocket_schemas import (
    ServerToolStartMessage,
    ServerToolCompleteMessage,
    MessageType,
)


class TestServerToolStartMessage:
    """Tests for ServerToolStartMessage schema."""

    def test_valid_tool_start_message(self):
        """Test creating valid tool start message."""
        msg = ServerToolStartMessage(
            tool_name="add",
            tool_input='{"a": 5, "b": 3}'
        )
        assert msg.type == MessageType.TOOL_START
        assert msg.tool_name == "add"
        assert msg.tool_input == '{"a": 5, "b": 3}'
        assert msg.timestamp is not None

    def test_tool_start_serialization(self):
        """Test that message serializes correctly."""
        msg = ServerToolStartMessage(
            tool_name="multiply",
            tool_input='{"a": 6, "b": 7}'
        )
        dumped = msg.model_dump()
        assert dumped["type"] == "tool_start"
        assert dumped["tool_name"] == "multiply"

    def test_tool_start_requires_tool_name(self):
        """Test that tool_name is required."""
        with pytest.raises(ValidationError):
            ServerToolStartMessage(tool_input='{"a": 5}')

    def test_tool_start_requires_tool_input(self):
        """Test that tool_input is required."""
        with pytest.raises(ValidationError):
            ServerToolStartMessage(tool_name="add")


class TestServerToolCompleteMessage:
    """Tests for ServerToolCompleteMessage schema."""

    def test_valid_tool_complete_message(self):
        """Test creating valid tool complete message."""
        msg = ServerToolCompleteMessage(
            tool_name="add",
            tool_result="8"
        )
        assert msg.type == MessageType.TOOL_COMPLETE
        assert msg.tool_name == "add"
        assert msg.tool_result == "8"
        assert msg.timestamp is not None

    def test_tool_complete_serialization(self):
        """Test that message serializes correctly."""
        msg = ServerToolCompleteMessage(
            tool_name="multiply",
            tool_result="42"
        )
        dumped = msg.model_dump()
        assert dumped["type"] == "tool_complete"
        assert dumped["tool_name"] == "multiply"
        assert dumped["tool_result"] == "42"

    def test_tool_complete_requires_tool_name(self):
        """Test that tool_name is required."""
        with pytest.raises(ValidationError):
            ServerToolCompleteMessage(tool_result="8")

    def test_tool_complete_requires_tool_result(self):
        """Test that tool_result is required."""
        with pytest.raises(ValidationError):
            ServerToolCompleteMessage(tool_name="add")
