# ABOUTME: AuthenticateUser use case implementing user authentication business logic
# ABOUTME: Handles user login with credential validation and token generation

from typing import Tuple

from app.core.domain.user import User
from app.core.ports.user_repository import IUserRepository
from app.core.ports.auth_service import IAuthService


class AuthenticateUser:
    """
    Use case for authenticating a user.

    This use case encapsulates the business logic for user authentication,
    including credential validation and JWT token generation.
    It depends only on port interfaces, not concrete implementations.
    """

    def __init__(
        self,
        user_repository: IUserRepository,
        auth_service: IAuthService
    ):
        """
        Initialize the AuthenticateUser use case.

        Args:
            user_repository: User repository port for data operations
            auth_service: Auth service port for password verification and token generation
        """
        self.user_repository = user_repository
        self.auth_service = auth_service

    async def execute(self, username_or_email: str, password: str) -> Tuple[User, str]:
        """
        Execute the user authentication use case.

        Args:
            username_or_email: Username or email address
            password: Plain text password

        Returns:
            Tuple of (User entity, JWT access token)

        Raises:
            ValueError: If credentials are invalid or user is inactive
        """
        user = await self.user_repository.get_by_email(username_or_email)
        if not user:
            user = await self.user_repository.get_by_username(username_or_email)

        if not user:
            raise ValueError("Invalid credentials")

        if not self.auth_service.verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")

        if not user.is_active:
            raise ValueError("User account is inactive")

        access_token = self.auth_service.create_access_token(user.id)

        return user, access_token
