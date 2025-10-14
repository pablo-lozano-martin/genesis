# ABOUTME: Streaming chat graph with token-by-token response support
# ABOUTME: Extended version of chat graph for real-time WebSocket streaming

from typing import AsyncGenerator, Literal
from langgraph.graph import StateGraph, START, END
from app.langgraph.state import ConversationState
from app.langgraph.nodes.process_input import process_user_input
from app.langgraph.nodes.format_response import format_response
from app.langgraph.nodes.save_history import save_to_history
from app.core.ports.llm_provider import ILLMProvider
from app.core.ports.message_repository import IMessageRepository
from app.core.ports.conversation_repository import IConversationRepository
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


def should_continue(state: ConversationState) -> Literal["call_llm_stream", "end"]:
    """
    Determine if we should continue to LLM streaming or end due to error.

    Args:
        state: Current conversation state

    Returns:
        Next node name or "end"
    """
    if state.get("error"):
        logger.warning(f"Error detected in conversation {state['conversation_id']}, ending flow")
        return "end"
    return "call_llm_stream"


async def call_llm_stream(
    state: ConversationState,
    llm_provider: ILLMProvider
) -> AsyncGenerator[str, None]:
    """
    Stream LLM responses token-by-token.

    This is a generator function that yields tokens as they are generated
    by the LLM provider. This enables real-time streaming to the client.

    Args:
        state: Current conversation state
        llm_provider: LLM provider instance

    Yields:
        Individual tokens from the LLM response
    """
    try:
        messages = state["messages"]
        conversation_id = state["conversation_id"]

        logger.info(f"Starting LLM streaming for conversation {conversation_id}")

        full_response = []

        async for token in llm_provider.stream(messages):
            full_response.append(token)
            yield token

        logger.info(f"LLM streaming completed for conversation {conversation_id}")

    except Exception as e:
        logger.error(f"LLM streaming failed for conversation {state['conversation_id']}: {e}")
        raise


def create_streaming_chat_graph(
    llm_provider: ILLMProvider,
    message_repository: IMessageRepository,
    conversation_repository: IConversationRepository
):
    """
    Create a streaming chat graph for real-time token streaming.

    This graph is designed for WebSocket communication where responses
    are streamed token-by-token to the client.

    The flow is similar to the regular chat graph but uses streaming
    LLM responses.

    Args:
        llm_provider: LLM provider instance for generating responses
        message_repository: Repository for persisting messages
        conversation_repository: Repository for updating conversation metadata

    Returns:
        Compiled LangGraph instance with streaming support
    """
    logger.info("Creating streaming chat conversation graph")

    graph_builder = StateGraph(ConversationState)

    graph_builder.add_node("process_input", process_user_input)
    graph_builder.add_node("format_response", format_response)
    graph_builder.add_node(
        "save_history",
        lambda state: save_to_history(state, message_repository, conversation_repository)
    )

    graph_builder.add_edge(START, "process_input")
    graph_builder.add_conditional_edges(
        "process_input",
        should_continue,
        {
            "call_llm_stream": "format_response",
            "end": END
        }
    )
    graph_builder.add_edge("format_response", "save_history")
    graph_builder.add_edge("save_history", END)

    graph = graph_builder.compile()

    logger.info("Streaming chat conversation graph compiled successfully")

    return graph, call_llm_stream
