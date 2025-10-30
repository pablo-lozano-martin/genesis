# LLM Integration Analysis

## Request Summary

Add speech-to-text transcription capability for chat messages. Users should be able to send audio input (voice messages) that are transcribed to text before being processed by the LLM. This requires integrating a speech-to-text AI service (OpenAI Whisper, Google Speech-to-Text, etc.) following the existing LLM integration patterns.

## Relevant Files & Modules

### Files to Examine

#### LLM Provider Abstraction
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - Abstract port interface defining the contract for LLM operations using LangChain BaseMessage types
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/provider_factory.py` - Factory for creating LLM provider instances based on configuration (openai, anthropic, gemini, ollama)

#### LLM Provider Implementations
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/openai_provider.py` - OpenAI implementation using LangChain's ChatOpenAI
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/anthropic_provider.py` - Anthropic/Claude implementation using LangChain's ChatAnthropic
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/gemini_provider.py` - Google Gemini implementation using LangChain's ChatGoogleGenerativeAI
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/ollama_provider.py` - Local Ollama implementation using LangChain's ChatOllama

#### Configuration & Settings
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py` - Pydantic settings with environment variable management for all LLM providers (API keys, model names, URLs)
- `/Users/pablolozano/Mac Projects August/genesis/.env.example` - Environment variable template showing configuration pattern

#### Message Input & Routing
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket handler for real-time chat with LangGraph streaming using astream_events()
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_router.py` - REST API endpoints for message retrieval from LangGraph checkpoints
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_schemas.py` - Pydantic schemas for message validation

#### LangGraph Integration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - Node for invoking LLM provider with tool binding
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - Conversation state extending LangGraph's MessagesState

#### Testing
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_llm_providers.py` - Unit tests for LLM provider factory

#### Dependencies
- `/Users/pablolozano/Mac Projects August/genesis/backend/requirements.txt` - Python dependencies including langchain-openai, langchain-anthropic, langchain-google-genai

### Key Functions & Classes

#### Port Interface
- `ILLMProvider` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - Abstract interface with methods: `generate()`, `stream()`, `get_model_name()`, `bind_tools()`, `get_model()`

#### Provider Factory
- `LLMProviderFactory.create_provider()` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/provider_factory.py` - Factory method selecting provider based on `settings.llm_provider`
- `get_llm_provider()` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/provider_factory.py` - Convenience function for provider creation

#### Provider Implementations
- `OpenAIProvider.__init__()` - Validates OPENAI_API_KEY and OPENAI_MODEL, creates ChatOpenAI instance
- `OpenAIProvider.generate()` - Async generation using `model.ainvoke(messages)`
- `OpenAIProvider.stream()` - Async streaming using `model.astream(messages)`
- Similar patterns in AnthropicProvider, GeminiProvider, OllamaProvider

#### Configuration
- `Settings` class in `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py` - Pydantic settings with API keys, model names, and provider selection

## Current Integration Overview

### Provider Abstraction

Genesis implements a clean hexagonal architecture with LLM providers as outbound adapters. The abstraction pattern is:

1. **Port Interface** (`ILLMProvider`): Abstract interface in the core domain defining the contract for LLM operations
2. **Factory Pattern** (`LLMProviderFactory`): Creates provider instances based on configuration
3. **Adapter Implementations**: Concrete implementations for OpenAI, Anthropic, Gemini, and Ollama
4. **LangChain Integration**: All providers use LangChain's native chat models and BaseMessage types

This pattern allows the application to switch between LLM providers without modifying core business logic.

### Provider Implementations

**Supported Providers:**
1. **OpenAI** - `ChatOpenAI` from langchain-openai
   - Models: GPT-4, GPT-3.5, etc.
   - API Key: `OPENAI_API_KEY`
   - Default Model: `gpt-4-turbo-preview`

2. **Anthropic** - `ChatAnthropic` from langchain-anthropic
   - Models: Claude 3 family
   - API Key: `ANTHROPIC_API_KEY`
   - Default Model: `claude-3-sonnet-20240229`

3. **Google Gemini** - `ChatGoogleGenerativeAI` from langchain-google-genai
   - Models: Gemini Pro, Gemini 2.0 Flash, etc.
   - API Key: `GOOGLE_API_KEY`
   - Default Model: `gemini-2.0-flash`

4. **Ollama** - `ChatOllama` from langchain-community
   - Local models: Llama2, Mistral, etc.
   - Base URL: `OLLAMA_BASE_URL`
   - Default Model: `llama2`

**Common Pattern:**
All providers follow the same structure:
- Constructor validates API keys and model names from settings
- Creates underlying LangChain chat model instance
- Implements `generate()`, `stream()`, `bind_tools()`, `get_model()` methods
- Error handling with logger output
- Async operations throughout

### Configuration Management

Configuration is managed through:

1. **Environment Variables** - Defined in `.env` file
2. **Pydantic Settings** - Type-safe access via `Settings` class
3. **Validation** - Automatic validation on application startup
4. **Provider Selection** - `LLM_PROVIDER` environment variable selects active provider

**Configuration Pattern:**
```python
# In settings.py
class Settings(BaseSettings):
    llm_provider: str = "openai"  # Provider selection

    # Provider-specific settings
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"

    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-sonnet-20240229"
    # ... etc.
