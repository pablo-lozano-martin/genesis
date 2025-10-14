# ABOUTME: Authentication API router with registration, login, and user info endpoints
# ABOUTME: Implements inbound adapter for authentication use cases

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.core.domain.user import UserCreate, UserResponse
from app.core.use_cases.register_user import RegisterUser
from app.core.use_cases.authenticate_user import AuthenticateUser
from app.infrastructure.security.auth_service import AuthService
from app.infrastructure.security.dependencies import CurrentUser
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])

auth_service = AuthService()


class TokenResponse(BaseModel):
    """JWT token response schema."""
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """
    Register a new user.

    Args:
        user_data: User registration data

    Returns:
        Created user entity (without password)

    Raises:
        HTTPException: If user already exists or validation fails
    """
    logger.info(f"Registration attempt for user: {user_data.username}")

    try:
        from app.adapters.outbound.repositories.mongo_user_repository import MongoUserRepository

        user_repository = MongoUserRepository()
        register_use_case = RegisterUser(user_repository, auth_service)

        user = await register_use_case.execute(user_data)

        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/token", response_model=TokenResponse)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """
    Login and get JWT access token.

    OAuth2 compatible token endpoint using username and password.

    Args:
        form_data: OAuth2 password flow form data (username and password)

    Returns:
        JWT access token

    Raises:
        HTTPException: If credentials are invalid
    """
    logger.info(f"Login attempt for user: {form_data.username}")

    try:
        from app.adapters.outbound.repositories.mongo_user_repository import MongoUserRepository

        user_repository = MongoUserRepository()
        authenticate_use_case = AuthenticateUser(user_repository, auth_service)

        user, access_token = await authenticate_use_case.execute(
            form_data.username,
            form_data.password
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(current_user: CurrentUser):
    """
    Refresh JWT access token.

    Protected endpoint that issues a new access token for the authenticated user.
    This allows users to extend their session without re-entering credentials.

    Args:
        current_user: Current authenticated user from JWT token

    Returns:
        New JWT access token
    """
    logger.info(f"Token refresh for user: {current_user.id}")

    new_access_token = auth_service.create_access_token(user_id=current_user.id)

    return TokenResponse(
        access_token=new_access_token,
        token_type="bearer"
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser):
    """
    Get current user information.

    Protected endpoint that returns the authenticated user's information.

    Args:
        current_user: Current authenticated user from JWT token

    Returns:
        Current user information
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )
