# ABOUTME: Node for invoking the LLM provider to generate responses
# ABOUTME: Uses LangChain BaseMessage types for LLM communication

from langgraph.types import RunnableConfig
from langchain_core.messages import AIMessage
from app.langgraph.state import ConversationState
from app.langgraph.tools.multiply import multiply
from app.langgraph.tools.add import add
from app.langgraph.tools.rag_search import rag_search
from app.langgraph.tools.read_data import read_data
from app.langgraph.tools.write_data import write_data
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

    # Check if tools are provided in config (used by specialized graphs like onboarding)
    config_tools = config.get("configurable", {}).get("tools")

    if config_tools is not None:
        # Use tools from config (e.g., onboarding graph with specific tools)
        all_tools = config_tools
        logger.info(f"Using {len(all_tools)} tools from graph configuration")
    else:
        # Default behavior: use local tools + MCP tools (for chat graphs)
        local_tools = [multiply, add, rag_search, read_data, write_data]

        # Get MCP tools from manager
        mcp_tools = []
        try:
            from app.infrastructure.mcp import MCPClientManager
            mcp_manager = MCPClientManager()
            mcp_tools = mcp_manager.get_tools()
            if mcp_tools:
                logger.info(f"Binding {len(mcp_tools)} MCP tools to LLM")
        except Exception as e:
            logger.warning(f"Failed to load MCP tools: {e}")

        # Combine all tools
        all_tools = local_tools + mcp_tools

    # Get LLM provider from config
    llm_provider = config["configurable"]["llm_provider"]
    llm_provider_with_tools = llm_provider.bind_tools(all_tools, parallel_tool_calls=False)

    # Generate response (llm_provider_with_tools.generate should work with BaseMessage types)
    ai_message = await llm_provider_with_tools.generate(messages)

    logger.info(f"LLM response generated for conversation {conversation_id}")

    return {
        "messages": [ai_message]
    }
