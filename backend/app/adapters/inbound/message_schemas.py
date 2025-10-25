# ABOUTME: Message API response schemas for message endpoints
# ABOUTME: Defines response formats for message retrieval from LangGraph checkpoints

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Enumeration of message roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


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
