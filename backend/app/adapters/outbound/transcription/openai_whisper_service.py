# ABOUTME: OpenAI Whisper transcription service adapter
# ABOUTME: Implements ITranscriptionService using OpenAI Whisper API

import os
from typing import Optional
from openai import AsyncOpenAI
from app.core.ports.transcription_service import ITranscriptionService
from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger
from app.infrastructure.storage.temp_file_handler import secure_temp_file

logger = get_logger(__name__)


class OpenAIWhisperService(ITranscriptionService):
    """OpenAI Whisper transcription implementation."""

    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")

        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.whisper_model
        logger.info("Initialized OpenAI Whisper service")

    async def transcribe(
        self,
        audio_content: bytes,
        filename: str,
        language: Optional[str] = None,
    ) -> dict:
        """Transcribe audio using OpenAI Whisper API."""

        # Use secure temp file handler
        with secure_temp_file(suffix=os.path.splitext(filename)[1]) as tmp_path:
            tmp_path.write_bytes(audio_content)

            try:
                with open(tmp_path, "rb") as audio_file:
                    response = await self.client.audio.transcriptions.create(
                        model=self.model,
                        file=audio_file,
                        language=language,
                        response_format="verbose_json"
                    )

                logger.info(f"Transcription successful: {len(response.text)} chars")

                return {
                    "text": response.text,
                    "language": response.language or language or "en",
                    "duration": response.duration
                }

            except Exception as e:
                logger.error(f"Whisper transcription failed: {e}")
                raise Exception(f"Transcription failed: {str(e)}")
