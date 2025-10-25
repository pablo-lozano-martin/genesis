# ABOUTME: WebSocket router for chat endpoints with LangGraph integration
# ABOUTME: Uses LangGraph streaming with automatic checkpointing

from fastapi import APIRouter, WebSocket, WebSocketException
from app.adapters.inbound.websocket_handler import handle_websocket_chat
from app.infrastructure.security.websocket_auth import get_user_from_websocket
from app.adapters.outbound.llm_providers.provider_factory import get_llm_provider
from app.adapters.outbound.repositories.mongo_conversation_repository import MongoConversationRepository
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat streaming using LangGraph.

    This endpoint:
    - Authenticates the user via token (query param or header)
    - Establishes a persistent WebSocket connection
    - Receives user messages
    - Streams LLM responses token-by-token via graph.astream_events()
    - Messages are automatically persisted via LangGraph checkpointer

    Authentication:
    - Send token as query parameter: /ws/chat?token=<jwt_token>
    - Or send in Authorization header: Bearer <jwt_token>

    Protocol:
    - Client sends: {"type": "message", "conversation_id": "uuid", "content": "..."}
    - Server streams: {"type": "token", "content": "..."}
    - Server completes: {"type": "complete", "conversation_id": "uuid"}
    - Server errors: {"type": "error", "message": "...", "code": "..."}

    Raises:
        WebSocketException: If authentication fails
    """
    try:
        user = await get_user_from_websocket(websocket)

        # Get compiled graph from app state
        graph = websocket.app.state.streaming_chat_graph

        llm_provider = get_llm_provider()
        conversation_repository = MongoConversationRepository()

        await handle_websocket_chat(
            websocket=websocket,
            user=user,
            graph=graph,
            llm_provider=llm_provider,
            conversation_repository=conversation_repository
        )

    except WebSocketException as e:
        logger.error(f"WebSocket authentication failed: {e.reason}")
        await websocket.close(code=e.code, reason=e.reason)
    except Exception as e:
        logger.error(f"Unexpected error in WebSocket endpoint: {e}")
        await websocket.close(code=1011, reason="Internal server error")
