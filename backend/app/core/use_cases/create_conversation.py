# ABOUTME: CreateConversation use case implementing conversation creation business logic
# ABOUTME: Handles creating new conversations for users

from app.core.domain.conversation import Conversation, ConversationCreate
from app.core.ports.conversation_repository import IConversationRepository


class CreateConversation:
    """
    Use case for creating a new conversation.

    This use case encapsulates the business logic for conversation creation.
    It depends only on port interfaces, not concrete implementations.
    """

    def __init__(self, conversation_repository: IConversationRepository):
        """
        Initialize the CreateConversation use case.

        Args:
            conversation_repository: Conversation repository port for data operations
        """
        self.conversation_repository = conversation_repository

    async def execute(self, user_id: str, conversation_data: ConversationCreate) -> Conversation:
        """
        Execute the conversation creation use case.

        Args:
            user_id: ID of the user creating the conversation
            conversation_data: Conversation creation data

        Returns:
            Created conversation entity

        Raises:
            ValueError: If user_id is invalid
        """
        if not user_id:
            raise ValueError("User ID is required")

        conversation = await self.conversation_repository.create(user_id, conversation_data)

        return conversation
