# ABOUTME: Unit tests for domain models validating Pydantic schemas
# ABOUTME: Tests User and Conversation domain models

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.core.domain.user import User, UserCreate, UserUpdate, UserResponse
from app.core.domain.conversation import Conversation, ConversationCreate, ConversationUpdate


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
            title="Test Conversation"
        )
        assert conversation.id == "conv123"
        assert conversation.user_id == "user123"
        assert conversation.title == "Test Conversation"

    def test_conversation_default_title(self):
        """Test conversation with default title."""
        conversation = Conversation(
            user_id="user123"
        )
        assert conversation.title == "New Conversation"
        assert conversation.message_count is None

    def test_conversation_create_valid(self):
        """Test ConversationCreate schema."""
        conv_data = ConversationCreate(title="Custom Title")
        assert conv_data.title == "Custom Title"

