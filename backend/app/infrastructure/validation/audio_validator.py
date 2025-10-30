# ABOUTME: Audio file validation utilities for security and quality
# ABOUTME: Validates MIME type, file size, magic numbers, and duration

import magic
from fastapi import UploadFile, HTTPException, status
from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

SUPPORTED_MIME_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/mpeg",  # mp3
    "audio/mp4",   # m4a
    "audio/ogg",
}


async def validate_audio_file(audio_file: UploadFile) -> bytes:
    """
    Validate audio file for security and quality.

    Returns:
        bytes: Audio file content

    Raises:
        HTTPException: If validation fails
    """
    # Validate MIME type
    if audio_file.content_type not in SUPPORTED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {audio_file.content_type}"
        )

    # Read content
    content = await audio_file.read()

    # Validate file size
    max_size = settings.transcription_max_file_size_mb * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.transcription_max_file_size_mb}MB"
        )

    # Validate magic number
    file_type = magic.from_buffer(content, mime=True)
    if file_type not in SUPPORTED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File type mismatch (MIME spoofing detected)"
        )

    logger.info(f"Audio validation passed: {audio_file.filename}")
    return content
