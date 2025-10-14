# ABOUTME: User REST API endpoints for profile management
# ABOUTME: Provides user profile viewing and updating

from fastapi import APIRouter, HTTPException, status
from app.core.domain.user import UserUpdate, UserResponse
from app.infrastructure.security.dependencies import CurrentUser
from app.adapters.outbound.repositories.mongo_user_repository import MongoUserRepository
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/user", tags=["user"])

user_repository = MongoUserRepository()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser):
    """
    Get current user information.

    Protected endpoint that returns the authenticated user's information.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: CurrentUser
):
    """
    Update current user information.

    Allows users to update their email, username, and full name.
    Password changes should be handled through a separate password reset flow.
    """
    logger.info(f"Updating user {current_user.id}")

    if user_data.email:
        existing = await user_repository.get_by_email(user_data.email)
        if existing and existing.id != current_user.id:
            logger.warning(f"Email {user_data.email} already in use")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )

    if user_data.username:
        existing = await user_repository.get_by_username(user_data.username)
        if existing and existing.id != current_user.id:
            logger.warning(f"Username {user_data.username} already in use")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already in use"
            )

    try:
        updated_user = await user_repository.update(current_user.id, user_data)

        logger.info(f"Updated user {current_user.id}")

        return UserResponse(
            id=updated_user.id,
            email=updated_user.email,
            username=updated_user.username,
            full_name=updated_user.full_name,
            is_active=updated_user.is_active,
            created_at=updated_user.created_at
        )

    except Exception as e:
        logger.error(f"Failed to update user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )
