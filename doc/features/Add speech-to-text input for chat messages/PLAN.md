# Implementation Plan: Add Speech-to-Text Input for Chat Messages

**Issue:** #19
**Feature:** Add speech-to-text input capability for chat messages
**Date:** 2025-10-30

---

## Executive Summary

This plan details the implementation of speech-to-text functionality for the Genesis chat application. Users will be able to record audio messages via a microphone button in the chat interface. The audio will be transcribed to text using OpenAI Whisper API before being sent through the existing message pipeline.

**Key Design Decisions:**
1. **Browser-based recording** with MediaRecorder API
2. **Backend transcription** via REST endpoint (POST /api/transcribe)
3. **OpenAI Whisper** as the transcription service (reuses existing OPENAI_API_KEY)
4. **Client-side flow**: Record → Upload → Transcribe → Display → User Review → Send via existing WebSocket
5. **No audio storage** initially (transcripts only)
6. **Custom React hook** (`useSpeechToText`) for clean separation of concerns

---

## Architecture Overview

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND                                                     │
│                                                              │
│ 1. User clicks microphone button in MessageInput           │
│ 2. Browser requests microphone permission                  │
│ 3. MediaRecorder API captures audio as WebM blob           │
│ 4. User clicks stop, audio recording completes             │
│    ↓                                                        │
│ 5. POST /api/transcribe with multipart/form-data          │
│    - Headers: Authorization: Bearer <jwt_token>            │
│    - Body: audio_file, conversation_id (optional)          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ HTTPS
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ BACKEND                                                      │
│                                                              │
│ 6. Authentication (CurrentUser dependency)                  │
│ 7. Validate audio file (MIME type, size ≤25MB, magic #)   │
│ 8. Verify conversation ownership (if conversation_id)      │
│ 9. Rate limiting check (10 req/min per user)              │
│    ↓                                                        │
│ 10. Save to secure temp file (600 permissions, random name)│
│ 11. Call OpenAI Whisper API                                │
│     - Model: whisper-1                                      │
│     - Returns: transcribed text                             │
│    ↓                                                        │
│ 12. Secure delete temp file (overwrite + unlink)           │
│ 13. Return TranscriptionResponse                           │
│     { "text": "...", "language": "en", "duration": 3.5 }   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ JSON Response
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND                                                     │
│                                                              │
│ 14. Display transcribed text in textarea                   │
│ 15. User reviews/edits text (critical for UX)              │
│ 16. User clicks Send button                                │
│ 17. Existing WebSocket flow:                               │
│     - ClientMessage → HumanMessage → LangGraph → AIMessage │
│     - Streaming response displayed                          │
└─────────────────────────────────────────────────────────────┘
```

### Integration Points

**Frontend:**
- `/frontend/src/components/chat/MessageInput.tsx` - Add microphone button
- `/frontend/src/hooks/useSpeechToText.ts` - **NEW** Recording and transcription logic
- `/frontend/src/services/transcriptionService.ts` - **NEW** API client for transcription endpoint

**Backend:**
- `/backend/app/adapters/inbound/transcription_router.py` - **NEW** REST endpoint
- `/backend/app/adapters/inbound/transcription_schemas.py` - **NEW** Request/response schemas
- `/backend/app/core/ports/transcription_service.py` - **NEW** Port interface
- `/backend/app/adapters/outbound/transcription/openai_whisper_service.py` - **NEW** Whisper adapter
- `/backend/app/infrastructure/validation/audio_validator.py` - **NEW** File validation
- `/backend/app/infrastructure/storage/temp_file_handler.py` - **NEW** Secure file handling

**No Changes Needed:**
- ✅ Existing WebSocket message flow (unchanged)
- ✅ LangGraph processing (unchanged)
- ✅ Message persistence (unchanged)
- ✅ Frontend ChatContext (unchanged)

---

## Implementation Phases

### Phase 1: Backend Infrastructure (Priority: HIGH)

**Objective:** Create transcription service infrastructure following hexagonal architecture

#### 1.1 Transcription Port Interface

**File:** `/backend/app/core/ports/transcription_service.py` (NEW)

```python
# ABOUTME: Port interface for speech-to-text transcription services
# ABOUTME: Defines abstract contract allowing multiple provider implementations

from abc import ABC, abstractmethod
from typing import BinaryIO, Optional

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
```

**Testing:**
- Unit test for interface validation (ensure abstract methods defined)

---

#### 1.2 OpenAI Whisper Service Implementation

**File:** `/backend/app/adapters/outbound/transcription/openai_whisper_service.py` (NEW)

```python
# ABOUTME: OpenAI Whisper transcription service adapter
# ABOUTME: Implements ITranscriptionService using OpenAI Whisper API

import tempfile
import os
from openai import AsyncOpenAI
from app.core.ports.transcription_service import ITranscriptionService
from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

class OpenAIWhisperService(ITranscriptionService):
    """OpenAI Whisper transcription implementation."""

    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")

        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "whisper-1"
        logger.info("Initialized OpenAI Whisper service")

    async def transcribe(
        self,
        audio_content: bytes,
        filename: str,
        language: Optional[str] = None,
    ) -> dict:
        """Transcribe audio using OpenAI Whisper API."""

        # Write to temporary file (Whisper API requires file)
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=os.path.splitext(filename)[1]
        ) as tmp_file:
            tmp_file.write(audio_content)
            tmp_path = tmp_file.name

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

        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
