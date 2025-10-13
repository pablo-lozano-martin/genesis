# ABOUTME: Message domain model representing a single message in a conversation
# ABOUTME: Contains message content, role, and metadata, database-agnostic

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Enumeration of message roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """
    Message domain model.

    Represents a single message in a conversation, which can be from
    the user, assistant, or system. This is a pure domain model
    without database concerns.
    """

    id: Optional[str] = Field(default=None, description="Message unique identifier")
    conversation_id: str = Field(..., description="ID of the conversation this message belongs to")
    role: MessageRole = Field(..., description="Role of the message sender")
    content: str = Field(..., min_length=1, description="Message content")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Message creation timestamp")
    metadata: Optional[dict] = Field(default=None, description="Additional metadata for the message")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439013",
                "conversation_id": "507f1f77bcf86cd799439012",
                "role": "user",
                "content": "How do I use Python decorators?",
                "created_at": "2025-01-15T10:30:00",
                "metadata": {"token_count": 8}
            }
        }


class MessageCreate(BaseModel):
    """Schema for creating a new message."""

    conversation_id: str
    role: MessageRole
    content: str = Field(..., min_length=1)
    metadata: Optional[dict] = None


class MessageResponse(BaseModel):
    """Public message response schema."""

    id: str
    conversation_id: str
    role: MessageRole
    content: str
    created_at: datetime
    metadata: Optional[dict] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439013",
                "conversation_id": "507f1f77bcf86cd799439012",
                "role": "user",
                "content": "How do I use Python decorators?",
                "created_at": "2025-01-15T10:30:00",
                "metadata": {"token_count": 8}
            }
        }
