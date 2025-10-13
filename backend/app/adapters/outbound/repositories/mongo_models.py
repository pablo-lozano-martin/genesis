# ABOUTME: Beanie ODM document models for MongoDB collections
# ABOUTME: Maps domain models to MongoDB documents with indexes and validation

from datetime import datetime
from typing import Optional
from beanie import Document, Indexed
from pydantic import EmailStr, Field

from app.core.domain.message import MessageRole


class UserDocument(Document):
    """
    User MongoDB document model.

    Maps the User domain model to MongoDB collection with indexes.
    """

    email: Indexed(EmailStr, unique=True)
    username: Indexed(str, unique=True)
    hashed_password: str
    full_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
        indexes = [
            "email",
            "username",
        ]


class ConversationDocument(Document):
    """
    Conversation MongoDB document model.

    Maps the Conversation domain model to MongoDB collection with indexes.
    """

    user_id: Indexed(str)
    title: str = "New Conversation"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = 0

    class Settings:
        name = "conversations"
        indexes = [
            "user_id",
            [("user_id", 1), ("updated_at", -1)],
        ]


class MessageDocument(Document):
    """
    Message MongoDB document model.

    Maps the Message domain model to MongoDB collection with indexes.
    """

    conversation_id: Indexed(str)
    role: MessageRole
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[dict] = None

    class Settings:
        name = "messages"
        indexes = [
            "conversation_id",
            [("conversation_id", 1), ("created_at", 1)],
        ]
