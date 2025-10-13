# ABOUTME: Authentication service port interface defining the contract for auth operations
# ABOUTME: Abstract interface following hexagonal architecture principles

from abc import ABC, abstractmethod
from typing import Optional

from app.core.domain.user import User


class IAuthService(ABC):
    """
    Authentication service port interface.

    Defines the contract for authentication operations. Implementations
    of this interface (adapters) handle password hashing, token generation,
    and validation without the core domain knowing about cryptographic details.
    """

    @abstractmethod
    def hash_password(self, password: str) -> str:
        """
        Hash a plain text password.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        pass

    @abstractmethod
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain text password against a hashed password.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against

        Returns:
            True if password matches, False otherwise
        """
        pass

    @abstractmethod
    def create_access_token(self, user_id: str) -> str:
        """
        Create a JWT access token for a user.

        Args:
            user_id: User unique identifier

        Returns:
            JWT access token
        """
        pass

    @abstractmethod
    def verify_token(self, token: str) -> Optional[str]:
        """
        Verify a JWT token and extract the user ID.

        Args:
            token: JWT token to verify

        Returns:
            User ID if token is valid, None otherwise
        """
        pass

    @abstractmethod
    async def get_current_user(self, token: str, user_repository) -> Optional[User]:
        """
        Get the current user from a JWT token.

        Args:
            token: JWT access token
            user_repository: User repository instance to fetch user data

        Returns:
            User entity if token is valid and user exists, None otherwise
        """
        pass
