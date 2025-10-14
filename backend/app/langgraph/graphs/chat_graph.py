# ABOUTME: Main chat conversation graph using LangGraph
# ABOUTME: Orchestrates the flow from user input to LLM response to persistence

from typing import Literal
from langgraph.graph import StateGraph, START, END
from app.langgraph.state import ConversationState
from app.langgraph.nodes.process_input import process_user_input
from app.langgraph.nodes.call_llm import call_llm
from app.langgraph.nodes.format_response import format_response
from app.langgraph.nodes.save_history import save_to_history
from app.core.ports.llm_provider import ILLMProvider
from app.core.ports.message_repository import IMessageRepository
from app.core.ports.conversation_repository import IConversationRepository
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


def should_continue(state: ConversationState) -> Literal["call_llm", "end"]:
    """
    Determine if we should continue to LLM or end due to error.

    Args:
        state: Current conversation state

    Returns:
        Next node name or "end"
    """
    if state.get("error"):
        logger.warning(f"Error detected in conversation {state['conversation_id']}, ending flow")
        return "end"
    return "call_llm"


def create_chat_graph(
    llm_provider: ILLMProvider,
    message_repository: IMessageRepository,
    conversation_repository: IConversationRepository
):
    """
    Create and compile the chat conversation graph.

    The graph flow:
    1. START -> process_input: Validate and format user input
    2. process_input -> call_llm (or END if error): Invoke LLM provider
    3. call_llm -> format_response: Format LLM response into Message
    4. format_response -> save_history: Persist messages to database
    5. save_history -> END: Complete the flow

    Args:
        llm_provider: LLM provider instance for generating responses
        message_repository: Repository for persisting messages
        conversation_repository: Repository for updating conversation metadata

    Returns:
        Compiled LangGraph instance
    """
    logger.info("Creating chat conversation graph")

    graph_builder = StateGraph(ConversationState)

    graph_builder.add_node("process_input", process_user_input)
    graph_builder.add_node(
        "call_llm",
        lambda state: call_llm(state, llm_provider)
    )
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
            "call_llm": "call_llm",
            "end": END
        }
    )
    graph_builder.add_edge("call_llm", "format_response")
    graph_builder.add_edge("format_response", "save_history")
    graph_builder.add_edge("save_history", END)

    graph = graph_builder.compile()

    logger.info("Chat conversation graph compiled successfully")

    return graph
