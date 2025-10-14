# ABOUTME: Node for invoking the LLM provider to generate responses
# ABOUTME: Handles LLM communication and error handling

from app.langgraph.state import ConversationState
from app.core.ports.llm_provider import ILLMProvider
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


async def call_llm(state: ConversationState, llm_provider: ILLMProvider) -> dict:
    """
    Call the LLM provider to generate a response.

    This node:
    - Invokes the configured LLM provider with message history
    - Handles errors gracefully
    - Returns the generated response or error state

    Args:
        state: Current conversation state
        llm_provider: LLM provider instance (injected dependency)

    Returns:
        Dictionary with state updates (llm_response or error)
    """
    try:
        messages = state["messages"]
        conversation_id = state["conversation_id"]

        logger.info(f"Calling LLM for conversation {conversation_id} with {len(messages)} messages")

        response = await llm_provider.generate(messages)

        logger.info(f"LLM response generated for conversation {conversation_id}")

        return {
            "llm_response": response,
            "error": None
        }

    except Exception as e:
        logger.error(f"LLM generation failed for conversation {state['conversation_id']}: {e}")
        return {
            "error": f"Failed to generate response: {str(e)}"
        }
