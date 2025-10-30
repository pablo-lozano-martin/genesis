# API Contract Analysis

## Request Summary
Add speech-to-text input capability for chat messages. Users should be able to record audio, send it to the backend for transcription, and have the transcribed text sent as a chat message.

## Relevant Files & Modules

### Files to Examine

#### API Layer (Inbound Adapters)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_router.py` - WebSocket endpoints for chat and onboarding
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket message handling and streaming logic
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py` - WebSocket message protocol schemas
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_router.py` - REST API for message retrieval
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_schemas.py` - Message response schemas
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/conversation_router.py` - Conversation CRUD endpoints
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/auth_router.py` - Authentication endpoints (error handling patterns)

#### Security & Dependencies
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/security/dependencies.py` - OAuth2 authentication dependencies for REST endpoints
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/security/websocket_auth.py` - WebSocket authentication utilities

#### Application Configuration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py` - FastAPI application setup and router registration
- `/Users/pablolozano/Mac Projects August/genesis/doc/general/API.md` - API reference documentation

### Key Endpoints & Functions

#### Current Message Submission Flow
- `WS /ws/chat?token=<jwt_token>` in `websocket_router.py` - Real-time chat streaming endpoint
- `WS /ws/onboarding?token=<jwt_token>` in `websocket_router.py` - Onboarding conversation endpoint
- `handle_websocket_chat()` in `websocket_handler.py` - Core WebSocket message processing
- `GET /api/conversations/{conversation_id}/messages` in `message_router.py` - Message retrieval endpoint

#### Schema Definitions
- `ClientMessage` in `websocket_schemas.py` - Client-to-server message format
- `MessageResponse` in `message_schemas.py` - Message retrieval response format
- `ServerTokenMessage`, `ServerCompleteMessage`, `ServerErrorMessage` in `websocket_schemas.py` - Server-to-client message types

#### Authentication Patterns
- `get_user_from_websocket()` in `websocket_auth.py` - WebSocket JWT authentication
- `get_current_user()` in `dependencies.py` - REST endpoint JWT authentication

## Current API Contract Overview

### Message Submission Architecture

The Genesis application uses a **WebSocket-first architecture** for real-time chat interactions. There are NO REST endpoints for submitting messages - all message submission happens through WebSocket connections with LangGraph streaming.

#### WebSocket Protocol

**Connection Endpoint:** `WS /ws/chat?token=<jwt_token>`

**Authentication:**
- JWT token as query parameter: `/ws/chat?token=<jwt_token>`
- OR Authorization header: `Bearer <jwt_token>`

**Client → Server Message Format:**
```json
{
  "type": "message",
  "conversation_id": "uuid",
  "content": "User message text"
}
```

**Server → Client Message Types:**
- `{ "type": "token", "content": "..." }` - Streaming token
- `{ "type": "complete", "message_id": "uuid", "conversation_id": "uuid" }` - Completion
- `{ "type": "error", "message": "...", "code": "..." }` - Error
- `{ "type": "tool_start", "tool_name": "...", "tool_input": "...", "source": "local|mcp" }` - Tool execution start
- `{ "type": "tool_complete", "tool_name": "...", "tool_result": "...", "source": "local|mcp" }` - Tool completion
- `{ "type": "pong" }` - Ping response

### Request Schemas

#### ClientMessage (WebSocket)
```python
class ClientMessage(BaseModel):
    type: MessageType = Field(default=MessageType.MESSAGE)
    conversation_id: str = Field(..., description="Conversation UUID")
    content: str = Field(..., min_length=1, description="User message content")
```

**Validation Rules:**
- `content` is required and must be at least 1 character
- `conversation_id` is required and must be a valid UUID string
- `type` defaults to "message"

### Response Schemas

#### MessageResponse (REST - for retrieval only)
```python
class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: MessageRole  # USER, ASSISTANT, SYSTEM
    content: str
    created_at: datetime
    metadata: Optional[dict] = None
```

### Authentication & Authorization

**REST Endpoints:**
- Use `CurrentUser = Annotated[User, Depends(get_current_active_user)]`
- JWT token in `Authorization: Bearer <token>` header
- Validated via `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")`

