# ABOUTME: User repository port interface defining the contract for user data operations
# ABOUTME: Abstract interface following hexagonal architecture principles

from abc import ABC, abstractmethod
from typing import Optional, List

from app.core.domain.user import User, UserCreate, UserUpdate


class IUserRepository(ABC):
    """
    User repository port interface.

    Defines the contract for user data operations. Implementations
    of this interface (adapters) handle the actual data persistence
    without the core domain knowing about database details.
    """

    @abstractmethod
    async def create(self, user_data: UserCreate, hashed_password: str) -> User:
        """
        Create a new user.

        Args:
            user_data: User creation data
            hashed_password: Pre-hashed password

        Returns:
            Created user entity

        Raises:
            ValueError: If user with email or username already exists
        """
        pass

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """
        Retrieve a user by ID.

        Args:
            user_id: User unique identifier

        Returns:
            User entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve a user by email address.

        Args:
            email: User email address

        Returns:
            User entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:
        """
        Retrieve a user by username.

        Args:
            username: Username

        Returns:
            User entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def update(self, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """
        Update user information.

        Args:
            user_id: User unique identifier
            user_data: User update data

        Returns:
            Updated user entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete(self, user_id: str) -> bool:
        """
        Delete a user.

        Args:
            user_id: User unique identifier

        Returns:
            True if user was deleted, False if not found
        """
        pass

    @abstractmethod
    async def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """
        List users with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of user entities
        """
        pass
