# ABOUTME: FastAPI security dependencies for OAuth2 authentication
# ABOUTME: Provides dependency functions for protected routes and current user retrieval

from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.domain.user import User
from app.infrastructure.security.auth_service import AuthService
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

auth_service = AuthService()


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    """
    Dependency to get the current authenticated user.

    Args:
        token: JWT access token from OAuth2PasswordBearer

    Returns:
        Current user entity

    Raises:
        HTTPException: If token is invalid or user not found
    """
    from app.adapters.outbound.repositories.mongo_user_repository import MongoUserRepository

    user_repository = MongoUserRepository()

    user = await auth_service.get_current_user(token, user_repository)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Dependency to get the current active user.

    Args:
        current_user: Current user from get_current_user dependency

    Returns:
        Current active user entity

    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


CurrentUser = Annotated[User, Depends(get_current_active_user)]
