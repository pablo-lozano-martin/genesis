# ABOUTME: Node for invoking the LLM provider to generate responses
# ABOUTME: Uses LangChain BaseMessage types for LLM communication

from langgraph.types import RunnableConfig
from langchain_core.messages import AIMessage
from app.langgraph.state import ConversationState
from app.langgraph.tools.multiply import multiply
from app.langgraph.tools.add import add
from app.langgraph.tools.web_search import web_search
from app.langgraph.tools.rag_search import rag_search
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


async def call_llm(state: ConversationState, config: RunnableConfig) -> dict:
    """
    Call the LLM provider to generate a response.

    This node:
    - Retrieves the LLM provider from RunnableConfig
    - Invokes the LLM with the message history (List[BaseMessage])
    - Returns an AIMessage with the generated response

    Args:
        state: Current conversation state with messages (List[BaseMessage])
        config: RunnableConfig containing llm_provider in configurable dict

    Returns:
        Dictionary with messages list containing the AIMessage response
    """
    messages = state["messages"]
    conversation_id = state["conversation_id"]

    logger.info(f"Calling LLM for conversation {conversation_id} with {len(messages)} messages")

    tools = [multiply, add, web_search, rag_search]

    # Get LLM provider from config
    llm_provider = config["configurable"]["llm_provider"]
    llm_provider_with_tools = llm_provider.bind_tools(tools, parallel_tool_calls=False)

    # Generate response (llm_provider_with_tools.generate should work with BaseMessage types)
    ai_message = await llm_provider_with_tools.generate(messages)

    logger.info(f"LLM response generated for conversation {conversation_id}")

    return {
        "messages": [ai_message]
    }
