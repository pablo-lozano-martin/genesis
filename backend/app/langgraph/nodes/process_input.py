# ABOUTME: Node for processing and validating user input messages
# ABOUTME: Ensures input is clean and properly formatted before LLM processing

from langchain_core.messages import HumanMessage
from app.langgraph.state import ConversationState
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


async def process_user_input(state: ConversationState) -> dict:
    """
    Process and validate user input before sending to LLM.

    This node:
    - Validates the input is not empty
    - Creates a HumanMessage for LangChain flow
    - Adds it to the message history
    - Sets error state if validation fails

    Args:
        state: Current conversation state

    Returns:
        Dictionary with state updates (messages or error)
    """
    current_input = state.get("current_input", "").strip()

    if not current_input:
        logger.warning(f"Empty input received for conversation {state['conversation_id']}")
        return {
            "error": "Input cannot be empty"
        }

    logger.info(f"Processing input for conversation {state['conversation_id']}")

    user_message = HumanMessage(content=current_input)

    return {
        "messages": [user_message],
        "error": None
    }
