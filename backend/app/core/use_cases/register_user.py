# ABOUTME: RegisterUser use case implementing user registration business logic
# ABOUTME: Handles user registration with validation and password hashing

from app.core.domain.user import User, UserCreate
from app.core.ports.user_repository import IUserRepository
from app.core.ports.auth_service import IAuthService


class RegisterUser:
    """
    Use case for registering a new user.

    This use case encapsulates the business logic for user registration,
    including validation, duplicate checking, and password hashing.
    It depends only on port interfaces, not concrete implementations.
    """

    def __init__(
        self,
        user_repository: IUserRepository,
        auth_service: IAuthService
    ):
        """
        Initialize the RegisterUser use case.

        Args:
            user_repository: User repository port for data operations
            auth_service: Auth service port for password hashing
        """
        self.user_repository = user_repository
        self.auth_service = auth_service

    async def execute(self, user_data: UserCreate) -> User:
        """
        Execute the user registration use case.

        Args:
            user_data: User registration data

        Returns:
            Created user entity

        Raises:
            ValueError: If user with email or username already exists
        """
        existing_user_email = await self.user_repository.get_by_email(user_data.email)
        if existing_user_email:
            raise ValueError(f"User with email {user_data.email} already exists")

        existing_user_username = await self.user_repository.get_by_username(user_data.username)
        if existing_user_username:
            raise ValueError(f"User with username {user_data.username} already exists")

        hashed_password = self.auth_service.hash_password(user_data.password)

        user = await self.user_repository.create(user_data, hashed_password)

        return user
