# ABOUTME: Conversation domain model representing a chat conversation entity
# ABOUTME: Contains conversation metadata and relationship to users, database-agnostic

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Conversation(BaseModel):
    """
    Conversation domain model.

    Represents a conversation between a user and the AI assistant.
    This is a pure domain model without database concerns.
    """

    id: Optional[str] = Field(default=None, description="Conversation unique identifier")
    user_id: str = Field(..., description="ID of the user who owns this conversation")
    title: str = Field(default="New Conversation", max_length=200, description="Conversation title")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Conversation creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    message_count: int = Field(default=0, ge=0, description="Total number of messages in conversation")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439012",
                "user_id": "507f1f77bcf86cd799439011",
                "title": "How to use Python decorators",
                "created_at": "2025-01-15T10:30:00",
                "updated_at": "2025-01-15T10:45:00",
                "message_count": 4
            }
        }


class ConversationCreate(BaseModel):
    """Schema for creating a new conversation."""

    title: Optional[str] = Field(default="New Conversation", max_length=200)


class ConversationUpdate(BaseModel):
    """Schema for updating conversation information."""

    title: Optional[str] = Field(default=None, max_length=200)


class ConversationResponse(BaseModel):
    """Public conversation response schema."""

    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439012",
                "user_id": "507f1f77bcf86cd799439011",
                "title": "How to use Python decorators",
                "created_at": "2025-01-15T10:30:00",
                "updated_at": "2025-01-15T10:45:00",
                "message_count": 4
            }
        }
