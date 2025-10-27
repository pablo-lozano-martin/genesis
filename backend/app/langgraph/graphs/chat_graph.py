# ABOUTME: Main chat conversation graph using LangGraph
# ABOUTME: LangGraph-first architecture with automatic checkpointing and native MessagesState

from typing import Optional, List, Callable
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from langgraph.prebuilt import ToolNode, tools_condition
from app.langgraph.state import ConversationState
from app.langgraph.nodes.process_input import process_user_input
from app.langgraph.nodes.call_llm import call_llm
from app.infrastructure.config.logging_config import get_logger
from app.langgraph.tools.multiply import multiply
from app.langgraph.tools.add import add
from app.langgraph.tools.web_search import web_search
from app.langgraph.tools.rag_search import rag_search


logger = get_logger(__name__)


def create_chat_graph(checkpointer: AsyncMongoDBSaver, tools: Optional[List[Callable]] = None):
    """
    Create and compile the chat conversation graph with automatic checkpointing.

    The graph flow:
    1. START -> process_input: Validate and create HumanMessage from user input
    2. process_input -> call_llm: Invoke LLM provider and get AIMessage response
    3. call_llm -> END: Complete (checkpointing happens automatically)

    LLM provider is passed via RunnableConfig during graph invocation.
    Message history is automatically persisted via the checkpointer.

    Args:
        checkpointer: AsyncMongoDBSaver instance for automatic state persistence
        tools: Optional list of tools (defaults to local tools)

    Returns:
        Compiled LangGraph instance with checkpointing enabled
    """
    logger.info("Creating chat conversation graph with checkpointer")

    graph_builder = StateGraph(ConversationState)

    if tools is None:
        # Default to local tools
        tools = [multiply, add, web_search, rag_search]

    # Add nodes (no format_response, no save_history - automatic now)
    graph_builder.add_node("process_input", process_user_input)
    graph_builder.add_node("call_llm", call_llm)
    graph_builder.add_node("tools", ToolNode(tools))

    # Define edges
    graph_builder.add_edge(START, "process_input")
    graph_builder.add_edge("process_input", "call_llm")
    graph_builder.add_conditional_edges("call_llm", tools_condition)
    graph_builder.add_edge("tools", "call_llm")

    # Compile with checkpointer for automatic state persistence
    graph = graph_builder.compile(checkpointer=checkpointer)

    logger.info("Chat conversation graph compiled successfully with checkpointing")

    return graph
