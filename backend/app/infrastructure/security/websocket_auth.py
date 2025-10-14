# ABOUTME: WebSocket authentication utilities for secure WebSocket connections
# ABOUTME: Validates JWT tokens from WebSocket query parameters or headers

from typing import Optional
from fastapi import WebSocket, WebSocketException, status
from app.core.domain.user import User
from app.infrastructure.security.auth_service import AuthService
from app.adapters.outbound.repositories.mongo_user_repository import MongoUserRepository
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

auth_service = AuthService()


async def get_user_from_websocket(websocket: WebSocket) -> Optional[User]:
    """
    Extract and validate user from WebSocket connection.

    Attempts to authenticate the user by:
    1. Checking for 'token' query parameter
    2. Checking for 'Authorization' header
    3. Validating the JWT token
    4. Retrieving the user from the database

    Args:
        websocket: WebSocket connection instance

    Returns:
        User entity if authentication successful, None otherwise

    Raises:
        WebSocketException: If authentication fails
    """
    token = None

    if "token" in websocket.query_params:
        token = websocket.query_params["token"]
        logger.debug("Token extracted from query parameters")
    elif "authorization" in websocket.headers:
        auth_header = websocket.headers["authorization"]
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            logger.debug("Token extracted from Authorization header")

    if not token:
        logger.warning("No authentication token provided in WebSocket connection")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication token required"
        )

    user_repository = MongoUserRepository()

    try:
        user = await auth_service.get_current_user(token, user_repository)

        if user is None:
            logger.warning("Invalid token provided in WebSocket connection")
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid authentication credentials"
            )

        if not user.is_active:
            logger.warning(f"Inactive user {user.id} attempted WebSocket connection")
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="User account is inactive"
            )

        logger.info(f"User {user.id} authenticated for WebSocket connection")
        return user

    except WebSocketException:
        raise
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {e}")
        raise WebSocketException(
            code=status.WS_1011_INTERNAL_ERROR,
            reason="Authentication failed"
        )
