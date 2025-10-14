# ABOUTME: Node for formatting LLM responses into proper Message objects
# ABOUTME: Converts raw LLM output into domain Message format

from app.langgraph.state import ConversationState
from app.core.domain.message import Message, MessageRole
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


async def format_response(state: ConversationState) -> dict:
    """
    Format the LLM response into a proper Message object.

    This node:
    - Takes the raw LLM response string
    - Creates a Message object with ASSISTANT role
    - Adds it to the message history
    - Clears the llm_response temporary field

    Args:
        state: Current conversation state

    Returns:
        Dictionary with state updates (messages, llm_response cleared)
    """
    llm_response = state.get("llm_response")

    if not llm_response:
        logger.warning(f"No LLM response to format for conversation {state['conversation_id']}")
        return {}

    logger.info(f"Formatting response for conversation {state['conversation_id']}")

    assistant_message = Message(
        conversation_id=state["conversation_id"],
        role=MessageRole.ASSISTANT,
        content=llm_response
    )

    return {
        "messages": [assistant_message],
        "llm_response": None
    }
