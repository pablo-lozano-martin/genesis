# ABOUTME: Pydantic schemas for transcription API request/response
# ABOUTME: Defines validation rules and OpenAPI documentation

from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    """Response schema for audio transcription."""

    text: str = Field(..., description="Transcribed text from audio")
    language: str = Field(..., description="Detected language (ISO 639-1)")
    duration: float = Field(..., description="Audio duration in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Hello, how can I help you today?",
                "language": "en",
                "duration": 3.5
            }
        }