```

**Environment Variable Pattern:**
```bash
# .env.example
LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4-turbo-preview
```

### Request/Response Handling

**Message Flow:**
1. Client sends message via WebSocket
2. WebSocket handler validates conversation ownership
3. Creates `HumanMessage` (LangChain BaseMessage type)
4. Passes to LangGraph via `graph.astream_events()`
5. LangGraph executes `call_llm` node
6. Node retrieves LLM provider from config and binds tools
7. Provider's `generate()` or `stream()` method invoked
8. LangChain handles serialization/deserialization
9. Response streamed back via WebSocket as tokens
10. LangGraph automatically checkpoints to MongoDB

**Key Characteristics:**
- All providers work with LangChain `BaseMessage` types (HumanMessage, AIMessage, SystemMessage)
- Streaming uses async generators (`AsyncGenerator[str, None]`)
- Tool calling supported via `bind_tools()` method
- Error handling at multiple layers (provider, graph, WebSocket handler)
- Automatic state persistence via LangGraph checkpointing

## Impact Analysis

### Components Affected by Speech-to-Text Integration

**New Components Needed:**
1. **Transcription Port Interface** - New port in `backend/app/core/ports/` defining speech-to-text contract
2. **Transcription Provider Implementations** - Adapters in `backend/app/adapters/outbound/transcription_providers/` for OpenAI Whisper, Google Speech-to-Text, etc.
3. **Transcription Provider Factory** - Factory pattern for provider selection
4. **Audio Upload Endpoint** - REST endpoint or WebSocket message type for audio file upload
5. **Audio Message Schema** - Pydantic schema for audio message validation

**Existing Components to Modify:**
1. **Settings** (`backend/app/infrastructure/config/settings.py`) - Add transcription provider configuration
2. **Environment Variables** (`.env.example`) - Add transcription API keys and settings
3. **WebSocket Handler** (`backend/app/adapters/inbound/websocket_handler.py`) - Handle audio message type
4. **Message Schemas** (`backend/app/adapters/inbound/message_schemas.py`) - Add audio message schema
5. **Requirements** (`backend/requirements.txt`) - Add speech-to-text SDK dependencies

**Components NOT Affected:**
- LLM provider implementations (unchanged)
- LangGraph nodes and graphs (unchanged)
- Conversation repository (unchanged)
- Core domain models (unchanged)

### Integration Points

**Primary Integration Point:**
The transcription happens BEFORE the message reaches LangGraph. The flow is:

```
Audio Upload → Transcription Service → Text → HumanMessage → LangGraph
```

This is analogous to how file uploads would work - preprocessing before entering the conversation flow.

## LLM Integration Recommendations

### Proposed Interfaces

Create a new port interface following the existing LLM provider pattern:

```python
# backend/app/core/ports/transcription_provider.py

from abc import ABC, abstractmethod
from typing import BinaryIO, Optional

