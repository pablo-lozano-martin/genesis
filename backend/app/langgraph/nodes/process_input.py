# ABOUTME: Node for processing and validating user input messages
# ABOUTME: Creates HumanMessage from user input for LangGraph-native message handling

from langchain_core.messages import HumanMessage
from app.langgraph.state import ConversationState
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


async def process_user_input(state: ConversationState) -> dict:
    """
    Process and validate user input before sending to LLM.

    This node:
    - Retrieves user input from the incoming state
    - Validates the input is not empty
    - Creates a LangChain HumanMessage object
    - Adds it to the message history via MessagesState reducer

    Args:
        state: Current conversation state

    Returns:
        Dictionary with messages list containing the HumanMessage
    """
    # Get user input from state (passed during graph invocation)
    user_input = state.get("user_input", "")

    if isinstance(user_input, str):
        user_input = user_input.strip()

    if not user_input:
        logger.warning(f"Empty input received for conversation {state['conversation_id']}")
        # Return empty update to allow error handling at graph level
        return {}

    logger.info(f"Processing input for conversation {state['conversation_id']}")

    # Create LangChain HumanMessage
    message = HumanMessage(content=user_input)

    return {
        "messages": [message]
    }
