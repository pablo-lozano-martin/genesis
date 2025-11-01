# ABOUTME: LangGraph state definition for conversation management
# ABOUTME: Uses native MessagesState with BaseMessage types for LangGraph-first architecture

from langgraph.graph import MessagesState
from typing import Optional


class ConversationState(MessagesState):
    """
    State schema for conversation flow in LangGraph.

    Extends LangGraph's native MessagesState to include conversation metadata
    and support for prebuilt agents like create_react_agent.

    The messages field comes from MessagesState and uses BaseMessage types
    (HumanMessage, AIMessage, SystemMessage, ToolMessage) with built-in
    add_messages reducer.

    Attributes:
        messages: List[BaseMessage] - Inherited from MessagesState, auto-managed
        conversation_id: UUID of the current conversation
        user_id: UUID of the user owning the conversation
        remaining_steps: Integer tracking steps remaining (required by create_react_agent)
    """
    conversation_id: str
    user_id: str

    # Required by create_react_agent
    remaining_steps: Optional[int] = None
