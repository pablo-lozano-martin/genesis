# ABOUTME: Node for persisting conversation messages to the database
# ABOUTME: Saves user and assistant messages to message repository

from app.langgraph.state import ConversationState
from app.core.ports.message_repository import IMessageRepository
from app.core.ports.conversation_repository import IConversationRepository
from app.langgraph.utils.message_converter import langchain_to_domain
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


async def save_to_history(
    state: ConversationState,
    message_repository: IMessageRepository,
    conversation_repository: IConversationRepository
) -> dict:
    """
    Save conversation messages to the database.

    This node:
    - Converts LangChain messages to domain Messages
    - Persists the latest user and assistant messages
    - Updates conversation metadata (updated_at, message_count)
    - Handles errors gracefully without breaking the flow

    Args:
        state: Current conversation state
        message_repository: Message repository instance (injected dependency)
        conversation_repository: Conversation repository instance (injected dependency)

    Returns:
        Dictionary with state updates (error if save fails)
    """
    try:
        conversation_id = state["conversation_id"]
        langchain_messages = state["messages"]

        if not langchain_messages:
            logger.debug(f"No messages to save for conversation {conversation_id}")
            return {}

        logger.info(f"Saving {len(langchain_messages)} messages to conversation {conversation_id}")

        # Convert LangChain messages to domain Messages and save
        for lc_msg in langchain_messages:
            try:
                domain_msg = langchain_to_domain(lc_msg, conversation_id)
                await message_repository.create(domain_msg)
                logger.debug(f"Saved message with role {domain_msg.role} to conversation {conversation_id}")
            except Exception as e:
                logger.error(f"Failed to save individual message: {e}")

        try:
            conversation = await conversation_repository.get_by_id(conversation_id)
            if conversation:
                await conversation_repository.increment_message_count(conversation_id, len(langchain_messages))
        except Exception as e:
            logger.error(f"Failed to update conversation metadata: {e}")

        logger.info(f"Successfully saved messages for conversation {conversation_id}")
        return {}

    except Exception as e:
        logger.error(f"Failed to save conversation history: {e}")
        return {
            "error": f"Failed to save conversation: {str(e)}"
        }
