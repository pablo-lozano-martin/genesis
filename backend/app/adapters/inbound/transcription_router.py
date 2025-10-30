# ABOUTME: FastAPI router for audio transcription endpoints
# ABOUTME: Handles audio upload, validation, and transcription requests

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from typing import Optional
from app.adapters.inbound.transcription_schemas import TranscriptionResponse
from app.adapters.outbound.transcription.openai_whisper_service import OpenAIWhisperService
from app.infrastructure.security.dependencies import CurrentUser
from app.infrastructure.validation.audio_validator import validate_audio_file
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/transcribe", tags=["transcription"])


@router.post("", response_model=TranscriptionResponse)
async def transcribe_audio(
    current_user: CurrentUser,
    audio_file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    conversation_id: Optional[str] = Form(None)
):
    """
    Transcribe audio file to text using OpenAI Whisper.

    Security:
    - Requires JWT authentication
    - Validates conversation ownership if conversation_id provided
    - File size limited to 25MB

    Supported formats: webm, wav, mp3, m4a, ogg
    """
    logger.info(f"Transcription request from user {current_user.id}")

    # Validate conversation ownership if provided
    if conversation_id:
        from app.adapters.outbound.repositories.mongo_conversation_repository import MongoConversationRepository

        repo = MongoConversationRepository()
        conversation = await repo.get_by_id(conversation_id)

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        if conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

    # Validate audio file
    try:
        logger.info(f"Validating audio file: {audio_file.filename}, content_type: {audio_file.content_type}")
        audio_content = await validate_audio_file(audio_file)
        logger.info(f"Audio file validated successfully, size: {len(audio_content)} bytes")
    except HTTPException as e:
        logger.error(f"Audio validation failed with HTTP exception: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Audio validation error: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid audio file: {str(e)}"
        )

    # Transcribe
    try:
        service = OpenAIWhisperService()
        result = await service.transcribe(
            audio_content=audio_content,
            filename=audio_file.filename,
            language=language
        )

        logger.info(f"Transcription successful for user {current_user.id}")
        return TranscriptionResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transcription service unavailable"
        )