**WebSocket Endpoints:**
- Use `get_user_from_websocket(websocket)` function
- JWT token from query param (`?token=`) or Authorization header
- Returns `User` entity or raises `WebSocketException`

**Authorization Pattern:**
- Conversation ownership always verified in App Database before accessing messages
- Pattern: Check `conversation.user_id == current_user.id`
- Returns 403 Forbidden if access denied, 404 if conversation not found

### Data Flow

```
1. Client establishes WebSocket connection with JWT token
   ↓
2. WebSocket handler authenticates user via get_user_from_websocket()
   ↓
3. Client sends JSON message with conversation_id and content
   ↓
4. Handler verifies conversation ownership in App Database
   ↓
5. Handler calls graph.astream_events(input_data, config) with:
   - input_data = {"messages": [HumanMessage], "conversation_id": ..., "user_id": ...}
   - config = RunnableConfig with thread_id = conversation.id
   ↓
6. LangGraph processes message through nodes and streams tokens
   ↓
7. Handler streams tokens to client via ServerTokenMessage
   ↓
8. LangGraph automatically persists messages via checkpointer
   ↓
9. Handler sends ServerCompleteMessage on completion
```

### Error Handling Patterns

The application uses consistent error handling across all API layers:

**REST Endpoints (HTTPException):**
```python
# 400 Bad Request - Validation errors, duplicate resources
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Specific error message"
)

# 401 Unauthorized - Authentication failures
raise HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"}
)

# 403 Forbidden - Authorization failures (access denied)
raise HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Access denied"
)

# 404 Not Found - Resource not found
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Resource not found"
)

# 500 Internal Server Error - Unexpected errors
raise HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail="Generic error message"
)
```

**WebSocket Endpoints (ServerErrorMessage):**
```python
error_msg = ServerErrorMessage(
    message="Human-readable error description",
    code="ERROR_CODE"  # e.g., "ACCESS_DENIED", "INVALID_FORMAT", "LLM_ERROR", "INTERNAL_ERROR"
)
await manager.send_message(websocket, error_msg.model_dump())
```

**WebSocket Authentication Failures (WebSocketException):**
```python
raise WebSocketException(
    code=status.WS_1008_POLICY_VIOLATION,  # or WS_1011_INTERNAL_ERROR
    reason="Human-readable reason"
)
```

### Existing File Upload Support

**Current Status:** NO file upload endpoints exist in the codebase.

- No `UploadFile` usage found in any routers
- No file storage infrastructure (local filesystem, S3, etc.)
- No multipart/form-data handling
- All current endpoints use JSON request bodies

## Impact Analysis

### Components Affected

1. **Inbound Adapters (API Layer):**
   - NEW: Audio transcription endpoint (REST or WebSocket)
   - NEW: Request schema for audio upload
   - NEW: Response schema for transcription result
   - UNCHANGED: Existing WebSocket message submission (will receive transcribed text)

2. **Infrastructure Layer:**
   - NEW: Speech-to-text service integration (OpenAI Whisper, Google Speech-to-Text, etc.)
   - NEW: Temporary file storage for audio upload
   - NEW: Audio file validation (format, size, duration)

3. **Security Layer:**
   - UNCHANGED: Use existing JWT authentication
   - NEW: Rate limiting considerations for audio uploads
   - NEW: File size validation to prevent abuse

4. **Domain Layer:**
   - UNCHANGED: No changes needed - transcribed text flows through existing message handling

### Integration Points

**Audio Transcription → Message Submission:**
- Option A: Client-side integration (frontend calls transcription endpoint, then sends text via WebSocket)
- Option B: Server-side integration (transcription endpoint automatically sends message via graph)

**Recommendation:** Option A (client-side) maintains clean separation of concerns and follows RESTful principles.

## API Contract Recommendations

### Proposed Endpoint

**Create a new REST endpoint for audio transcription:**

**Endpoint:** `POST /api/transcribe`

**Why REST instead of WebSocket?**
- Audio file upload requires multipart/form-data encoding
- One-shot request/response pattern (not streaming)
- Simpler error handling and retry logic
- Standard HTTP file upload patterns
- Client can chain transcription → WebSocket message submission

### Proposed Request Schema

