# ABOUTME: Integration tests for message creation API endpoint
# ABOUTME: Tests POST /api/conversations/{id}/messages with authorization and error handling

import pytest
from httpx import AsyncClient
import random
import string


@pytest.mark.integration
class TestMessageCreationAPI:
    """Integration tests for POST /api/conversations/{id}/messages."""

    async def create_user_and_login(self, client: AsyncClient) -> dict:
        """Helper: Create user and return auth headers."""
        unique_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        user_data = {
            "email": f"msg{unique_id}@example.com",
            "username": f"msguser{unique_id}",
            "password": "securepass123",
            "full_name": "Test User"
        }

        await client.post("/api/auth/register", json=user_data)

        login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }

        response = await client.post(
            "/api/auth/token",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    async def create_conversation(self, client: AsyncClient, headers: dict) -> str:
        """Helper: Create conversation and return ID."""
        response = await client.post(
            "/api/conversations",
            json={"title": "Test"},
            headers=headers
        )
        return response.json()["id"]

    @pytest.mark.asyncio
    async def test_create_message_success(self, client: AsyncClient):
        """Test successful message creation with both messages."""
        headers = await self.create_user_and_login(client)
        conversation_id = await self.create_conversation(client, headers)

        response = await client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": "What is Python?"},
            headers=headers
        )

        assert response.status_code == 201
        data = response.json()
        assert "user_message" in data
        assert "assistant_message" in data
        assert data["user_message"]["content"] == "What is Python?"
        assert data["user_message"]["role"] == "user"
        assert data["assistant_message"]["role"] == "assistant"
        assert len(data["assistant_message"]["content"]) > 0

    @pytest.mark.asyncio
    async def test_create_message_conversation_not_found(self, client: AsyncClient):
        """Test 404 when conversation doesn't exist."""
        headers = await self.create_user_and_login(client)

        response = await client.post(
            "/api/conversations/000000000000000000000000/messages",
            json={"content": "Hello"},
            headers=headers
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_message_access_denied(self, client: AsyncClient):
        """Test 403 when user doesn't own conversation."""
        headers_a = await self.create_user_and_login(client)
        conversation_id = await self.create_conversation(client, headers_a)

        headers_b = await self.create_user_and_login(client)
        response = await client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": "Hacked"},
            headers=headers_b
        )

        assert response.status_code == 403
        assert "denied" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_message_unauthorized(self, client: AsyncClient):
        """Test 401 when not authenticated."""
        response = await client.post(
            "/api/conversations/any-id/messages",
            json={"content": "Hello"}
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_message_validation_error(self, client: AsyncClient):
        """Test 422 when content validation fails."""
        headers = await self.create_user_and_login(client)
        conversation_id = await self.create_conversation(client, headers)

        response = await client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": ""},
            headers=headers
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_message_updates_count(self, client: AsyncClient):
        """Test that message_count is updated after creation."""
        headers = await self.create_user_and_login(client)
        conversation_id = await self.create_conversation(client, headers)

        await client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": "Hello"},
            headers=headers
        )

        response = await client.get(
            f"/api/conversations/{conversation_id}",
            headers=headers
        )

        assert response.json()["message_count"] == 2


@pytest.fixture(scope="session", autouse=True)
def setup_test_ids():
    """Setup random ID for test isolation."""
    pytest.random_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
