# ABOUTME: LangGraph state definition for conversation management
# ABOUTME: Uses native MessagesState with BaseMessage types for LangGraph-first architecture

from langgraph.graph import MessagesState
from typing import Optional


class ConversationState(MessagesState):
    """
    State schema for conversation flow in LangGraph with onboarding fields.

    Extends LangGraph's native MessagesState to include conversation metadata
    and onboarding-specific fields for agent-driven data collection.

    The messages field comes from MessagesState and uses BaseMessage types
    (HumanMessage, AIMessage, SystemMessage, ToolMessage) with built-in
    add_messages reducer.

    Attributes:
        messages: List[BaseMessage] - Inherited from MessagesState, auto-managed
        conversation_id: UUID of the current conversation
        user_id: UUID of the user owning the conversation
        remaining_steps: Integer tracking steps remaining (required by create_react_agent)

        # Onboarding fields (collected via read_data/write_data tools)
        employee_name: Optional employee full name
        employee_id: Optional employee ID number
        starter_kit: Optional starter kit choice (mouse, keyboard, or backpack)
        dietary_restrictions: Optional dietary information
        meeting_scheduled: Boolean flag for meeting status
        conversation_summary: LLM-generated summary of conversation
    """
    conversation_id: str
    user_id: str

    # Required by create_react_agent
    remaining_steps: Optional[int] = None

    # Onboarding fields (collected via read_data/write_data tools)
    employee_name: Optional[str] = None
    employee_id: Optional[str] = None
    starter_kit: Optional[str] = None
    dietary_restrictions: Optional[str] = None
    meeting_scheduled: Optional[bool] = None
    conversation_summary: Optional[str] = None