```python
# File: backend/app/adapters/inbound/transcription_schemas.py

from pydantic import BaseModel, Field
from typing import Optional
from fastapi import UploadFile, File

class TranscriptionRequest:
    """
    Audio transcription request (multipart/form-data).

    Note: FastAPI handles multipart/form-data via parameters, not Pydantic models.
    """
    audio_file: UploadFile = File(
        ...,
        description="Audio file to transcribe (supported formats: mp3, mp4, mpeg, mpga, m4a, wav, webm)"
    )
    language: Optional[str] = Field(
        default=None,
        description="ISO 639-1 language code (e.g., 'en', 'es'). Auto-detected if not provided."
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Optional conversation ID for context-aware transcription"
    )

class TranscriptionResponse(BaseModel):
    """Audio transcription response."""

    text: str = Field(..., description="Transcribed text from audio")
    language: Optional[str] = Field(None, description="Detected or specified language")
    duration: Optional[float] = Field(None, description="Audio duration in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Hello, how can I help you today?",
                "language": "en",
                "duration": 3.5
            }
        }

class TranscriptionErrorResponse(BaseModel):
    """Error response for transcription failures."""

    detail: str = Field(..., description="Error description")
    error_code: str = Field(..., description="Machine-readable error code")

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Audio file exceeds maximum duration of 60 seconds",
                "error_code": "AUDIO_TOO_LONG"
            }
        }
```

### Proposed Endpoint Implementation

```python
# File: backend/app/adapters/inbound/transcription_router.py

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from typing import Optional
from app.adapters.inbound.transcription_schemas import TranscriptionResponse
from app.infrastructure.security.dependencies import CurrentUser
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/transcribe", tags=["transcription"])

# Validation constants
MAX_FILE_SIZE_MB = 25  # OpenAI Whisper limit
MAX_DURATION_SECONDS = 60  # Reasonable limit for chat messages
SUPPORTED_FORMATS = {
    "audio/mpeg",      # mp3
    "audio/mp4",       # mp4, m4a
    "audio/wav",       # wav
    "audio/webm",      # webm
    "audio/ogg",       # ogg
}

@router.post("", response_model=TranscriptionResponse)
async def transcribe_audio(
    current_user: CurrentUser,
    audio_file: UploadFile = File(..., description="Audio file to transcribe"),
    language: Optional[str] = Form(None, description="ISO 639-1 language code"),
    conversation_id: Optional[str] = Form(None, description="Optional conversation ID")
):
    """
    Transcribe audio file to text using speech-to-text service.

    The transcribed text can then be sent via WebSocket to continue the conversation.

    **Supported Formats:** mp3, mp4, mpeg, mpga, m4a, wav, webm, ogg
    **Max File Size:** 25MB
    **Max Duration:** 60 seconds

    Args:
        current_user: Authenticated user (from JWT token)
        audio_file: Audio file upload
        language: Optional language code for transcription
        conversation_id: Optional conversation context

    Returns:
        TranscriptionResponse with transcribed text

    Raises:
        HTTPException 400: Invalid file format, size, or duration
        HTTPException 401: Authentication failure
        HTTPException 500: Transcription service error
    """
    logger.info(f"Transcription request from user {current_user.id}, file: {audio_file.filename}")

    # Validate file type
    if audio_file.content_type not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format: {audio_file.content_type}. Supported formats: {', '.join(SUPPORTED_FORMATS)}"
        )

    # Validate file size
    audio_file.file.seek(0, 2)  # Seek to end
    file_size = audio_file.file.tell()
    audio_file.file.seek(0)  # Reset to beginning

    max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audio file exceeds maximum size of {MAX_FILE_SIZE_MB}MB"
        )

    # Verify conversation ownership if conversation_id provided
    if conversation_id:
        from app.adapters.outbound.repositories.mongo_conversation_repository import MongoConversationRepository
        conversation_repository = MongoConversationRepository()
        conversation = await conversation_repository.get_by_id(conversation_id)

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

    try:
        # TODO: Get transcription service from dependency injection
        # transcription_service = get_transcription_service()

        # Read audio file content
        audio_content = await audio_file.read()

        # TODO: Call transcription service
        # result = await transcription_service.transcribe(
        #     audio_content=audio_content,
        #     filename=audio_file.filename,
        #     language=language,
        #     user_id=current_user.id
        # )

        # Placeholder response
        result = {
            "text": "Transcribed text will appear here",
            "language": language or "en",
            "duration": 3.5
        }

        logger.info(f"Transcription successful for user {current_user.id}")

        return TranscriptionResponse(**result)

    except ValueError as e:
        # Validation errors from transcription service
        logger.warning(f"Transcription validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Transcription failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transcription service unavailable"
        )
```

