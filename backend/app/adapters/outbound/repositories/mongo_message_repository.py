# ABOUTME: MongoDB implementation of IMessageRepository port interface
# ABOUTME: Handles message data persistence using Beanie ODM

from typing import Optional, List

from app.core.domain.message import Message, MessageCreate
from app.core.ports.message_repository import IMessageRepository
from app.adapters.outbound.repositories.mongo_models import MessageDocument


class MongoMessageRepository(IMessageRepository):
    """
    MongoDB implementation of IMessageRepository.

    This adapter implements the message repository port using MongoDB
    and Beanie ODM. It translates between domain models and MongoDB documents.
    """

    def _to_domain(self, doc: MessageDocument) -> Message:
        """Convert MongoDB document to domain model."""
        return Message(
            id=str(doc.id),
            conversation_id=doc.conversation_id,
            role=doc.role,
            content=doc.content,
            created_at=doc.created_at,
            metadata=doc.metadata
        )

    async def create(self, message_data: MessageCreate) -> Message:
        """
        Create a new message.

        Args:
            message_data: Message creation data

        Returns:
            Created message entity
        """
        doc = MessageDocument(
            conversation_id=message_data.conversation_id,
            role=message_data.role,
            content=message_data.content,
            metadata=message_data.metadata
        )

        await doc.insert()
        return self._to_domain(doc)

    async def get_by_id(self, message_id: str) -> Optional[Message]:
        """Retrieve a message by ID."""
        doc = await MessageDocument.get(message_id)
        return self._to_domain(doc) if doc else None

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
        docs = await MessageDocument.find(
            MessageDocument.conversation_id == conversation_id
        ).sort(MessageDocument.created_at).skip(skip).limit(limit).to_list()

        return [self._to_domain(doc) for doc in docs]

    async def delete(self, message_id: str) -> bool:
        """
        Delete a message.

        Args:
            message_id: Message unique identifier

        Returns:
            True if message was deleted, False if not found
        """
        doc = await MessageDocument.get(message_id)
        if not doc:
            return False

        await doc.delete()
        return True

    async def delete_by_conversation_id(self, conversation_id: str) -> int:
        """
        Delete all messages for a conversation.

        Args:
            conversation_id: Conversation unique identifier

        Returns:
            Number of messages deleted
        """
        result = await MessageDocument.find(
            MessageDocument.conversation_id == conversation_id
        ).delete()

        return result.deleted_count if result else 0
