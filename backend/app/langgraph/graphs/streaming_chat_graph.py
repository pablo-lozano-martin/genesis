# ABOUTME: Streaming chat graph with token-by-token response support via graph.astream_events()
# ABOUTME: Uses LangGraph-first architecture with automatic checkpointing and native streaming

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from app.langgraph.state import ConversationState
from app.langgraph.nodes.process_input import process_user_input
from app.langgraph.nodes.call_llm import call_llm
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


def create_streaming_chat_graph(checkpointer: AsyncMongoDBSaver):
    """
    Create and compile the streaming chat graph with automatic checkpointing.

    This graph uses LangGraph's astream_events() for token-by-token streaming.
    The structure is identical to the regular chat graph, but streaming is
    handled at the graph invocation level using astream_events() rather than
    within the graph nodes.

    The graph flow:
    1. START -> process_input: Validate and create HumanMessage from user input
    2. process_input -> call_llm: Invoke LLM provider and get AIMessage response
    3. call_llm -> END: Complete (checkpointing happens automatically)

    WebSocket handlers use graph.astream_events() to stream LLM tokens in real-time.
    LLM provider is passed via RunnableConfig during graph invocation.

    Args:
        checkpointer: AsyncMongoDBSaver instance for automatic state persistence

    Returns:
        Compiled LangGraph instance with checkpointing and streaming support
    """
    logger.info("Creating streaming chat conversation graph with checkpointer")

    graph_builder = StateGraph(ConversationState)

    # Add nodes (streaming handled by astream_events at invocation level)
    graph_builder.add_node("process_input", process_user_input)
    graph_builder.add_node("call_llm", call_llm)

    # Define edges
    graph_builder.add_edge(START, "process_input")
    graph_builder.add_edge("process_input", "call_llm")
    graph_builder.add_edge("call_llm", END)

    # Compile with checkpointer for automatic state persistence
    graph = graph_builder.compile(checkpointer=checkpointer)

    logger.info("Streaming chat conversation graph compiled successfully with checkpointing")

    return graph
