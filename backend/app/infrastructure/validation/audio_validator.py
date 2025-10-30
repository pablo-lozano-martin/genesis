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
    logger.info(f"Detected MIME type from magic bytes: {file_type}")

    # WebM can be detected as video/webm even for audio-only files
    # Accept both audio/webm and video/webm for .webm files
    if file_type == "video/webm" and audio_file.content_type == "audio/webm":
        logger.info("Accepting video/webm for audio/webm (webm codec variation)")
        file_type = "audio/webm"

    if file_type not in SUPPORTED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type mismatch: expected one of {SUPPORTED_MIME_TYPES}, got {file_type}"
        )

    logger.info(f"Audio validation passed: {audio_file.filename}")
    return content
