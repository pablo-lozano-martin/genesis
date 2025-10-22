# ABOUTME: Message conversion utilities between domain and LangChain messages
# ABOUTME: Enables bidirectional conversion for LangGraph integration

from typing import List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from app.core.domain.message import Message, MessageRole


def domain_to_langchain(domain_messages: List[Message]) -> List[BaseMessage]:
    """Convert domain Messages to LangChain messages.

    Args:
        domain_messages: List of domain Message objects

    Returns:
        List of LangChain BaseMessage objects
    """
    langchain_messages = []

    for msg in domain_messages:
        if msg.role == MessageRole.USER:
            langchain_messages.append(HumanMessage(content=msg.content))

        elif msg.role == MessageRole.ASSISTANT:
            ai_msg = AIMessage(content=msg.content or "")
            # Restore tool_calls from metadata if present
            if msg.metadata and "tool_calls" in msg.metadata:
                ai_msg.tool_calls = msg.metadata["tool_calls"]
            langchain_messages.append(ai_msg)

        elif msg.role == MessageRole.SYSTEM:
            langchain_messages.append(SystemMessage(content=msg.content))

        elif msg.role == MessageRole.TOOL:
            # Extract tool metadata
            tool_call_id = msg.metadata.get("tool_call_id", "") if msg.metadata else ""
            name = msg.metadata.get("name", "") if msg.metadata else ""
            langchain_messages.append(
                ToolMessage(
                    content=msg.content,
                    tool_call_id=tool_call_id,
                    name=name
                )
            )

    return langchain_messages


def langchain_to_domain(lc_message: BaseMessage, conversation_id: str) -> Message:
    """Convert a single LangChain message to domain Message.

    Args:
        lc_message: LangChain message (HumanMessage, AIMessage, ToolMessage, etc.)
        conversation_id: ID of the conversation

    Returns:
        Domain Message object

    Raises:
        ValueError: If message type is unknown
    """
    if isinstance(lc_message, HumanMessage):
        return Message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=lc_message.content
        )

    elif isinstance(lc_message, AIMessage):
        # Check if AIMessage has tool calls
        metadata = None
        if hasattr(lc_message, 'tool_calls') and lc_message.tool_calls:
            metadata = {"tool_calls": lc_message.tool_calls}

        return Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=lc_message.content or "",
            metadata=metadata
        )

    elif isinstance(lc_message, ToolMessage):
        return Message(
            conversation_id=conversation_id,
            role=MessageRole.TOOL,
            content=lc_message.content,
            metadata={
                "tool_call_id": lc_message.tool_call_id,
                "name": getattr(lc_message, 'name', '')
            }
        )

    elif isinstance(lc_message, SystemMessage):
        return Message(
            conversation_id=conversation_id,
            role=MessageRole.SYSTEM,
            content=lc_message.content
        )

    else:
        raise ValueError(f"Unknown message type: {type(lc_message)}")
