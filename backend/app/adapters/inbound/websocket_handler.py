# ABOUTME: WebSocket handler for real-time chat streaming using LangGraph
# ABOUTME: Uses graph.astream_events() for token-by-token streaming with automatic checkpointing

import json
from typing import Dict
from fastapi import WebSocket, WebSocketDisconnect
from langgraph.types import RunnableConfig
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
from app.core.ports.llm_provider import ILLMProvider
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
    graph,
    llm_provider: ILLMProvider,
    conversation_repository: IConversationRepository
):
    """
    Handle WebSocket chat session for a user using LangGraph.

    This function:
    - Establishes the WebSocket connection
    - Receives user messages
    - Streams LLM responses token-by-token via graph.astream_events()
    - Messages are automatically persisted via LangGraph checkpointer
    - Handles errors and disconnections

    Args:
        websocket: WebSocket connection instance
        user: Authenticated user
        graph: Compiled LangGraph instance with checkpointing
        llm_provider: LLM provider for generating responses
        conversation_repository: Repository for conversation ownership verification
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

                # Verify conversation ownership (authorization at App DB layer)
                if not conversation or conversation.user_id != user.id:
                    logger.warning(f"User {user.id} attempted to access conversation {conversation_id}")
                    error_msg = ServerErrorMessage(
                        message="Conversation not found or access denied",
                        code="ACCESS_DENIED"
                    )
                    await manager.send_message(websocket, error_msg.model_dump())
                    continue

                # Create RunnableConfig with thread_id (conversation.id) and llm_provider
                config = RunnableConfig(
                    configurable={
                        "thread_id": conversation.id,
                        "llm_provider": llm_provider,
                        "user_id": user.id
                    }
                )

                # Prepare input for graph
                input_data = {
                    "user_input": client_message.content,
                    "conversation_id": conversation.id,
                    "user_id": user.id
                }

                logger.info(f"Starting LangGraph streaming for conversation {conversation_id}")

                try:
                    # Stream LLM tokens using graph.astream_events()
                    # Checkpointing happens automatically
                    async for event in graph.astream_events(input_data, config, version="v2"):
                        # Stream tokens from LLM to client
                        if event["event"] == "on_chat_model_stream":
                            chunk = event["data"]["chunk"]
                            if hasattr(chunk, 'content') and chunk.content:
                                token_msg = ServerTokenMessage(content=chunk.content)
                                await manager.send_message(websocket, token_msg.model_dump())

                    logger.info(f"LangGraph streaming completed for conversation {conversation_id}")

                    # Send completion message (checkpointing already done)
                    complete_msg = ServerCompleteMessage(
                        message_id=None,  # No longer tracking individual message IDs
                        conversation_id=conversation_id
                    )
                    await manager.send_message(websocket, complete_msg.model_dump())

                except Exception as e:
                    logger.error(f"LangGraph streaming failed for user {user.id}: {e}")
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
