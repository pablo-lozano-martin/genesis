# ABOUTME: ReAct-based onboarding conversation graph using LangGraph.
# ABOUTME: Implements proactive agent behavior via system prompt injection for structured data collection.

from typing import Optional, List, Callable
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage
from app.langgraph.state import ConversationState
from app.langgraph.nodes.process_input import process_user_input
from app.langgraph.nodes.call_llm import call_llm
from app.langgraph.prompts.onboarding_prompts import ONBOARDING_SYSTEM_PROMPT
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


def inject_system_prompt(state: ConversationState) -> dict:
    """
    Inject system prompt at start of conversation if not already present.

    Checks if first message is SystemMessage. If not, prepends system prompt.
    This ensures the LLM operates with consistent role context throughout conversation.

    Args:
        state: Current ConversationState with messages list

    Returns:
        Dictionary with messages key containing system prompt, or empty dict if already present
    """
    messages = state.get("messages", [])

    # Check if system prompt already present
    if messages and isinstance(messages[0], SystemMessage):
        return {}  # No update needed

    # Prepend system prompt
    system_message = SystemMessage(content=ONBOARDING_SYSTEM_PROMPT)

    return {
        "messages": [system_message]  # MessagesState will prepend this
    }


def create_onboarding_graph(
    checkpointer: AsyncMongoDBSaver,
    tools: Optional[List[Callable]] = None
):
    """
    Create ReAct-based onboarding graph with system prompt injection.

    The ReAct pattern is implemented via:
    1. System message injection sets agent behavior (reasoning + acting)
    2. tools_condition enables iterative tool use
    3. Agent loops between reasoning (call_llm) and acting (ToolNode) until complete

    Graph flow:
    START -> process_input -> inject_system_prompt -> call_llm -> tools_condition
                                                        ↑              ↓ (tool_calls)
                                                        └── ToolNode ←┘
                                                                       ↓ (no tool_calls)
                                                                      END

    Args:
        checkpointer: AsyncMongoDBSaver for state persistence
        tools: List of tools to bind (read_data, write_data, rag_search, export_data)

    Returns:
        Compiled graph ready for invocation
    """
    if tools is None:
        from app.langgraph.tools import read_data, write_data, rag_search, export_data
        tools = [read_data, write_data, rag_search, export_data]

    logger.info("Creating onboarding graph with ReAct pattern")

    graph_builder = StateGraph(ConversationState)

    # Add nodes
    graph_builder.add_node("process_input", process_user_input)
    graph_builder.add_node("inject_system_prompt", inject_system_prompt)
    graph_builder.add_node("call_llm", call_llm)
    graph_builder.add_node("tools", ToolNode(tools))

    # Define edges (ReAct loop)
    graph_builder.add_edge(START, "process_input")
    graph_builder.add_edge("process_input", "inject_system_prompt")
    graph_builder.add_edge("inject_system_prompt", "call_llm")
    graph_builder.add_conditional_edges("call_llm", tools_condition)  # Routes to tools or END
    graph_builder.add_edge("tools", "call_llm")  # Loop back for next reasoning step

    compiled_graph = graph_builder.compile(checkpointer=checkpointer)

    logger.info("Onboarding graph compiled with system prompt injection and ReAct pattern")

    return compiled_graph