```

**Configuration Changes:**

**File:** `/backend/app/infrastructure/config/settings.py` (MODIFY)

Add these fields to the `Settings` class:

```python
# Transcription settings
whisper_model: str = "whisper-1"
transcription_max_file_size_mb: int = 25
transcription_max_duration_seconds: int = 300  # 5 minutes
```

**File:** `/.env.example` (MODIFY)

```bash
# Transcription Configuration (reuses OPENAI_API_KEY)
WHISPER_MODEL=whisper-1
TRANSCRIPTION_MAX_FILE_SIZE_MB=25
TRANSCRIPTION_MAX_DURATION_SECONDS=300
```

**Dependencies:**

**File:** `/backend/requirements.txt` (MODIFY)

```txt
# Add these lines:
openai>=1.0.0
python-multipart
slowapi>=0.1.8  # For rate limiting
python-magic  # For file magic number validation
```

**Testing:**
- Unit test: Mock OpenAI client, verify correct API call
- Unit test: Verify temp file cleanup on success
- Unit test: Verify temp file cleanup on failure
- Unit test: Test language parameter passing
- Unit test: Test error handling (API failure)

---

#### 1.3 Audio Validation Module

**File:** `/backend/app/infrastructure/validation/audio_validator.py` (NEW)

```python
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
```

**Testing:**
- Unit test: Valid audio file passes
- Unit test: Invalid MIME type rejected
- Unit test: Oversized file rejected
- Unit test: MIME spoofing detected
- Integration test: Upload valid audio, verify validation

---

#### 1.4 API Schemas

**File:** `/backend/app/adapters/inbound/transcription_schemas.py` (NEW)

```python
# ABOUTME: Pydantic schemas for transcription API request/response
# ABOUTME: Defines validation rules and OpenAPI documentation

from pydantic import BaseModel, Field
from typing import Optional

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
```

---

#### 1.5 Transcription API Endpoint

**File:** `/backend/app/adapters/inbound/transcription_router.py` (NEW)

```python
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
    - Rate limited to 10 requests/minute per user
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
        audio_content = await validate_audio_file(audio_file)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid audio file"
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
```

**Register Router:**

**File:** `/backend/app/main.py` (MODIFY)

Add after existing router registrations:

```python
from app.adapters.inbound.transcription_router import router as transcription_router

