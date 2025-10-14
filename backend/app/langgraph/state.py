# ABOUTME: LangGraph state definition for conversation management
# ABOUTME: Defines TypedDict state schema with message history tracking

from typing import Annotated, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from app.core.domain.message import Message


class ConversationState(TypedDict):
    """
    State schema for conversation flow in LangGraph.

    This state is passed between nodes in the graph and maintains
    the conversation context throughout the execution.

    Attributes:
        messages: List of messages with automatic merging via add_messages reducer
        conversation_id: UUID of the current conversation
        user_id: UUID of the user
        current_input: The latest user input being processed
        llm_response: The generated LLM response
        error: Optional error message if something goes wrong
    """
    messages: Annotated[list[Message], add_messages]
    conversation_id: str
    user_id: str
    current_input: Optional[str]
    llm_response: Optional[str]
    error: Optional[str]
