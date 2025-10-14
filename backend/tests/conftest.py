# ABOUTME: Pytest configuration and shared fixtures for testing
# ABOUTME: Provides reusable test fixtures for database, app, and client setup

import pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from unittest.mock import AsyncMock, MagicMock

from app.main import create_app
from app.core.domain.user import User, UserCreate
from app.core.domain.conversation import Conversation
from app.core.domain.message import Message, MessageRole
from app.infrastructure.security.auth_service import AuthService


@pytest.fixture
async def app() -> FastAPI:
    """Create a FastAPI application instance for testing."""
    return create_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing API endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_user_repository():
    """Create a mock user repository for testing."""
    return AsyncMock()


@pytest.fixture
def mock_conversation_repository():
    """Create a mock conversation repository for testing."""
    return AsyncMock()


@pytest.fixture
def mock_message_repository():
    """Create a mock message repository for testing."""
    return AsyncMock()


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider for testing."""
    mock = AsyncMock()
    mock.generate = AsyncMock(return_value="Test LLM response")

    async def mock_stream():
        for token in ["Test ", "LLM ", "response"]:
            yield token

    mock.stream = mock_stream
    return mock


@pytest.fixture
def sample_user() -> User:
    """Create a sample user for testing."""
    return User(
        id="test-user-id",
        email="test@example.com",
        username="testuser",
        hashed_password="$2b$12$hashedpassword",
        full_name="Test User",
        is_active=True
    )


@pytest.fixture
def sample_user_create() -> UserCreate:
    """Create a sample user creation data for testing."""
    return UserCreate(
        email="test@example.com",
        username="testuser",
        password="testpass123",
        full_name="Test User"
    )


@pytest.fixture
def sample_conversation(sample_user: User) -> Conversation:
    """Create a sample conversation for testing."""
    return Conversation(
        id="test-conversation-id",
        user_id=sample_user.id,
        title="Test Conversation",
        message_count=0
    )


@pytest.fixture
def sample_message(sample_conversation: Conversation) -> Message:
    """Create a sample message for testing."""
    return Message(
        id="test-message-id",
        conversation_id=sample_conversation.id,
        role=MessageRole.USER,
        content="Test message content"
    )


@pytest.fixture
def auth_service():
    """Create an auth service instance for testing."""
    return AuthService()
