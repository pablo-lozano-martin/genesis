# ABOUTME: Conversation repository port interface defining the contract for conversation data operations
# ABOUTME: Abstract interface following hexagonal architecture principles

from abc import ABC, abstractmethod
from typing import Optional, List

from app.core.domain.conversation import Conversation, ConversationCreate, ConversationUpdate


class IConversationRepository(ABC):
    """
    Conversation repository port interface.

    Defines the contract for conversation data operations. Implementations
    of this interface (adapters) handle the actual data persistence
    without the core domain knowing about database details.
    """

    @abstractmethod
    async def create(self, user_id: str, conversation_data: ConversationCreate) -> Conversation:
        """
        Create a new conversation.

        Args:
            user_id: ID of the user who owns the conversation
            conversation_data: Conversation creation data

        Returns:
            Created conversation entity
        """
        pass

    @abstractmethod
    async def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """
        Retrieve a conversation by ID.

        Args:
            conversation_id: Conversation unique identifier

        Returns:
            Conversation entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: str, skip: int = 0, limit: int = 100) -> List[Conversation]:
        """
        List conversations for a specific user.

        Args:
            user_id: User unique identifier
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of conversation entities
        """
        pass

    @abstractmethod
    async def update(self, conversation_id: str, conversation_data: ConversationUpdate) -> Optional[Conversation]:
        """
        Update conversation information.

        Args:
            conversation_id: Conversation unique identifier
            conversation_data: Conversation update data

        Returns:
            Updated conversation entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete(self, conversation_id: str) -> bool:
        """
        Delete a conversation.

        Args:
            conversation_id: Conversation unique identifier

        Returns:
            True if conversation was deleted, False if not found
        """
        pass

    @abstractmethod
    async def increment_message_count(self, conversation_id: str, count: int = 1) -> Optional[Conversation]:
        """
        Increment the message count for a conversation.

        Args:
            conversation_id: Conversation unique identifier
            count: Number to increment by (default: 1)

        Returns:
            Updated conversation entity if found, None otherwise
        """
        pass
