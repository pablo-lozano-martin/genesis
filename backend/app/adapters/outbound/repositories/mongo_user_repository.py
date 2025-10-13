# ABOUTME: MongoDB implementation of IUserRepository port interface
# ABOUTME: Handles user data persistence using Beanie ODM

from typing import Optional, List
from datetime import datetime

from app.core.domain.user import User, UserCreate, UserUpdate
from app.core.ports.user_repository import IUserRepository
from app.adapters.outbound.repositories.mongo_models import UserDocument


class MongoUserRepository(IUserRepository):
    """
    MongoDB implementation of IUserRepository.

    This adapter implements the user repository port using MongoDB
    and Beanie ODM. It translates between domain models and MongoDB documents.
    """

    def _to_domain(self, doc: UserDocument) -> User:
        """Convert MongoDB document to domain model."""
        return User(
            id=str(doc.id),
            email=doc.email,
            username=doc.username,
            hashed_password=doc.hashed_password,
            full_name=doc.full_name,
            is_active=doc.is_active,
            created_at=doc.created_at,
            updated_at=doc.updated_at
        )

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
        existing_email = await UserDocument.find_one(UserDocument.email == user_data.email)
        if existing_email:
            raise ValueError(f"User with email {user_data.email} already exists")

        existing_username = await UserDocument.find_one(UserDocument.username == user_data.username)
        if existing_username:
            raise ValueError(f"User with username {user_data.username} already exists")

        doc = UserDocument(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
            full_name=user_data.full_name
        )

        await doc.insert()
        return self._to_domain(doc)

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Retrieve a user by ID."""
        doc = await UserDocument.get(user_id)
        return self._to_domain(doc) if doc else None

    async def get_by_email(self, email: str) -> Optional[User]:
        """Retrieve a user by email address."""
        doc = await UserDocument.find_one(UserDocument.email == email)
        return self._to_domain(doc) if doc else None

    async def get_by_username(self, username: str) -> Optional[User]:
        """Retrieve a user by username."""
        doc = await UserDocument.find_one(UserDocument.username == username)
        return self._to_domain(doc) if doc else None

    async def update(self, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """
        Update user information.

        Args:
            user_id: User unique identifier
            user_data: User update data

        Returns:
            Updated user entity if found, None otherwise
        """
        doc = await UserDocument.get(user_id)
        if not doc:
            return None

        update_dict = user_data.model_dump(exclude_unset=True)
        if update_dict:
            update_dict["updated_at"] = datetime.utcnow()
            for key, value in update_dict.items():
                setattr(doc, key, value)
            await doc.save()

        return self._to_domain(doc)

    async def delete(self, user_id: str) -> bool:
        """
        Delete a user.

        Args:
            user_id: User unique identifier

        Returns:
            True if user was deleted, False if not found
        """
        doc = await UserDocument.get(user_id)
        if not doc:
            return False

        await doc.delete()
        return True

    async def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """
        List users with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of user entities
        """
        docs = await UserDocument.find_all().skip(skip).limit(limit).to_list()
        return [self._to_domain(doc) for doc in docs]
