# ABOUTME: Port interface for speech-to-text transcription services
# ABOUTME: Defines abstract contract allowing multiple provider implementations

from abc import ABC, abstractmethod
from typing import Optional


class ITranscriptionService(ABC):
    """Port interface for speech-to-text transcription."""

    @abstractmethod
    async def transcribe(
        self,
        audio_content: bytes,
        filename: str,
        language: Optional[str] = None,
    ) -> dict:
        """
        Transcribe audio to text.

        Args:
            audio_content: Raw audio file bytes
            filename: Original filename for format detection
            language: Optional ISO 639-1 language code

        Returns:
            dict with keys: text (str), language (str), duration (float)

        Raises:
            ValueError: If audio is invalid or too long
            Exception: If transcription service fails
        """
        pass