### Infrastructure: Speech-to-Text Service

**Create a port (interface) in the core domain:**

```python
# File: backend/app/core/ports/transcription_service.py

from abc import ABC, abstractmethod
from typing import Optional

class ITranscriptionService(ABC):
    """
    Port (interface) for speech-to-text transcription services.

    Allows swapping between different transcription providers
    (OpenAI Whisper, Google Speech-to-Text, AssemblyAI, etc.)
    """

    @abstractmethod
    async def transcribe(
        self,
        audio_content: bytes,
        filename: str,
        language: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> dict:
        """
        Transcribe audio content to text.

        Args:
            audio_content: Raw audio file bytes
            filename: Original filename (for format detection)
            language: ISO 639-1 language code (optional)
            user_id: User ID for logging/tracking (optional)

        Returns:
            dict with keys: text, language, duration

        Raises:
            ValueError: If audio is invalid (too long, corrupted, etc.)
            Exception: If transcription service fails
        """
        pass
```

**Create adapter implementations:**

```python
# File: backend/app/adapters/outbound/transcription/openai_transcription_service.py

import tempfile
import os
from openai import AsyncOpenAI
from app.core.ports.transcription_service import ITranscriptionService
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

class OpenAITranscriptionService(ITranscriptionService):
    """OpenAI Whisper transcription service implementation."""

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def transcribe(
        self,
        audio_content: bytes,
        filename: str,
        language: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> dict:
        """
        Transcribe audio using OpenAI Whisper API.

        See: https://platform.openai.com/docs/guides/speech-to-text
        """
        # Write to temporary file (OpenAI API requires file-like object)
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp_file:
            tmp_file.write(audio_content)
            tmp_file_path = tmp_file.name

        try:
            # Call OpenAI Whisper API
            with open(tmp_file_path, "rb") as audio_file:
                transcription = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                    response_format="verbose_json"  # Includes detected language and duration
                )

            return {
                "text": transcription.text,
                "language": transcription.language,
                "duration": transcription.duration
            }

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
```

**Factory for dependency injection:**

```python
# File: backend/app/adapters/outbound/transcription/transcription_service_factory.py

from app.core.ports.transcription_service import ITranscriptionService
from app.adapters.outbound.transcription.openai_transcription_service import OpenAITranscriptionService
from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

def get_transcription_service() -> ITranscriptionService:
    """
    Factory function to create transcription service based on configuration.

    Returns:
        ITranscriptionService implementation
    """
    # TODO: Add TRANSCRIPTION_PROVIDER to settings (default: openai)
    provider = getattr(settings, "transcription_provider", "openai").lower()

    if provider == "openai":
        api_key = settings.openai_api_key
        logger.info("Using OpenAI Whisper for transcription")
        return OpenAITranscriptionService(api_key=api_key)
    else:
        raise ValueError(f"Unsupported transcription provider: {provider}")
```

### Data Flow with Transcription

```
Frontend Flow:
1. User records audio via browser MediaRecorder API
   ↓
2. Convert to supported format (webm, mp3, etc.)
   ↓
3. Upload via POST /api/transcribe with multipart/form-data
   ↓
4. Receive TranscriptionResponse with text
   ↓
5. Send transcribed text via existing WebSocket connection
   ↓
6. Display in chat UI with streaming response

Backend Flow:
1. Receive audio file at POST /api/transcribe
   ↓
2. Authenticate user via CurrentUser dependency
   ↓
3. Validate file format, size, and duration
   ↓
4. Verify conversation ownership (if conversation_id provided)
   ↓
5. Call transcription service (OpenAI Whisper)
   ↓
6. Return TranscriptionResponse with text
   ↓
7. Frontend sends text via WebSocket (existing flow)
```

## Implementation Guidance

### Step-by-Step Approach

