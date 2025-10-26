# ABOUTME: Node for validating incoming messages before LLM processing
# ABOUTME: Validates messages exist in state for LangGraph-native message handling

from app.langgraph.state import ConversationState
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


async def process_user_input(state: ConversationState) -> dict:
    """
    Validate that messages exist in state before proceeding to LLM.

    With LangGraph-first architecture, HumanMessage is created in the WebSocket
    handler and passed in the messages field. This node validates the state
    has messages before proceeding to the LLM node.

    Args:
        state: Current conversation state with messages from MessagesState

    Returns:
        Empty dict (no state update needed, just validation)
    """
    messages = state.get("messages", [])
    conversation_id = state.get("conversation_id", "unknown")

    logger.info(f"Validating input for conversation {conversation_id}: {len(messages)} messages in state")

    if not messages:
        logger.warning(f"No messages in state for conversation {conversation_id}")
        raise ValueError("No messages provided in state")

    # Validation passed, no state update needed
    return {}
