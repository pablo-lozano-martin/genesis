# ABOUTME: WebSocket message protocol schemas for client-server communication
# ABOUTME: Defines message types for streaming chat interactions

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """WebSocket message type enumeration."""

    MESSAGE = "message"
    TOKEN = "token"
    COMPLETE = "complete"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


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
