# ABOUTME: Unit tests for domain models validating Pydantic schemas
# ABOUTME: Tests User, Conversation, and Message domain models

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.core.domain.user import User, UserCreate, UserUpdate, UserResponse
from app.core.domain.conversation import Conversation, ConversationCreate, ConversationUpdate
from app.core.domain.message import Message, MessageCreate, MessageRole


class TestUserModel:
    """Tests for User domain model."""

    def test_user_creation_valid(self):
        """Test creating a valid user."""
        user = User(
            id="123",
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_pwd",
            full_name="Test User",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        assert user.id == "123"
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.is_active is True

    def test_user_create_valid(self):
        """Test UserCreate schema validation."""
        user_data = UserCreate(
            email="test@example.com",
            username="testuser",
            password="securepass123",
            full_name="Test User"
        )
        assert user_data.email == "test@example.com"
        assert user_data.password == "securepass123"

    def test_user_create_invalid_email(self):
        """Test UserCreate with invalid email."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="invalid-email",
                username="testuser",
                password="securepass123"
            )

    def test_user_create_short_username(self):
        """Test UserCreate with username too short."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                username="ab",
                password="securepass123"
            )

    def test_user_create_short_password(self):
        """Test UserCreate with password too short."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="short"
            )


class TestConversationModel:
    """Tests for Conversation domain model."""

    def test_conversation_creation_valid(self):
        """Test creating a valid conversation."""
        conversation = Conversation(
            id="conv123",
            user_id="user123",
            title="Test Conversation",
            message_count=5
        )
        assert conversation.id == "conv123"
        assert conversation.user_id == "user123"
        assert conversation.title == "Test Conversation"
        assert conversation.message_count == 5

    def test_conversation_default_title(self):
        """Test conversation with default title."""
        conversation = Conversation(
            user_id="user123"
        )
        assert conversation.title == "New Conversation"
        assert conversation.message_count == 0

    def test_conversation_create_valid(self):
        """Test ConversationCreate schema."""
        conv_data = ConversationCreate(title="Custom Title")
        assert conv_data.title == "Custom Title"

    def test_conversation_negative_message_count(self):
        """Test conversation with negative message count."""
        with pytest.raises(ValidationError):
            Conversation(
                user_id="user123",
                message_count=-1
            )


class TestMessageModel:
    """Tests for Message domain model."""

    def test_message_creation_valid(self):
        """Test creating a valid message."""
        message = Message(
            id="msg123",
            conversation_id="conv123",
            role=MessageRole.USER,
            content="Hello, world!"
        )
        assert message.id == "msg123"
        assert message.conversation_id == "conv123"
        assert message.role == MessageRole.USER
        assert message.content == "Hello, world!"

    def test_message_roles(self):
        """Test all message role types."""
        user_msg = Message(
            conversation_id="conv123",
            role=MessageRole.USER,
            content="User message"
        )
        assistant_msg = Message(
            conversation_id="conv123",
            role=MessageRole.ASSISTANT,
            content="Assistant message"
        )
        system_msg = Message(
            conversation_id="conv123",
            role=MessageRole.SYSTEM,
            content="System message"
        )

        assert user_msg.role == MessageRole.USER
        assert assistant_msg.role == MessageRole.ASSISTANT
        assert system_msg.role == MessageRole.SYSTEM

    def test_message_empty_content(self):
        """Test message with empty content."""
        with pytest.raises(ValidationError):
            Message(
                conversation_id="conv123",
                role=MessageRole.USER,
                content=""
            )

    def test_message_with_metadata(self):
        """Test message with metadata."""
        message = Message(
            conversation_id="conv123",
            role=MessageRole.USER,
            content="Test",
            metadata={"token_count": 10, "model": "gpt-4"}
        )
        assert message.metadata["token_count"] == 10
        assert message.metadata["model"] == "gpt-4"