class ITranscriptionProvider(ABC):
    """
    Transcription provider port interface.

    Defines the contract for speech-to-text operations.
    Implementations handle communication with transcription APIs
    (OpenAI Whisper, Google Speech-to-Text, etc.) without the core
    domain knowing about provider-specific details.
    """

    @abstractmethod
    async def transcribe(
        self,
        audio_file: BinaryIO,
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> str:
        """
        Transcribe audio to text.

        Args:
            audio_file: Audio file object (binary stream)
            language: Optional language code (e.g., "en", "es")
            prompt: Optional context for better transcription

        Returns:
            Transcribed text as string

        Raises:
            Exception: If transcription fails
        """
        pass

    @abstractmethod
    async def get_provider_name(self) -> str:
        """
        Get the name of the transcription provider.

        Returns:
            Provider name (e.g., "openai-whisper", "google-speech")
        """
        pass
```

### Proposed Implementations

**1. OpenAI Whisper Provider (Recommended)**

OpenAI Whisper is the recommended provider because:
- Genesis already uses OpenAI for LLM (existing API key can be reused)
- `langchain-openai` package is already installed
- OpenAI SDK supports Whisper API natively
- Simple, reliable, and well-documented
- Good accuracy and language support

```python
# backend/app/adapters/outbound/transcription_providers/openai_whisper_provider.py

from typing import BinaryIO, Optional
from openai import AsyncOpenAI
from app.core.ports.transcription_provider import ITranscriptionProvider
from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

class OpenAIWhisperProvider(ITranscriptionProvider):
    """
    OpenAI Whisper transcription provider implementation.

    Uses OpenAI's Whisper API for speech-to-text transcription.
    """

    def __init__(self):
        """Initialize the OpenAI Whisper provider."""
        if not settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is not configured. "
                "Please set OPENAI_API_KEY in your .env file."
            )

        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.whisper_model  # Default: "whisper-1"
        logger.info(f"Initialized OpenAI Whisper provider with model: {self.model}")

    async def transcribe(
        self,
        audio_file: BinaryIO,
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> str:
        """
        Transcribe audio using OpenAI Whisper.

        Args:
            audio_file: Audio file (MP3, WAV, etc.)
            language: Optional ISO-639-1 language code
            prompt: Optional context for better transcription

        Returns:
            Transcribed text

        Raises:
            Exception: If transcription fails
        """
        try:
            # Prepare transcription request
            kwargs = {"file": audio_file, "model": self.model}

            if language:
                kwargs["language"] = language

            if prompt:
                kwargs["prompt"] = prompt

            # Call Whisper API
            response = await self.client.audio.transcriptions.create(**kwargs)

            logger.info(f"Successfully transcribed audio ({len(response.text)} chars)")
            return response.text

        except Exception as e:
            logger.error(f"OpenAI Whisper transcription failed: {e}")
            raise Exception(f"Failed to transcribe audio: {str(e)}")

    async def get_provider_name(self) -> str:
        """Get the provider name."""
        return "openai-whisper"
```

**2. Google Speech-to-Text Provider (Alternative)**

```python
# backend/app/adapters/outbound/transcription_providers/google_speech_provider.py

from typing import BinaryIO, Optional
from google.cloud import speech_v1
from app.core.ports.transcription_provider import ITranscriptionProvider
from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

class GoogleSpeechProvider(ITranscriptionProvider):
    """
    Google Speech-to-Text provider implementation.

    Uses Google Cloud Speech-to-Text API for transcription.
    """

    def __init__(self):
        """Initialize the Google Speech provider."""
        if not settings.google_api_key:
            raise ValueError(
                "GOOGLE_API_KEY is not configured. "
                "Please set GOOGLE_API_KEY in your .env file."
            )

        self.client = speech_v1.SpeechAsyncClient()
        logger.info("Initialized Google Speech-to-Text provider")

    async def transcribe(
        self,
        audio_file: BinaryIO,
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> str:
        """Transcribe audio using Google Speech-to-Text."""
        try:
            audio_content = audio_file.read()

            audio = speech_v1.RecognitionAudio(content=audio_content)
            config = speech_v1.RecognitionConfig(
                encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
                language_code=language or "en-US",
                enable_automatic_punctuation=True
            )

            response = await self.client.recognize(config=config, audio=audio)

            # Combine all transcripts
            transcript = " ".join(
                result.alternatives[0].transcript
                for result in response.results
            )

            logger.info(f"Successfully transcribed audio ({len(transcript)} chars)")
            return transcript

        except Exception as e:
            logger.error(f"Google Speech transcription failed: {e}")
            raise Exception(f"Failed to transcribe audio: {str(e)}")

    async def get_provider_name(self) -> str:
        """Get the provider name."""
        return "google-speech"
```

**3. Transcription Provider Factory**

```python
# backend/app/adapters/outbound/transcription_providers/transcription_factory.py

from app.core.ports.transcription_provider import ITranscriptionProvider
from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

class TranscriptionProviderFactory:
    """Factory for creating transcription provider instances."""

    @staticmethod
    def create_provider() -> ITranscriptionProvider:
        """
        Create a transcription provider based on configuration.

        Returns:
            ITranscriptionProvider instance

        Raises:
            ValueError: If provider is not supported
        """
        provider_name = settings.transcription_provider.lower()

        logger.info(f"Creating transcription provider: {provider_name}")

        if provider_name == "openai-whisper":
            from app.adapters.outbound.transcription_providers.openai_whisper_provider import OpenAIWhisperProvider
            return OpenAIWhisperProvider()

        elif provider_name == "google-speech":
            from app.adapters.outbound.transcription_providers.google_speech_provider import GoogleSpeechProvider
            return GoogleSpeechProvider()

        else:
            raise ValueError(
                f"Unsupported transcription provider: {provider_name}. "
                f"Supported providers: openai-whisper, google-speech"
            )

def get_transcription_provider() -> ITranscriptionProvider:
    """Convenience function to get transcription provider."""
    return TranscriptionProviderFactory.create_provider()
```

### Configuration Changes

**Settings Updates:**

```python
# backend/app/infrastructure/config/settings.py

class Settings(BaseSettings):
    # ... existing settings ...

    # Transcription Provider Settings
    transcription_provider: str = "openai-whisper"  # openai-whisper, google-speech

    # OpenAI Whisper Settings (reuses OPENAI_API_KEY)
    whisper_model: str = "whisper-1"
    whisper_language: Optional[str] = None  # Auto-detect if None

    # Google Speech Settings (reuses GOOGLE_API_KEY)
    google_speech_model: str = "default"
    google_speech_language: str = "en-US"
```

**Environment Variables:**

```bash
# .env.example

# Transcription Provider Selection
TRANSCRIPTION_PROVIDER=openai-whisper  # openai-whisper, google-speech

# OpenAI Whisper Configuration (reuses OPENAI_API_KEY)
WHISPER_MODEL=whisper-1
WHISPER_LANGUAGE=  # Optional, auto-detect if empty

# Google Speech Configuration (reuses GOOGLE_API_KEY)
GOOGLE_SPEECH_MODEL=default
GOOGLE_SPEECH_LANGUAGE=en-US
```

**Dependencies:**

```txt
# requirements.txt additions

# OpenAI SDK (for Whisper API - direct client, not LangChain wrapper)
openai>=1.0.0

# Google Speech (optional, only if using Google provider)
# google-cloud-speech>=2.0.0
```

### Data Flow

**Audio Message Flow:**

```
1. Frontend records audio
   ↓
2. Audio uploaded via WebSocket or REST endpoint
   - Message type: "audio" or multipart form data
   - File format: MP3, WAV, OGG, etc.
   ↓
3. Backend receives audio file
   ↓
4. WebSocket handler detects audio message type
   ↓
5. Call transcription provider
   - transcription_provider.transcribe(audio_file)
   - Returns transcribed text
   ↓
6. Create HumanMessage with transcribed text
   ↓
7. Pass to LangGraph (existing flow)
   - graph.astream_events({"messages": [HumanMessage(content=text)]})
   ↓
8. LLM processes text message (unchanged)
   ↓
9. Response streamed back to client
   ↓
10. Optional: Store original audio file reference in message metadata
```

**WebSocket Message Schema:**

```python
# backend/app/adapters/inbound/websocket_schemas.py

class ClientAudioMessage(BaseModel):
    """Audio message from client."""
    type: Literal[MessageType.AUDIO] = MessageType.AUDIO
    conversation_id: str
    audio_data: str  # Base64-encoded audio
    audio_format: str  # "mp3", "wav", "ogg", etc.
    language: Optional[str] = None  # Optional language hint

class ServerTranscriptionMessage(BaseModel):
    """Transcription result to client."""
    type: Literal[MessageType.TRANSCRIPTION] = MessageType.TRANSCRIPTION
    transcribed_text: str
    confidence: Optional[float] = None  # If provider supports it
```

**Alternative: REST Endpoint for Audio Upload**

```python
# backend/app/adapters/inbound/message_router.py

from fastapi import UploadFile, File

@router.post("/{conversation_id}/audio")
async def upload_audio_message(
    conversation_id: str,
    current_user: CurrentUser,
    audio_file: UploadFile = File(...),
    language: Optional[str] = None
):
    """
    Upload audio message for transcription.

    Returns transcribed text that can be sent via WebSocket.
    """
    # Validate conversation ownership
    conversation = await conversation_repository.get_by_id(conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Transcribe audio
    transcription_provider = get_transcription_provider()
    transcribed_text = await transcription_provider.transcribe(
        audio_file.file,
        language=language
    )

    return {"transcribed_text": transcribed_text}
```

## Implementation Guidance

### Step-by-Step Approach

**Phase 1: Backend Transcription Infrastructure**

1. Create transcription port interface
   - File: `backend/app/core/ports/transcription_provider.py`
   - Define `ITranscriptionProvider` abstract class

2. Implement OpenAI Whisper provider
   - File: `backend/app/adapters/outbound/transcription_providers/openai_whisper_provider.py`
   - Use OpenAI SDK's async client
   - Implement `transcribe()` and `get_provider_name()` methods

3. Create transcription provider factory
   - File: `backend/app/adapters/outbound/transcription_providers/transcription_factory.py`
   - Follow same pattern as `LLMProviderFactory`

4. Update settings and configuration
   - Add transcription settings to `Settings` class
   - Update `.env.example` with transcription variables
   - Add `openai>=1.0.0` to `requirements.txt`

5. Write unit tests
   - File: `backend/tests/unit/test_transcription_providers.py`
   - Test factory, provider initialization, error handling
   - Mock OpenAI API calls

**Phase 2: API Endpoint for Audio Upload**

6. Create audio message schemas
   - File: `backend/app/adapters/inbound/message_schemas.py`
   - Define `AudioMessageRequest` and `TranscriptionResponse`

7. Add REST endpoint for audio upload
   - File: `backend/app/adapters/inbound/message_router.py`
   - Endpoint: `POST /api/conversations/{id}/transcribe`
   - Accept audio file, return transcribed text

8. Test audio upload endpoint
   - File: `backend/tests/integration/test_audio_upload.py`
   - Test with mock audio files

**Phase 3: WebSocket Integration (Optional)**

9. Extend WebSocket handler for audio messages
   - File: `backend/app/adapters/inbound/websocket_handler.py`
   - Add handling for audio message type
   - Transcribe before creating HumanMessage

10. Update WebSocket schemas
    - File: `backend/app/adapters/inbound/websocket_schemas.py`
    - Add `ClientAudioMessage` and `ServerTranscriptionMessage`

**Phase 4: Frontend Integration**

11. Add audio recording component
    - Use Web Audio API or MediaRecorder API
    - Record audio from microphone

12. Implement audio upload to backend
    - Send audio via REST endpoint or WebSocket
    - Display transcribed text before sending

13. Add UI for audio messages
    - Microphone button in chat input
    - Recording indicator
    - Transcription preview

### Best Practices

**Error Handling:**
- Validate audio file format and size before transcription
- Handle API rate limits gracefully
- Provide user-friendly error messages
- Log all transcription attempts and failures

**Security:**
- Validate conversation ownership before transcription
- Limit audio file size (e.g., 25MB max)
- Validate audio file formats (whitelist MP3, WAV, OGG)
- Rate limit transcription requests per user

**Performance:**
- Transcription is async (doesn't block WebSocket)
- Consider caching transcriptions by audio hash
- Monitor transcription latency

**User Experience:**
- Show transcription progress indicator
- Allow users to edit transcribed text before sending
- Optional: Store both audio and transcript

## Risks and Considerations

### Technical Risks

**1. Audio File Size and Upload Time**
- Risk: Large audio files slow down user experience
- Mitigation: Limit file size to 25MB, compress audio on client side, use streaming upload

**2. Transcription Latency**
- Risk: Whisper API can take 2-10 seconds for longer audio
- Mitigation: Show loading state, consider real-time streaming transcription for long recordings

**3. Transcription Accuracy**
- Risk: Poor audio quality or accents may reduce accuracy
- Mitigation: Allow users to edit transcribed text, provide language hint option

**4. API Costs**
- Risk: OpenAI Whisper charges per minute of audio ($0.006/min)
- Mitigation: Monitor usage, set user quotas, consider caching

**5. Concurrent Transcription Requests**
- Risk: Multiple users uploading audio simultaneously
- Mitigation: Use async operations, implement rate limiting, consider queue system

### Integration Risks

**1. Inconsistent Provider Behavior**
- Risk: Different transcription providers return different formats
- Mitigation: Abstract provider differences behind `ITranscriptionProvider` interface

**2. Missing API Keys**
- Risk: Transcription fails if OPENAI_API_KEY not configured
- Mitigation: Validate API key on startup, provide clear error messages

**3. Audio Format Compatibility**
- Risk: Some audio formats may not be supported
- Mitigation: Convert audio to supported format (MP3, WAV) on client or server

### Deployment Considerations

**1. Environment Configuration**
- Ensure `TRANSCRIPTION_PROVIDER` and `WHISPER_MODEL` are set in production
- Reuse existing `OPENAI_API_KEY` if using OpenAI Whisper

**2. File Storage**
- Decision: Store original audio files or only transcripts?
- Recommendation: Start with transcripts only (simpler), add audio storage later if needed

**3. Monitoring**
- Track transcription success/failure rates
- Monitor transcription latency
- Alert on high API costs

## Testing Strategy

### Unit Tests

**Transcription Provider Tests:**
```python
# backend/tests/unit/test_transcription_providers.py

@pytest.mark.unit
class TestTranscriptionProviderFactory:
    """Test transcription provider factory."""

    def test_create_openai_whisper_provider(self, mock_settings):
        """Test creating OpenAI Whisper provider."""
        mock_settings.transcription_provider = "openai-whisper"
        mock_settings.openai_api_key = "test-key"
        provider = TranscriptionProviderFactory.create_provider()
        assert provider.__class__.__name__ == "OpenAIWhisperProvider"

    def test_create_unsupported_provider_raises_error(self, mock_settings):
        """Test creating unsupported provider raises ValueError."""
        mock_settings.transcription_provider = "unsupported"
        with pytest.raises(ValueError):
            TranscriptionProviderFactory.create_provider()

@pytest.mark.unit
class TestOpenAIWhisperProvider:
    """Test OpenAI Whisper provider."""

    @pytest.mark.asyncio
    async def test_transcribe_success(self, mock_openai_client):
        """Test successful transcription."""
        # Mock OpenAI response
        mock_openai_client.audio.transcriptions.create.return_value = \
            MagicMock(text="Hello, this is a test.")

        provider = OpenAIWhisperProvider()
        audio_file = BytesIO(b"fake audio data")
        result = await provider.transcribe(audio_file)

        assert result == "Hello, this is a test."

    @pytest.mark.asyncio
    async def test_transcribe_with_language(self, mock_openai_client):
        """Test transcription with language hint."""
        provider = OpenAIWhisperProvider()
        audio_file = BytesIO(b"fake audio data")
        await provider.transcribe(audio_file, language="es")

        # Verify language passed to API
        call_kwargs = mock_openai_client.audio.transcriptions.create.call_args[1]
        assert call_kwargs["language"] == "es"
```

### Integration Tests

**Audio Upload Endpoint Tests:**
```python
# backend/tests/integration/test_audio_upload.py

@pytest.mark.integration
class TestAudioUploadEndpoint:
    """Test audio upload and transcription endpoint."""

    @pytest.mark.asyncio
    async def test_upload_audio_success(self, client, auth_headers, test_conversation):
        """Test successful audio upload and transcription."""
        # Create mock audio file
        audio_file = create_mock_audio_file()

        response = await client.post(
            f"/api/conversations/{test_conversation.id}/transcribe",
            files={"audio_file": ("test.mp3", audio_file, "audio/mpeg")},
            headers=auth_headers
        )

        assert response.status_code == 200
        assert "transcribed_text" in response.json()

    @pytest.mark.asyncio
    async def test_upload_audio_unauthorized(self, client, test_conversation):
        """Test audio upload without authentication fails."""
        audio_file = create_mock_audio_file()

        response = await client.post(
            f"/api/conversations/{test_conversation.id}/transcribe",
            files={"audio_file": ("test.mp3", audio_file, "audio/mpeg")}
        )

        assert response.status_code == 401
```

### End-to-End Tests

**Full Audio-to-LLM Flow:**
1. Record audio in frontend
2. Upload to backend
3. Transcribe audio
4. Send transcribed text to LLM
5. Receive response
6. Verify message stored in LangGraph checkpoint

### Testing with Mocks

**Mock OpenAI API:**
- Use `pytest-mock` to mock OpenAI client
- Return predefined transcription text
- Test error scenarios (API timeout, invalid audio, etc.)

**Mock Audio Files:**
- Create small test audio files (MP3, WAV)
- Use synthetic audio or silence for tests
- Test various file sizes and formats

## Recommendations Summary

### Recommended Approach

**Primary Recommendation: OpenAI Whisper**

1. **Use OpenAI Whisper as the primary transcription provider**
   - Reuses existing `OPENAI_API_KEY` (no new API key needed)
   - OpenAI SDK already compatible with langchain-openai
   - Simple, reliable, well-documented API
   - Good accuracy and multi-language support

2. **Follow existing LLM provider pattern**
   - Create `ITranscriptionProvider` port interface
   - Implement `OpenAIWhisperProvider` adapter
   - Use factory pattern for provider selection
   - Configuration via Pydantic settings

3. **Start with REST endpoint, add WebSocket later**
   - Phase 1: `POST /api/conversations/{id}/transcribe` endpoint
   - Phase 2: WebSocket audio message support (if needed)
   - Simpler to implement and test

4. **Transcribe BEFORE LangGraph**
   - Transcription is preprocessing, not part of LLM flow
   - HumanMessage contains transcribed text (not audio)
   - LangGraph remains unchanged

5. **Store transcripts only (initially)**
   - Simpler implementation
   - Lower storage costs
   - Add original audio storage later if needed

### Configuration Recommendations

**Minimal Configuration:**
```bash
# .env additions (minimal - reuses OPENAI_API_KEY)
TRANSCRIPTION_PROVIDER=openai-whisper
WHISPER_MODEL=whisper-1
```

**Dependencies:**
```txt
# requirements.txt addition
openai>=1.0.0  # For direct Whisper API access
```

### Architecture Alignment

The transcription integration aligns perfectly with Genesis's hexagonal architecture:

- **Port Interface**: `ITranscriptionProvider` (core domain)
- **Adapters**: Provider implementations (outbound)
- **Factory**: `TranscriptionProviderFactory` (outbound)
- **Configuration**: Pydantic settings (infrastructure)
- **Inbound**: REST endpoint or WebSocket handler (inbound)

This maintains clean separation of concerns and makes it easy to:
- Switch transcription providers
- Test without hitting real APIs
- Add new providers without core changes
- Deploy with different providers per environment
