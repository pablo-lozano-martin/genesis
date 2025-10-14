# ABOUTME: Integration tests for authentication API endpoints
# ABOUTME: Tests register, login, and token refresh functionality

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestAuthAPI:
    """Integration tests for authentication endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "Genesis" in data["app"]

    @pytest.mark.asyncio
    async def test_register_user_success(self, client: AsyncClient):
        """Test successful user registration."""
        user_data = {
            "email": f"test{pytest.random_id}@example.com",
            "username": f"testuser{pytest.random_id}",
            "password": "securepass123",
            "full_name": "Test User"
        }

        response = await client.post("/api/auth/register", json=user_data)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert "password" not in data

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email."""
        user_data = {
            "email": "invalid-email",
            "username": "testuser",
            "password": "securepass123"
        }

        response = await client.post("/api/auth/register", json=user_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_flow(self, client: AsyncClient):
        """Test complete login flow."""
        user_data = {
            "email": f"login{pytest.random_id}@example.com",
            "username": f"loginuser{pytest.random_id}",
            "password": "securepass123"
        }

        register_response = await client.post("/api/auth/register", json=user_data)
        assert register_response.status_code == 201

        login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }

        response = await client.post(
            "/api/auth/token",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        token = data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        me_response = await client.get("/api/auth/me", headers=headers)
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["username"] == user_data["username"]

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Test login with invalid credentials."""
        login_data = {
            "username": "nonexistent",
            "password": "wrongpass"
        }

        response = await client.post(
            "/api/auth/token",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 401


@pytest.fixture(scope="session", autouse=True)
def setup_test_ids():
    """Setup random ID for test isolation."""
    import random
    import string
    pytest.random_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
