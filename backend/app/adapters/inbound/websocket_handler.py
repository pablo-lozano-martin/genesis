# ABOUTME: WebSocket handler for real-time chat streaming
# ABOUTME: Manages WebSocket connections and streams LLM responses token-by-token

import json
from typing import Dict
from fastapi import WebSocket, WebSocketDisconnect
from app.adapters.inbound.websocket_schemas import (
    ClientMessage,
    ServerTokenMessage,
    ServerCompleteMessage,
    ServerErrorMessage,
    PingMessage,
    PongMessage,
    MessageType
)
from app.core.domain.user import User
from app.core.domain.message import Message, MessageRole
from app.core.ports.llm_provider import ILLMProvider
from app.core.ports.message_repository import IMessageRepository
from app.core.ports.conversation_repository import IConversationRepository
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for chat sessions.

    Maintains active connections and handles broadcasting to specific clients.
    """

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"WebSocket connected for user {user_id}")

    def disconnect(self, user_id: str):
        """Unregister a WebSocket connection."""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_message(self, websocket: WebSocket, message: dict):
        """Send a message to a specific WebSocket."""
        await websocket.send_text(json.dumps(message))


manager = ConnectionManager()


async def handle_websocket_chat(
    websocket: WebSocket,
    user: User,
    llm_provider: ILLMProvider,
    message_repository: IMessageRepository,
    conversation_repository: IConversationRepository
):
    """
    Handle WebSocket chat session for a user.

    This function:
    - Establishes the WebSocket connection
    - Receives user messages
    - Streams LLM responses token-by-token
    - Persists messages to the database
    - Handles errors and disconnections

    Args:
        websocket: WebSocket connection instance
        user: Authenticated user
        llm_provider: LLM provider for generating responses
        message_repository: Repository for persisting messages
        conversation_repository: Repository for conversation metadata
    """
    await manager.connect(websocket, user.id)

    try:
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(f"Received message from user {user.id}: {data[:100]}")

                try:
                    raw_message = json.loads(data)
                    message_type = raw_message.get("type")

                    if message_type == MessageType.PING:
                        PingMessage.model_validate(raw_message)
                        await manager.send_message(websocket, PongMessage().model_dump())
                        continue

                    client_message = ClientMessage.model_validate(raw_message)
                except Exception as e:
                    logger.error(f"Invalid message format from user {user.id}: {e}")
                    error_msg = ServerErrorMessage(
                        message="Invalid message format",
                        code="INVALID_FORMAT"
                    )
                    await manager.send_message(websocket, error_msg.model_dump())
                    continue

                conversation_id = client_message.conversation_id
                conversation = await conversation_repository.get_by_id(conversation_id)

                if not conversation or conversation.user_id != user.id:
                    logger.warning(f"User {user.id} attempted to access conversation {conversation_id}")
                    error_msg = ServerErrorMessage(
                        message="Conversation not found or access denied",
                        code="ACCESS_DENIED"
                    )
                    await manager.send_message(websocket, error_msg.model_dump())
                    continue

                user_message = Message(
                    conversation_id=conversation_id,
                    role=MessageRole.USER,
                    content=client_message.content
                )

                saved_user_message = await message_repository.create(user_message)
                logger.info(f"Saved user message {saved_user_message.id} to conversation {conversation_id}")

                messages = await message_repository.get_by_conversation_id(conversation_id)

                full_response = []
                try:
                    async for token in llm_provider.stream(messages):
                        full_response.append(token)
                        token_msg = ServerTokenMessage(content=token)
                        await manager.send_message(websocket, token_msg.model_dump())

                    response_content = "".join(full_response)

                    assistant_message = Message(
                        conversation_id=conversation_id,
                        role=MessageRole.ASSISTANT,
                        content=response_content
                    )

                    saved_assistant_message = await message_repository.create(assistant_message)
                    logger.info(f"Saved assistant message {saved_assistant_message.id} to conversation {conversation_id}")

                    await conversation_repository.increment_message_count(conversation_id, 2)

                    complete_msg = ServerCompleteMessage(
                        message_id=saved_assistant_message.id,
                        conversation_id=conversation_id
                    )
                    await manager.send_message(websocket, complete_msg.model_dump())

                except Exception as e:
                    logger.error(f"LLM streaming failed for user {user.id}: {e}")
                    error_msg = ServerErrorMessage(
                        message=f"Failed to generate response: {str(e)}",
                        code="LLM_ERROR"
                    )
                    await manager.send_message(websocket, error_msg.model_dump())

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for user {user.id}")
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message for user {user.id}: {e}")
                try:
                    error_msg = ServerErrorMessage(
                        message="Internal server error",
                        code="INTERNAL_ERROR"
                    )
                    await manager.send_message(websocket, error_msg.model_dump())
                except:
                    break

    finally:
        manager.disconnect(user.id)