app.include_router(transcription_router)
```

**Testing:**
- Integration test: Authenticated user uploads audio, receives transcription
- Integration test: Unauthenticated request rejected (401)
- Integration test: Invalid conversation_id rejected (404)
- Integration test: Other user's conversation rejected (403)
- Integration test: Invalid audio file rejected (400)
- Integration test: Oversized file rejected (413)
- E2E test: Upload audio → transcribe → send message → LLM response

---

### Phase 2: Frontend UI Components (Priority: HIGH)

**Objective:** Add microphone button to MessageInput with clean separation of concerns

#### 2.1 Speech-to-Text Custom Hook

**File:** `/frontend/src/hooks/useSpeechToText.ts` (NEW)

```typescript
// ABOUTME: Custom React hook for browser audio recording and transcription
// ABOUTME: Manages MediaRecorder API, audio state, and transcription service calls

import { useState, useRef, useCallback } from 'react';
import { transcriptionService } from '../services/transcriptionService';

interface UseSpeechToTextOptions {
  onTranscriptComplete?: (transcript: string) => void;
  conversationId?: string;
  language?: string;
}

interface UseSpeechToTextReturn {
  isRecording: boolean;
  isTranscribing: boolean;
  error: string | null;
  transcript: string;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  resetTranscript: () => void;
}

export function useSpeechToText(
  options: UseSpeechToTextOptions = {}
): UseSpeechToTextReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transcript, setTranscript] = useState('');

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    try {
      setError(null);

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Create MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());

        // Create audio blob
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });

        // Transcribe
        setIsTranscribing(true);
        try {
          const result = await transcriptionService.transcribe(
            audioBlob,
            options.conversationId,
            options.language
          );

          setTranscript(result.text);
          setError(null);

          if (options.onTranscriptComplete) {
            options.onTranscriptComplete(result.text);
          }
        } catch (err) {
          const errorMessage = err instanceof Error ? err.message : 'Transcription failed';
          setError(errorMessage);
        } finally {
          setIsTranscribing(false);
        }
      };

      mediaRecorder.start();
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to access microphone';
      setError(errorMessage);
      setIsRecording(false);
    }
  }, [options]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  }, [isRecording]);

  const resetTranscript = useCallback(() => {
    setTranscript('');
    setError(null);
  }, []);

  return {
    isRecording,
    isTranscribing,
    error,
    transcript,
    startRecording,
    stopRecording,
    resetTranscript,
  };
}
```

**Testing:**
- Unit test: Hook initializes with correct default state
- Unit test: startRecording requests microphone permission
- Unit test: stopRecording stops MediaRecorder
- Unit test: Transcription updates transcript state
- Unit test: Error handling for permission denied
- Unit test: Cleanup on unmount

---

#### 2.2 Transcription Service Client

**File:** `/frontend/src/services/transcriptionService.ts` (NEW)

```typescript
// ABOUTME: API client for backend transcription service
// ABOUTME: Handles audio upload and transcription requests with auth headers

import axios from 'axios';
import axiosConfig from './axiosConfig';

export interface TranscriptionResponse {
  text: string;
  language: string;
  duration: number;
}

