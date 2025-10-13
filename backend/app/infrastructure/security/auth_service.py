# ABOUTME: Authentication service implementation handling password hashing and JWT tokens
# ABOUTME: Implements IAuthService port interface using bcrypt and python-jose

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.ports.auth_service import IAuthService
from app.core.ports.user_repository import IUserRepository
from app.core.domain.user import User
from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService(IAuthService):
    """
    Authentication service implementation.

    Provides password hashing with bcrypt and JWT token operations.
    This is an adapter that implements the IAuthService port.
    """

    def hash_password(self, password: str) -> str:
        """
        Hash a plain text password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Bcrypt hashed password
        """
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain text password against a hashed password.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Bcrypt hashed password to compare against

        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, user_id: str) -> str:
        """
        Create a JWT access token for a user.

        Args:
            user_id: User unique identifier

        Returns:
            JWT access token
        """
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        to_encode = {
            "sub": user_id,
            "exp": expire,
            "type": "access"
        }
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[str]:
        """
        Verify a JWT token and extract the user ID.

        Args:
            token: JWT token to verify

        Returns:
            User ID if token is valid, None otherwise
        """
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
            return user_id
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None

    async def get_current_user(self, token: str, user_repository: IUserRepository) -> Optional[User]:
        """
        Get the current user from a JWT token.

        Args:
            token: JWT access token
            user_repository: User repository instance to fetch user data

        Returns:
            User entity if token is valid and user exists, None otherwise
        """
        user_id = self.verify_token(token)
        if user_id is None:
            return None

        user = await user_repository.get_by_id(user_id)
        return user
