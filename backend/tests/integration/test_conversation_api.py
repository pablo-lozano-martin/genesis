# ABOUTME: Integration tests for conversation API endpoints
# ABOUTME: Tests conversation CRUD operations

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestConversationAPI:
    """Integration tests for conversation endpoints."""

    async def create_user_and_login(self, client: AsyncClient):
        """Helper to create a user and get auth token."""
        user_data = {
            "email": f"conv{pytest.random_id}@example.com",
            "username": f"convuser{pytest.random_id}",
            "password": "securepass123"
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

    @pytest.mark.asyncio
    async def test_create_conversation(self, client: AsyncClient):
        """Test creating a new conversation."""
        headers = await self.create_user_and_login(client)

        response = await client.post(
            "/api/conversations",
            json={"title": "Test Conversation"},
            headers=headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Conversation"
        assert data["message_count"] == 0
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_conversations(self, client: AsyncClient):
        """Test listing user conversations."""
        headers = await self.create_user_and_login(client)

        await client.post(
            "/api/conversations",
            json={"title": "Conversation 1"},
            headers=headers
        )

        await client.post(
            "/api/conversations",
            json={"title": "Conversation 2"},
            headers=headers
        )

        response = await client.get("/api/conversations", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_get_conversation(self, client: AsyncClient):
        """Test getting a specific conversation."""
        headers = await self.create_user_and_login(client)

        create_response = await client.post(
            "/api/conversations",
            json={"title": "Get Test"},
            headers=headers
        )

        conversation_id = create_response.json()["id"]

        response = await client.get(
            f"/api/conversations/{conversation_id}",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Get Test"
        assert data["id"] == conversation_id

    @pytest.mark.asyncio
    async def test_delete_conversation(self, client: AsyncClient):
        """Test deleting a conversation."""
        headers = await self.create_user_and_login(client)

        create_response = await client.post(
            "/api/conversations",
            json={"title": "To Delete"},
            headers=headers
        )

        conversation_id = create_response.json()["id"]

        delete_response = await client.delete(
            f"/api/conversations/{conversation_id}",
            headers=headers
        )

        assert delete_response.status_code == 204

        get_response = await client.get(
            f"/api/conversations/{conversation_id}",
            headers=headers
        )

        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client: AsyncClient):
        """Test that endpoints require authentication."""
        response = await client.get("/api/conversations")
        assert response.status_code == 401