class TranscriptionService {
  private getAuthHeaders() {
    const token = localStorage.getItem('token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async transcribe(
    audioBlob: Blob,
    conversationId?: string,
    language?: string
  ): Promise<TranscriptionResponse> {
    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'recording.webm');

    if (conversationId) {
      formData.append('conversation_id', conversationId);
    }

    if (language) {
      formData.append('language', language);
    }

    const response = await axiosConfig.post<TranscriptionResponse>(
      '/api/transcribe',
      formData,
      {
        headers: {
          ...this.getAuthHeaders(),
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  }
}

export const transcriptionService = new TranscriptionService();
```

**Testing:**
- Unit test: Transcribe method creates correct FormData
- Unit test: Auth headers included in request
- Integration test: Upload audio to backend, receive transcription

---

#### 2.3 Update MessageInput Component

**File:** `/frontend/src/components/chat/MessageInput.tsx` (MODIFY)

**Current code (lines 1-50):** Simple textarea with Send button

**Modifications needed:**

1. Import hook and icon:
```typescript
import { Mic, Loader2 } from 'lucide-react';
import { useSpeechToText } from '../hooks/useSpeechToText';
import { useEffect } from 'react';
```

2. Add hook usage (after line 14):
```typescript
const {
  isRecording,
  isTranscribing,
  error: transcriptionError,
  transcript,
  startRecording,
  stopRecording,
  resetTranscript
} = useSpeechToText({
  onTranscriptComplete: (text) => {
    setInput(text);
  }
});
```

3. Add microphone button (in the flex container, line 30):
```typescript
<button
  onClick={isRecording ? stopRecording : startRecording}
  disabled={disabled || isTranscribing}
  aria-label={isRecording ? "Stop recording" : "Start recording"}
  aria-pressed={isRecording}
  className={`px-4 py-2 rounded-lg border transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed ${
    isRecording
      ? "bg-red-50 border-red-500 text-red-600 hover:bg-red-100 animate-pulse"
      : "bg-white border-gray-300 text-gray-700 hover:bg-gray-50"
  }`}
>
  {isTranscribing ? (
    <Loader2 className="h-5 w-5 animate-spin" />
  ) : isRecording ? (
    <Mic className="h-5 w-5" />
  ) : (
    <Mic className="h-5 w-5" />
  )}
</button>
```

4. Add error display (after textarea):
```typescript
{transcriptionError && (
  <div className="text-red-500 text-sm mt-2">
    {transcriptionError}
  </div>
)}
```

**Final UI Layout:**
```
[Textarea (flex-1)] [Mic Button] [Send Button]
```

**Testing:**
- Unit test: Microphone button renders
- Unit test: Click microphone starts recording
- Unit test: Click again stops recording
- Unit test: Transcript updates textarea
- Unit test: Error message displays on failure
- Unit test: Button disabled when component disabled
- Integration test: Full recording → transcription → send flow
- E2E test: User records audio, edits, sends message

---

### Phase 3: Security & Rate Limiting (Priority: MEDIUM)

**Objective:** Protect against abuse and secure file handling

#### 3.1 Rate Limiting

**File:** `/backend/app/main.py` (MODIFY)

Add rate limiting to the application:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# After app initialization
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

**File:** `/backend/app/adapters/inbound/transcription_router.py` (MODIFY)

Add rate limiting to transcription endpoint:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("", response_model=TranscriptionResponse)
@limiter.limit("10/minute")  # 10 requests per minute per IP
async def transcribe_audio(...):
    # existing implementation
```

**Testing:**
- Integration test: 11th request in 1 minute returns 429
- Integration test: Rate limit resets after 1 minute

---

#### 3.2 Secure Temporary File Handling

**File:** `/backend/app/infrastructure/storage/temp_file_handler.py` (NEW)

```python
# ABOUTME: Secure temporary file handling with guaranteed cleanup
# ABOUTME: Provides context manager for audio file storage with secure permissions

import tempfile
import os
from pathlib import Path
from uuid import uuid4
from contextlib import contextmanager

@contextmanager
def secure_temp_file(suffix: str = ".webm"):
    """
    Context manager for secure temporary file handling.
    - Creates file in OS temp directory
    - Sets secure permissions (600)
    - Generates random filename
    - Guarantees cleanup on exit
    """
    temp_dir = tempfile.gettempdir()
    filename = f"{uuid4().hex}{suffix}"
    filepath = Path(temp_dir) / filename

    try:
        # Create file with secure permissions (owner read/write only)
        filepath.touch(mode=0o600)
        yield filepath
    finally:
        # Secure delete: overwrite before deletion
        if filepath.exists():
            try:
                size = filepath.stat().st_size
                filepath.write_bytes(os.urandom(size))
            except:
                pass
            filepath.unlink()
```

Update OpenAI Whisper service to use this:

**File:** `/backend/app/adapters/outbound/transcription/openai_whisper_service.py` (MODIFY)

```python
from app.infrastructure.storage.temp_file_handler import secure_temp_file

async def transcribe(...):
    with secure_temp_file(suffix=os.path.splitext(filename)[1]) as tmp_path:
        tmp_path.write_bytes(audio_content)

        with open(tmp_path, "rb") as audio_file:
            response = await self.client.audio.transcriptions.create(...)

        return {...}
```

**Testing:**
- Unit test: Temp file created with 600 permissions
- Unit test: Temp file deleted on success
- Unit test: Temp file deleted on exception
- Unit test: Secure delete overwrites before unlink

---

### Phase 4: Testing & Documentation (Priority: MEDIUM)

#### 4.1 Backend Tests

**File:** `/backend/tests/unit/test_transcription_service.py` (NEW)

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO
from app.adapters.outbound.transcription.openai_whisper_service import OpenAIWhisperService

@pytest.mark.asyncio
async def test_transcribe_success():
    """Test successful audio transcription."""
    service = OpenAIWhisperService()

    with patch.object(service.client.audio.transcriptions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = MagicMock(
            text="Hello world",
            language="en",
            duration=2.5
        )

        result = await service.transcribe(
            audio_content=b"fake audio",
            filename="test.mp3"
        )

        assert result["text"] == "Hello world"
        assert result["language"] == "en"
        assert result["duration"] == 2.5

@pytest.mark.asyncio
async def test_transcribe_with_language():
    """Test transcription with language hint."""
    service = OpenAIWhisperService()

    with patch.object(service.client.audio.transcriptions, 'create', new_callable=AsyncMock) as mock_create:
        await service.transcribe(
            audio_content=b"fake audio",
            filename="test.mp3",
            language="es"
        )

        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["language"] == "es"
```

**File:** `/backend/tests/integration/test_transcription_api.py` (NEW)

```python
import pytest
from httpx import AsyncClient
from io import BytesIO

@pytest.mark.asyncio
async def test_transcribe_endpoint_authenticated(client: AsyncClient, auth_headers: dict):
    """Test authenticated transcription request."""
    audio_file = BytesIO(b"fake audio content")

    response = await client.post(
        "/api/transcribe",
        headers=auth_headers,
        files={"audio_file": ("test.mp3", audio_file, "audio/mpeg")}
    )

    assert response.status_code == 200
    data = response.json()
    assert "text" in data
    assert "language" in data
    assert "duration" in data

@pytest.mark.asyncio
async def test_transcribe_endpoint_unauthenticated(client: AsyncClient):
    """Test unauthenticated request is rejected."""
    audio_file = BytesIO(b"fake audio content")

    response = await client.post(
        "/api/transcribe",
        files={"audio_file": ("test.mp3", audio_file, "audio/mpeg")}
    )

    assert response.status_code == 401
```

#### 4.2 Frontend Tests

**File:** `/frontend/src/hooks/useSpeechToText.test.ts` (NEW)

```typescript
import { renderHook, act } from '@testing-library/react';
import { useSpeechToText } from './useSpeechToText';

describe('useSpeechToText', () => {
  beforeEach(() => {
    // Mock navigator.mediaDevices
    global.navigator.mediaDevices = {
      getUserMedia: jest.fn(),
    } as any;
  });

  it('should initialize with default state', () => {
    const { result } = renderHook(() => useSpeechToText());

    expect(result.current.isRecording).toBe(false);
    expect(result.current.isTranscribing).toBe(false);
    expect(result.current.error).toBe(null);
    expect(result.current.transcript).toBe('');
  });

  it('should start recording when startRecording is called', async () => {
    const mockStream = {
      getTracks: () => [{ stop: jest.fn() }],
    };

    (navigator.mediaDevices.getUserMedia as jest.Mock).mockResolvedValue(mockStream);

    const { result } = renderHook(() => useSpeechToText());

    await act(async () => {
      await result.current.startRecording();
    });

    expect(result.current.isRecording).toBe(true);
  });

  // Additional tests...
});
```

**File:** `/frontend/src/components/chat/MessageInput.test.tsx` (MODIFY)

Add tests for microphone button functionality.

---

#### 4.3 API Documentation

**File:** `/doc/general/API.md` (MODIFY)

Add transcription endpoint documentation:

```markdown
### POST /api/transcribe

Transcribe audio file to text using OpenAI Whisper.

**Authentication:** Required (JWT token)

**Rate Limit:** 10 requests/minute per user

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body:
  - `audio_file` (file, required): Audio file (webm, wav, mp3, m4a, ogg)
  - `language` (string, optional): ISO 639-1 language code (e.g., "en", "es")
  - `conversation_id` (string, optional): Conversation ID for ownership verification

**Response:**
```json
{
  "text": "Transcribed text from audio",
  "language": "en",
  "duration": 3.5
}
```

**Error Codes:**
- 400: Invalid audio file format or size
- 401: Authentication required
- 403: Access denied (conversation ownership)
- 413: File too large (>25MB)
- 429: Rate limit exceeded
- 500: Transcription service error
```

---

## File Checklist

### Files to Create (Backend)

- [ ] `/backend/app/core/ports/transcription_service.py`
- [ ] `/backend/app/adapters/outbound/transcription/openai_whisper_service.py`
- [ ] `/backend/app/adapters/inbound/transcription_router.py`
- [ ] `/backend/app/adapters/inbound/transcription_schemas.py`
- [ ] `/backend/app/infrastructure/validation/audio_validator.py`
- [ ] `/backend/app/infrastructure/storage/temp_file_handler.py`
- [ ] `/backend/tests/unit/test_transcription_service.py`
- [ ] `/backend/tests/integration/test_transcription_api.py`

### Files to Modify (Backend)

- [ ] `/backend/app/infrastructure/config/settings.py` - Add transcription settings
- [ ] `/backend/app/main.py` - Register transcription router, add rate limiting
- [ ] `/backend/requirements.txt` - Add dependencies
- [ ] `/.env.example` - Add transcription env vars
- [ ] `/doc/general/API.md` - Document transcription endpoint

### Files to Create (Frontend)

- [ ] `/frontend/src/hooks/useSpeechToText.ts`
- [ ] `/frontend/src/services/transcriptionService.ts`
- [ ] `/frontend/src/hooks/useSpeechToText.test.ts`

### Files to Modify (Frontend)

- [ ] `/frontend/src/components/chat/MessageInput.tsx` - Add microphone button
- [ ] `/frontend/package.json` - No changes needed (lucide-react already installed)

---

## Dependencies

### Backend

```txt
openai>=1.0.0              # OpenAI Whisper API
python-multipart           # File upload support
slowapi>=0.1.8            # Rate limiting
python-magic              # File magic number validation
```

### Frontend

No new dependencies needed:
- `lucide-react` - Already installed (for Mic icon)
- `axios` - Already installed (for API calls)

---

## Environment Variables

```bash
# Add to .env
TRANSCRIPTION_PROVIDER=openai-whisper
WHISPER_MODEL=whisper-1
TRANSCRIPTION_MAX_FILE_SIZE_MB=25
TRANSCRIPTION_MAX_DURATION_SECONDS=300
```

---

## Security Considerations

1. **Authentication:** All requests require valid JWT token
2. **Authorization:** Conversation ownership verified before transcription
3. **Rate Limiting:** 10 requests/minute per user to prevent abuse
4. **File Validation:**
   - MIME type whitelist (webm, wav, mp3, m4a, ogg)
   - Magic number verification (prevents spoofing)
   - Size limit: 25MB
   - Duration limit: 5 minutes
5. **Secure File Handling:**
   - Temp files with 600 permissions
   - Random filenames (prevents path traversal)
   - Guaranteed cleanup (context managers)
   - Secure delete (overwrite before unlink)
6. **API Key Protection:** OPENAI_API_KEY stored in environment, never logged

---

## Privacy Considerations

1. **Audio Storage:** NO audio files stored permanently (transcripts only)
2. **Temporary Files:** Deleted immediately after transcription
3. **Third-Party Processing:** Audio sent to OpenAI Whisper API
4. **User Consent:** Should display notice before first recording
5. **Data Retention:** Transcripts stored in LangGraph checkpoints (existing pattern)

---

## Cost Implications

**OpenAI Whisper Pricing:** $0.006 per minute of audio

**Example Costs:**
- 60-second recording: $0.006
- 1,000 transcriptions/day (60s avg): $6/day = $180/month
- 10,000 transcriptions/month: $60/month

**Mitigation:**
- Rate limiting (10 req/min per user)
- File duration limit (5 min max)
- Monitor usage via OpenAI dashboard
- Set budget alerts

---

## Testing Strategy

### Unit Tests
- ✅ Transcription service (mock OpenAI API)
- ✅ Audio validator (MIME type, size, magic number)
- ✅ Temp file handler (permissions, cleanup)
- ✅ useSpeechToText hook (MediaRecorder, states)

### Integration Tests
- ✅ POST /api/transcribe (auth, validation, transcription)
- ✅ Rate limiting (429 after 10 requests)
- ✅ Conversation ownership (403 for other user's conversation)
- ✅ File upload (multipart/form-data)

### End-to-End Tests
- ✅ Full user journey: Record → Upload → Transcribe → Display → Send
- ✅ Error scenarios: Permission denied, transcription failure, network error
- ✅ Browser compatibility: Chrome, Firefox, Safari

---

## Success Criteria

1. **Functional:**
   - ✅ User can click microphone button to start recording
   - ✅ Recording indicator shows visual feedback
   - ✅ Audio transcribed accurately (>90% accuracy for clear audio)
   - ✅ Transcribed text appears in textarea for review
   - ✅ User can edit transcribed text before sending
   - ✅ Existing message flow works unchanged

2. **Performance:**
   - ✅ Transcription completes in <10 seconds for 60s audio
   - ✅ No WebSocket blocking during transcription
   - ✅ Temp files cleaned up within 1 second

3. **Security:**
   - ✅ All requests authenticated
   - ✅ Conversation ownership verified
   - ✅ Rate limiting enforced
   - ✅ File validation prevents malicious uploads
   - ✅ No audio files stored permanently

4. **User Experience:**
   - ✅ Clear visual feedback (recording, transcribing states)
   - ✅ Helpful error messages
   - ✅ Microphone button accessible via keyboard
   - ✅ Screen reader announcements for state changes

---

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Transcription latency (5-10s) | High | High | Show loading indicator, allow concurrent UI interaction |
| Poor audio quality → low accuracy | Medium | Medium | Allow text editing before send, suggest quiet environment |
| API cost overruns | High | Low | Rate limiting, usage monitoring, budget alerts |
| Browser compatibility (Safari) | Medium | Low | Feature detection, fallback message for unsupported browsers |
| Microphone permission denied | Medium | Medium | Clear error message, instructions to re-enable |
| MIME spoofing (security) | High | Low | Magic number verification, file size limits |

---

## Next Steps After Implementation

1. **Monitor Usage:**
   - Track transcription success/failure rates
   - Monitor API costs (OpenAI dashboard)
   - Collect user feedback on accuracy

2. **Future Enhancements:**
   - Support for more languages (auto-detect vs. manual select)
   - Real-time streaming transcription (long recordings)
   - Audio playback of original recording
   - Alternative transcription providers (Google Speech, AssemblyAI)
   - Speaker diarization (multi-speaker support)

3. **Performance Optimization:**
   - Client-side audio compression (reduce file size)
   - Caching transcriptions by audio hash
   - Background worker queue for high traffic

---

## References

**Analyzer Documents:**
- `/doc/features/Add speech-to-text input for chat messages/react_frontend.md`
- `/doc/features/Add speech-to-text input for chat messages/ui_components.md`
- `/doc/features/Add speech-to-text input for chat messages/api_contract.md`
- `/doc/features/Add speech-to-text input for chat messages/data_flow.md`
- `/doc/features/Add speech-to-text input for chat messages/security.md`
- `/doc/features/Add speech-to-text input for chat messages/llm_integration.md`

**External Documentation:**
- [OpenAI Whisper API](https://platform.openai.com/docs/guides/speech-to-text)
- [MediaRecorder API](https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)

---

**Plan prepared by:** Claude (LLM Integration Analyzer, Security Analyzer, API Contract Analyzer, Data Flow Analyzer, React Frontend Analyzer, Shadcn UI Analyzer)
**Plan version:** 1.0
**Date:** 2025-10-30
