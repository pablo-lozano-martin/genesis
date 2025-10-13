# ABOUTME: Message repository port interface defining the contract for message data operations
# ABOUTME: Abstract interface following hexagonal architecture principles

from abc import ABC, abstractmethod
from typing import Optional, List

from app.core.domain.message import Message, MessageCreate


class IMessageRepository(ABC):
    """
    Message repository port interface.

    Defines the contract for message data operations. Implementations
    of this interface (adapters) handle the actual data persistence
    without the core domain knowing about database details.
    """

    @abstractmethod
    async def create(self, message_data: MessageCreate) -> Message:
        """
        Create a new message.

        Args:
            message_data: Message creation data

        Returns:
            Created message entity
        """
        pass

    @abstractmethod
    async def get_by_id(self, message_id: str) -> Optional[Message]:
        """
        Retrieve a message by ID.

        Args:
            message_id: Message unique identifier

        Returns:
            Message entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_conversation_id(
        self,
        conversation_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        """
        List messages for a specific conversation.

        Args:
            conversation_id: Conversation unique identifier
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of message entities ordered by creation time
        """
        pass

    @abstractmethod
    async def delete(self, message_id: str) -> bool:
        """
        Delete a message.

        Args:
            message_id: Message unique identifier

        Returns:
            True if message was deleted, False if not found
        """
        pass

    @abstractmethod
    async def delete_by_conversation_id(self, conversation_id: str) -> int:
        """
        Delete all messages for a conversation.

        Args:
            conversation_id: Conversation unique identifier

        Returns:
            Number of messages deleted
        """
        pass
