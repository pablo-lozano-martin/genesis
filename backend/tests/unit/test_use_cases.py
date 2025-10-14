# ABOUTME: Unit tests for use cases with mocked dependencies
# ABOUTME: Tests business logic in isolation from infrastructure

import pytest
from unittest.mock import AsyncMock

from app.core.use_cases.register_user import RegisterUser
from app.core.use_cases.authenticate_user import AuthenticateUser
from app.core.domain.user import User, UserCreate


@pytest.mark.unit
class TestRegisterUser:
    """Tests for RegisterUser use case."""

    @pytest.mark.asyncio
    async def test_register_user_success(
        self, mock_user_repository, auth_service, sample_user_create
    ):
        """Test successful user registration."""
        mock_user_repository.get_by_email = AsyncMock(return_value=None)
        mock_user_repository.get_by_username = AsyncMock(return_value=None)
        mock_user_repository.create = AsyncMock(
            return_value=User(
                id="new-user-id",
                email=sample_user_create.email,
                username=sample_user_create.username,
                hashed_password="hashed",
                is_active=True
            )
        )

        use_case = RegisterUser(mock_user_repository, auth_service)
        user = await use_case.execute(sample_user_create)

        assert user.id == "new-user-id"
        assert user.email == sample_user_create.email
        assert user.username == sample_user_create.username
        mock_user_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(
        self, mock_user_repository, auth_service, sample_user_create, sample_user
    ):
        """Test registration with duplicate email."""
        mock_user_repository.get_by_email = AsyncMock(return_value=sample_user)

        use_case = RegisterUser(mock_user_repository, auth_service)

        with pytest.raises(ValueError, match="already exists"):
            await use_case.execute(sample_user_create)

    @pytest.mark.asyncio
    async def test_register_user_duplicate_username(
        self, mock_user_repository, auth_service, sample_user_create, sample_user
    ):
        """Test registration with duplicate username."""
        mock_user_repository.get_by_email = AsyncMock(return_value=None)
        mock_user_repository.get_by_username = AsyncMock(return_value=sample_user)

        use_case = RegisterUser(mock_user_repository, auth_service)

        with pytest.raises(ValueError, match="already exists"):
            await use_case.execute(sample_user_create)


@pytest.mark.unit
class TestAuthenticateUser:
    """Tests for AuthenticateUser use case."""

    @pytest.mark.asyncio
    async def test_authenticate_user_success(
        self, mock_user_repository, auth_service, sample_user
    ):
        """Test successful authentication."""
        mock_user_repository.get_by_username = AsyncMock(return_value=sample_user)

        hashed = auth_service.hash_password("testpass123")
        sample_user.hashed_password = hashed

        use_case = AuthenticateUser(mock_user_repository, auth_service)
        user, token = await use_case.execute("testuser", "testpass123")

        assert user.id == sample_user.id
        assert user.username == sample_user.username
        assert token is not None
        assert isinstance(token, str)

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_username(
        self, mock_user_repository, auth_service
    ):
        """Test authentication with invalid username."""
        mock_user_repository.get_by_username = AsyncMock(return_value=None)

        use_case = AuthenticateUser(mock_user_repository, auth_service)

        with pytest.raises(ValueError, match="Invalid credentials"):
            await use_case.execute("nonexistent", "password")

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_password(
        self, mock_user_repository, auth_service, sample_user
    ):
        """Test authentication with invalid password."""
        mock_user_repository.get_by_username = AsyncMock(return_value=sample_user)
        sample_user.hashed_password = auth_service.hash_password("correctpass")

        use_case = AuthenticateUser(mock_user_repository, auth_service)

        with pytest.raises(ValueError, match="Invalid credentials"):
            await use_case.execute("testuser", "wrongpass")

    @pytest.mark.asyncio
    async def test_authenticate_user_inactive(
        self, mock_user_repository, auth_service, sample_user
    ):
        """Test authentication with inactive user."""
        sample_user.is_active = False
        sample_user.hashed_password = auth_service.hash_password("testpass123")
        mock_user_repository.get_by_username = AsyncMock(return_value=sample_user)

        use_case = AuthenticateUser(mock_user_repository, auth_service)

        with pytest.raises(ValueError, match="inactive"):
            await use_case.execute("testuser", "testpass123")
