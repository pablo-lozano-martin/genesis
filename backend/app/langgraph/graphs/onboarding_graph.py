# ABOUTME: Onboarding agent graph factory using LangGraph's prebuilt create_react_agent
# ABOUTME: Replaced custom ReAct implementation with prebuilt for cleaner, maintainable code

from typing import Optional, List, Callable
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from app.langgraph.state import ConversationState
from app.langgraph.prompts.onboarding_prompts import ONBOARDING_SYSTEM_PROMPT
from app.core.ports.llm_provider import ILLMProvider
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


def create_onboarding_graph(
    checkpointer: AsyncMongoDBSaver,
    tools: Optional[List[Callable]] = None,
    llm_provider: Optional[ILLMProvider] = None
):
    """
    Create onboarding agent graph using LangGraph's prebuilt create_react_agent.

    Advantages over hand-built approach:
    - Simpler implementation: no custom nodes for process_input, inject_system_prompt, call_llm
    - Automatically handles ReAct loop (reason → act → repeat)
    - System prompt injection built-in via prompt parameter
    - Streaming support maintained via astream_events()

    Args:
        checkpointer: AsyncMongoDBSaver for state persistence
        tools: Optional list of tools (defaults to onboarding tools)
        llm_provider: ILLMProvider instance (defaults to factory-created provider)

    Returns:
        Compiled LangGraph agent ready for invocation
    """
    # Import default tools if not provided
    if tools is None:
        from app.langgraph.tools import read_data, write_data, rag_search, export_data
        tools = [read_data, write_data, rag_search, export_data]

    # Get LLM provider if not provided
    if llm_provider is None:
        from app.adapters.outbound.llm_providers.provider_factory import get_llm_provider
        llm_provider = get_llm_provider()

    # Get underlying LangChain model from provider abstraction
    model = llm_provider.get_model()

    # Create prebuilt agent with built-in ReAct loop
    agent = create_react_agent(
        model=model,
        tools=tools,
        state_schema=ConversationState,
        prompt=ONBOARDING_SYSTEM_PROMPT,
        checkpointer=checkpointer
    )

    # Store tools as metadata for WebSocket handler access
    agent._tools = tools

    logger.info(
        f"Onboarding graph created with create_react_agent "
        f"(tools: {[t.__name__ if hasattr(t, '__name__') else str(t) for t in tools]})"
    )

    return agent
