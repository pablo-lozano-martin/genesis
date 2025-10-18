# ABOUTME: SendMessage use case implementing message sending and LLM response business logic
# ABOUTME: Handles user message creation, LLM invocation, and assistant response storage

from typing import List

from app.core.domain.message import Message, MessageCreate, MessageRole
from app.core.ports.message_repository import IMessageRepository
from app.core.ports.conversation_repository import IConversationRepository
from app.core.ports.llm_provider import ILLMProvider


class SendMessage:
    """
    Use case for sending a message and getting an LLM response.

    This use case encapsulates the business logic for:
    1. Saving the user's message
    2. Retrieving conversation history
    3. Calling the LLM provider
    4. Saving the assistant's response
    5. Updating conversation metadata

    It depends only on port interfaces, not concrete implementations.
    """

    def __init__(
        self,
        message_repository: IMessageRepository,
        conversation_repository: IConversationRepository,
        llm_provider: ILLMProvider
    ):
        """
        Initialize the SendMessage use case.

        Args:
            message_repository: Message repository port for data operations
            conversation_repository: Conversation repository port for data operations
            llm_provider: LLM provider port for generating responses
        """
        self.message_repository = message_repository
        self.conversation_repository = conversation_repository
        self.llm_provider = llm_provider

    async def execute(self, conversation_id: str, user_message_content: str) -> Message:
        """
        Execute the send message use case.

        Args:
            conversation_id: ID of the conversation
            user_message_content: Content of the user's message

        Returns:
            Assistant's response message

        Raises:
            ValueError: If conversation doesn't exist or message is empty
        """
        if not user_message_content or not user_message_content.strip():
            raise ValueError("Message content cannot be empty")

        conversation = await self.conversation_repository.get_by_id(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        user_message = MessageCreate(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=user_message_content.strip()
        )
        await self.message_repository.create(user_message)

        conversation_history = await self.message_repository.get_by_conversation_id(
            conversation_id
        )

        assistant_response_content = await self.llm_provider.generate(conversation_history)

        assistant_message = MessageCreate(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=assistant_response_content
        )
        assistant_message_entity = await self.message_repository.create(assistant_message)

        await self.conversation_repository.increment_message_count(conversation_id, 2)

        return assistant_message_entity