1. **Create Infrastructure (Ports & Adapters):**
   - Create `ITranscriptionService` port in `backend/app/core/ports/transcription_service.py`
   - Create `OpenAITranscriptionService` adapter in `backend/app/adapters/outbound/transcription/`
   - Create factory function `get_transcription_service()` for dependency injection
   - Add environment variables to `settings.py`: `TRANSCRIPTION_PROVIDER`, `TRANSCRIPTION_MAX_FILE_SIZE_MB`

2. **Create API Schemas:**
   - Create `backend/app/adapters/inbound/transcription_schemas.py`
   - Define `TranscriptionResponse` and `TranscriptionErrorResponse` Pydantic models
   - Add validation constants (max file size, supported formats, max duration)

3. **Create API Router:**
   - Create `backend/app/adapters/inbound/transcription_router.py`
   - Implement `POST /api/transcribe` endpoint with file upload handling
   - Add authentication via `CurrentUser` dependency
   - Add file validation (format, size)
   - Add conversation ownership verification
   - Add comprehensive error handling following existing patterns

4. **Register Router:**
   - Import router in `backend/app/main.py`
   - Add `app.include_router(transcription_router)` after other routers
   - Update API documentation in `doc/general/API.md`

5. **Testing:**
   - Unit tests for `OpenAITranscriptionService`
   - Integration tests for `/api/transcribe` endpoint
   - Test file validation (invalid formats, oversized files)
   - Test authentication and authorization
   - Test error handling for transcription failures

6. **Frontend Integration:**
   - Add audio recording UI component
   - Implement audio upload to `/api/transcribe`
   - Handle transcription response
   - Send transcribed text via existing WebSocket message flow
   - Add loading/error states during transcription

### Alternative Approach: WebSocket-based Transcription

**NOT RECOMMENDED** but documented for completeness:

Instead of REST endpoint, extend WebSocket protocol:

```python
# Add to websocket_schemas.py
class AudioMessage(BaseModel):
    type: Literal[MessageType.AUDIO] = MessageType.AUDIO
    conversation_id: str
    audio_data: str  # Base64-encoded audio
    audio_format: str  # "webm", "mp3", etc.
    language: Optional[str] = None
```

**Why NOT recommended:**
- Mixing binary data with text protocol is awkward
- Base64 encoding increases payload size by ~33%
- No standard HTTP error codes (harder error handling)
- Complicates WebSocket handler logic
- Harder to implement retries
- Cannot leverage standard multipart/form-data tooling

## Risks and Considerations

### Breaking Changes
- **None** - This is a new endpoint with no impact on existing API contracts

### Security Concerns

1. **File Upload Abuse:**
   - Risk: Users upload very large files to exhaust server resources
   - Mitigation: Enforce MAX_FILE_SIZE (25MB) and MAX_DURATION (60s)
   - Mitigation: Add rate limiting (e.g., 10 requests per minute per user)

2. **Cost Management:**
   - Risk: OpenAI Whisper API charges per audio minute
   - Mitigation: Track usage per user, add usage limits
   - Mitigation: Consider caching transcriptions for duplicate audio

3. **Malicious File Uploads:**
   - Risk: Users upload non-audio files disguised as audio
   - Mitigation: Validate content-type header AND file magic numbers
   - Mitigation: Use temporary storage and clean up after transcription

4. **PII in Audio:**
   - Risk: Audio may contain sensitive personal information
   - Mitigation: Do NOT store audio files permanently
   - Mitigation: Add retention policy for temporary files
   - Mitigation: Log transcription requests but not content

### Performance Considerations

1. **Transcription Latency:**
   - OpenAI Whisper typically takes 2-5 seconds for short audio clips
   - Frontend should show loading state during transcription
   - Consider timeout handling (e.g., 30-second timeout)

2. **Temporary File Cleanup:**
   - Ensure temporary files are deleted even if transcription fails
   - Use try/finally blocks for cleanup
   - Consider background job to clean orphaned temp files

3. **Concurrent Requests:**
   - Transcription is I/O-bound (waiting for API response)
   - FastAPI's async handling is appropriate
   - Consider queueing for high traffic scenarios

### Cost Implications

**OpenAI Whisper API Pricing (as of 2024):**
- $0.006 per minute of audio
- 60-second max duration = $0.006 per transcription
- 1000 transcriptions/day = $6/day = $180/month

