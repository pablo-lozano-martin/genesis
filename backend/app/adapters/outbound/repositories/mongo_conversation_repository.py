# ABOUTME: MongoDB implementation of IConversationRepository port interface
# ABOUTME: Handles conversation data persistence using Beanie ODM

from typing import Optional, List
from datetime import datetime

from app.core.domain.conversation import Conversation, ConversationCreate, ConversationUpdate
from app.core.ports.conversation_repository import IConversationRepository
from app.adapters.outbound.repositories.mongo_models import ConversationDocument


class MongoConversationRepository(IConversationRepository):
    """
    MongoDB implementation of IConversationRepository.

    This adapter implements the conversation repository port using MongoDB
    and Beanie ODM. It translates between domain models and MongoDB documents.
    """

    def _to_domain(self, doc: ConversationDocument) -> Conversation:
        """Convert MongoDB document to domain model."""
        return Conversation(
            id=str(doc.id),
            user_id=doc.user_id,
            title=doc.title,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            message_count=doc.message_count
        )

    async def create(self, user_id: str, conversation_data: ConversationCreate) -> Conversation:
        """
        Create a new conversation.

        Args:
            user_id: ID of the user who owns the conversation
            conversation_data: Conversation creation data

        Returns:
            Created conversation entity
        """
        doc = ConversationDocument(
            user_id=user_id,
            title=conversation_data.title or "New Conversation"
        )

        await doc.insert()
        return self._to_domain(doc)

    async def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """Retrieve a conversation by ID."""
        doc = await ConversationDocument.get(conversation_id)
        return self._to_domain(doc) if doc else None

    async def get_by_user_id(self, user_id: str, skip: int = 0, limit: int = 100) -> List[Conversation]:
        """
        List conversations for a specific user.

        Args:
            user_id: User unique identifier
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of conversation entities ordered by updated_at descending
        """
        docs = await ConversationDocument.find(
            ConversationDocument.user_id == user_id
        ).sort(-ConversationDocument.updated_at).skip(skip).limit(limit).to_list()

        return [self._to_domain(doc) for doc in docs]

    async def update(self, conversation_id: str, conversation_data: ConversationUpdate) -> Optional[Conversation]:
        """
        Update conversation information.

        Args:
            conversation_id: Conversation unique identifier
            conversation_data: Conversation update data

        Returns:
            Updated conversation entity if found, None otherwise
        """
        doc = await ConversationDocument.get(conversation_id)
        if not doc:
            return None

        update_dict = conversation_data.model_dump(exclude_unset=True)
        if update_dict:
            update_dict["updated_at"] = datetime.utcnow()
            for key, value in update_dict.items():
                setattr(doc, key, value)
            await doc.save()

        return self._to_domain(doc)

    async def delete(self, conversation_id: str) -> bool:
        """
        Delete a conversation.

        Args:
            conversation_id: Conversation unique identifier

        Returns:
            True if conversation was deleted, False if not found
        """
        doc = await ConversationDocument.get(conversation_id)
        if not doc:
            return False

        await doc.delete()
        return True

    async def increment_message_count(self, conversation_id: str, count: int = 1) -> Optional[Conversation]:
        """
        Increment the message count for a conversation.

        Args:
            conversation_id: Conversation unique identifier
            count: Number to increment by (default: 1)

        Returns:
            Updated conversation entity if found, None otherwise
        """
        doc = await ConversationDocument.get(conversation_id)
        if not doc:
            return None

        doc.message_count += count
        doc.updated_at = datetime.utcnow()
        await doc.save()

        return self._to_domain(doc)
