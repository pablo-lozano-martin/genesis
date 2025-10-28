# ABOUTME: WebSocket message protocol schemas for client-server communication
# ABOUTME: Defines message types for streaming chat interactions

from enum import Enum
from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """WebSocket message type enumeration."""

    MESSAGE = "message"
    TOKEN = "token"
    COMPLETE = "complete"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"
    TOOL_START = "tool_start"
    TOOL_COMPLETE = "tool_complete"


class ClientMessage(BaseModel):
    """
    Message sent from client to server.

    Represents a user message to be processed by the LLM.
    """

    type: MessageType = Field(default=MessageType.MESSAGE, description="Message type")
    conversation_id: str = Field(..., description="Conversation UUID")
    content: str = Field(..., min_length=1, description="User message content")


class ServerTokenMessage(BaseModel):
    """
    Token message sent from server to client during streaming.

    Contains a partial response token from the LLM.
    """

    type: MessageType = Field(default=MessageType.TOKEN, description="Message type")
    content: str = Field(..., description="Token content")


class ServerCompleteMessage(BaseModel):
    """
    Completion message sent from server to client.

    Indicates the LLM response is complete.
    """

    type: MessageType = Field(default=MessageType.COMPLETE, description="Message type")
    message_id: str = Field(..., description="Saved message UUID")
    conversation_id: str = Field(..., description="Conversation UUID")


class ServerErrorMessage(BaseModel):
    """
    Error message sent from server to client.

    Indicates an error occurred during processing.
    """

    type: MessageType = Field(default=MessageType.ERROR, description="Message type")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(default=None, description="Error code")


class PingMessage(BaseModel):
    """Ping message for connection health check."""

    type: MessageType = Field(default=MessageType.PING, description="Message type")


class PongMessage(BaseModel):
    """Pong response to ping."""

    type: MessageType = Field(default=MessageType.PONG, description="Message type")


class ServerToolStartMessage(BaseModel):
    """
    Server message indicating tool execution has started.

    Sent when the LLM decides to call a tool and before the tool executes.
    """

    type: Literal[MessageType.TOOL_START] = MessageType.TOOL_START
    tool_name: str = Field(..., description="Name of the tool being executed")
    tool_input: str = Field(..., description="JSON string of input arguments")
    source: Optional[str] = Field(
        default="local",
        description="Tool source: 'local' for Python tools, 'mcp' for MCP protocol tools"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO timestamp of tool start"
    )


class ServerToolCompleteMessage(BaseModel):
    """
    Server message indicating tool execution has completed.

    Sent when the tool finishes execution with results.
    """

    type: Literal[MessageType.TOOL_COMPLETE] = MessageType.TOOL_COMPLETE
    tool_name: str = Field(..., description="Name of the tool that completed")
    tool_result: str = Field(..., description="String representation of tool result")
    source: Optional[str] = Field(
        default="local",
        description="Tool source: 'local' for Python tools, 'mcp' for MCP protocol tools"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO timestamp of tool completion"
    )


ServerMessage = (
    ServerTokenMessage
    | ServerCompleteMessage
    | ServerErrorMessage
    | PongMessage
    | ServerToolStartMessage
    | ServerToolCompleteMessage
)