**Recommendations:**
- Monitor usage via OpenAI dashboard
- Set usage alerts
- Consider free tier alternatives for development (e.g., local Whisper model)

### Dependencies

**New Python Packages Required:**
```
openai>=1.0.0  # For OpenAI Whisper API
python-multipart  # For FastAPI file upload handling
```

**Environment Variables Required:**
```bash
# Transcription service configuration
TRANSCRIPTION_PROVIDER=openai  # or "google", "assemblyai", etc.
TRANSCRIPTION_MAX_FILE_SIZE_MB=25
TRANSCRIPTION_MAX_DURATION_SECONDS=60

# OpenAI API (likely already exists)
OPENAI_API_KEY=sk-...
```

### Alternative Transcription Providers

If OpenAI Whisper is not suitable, consider:

1. **Google Cloud Speech-to-Text:**
   - Pros: Very accurate, supports 125+ languages
   - Cons: More complex setup, requires GCP account
   - Pricing: $0.006 per 15 seconds

2. **AssemblyAI:**
   - Pros: Simple API, good accuracy
   - Cons: Additional vendor dependency
   - Pricing: $0.00025 per second (~$0.015 per minute)

3. **Local Whisper (faster-whisper):**
   - Pros: No API costs, no external dependency
   - Cons: Requires GPU for reasonable performance, higher infrastructure costs
   - Pricing: Free (but server costs)

**Recommendation:** Start with OpenAI Whisper for simplicity. The port/adapter architecture makes it easy to swap providers later.

## Testing Strategy

### Unit Tests

```python
# File: backend/tests/unit/test_openai_transcription_service.py

import pytest
from unittest.mock import AsyncMock, patch
from app.adapters.outbound.transcription.openai_transcription_service import OpenAITranscriptionService

@pytest.mark.asyncio
async def test_transcribe_success():
    """Test successful transcription."""
    service = OpenAITranscriptionService(api_key="test-key")

    # Mock OpenAI API response
    with patch.object(service.client.audio.transcriptions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = {
            "text": "Hello world",
            "language": "en",
            "duration": 2.5
        }

        result = await service.transcribe(
            audio_content=b"fake audio data",
            filename="test.mp3",
            language="en"
        )

        assert result["text"] == "Hello world"
        assert result["language"] == "en"
        assert result["duration"] == 2.5

@pytest.mark.asyncio
async def test_transcribe_cleans_up_temp_file():
    """Test that temporary files are cleaned up after transcription."""
    service = OpenAITranscriptionService(api_key="test-key")

    with patch.object(service.client.audio.transcriptions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = Exception("API error")

        with pytest.raises(Exception):
            await service.transcribe(
                audio_content=b"fake audio data",
                filename="test.mp3"
            )

        # Verify no temp files left behind
        # (Implementation-specific assertion)
```

### Integration Tests

```python
# File: backend/tests/integration/test_transcription_api.py

import pytest
from httpx import AsyncClient
from fastapi import status
from io import BytesIO

@pytest.mark.asyncio
async def test_transcribe_endpoint_success(
    async_client: AsyncClient,
    auth_headers: dict,
    mock_transcription_service
):
    """Test successful audio transcription via API."""

    # Create fake audio file
    audio_file = BytesIO(b"fake audio content")

    response = await async_client.post(
        "/api/transcribe",
        headers=auth_headers,
        files={"audio_file": ("test.mp3", audio_file, "audio/mpeg")},
        data={"language": "en"}
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "text" in data
    assert "language" in data
    assert data["language"] == "en"

@pytest.mark.asyncio
async def test_transcribe_endpoint_requires_auth(async_client: AsyncClient):
    """Test that transcription endpoint requires authentication."""

    audio_file = BytesIO(b"fake audio content")

    response = await async_client.post(
        "/api/transcribe",
        files={"audio_file": ("test.mp3", audio_file, "audio/mpeg")}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_transcribe_endpoint_validates_file_size(
    async_client: AsyncClient,
    auth_headers: dict
):
    """Test that endpoint rejects oversized files."""

    # Create fake audio larger than MAX_FILE_SIZE
    large_audio = BytesIO(b"x" * (26 * 1024 * 1024))  # 26MB

    response = await async_client.post(
        "/api/transcribe",
        headers=auth_headers,
        files={"audio_file": ("large.mp3", large_audio, "audio/mpeg")}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "exceeds maximum size" in response.json()["detail"]

@pytest.mark.asyncio
async def test_transcribe_endpoint_validates_conversation_ownership(
    async_client: AsyncClient,
    auth_headers: dict,
    other_user_conversation_id: str
):
    """Test that endpoint verifies conversation ownership."""

    audio_file = BytesIO(b"fake audio content")

    response = await async_client.post(
        "/api/transcribe",
        headers=auth_headers,
        files={"audio_file": ("test.mp3", audio_file, "audio/mpeg")},
        data={"conversation_id": other_user_conversation_id}
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
```

