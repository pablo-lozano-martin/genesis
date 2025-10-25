# ABOUTME: LangGraph state definition for conversation management
# ABOUTME: Uses native MessagesState with BaseMessage types for LangGraph-first architecture

from langgraph.graph import MessagesState


class ConversationState(MessagesState):
    """
    State schema for conversation flow in LangGraph.

    Extends LangGraph's native MessagesState to include conversation metadata.
    The messages field comes from MessagesState and uses BaseMessage types
    (HumanMessage, AIMessage, SystemMessage) with built-in add_messages reducer.

    Attributes:
        messages: List[BaseMessage] - Inherited from MessagesState, automatically managed
        conversation_id: UUID of the current conversation
        user_id: UUID of the user owning the conversation
    """
    conversation_id: str
    user_id: str
