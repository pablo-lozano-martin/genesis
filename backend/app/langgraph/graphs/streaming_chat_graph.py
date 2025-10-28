# ABOUTME: Streaming chat graph with token-by-token response support via graph.astream_events()
# ABOUTME: Uses LangGraph-first architecture with automatic checkpointing and native streaming

from typing import Optional, List, Callable
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from langgraph.prebuilt import ToolNode, tools_condition
from app.langgraph.state import ConversationState
from app.langgraph.nodes.process_input import process_user_input
from app.langgraph.nodes.call_llm import call_llm
from app.langgraph.tools.multiply import multiply
from app.langgraph.tools.add import add
from app.langgraph.tools.rag_search import rag_search
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


def create_streaming_chat_graph(checkpointer: AsyncMongoDBSaver, tools: Optional[List[Callable]] = None):
    """
    Create and compile the streaming chat graph with automatic checkpointing.

    This graph uses LangGraph's astream_events() for token-by-token streaming.
    The structure includes tool execution to handle tool calls properly.
    The graph flow:
    1. START -> process_input: Validate and create HumanMessage from user input
    2. process_input -> call_llm: Invoke LLM provider and get AIMessage response
    3. call_llm -> tools (if tool calls) -> call_llm -> END: Handle tool execution loop
    4. call_llm -> END (if no tool calls)

    WebSocket handlers use graph.astream_events() to stream LLM tokens in real-time.
    LLM provider is passed via RunnableConfig during graph invocation.

    Args:
        checkpointer: AsyncMongoDBSaver instance for automatic state persistence
        tools: Optional list of tools (defaults to local tools)

    Returns:
        Compiled LangGraph instance with checkpointer, streaming support, and tool execution
    """
    logger.info("Creating streaming chat conversation graph with checkpointer and tool execution")

    graph_builder = StateGraph(ConversationState)

    if tools is None:
        # Default to local tools
        tools = [multiply, add, rag_search]

    # Add nodes (streaming handled by astream_events at invocation level)
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

    logger.info("Streaming chat conversation graph compiled successfully with checkpointing and tool execution")

    return graph