### End-to-End Tests

```python
# File: backend/tests/e2e/test_transcription_to_message_flow.py

import pytest
from httpx import AsyncClient
from io import BytesIO

@pytest.mark.asyncio
async def test_full_audio_message_flow(
    async_client: AsyncClient,
    websocket_client,
    auth_headers: dict,
    conversation_id: str
):
    """Test complete flow: record audio → transcribe → send message → receive response."""

    # Step 1: Transcribe audio
    audio_file = BytesIO(b"fake audio content")

    response = await async_client.post(
        "/api/transcribe",
        headers=auth_headers,
        files={"audio_file": ("test.mp3", audio_file, "audio/mpeg")},
        data={"conversation_id": conversation_id}
    )

    assert response.status_code == 200
    transcription = response.json()
    transcribed_text = transcription["text"]

    # Step 2: Send transcribed text via WebSocket
    await websocket_client.send_json({
        "type": "message",
        "conversation_id": conversation_id,
        "content": transcribed_text
    })

    # Step 3: Receive streaming response
    tokens = []
    while True:
        message = await websocket_client.receive_json()

        if message["type"] == "token":
            tokens.append(message["content"])
        elif message["type"] == "complete":
            break
        elif message["type"] == "error":
            pytest.fail(f"Received error: {message}")

    # Verify response
    assert len(tokens) > 0
    full_response = "".join(tokens)
    assert len(full_response) > 0
```

## Summary

### Key Decisions

1. **Use REST endpoint (POST /api/transcribe) instead of extending WebSocket protocol**
   - Cleaner separation of concerns
   - Standard HTTP file upload patterns
   - Better error handling and retry logic

2. **Client-side integration (frontend chains transcription → WebSocket message)**
   - Maintains clean API boundaries
   - No changes needed to existing WebSocket message flow
   - Frontend controls the user experience

3. **Create port/adapter for transcription service**
   - Follows hexagonal architecture
   - Easy to swap providers (OpenAI, Google, AssemblyAI)
   - Testable with mocks

4. **No persistent audio storage**
   - Audio stored in temporary files during transcription
   - Deleted immediately after transcription completes
   - Reduces storage costs and privacy risks

### Files to Create

1. `backend/app/core/ports/transcription_service.py` - Transcription service port (interface)
2. `backend/app/adapters/outbound/transcription/openai_transcription_service.py` - OpenAI Whisper implementation
3. `backend/app/adapters/outbound/transcription/transcription_service_factory.py` - Factory for DI
4. `backend/app/adapters/inbound/transcription_schemas.py` - API request/response schemas
5. `backend/app/adapters/inbound/transcription_router.py` - REST API endpoint
6. `backend/tests/unit/test_openai_transcription_service.py` - Unit tests
7. `backend/tests/integration/test_transcription_api.py` - Integration tests
8. `backend/tests/e2e/test_transcription_to_message_flow.py` - End-to-end tests

### Files to Modify

1. `backend/app/main.py` - Register transcription router
2. `backend/app/infrastructure/config/settings.py` - Add transcription config
3. `backend/requirements.txt` - Add `openai` and `python-multipart` packages
4. `doc/general/API.md` - Document new endpoint
5. `.env.example` - Add transcription environment variables

### No Changes Needed

- WebSocket message submission flow (unchanged)
- Message schemas and validation (unchanged)
- LangGraph integration (unchanged)
- Authentication/authorization patterns (reused as-is)
