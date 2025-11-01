# ABOUTME: Generic chat graph using LangGraph's prebuilt create_react_agent
# ABOUTME: Simpler alternative to custom node implementation with built-in ReAct loop

from typing import Optional, List, Callable
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from app.langgraph.state import ConversationState
from app.core.ports.llm_provider import ILLMProvider
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


# Default system prompt for generic conversational agent
DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant. You have access to various tools to help answer questions and complete tasks.

When using tools:
- Choose the most appropriate tool for the task
- Provide clear and accurate information
- If you're not sure about something, say so

Engage naturally with the user and provide helpful, accurate responses."""


def create_react_agent_graph(
    checkpointer: AsyncMongoDBSaver,
    tools: Optional[List[Callable]] = None,
    llm_provider: Optional[ILLMProvider] = None,
    system_prompt: Optional[str] = None
):
    """
    Create chat agent graph using LangGraph's prebuilt create_react_agent.

    Advantages over hand-built approach:
    - Simpler implementation: no custom nodes needed
    - Automatically handles ReAct loop (reason → act → repeat)
    - System prompt injection built-in via prompt parameter
    - Streaming support maintained via astream_events()

    Args:
        checkpointer: AsyncMongoDBSaver for state persistence
        tools: Optional list of tools (defaults to standard tools)
        llm_provider: ILLMProvider instance (defaults to factory-created provider)
        system_prompt: Optional system prompt (defaults to generic assistant prompt)

    Returns:
        Compiled LangGraph agent ready for invocation
    """
    # Import default tools if not provided
    if tools is None:
        from app.langgraph.tools import multiply, add, rag_search
        tools = [multiply, add, rag_search]

    # Get LLM provider if not provided
    if llm_provider is None:
        from app.adapters.outbound.llm_providers.provider_factory import get_llm_provider
        llm_provider = get_llm_provider()

    # Use default system prompt if not provided
    if system_prompt is None:
        system_prompt = DEFAULT_SYSTEM_PROMPT

    # Get underlying LangChain model from provider abstraction
    model = llm_provider.get_model()

    # Create prebuilt agent with built-in ReAct loop
    agent = create_react_agent(
        model=model,
        tools=tools,
        state_schema=ConversationState,
        prompt=system_prompt,
        checkpointer=checkpointer
    )

    # Store tools as metadata for WebSocket handler access
    agent._tools = tools

    logger.info(
        f"React agent graph created with create_react_agent "
        f"(tools: {len(tools)})"
    )

    return agent
