# Data Flow Analysis

## Request Summary
Add speech-to-text capability to the chat messaging system. This requires understanding how messages flow from the frontend through the backend to the database, including all transformation and validation steps, so that audio transcription can be properly integrated into the existing data flow.

## Relevant Files & Modules

### API Layer (Inbound Adapters)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket chat handler using LangGraph streaming
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py` - WebSocket message protocol schemas (ClientMessage, ServerTokenMessage, etc.)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_router.py` - WebSocket endpoint registration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_router.py` - REST endpoint for retrieving message history
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_schemas.py` - Message response schemas (MessageResponse, MessageRole)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/conversation_router.py` - Conversation CRUD REST endpoints

### LangGraph Layer (Core Processing)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - ConversationState definition extending MessagesState
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Main chat graph definition
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Streaming chat graph with token-by-token support
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/process_input.py` - Input validation node
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - LLM invocation node
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state_retrieval.py` - Utilities for retrieving messages from checkpoints

### Domain Layer
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/conversation.py` - Conversation domain model
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - LLM provider port interface
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/conversation_repository.py` - Conversation repository port interface

### Infrastructure Layer (Outbound Adapters)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_conversation_repository.py` - MongoDB conversation repository implementation
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_models.py` - Beanie ODM document models (UserDocument, ConversationDocument)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/` - LLM provider implementations (OpenAI, Anthropic, Gemini, Ollama)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/langgraph_checkpointer.py` - LangGraph checkpointer setup for MongoDB
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/mongodb.py` - MongoDB connection management (AppDatabase, LangGraphDatabase)

### Application Bootstrap
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py` - FastAPI application entry point and lifecycle management

### Key Functions & Classes
- `handle_websocket_chat()` in `websocket_handler.py` - Main WebSocket message handling loop
- `ClientMessage` in `websocket_schemas.py` - Client-to-server message schema (contains conversation_id and content)
- `HumanMessage` in LangChain - LangChain message type created from client input
- `ConversationState` in `state.py` - LangGraph state with messages field (List[BaseMessage])
- `process_user_input()` in `process_input.py` - Validates messages exist in state
- `call_llm()` in `call_llm.py` - Invokes LLM provider with message history
- `AsyncMongoDBSaver` - LangGraph checkpointer for automatic message persistence
- `get_conversation_messages()` in `state_retrieval.py` - Retrieves messages from LangGraph checkpoint
- `ConversationDocument` in `mongo_models.py` - MongoDB document for conversation metadata

## Current Data Flow Overview

This system uses a **LangGraph-first architecture** where messages are NOT stored in a traditional message repository or collection. Instead, all messages are automatically persisted by LangGraph's checkpointing system in MongoDB.

### Architecture Dual-Database Pattern
The system uses two separate MongoDB databases:
1. **App Database** (`genesis_db`): Stores conversation metadata (ConversationDocument, UserDocument) using Beanie ODM
2. **LangGraph Database** (`langgraph_db`): Stores message history and conversation state via AsyncMongoDBSaver checkpoints

### Data Entry Points

**Primary Entry Point: WebSocket Connection**
1. Client establishes WebSocket connection to `/ws/chat` endpoint
2. Authentication happens via JWT token in connection headers
3. WebSocket handler (`handle_websocket_chat`) manages the connection lifecycle
4. Client sends messages as JSON with schema: `{"type": "message", "conversation_id": "uuid", "content": "text"}`

**Secondary Entry Point: REST API (Read-Only)**
1. Client retrieves message history via `GET /api/conversations/{conversation_id}/messages`
2. This endpoint reads from LangGraph checkpoints, NOT from a separate message collection
3. Returns paginated list of MessageResponse objects

### Transformation Layers

The system has distinct transformation boundaries that respect clean architecture:

**Layer 1: API Schema → LangChain Message (WebSocket Handler)**
- **Location**: `websocket_handler.py` lines 99-143
- **Input**: `ClientMessage` (Pydantic schema with `type`, `conversation_id`, `content`)
- **Transformation**: Creates `HumanMessage(content=client_message.content)` from LangChain
- **Output**: LangChain `HumanMessage` object
- **Responsibility**: Translates API protocol into LangChain message types

**Layer 2: Message → LangGraph State (WebSocket Handler)**
- **Location**: `websocket_handler.py` lines 139-143
- **Input**: `HumanMessage` object
- **Transformation**: Wraps message in `input_data` dict with metadata
- **Output**: Dict with keys: `{"messages": [HumanMessage], "conversation_id": str, "user_id": str}`
- **Responsibility**: Prepares input for LangGraph graph invocation

**Layer 3: State Validation (Process Input Node)**
- **Location**: `process_input.py` lines 10-34
- **Input**: `ConversationState` with messages field
- **Transformation**: Validates messages exist, no actual transformation
- **Output**: Empty dict (no state update, just validation)
- **Responsibility**: Ensures state integrity before LLM processing

**Layer 4: LLM Processing (Call LLM Node)**
- **Location**: `call_llm.py` lines 17-74
- **Input**: `ConversationState` with `List[BaseMessage]`
- **Transformation**: Invokes LLM provider, gets AIMessage response
- **Output**: Dict with `{"messages": [AIMessage]}`
- **Responsibility**: Generates AI response from conversation history

**Layer 5: Automatic Checkpointing (LangGraph)**
- **Location**: Managed by LangGraph's `AsyncMongoDBSaver` automatically
- **Input**: Updated `ConversationState` after each node
- **Transformation**: Serializes state to MongoDB checkpoint format
- **Output**: Persisted checkpoint in `langgraph_db.checkpoints` collection
- **Responsibility**: Automatic persistence without manual intervention

**Layer 6: Checkpoint → MessageResponse (Message Router)**
- **Location**: `message_router.py` lines 64-98
- **Input**: List of `BaseMessage` from LangGraph checkpoint
- **Transformation**: Filters messages (removes system/tool messages), maps to `MessageResponse`
- **Output**: List of `MessageResponse` (with generated id, role, content, created_at)
- **Responsibility**: Converts internal checkpoint data to public API format

### Persistence Layer

**Conversation Metadata Persistence**
- **Repository**: `MongoConversationRepository`
- **Collection**: `conversations` in App Database
- **Fields**: `id`, `user_id`, `title`, `created_at`, `updated_at`, `message_count` (deprecated)
- **Purpose**: Stores conversation ownership and metadata, NOT messages

**Message History Persistence**
- **Mechanism**: LangGraph `AsyncMongoDBSaver` checkpointer
- **Collection**: `checkpoints` in LangGraph Database (auto-created)
- **Format**: Internal LangGraph checkpoint format (serialized state)
- **Purpose**: Stores complete conversation state including all messages
- **Access**: Via `graph.aget_state(config)` or `graph.astream_events()`

**Key Insight**: There is NO separate Message model or MessageDocument. Messages exist ONLY as part of LangGraph checkpoint state.

### Data Exit Points

**Primary Exit: WebSocket Streaming Response**
1. `graph.astream_events()` streams LLM tokens in real-time
2. WebSocket handler emits `ServerTokenMessage` for each token
3. On completion, emits `ServerCompleteMessage`
4. Messages are automatically saved to checkpoint during streaming

**Secondary Exit: REST API Response**
1. `get_conversation_messages()` retrieves messages from checkpoint
2. `message_router.py` transforms `BaseMessage` → `MessageResponse`
3. Filters out internal messages (tool calls, system messages)
4. Returns paginated JSON array

## Impact Analysis

### Affected Components for Speech-to-Text Integration

**1. WebSocket Schema Layer**
- `ClientMessage` needs extension to support audio data
- New field for audio blob/file reference or base64 encoded audio
- Validation for audio format, size limits

**2. WebSocket Handler Layer**
- New preprocessing step BEFORE `HumanMessage` creation
- Transcription service integration point
- Error handling for transcription failures

**3. Message Metadata**
- Need to track message origin (text vs. transcribed audio)
- Potential storage of audio file reference for playback
- Transcription confidence scores

**4. LangGraph State**
- `ConversationState.messages` already handles text correctly
- No changes needed to state schema (messages remain text-based after transcription)
- Metadata can be stored in `additional_kwargs` on `HumanMessage`

**5. Persistence Layer**
- Audio files may need separate storage (S3, GridFS, etc.)
- Reference to audio stored in message metadata
- LangGraph checkpoint automatically persists metadata

**6. Message Retrieval**
- `MessageResponse` may need audio_url field
- Frontend needs to know if message originated from audio

## Data Flow Recommendations

### Proposed DTOs

**Extended Client Message Schema**
```python
class AudioData(BaseModel):
    """Audio data for speech-to-text transcription."""
    format: str = Field(..., description="Audio format (webm, mp3, wav)")
    data: str = Field(..., description="Base64 encoded audio data")
    duration: Optional[float] = Field(None, description="Audio duration in seconds")

class ClientMessage(BaseModel):
    """Enhanced message schema with audio support."""
    type: MessageType = Field(default=MessageType.MESSAGE)
    conversation_id: str = Field(...)
    content: Optional[str] = Field(None, description="Text content (empty if audio)")
    audio: Optional[AudioData] = Field(None, description="Audio data for transcription")

    @validator('content', 'audio')
    def validate_content_or_audio(cls, v, values):
        # Ensure either content or audio is provided
        if not values.get('content') and not values.get('audio'):
            raise ValueError("Either content or audio must be provided")
        return v
```

**Enhanced Message Response Schema**
```python
class MessageResponse(BaseModel):
    """Enhanced message response with audio metadata."""
    id: str
    conversation_id: str
    role: MessageRole
    content: str  # Transcribed text for audio messages
    created_at: datetime
    metadata: Optional[dict] = None
    is_audio_transcription: bool = Field(default=False)
    audio_url: Optional[str] = Field(None, description="URL to original audio file")
    transcription_confidence: Optional[float] = Field(None)
```

### Proposed Transformations

**New Transformation: Audio → Text (Before HumanMessage Creation)**
- **Location**: New function in `websocket_handler.py` or separate `transcription_service.py`
- **Input**: `AudioData` from `ClientMessage`
- **Process**:
  1. Decode base64 audio data
  2. Call speech-to-text service (OpenAI Whisper, Google Speech-to-Text, etc.)
  3. Get transcription text + confidence score
  4. Handle errors (return error message to client)
- **Output**: Transcribed text string + metadata dict
- **Integration Point**: Lines 137-143 in `websocket_handler.py` (before HumanMessage creation)

**Modified Transformation: ClientMessage → HumanMessage (With Audio Support)**
```python
# Current flow:
human_message = HumanMessage(content=client_message.content)

# Proposed flow:
if client_message.audio:
    # Transcribe audio
    transcription_result = await transcription_service.transcribe(client_message.audio)
    content = transcription_result.text
    metadata = {
        "is_audio_transcription": True,
        "audio_format": client_message.audio.format,
        "audio_duration": client_message.audio.duration,
        "transcription_confidence": transcription_result.confidence,
        "audio_file_id": transcription_result.file_id  # If stored
    }
else:
    content = client_message.content
    metadata = {}

human_message = HumanMessage(content=content, additional_kwargs=metadata)
```

**Modified Transformation: BaseMessage → MessageResponse (With Audio Metadata)**
```python
# Extract audio metadata from additional_kwargs
is_audio = msg.additional_kwargs.get("is_audio_transcription", False)
audio_file_id = msg.additional_kwargs.get("audio_file_id")
audio_url = generate_audio_url(audio_file_id) if audio_file_id else None

MessageResponse(
    id=str(uuid4()),
    conversation_id=conversation_id,
    role=role,
    content=msg.content,
    created_at=datetime.utcnow(),
    metadata=msg.additional_kwargs,
    is_audio_transcription=is_audio,
    audio_url=audio_url,
    transcription_confidence=msg.additional_kwargs.get("transcription_confidence")
)
```

### Repository Changes

**No Changes to ConversationRepository**
- Conversation metadata remains unchanged
- No message_count updates needed (deprecated field)

**New Audio Storage Service (Port + Adapter)**
- **Port**: `IAudioStorageService` in `app/core/ports/audio_storage.py`
- **Methods**:
  - `async def store_audio(audio_data: bytes, format: str, conversation_id: str) -> str` - Returns file_id
  - `async def get_audio_url(file_id: str) -> str` - Returns signed URL
  - `async def delete_audio(file_id: str) -> bool` - Cleanup
- **Adapter Options**:
  - S3 adapter for cloud storage
  - GridFS adapter for MongoDB (if keeping storage simple)
  - Local filesystem adapter for development

**No Changes to LangGraph Checkpointer**
- Metadata in `additional_kwargs` is automatically persisted
- No schema changes needed

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ FRONTEND                                                         │
│ User records audio → Send ClientMessage with AudioData          │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│ WEBSOCKET HANDLER (websocket_handler.py)                        │
│ 1. Validate ClientMessage schema                                │
│ 2. Check conversation ownership                                 │
│ 3. IF audio field present:                                      │
│    ├─→ Call transcription_service.transcribe(audio_data)        │
│    ├─→ Store audio file (optional, get file_id)                 │
│    └─→ Get transcribed text + metadata                          │
│ 4. Create HumanMessage(content=text, additional_kwargs=metadata)│
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│ LANGGRAPH STATE PREPARATION                                     │
│ input_data = {                                                  │
│   "messages": [HumanMessage],                                   │
│   "conversation_id": str,                                       │
│   "user_id": str                                                │
│ }                                                               │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│ LANGGRAPH PROCESSING                                            │
│ graph.astream_events(input_data, config) →                      │
│ 1. process_input node (validate)                                │
│ 2. call_llm node (generate response)                            │
│ 3. Automatic checkpointing (saves HumanMessage + AIMessage)     │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│ PERSISTENCE                                                      │
│ - LangGraph Checkpoint (messages with metadata)                 │
│ - Audio Storage Service (original audio file, optional)         │
│ - Conversation metadata (no changes needed)                     │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│ RESPONSE TO FRONTEND                                            │
│ - WebSocket: Stream AIMessage tokens in real-time               │
│ - REST API: Retrieve messages with audio metadata               │
│   (is_audio_transcription, audio_url, confidence)               │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Guidance

### Step-by-Step Approach

**Phase 1: Create Transcription Service (Infrastructure Layer)**
1. Define `ITranscriptionService` port in `app/core/ports/transcription_service.py`
   - Method: `async def transcribe(audio_data: bytes, format: str) -> TranscriptionResult`
   - TranscriptionResult: `text`, `confidence`, `language` (optional)
2. Implement adapter using OpenAI Whisper or other service
   - Place in `app/adapters/outbound/transcription_services/whisper_transcription.py`
   - Handle audio format conversion if needed
   - Implement retry logic and error handling
3. Register service in `main.py` during application startup
4. Add configuration to settings (API keys, model selection)

**Phase 2: Extend Schemas (API Layer)**
1. Add `AudioData` model to `websocket_schemas.py`
2. Extend `ClientMessage` with optional `audio` field
3. Add validation to ensure either `content` or `audio` is present
4. Extend `MessageResponse` in `message_schemas.py` with audio metadata fields
5. Update OpenAPI documentation examples

**Phase 3: Integrate Transcription (WebSocket Handler)**
1. Modify `handle_websocket_chat()` in `websocket_handler.py`
2. Add transcription logic before `HumanMessage` creation:
   ```python
   if client_message.audio:
       # Decode base64 audio
       audio_bytes = base64.b64decode(client_message.audio.data)

       # Transcribe
       transcription_result = await transcription_service.transcribe(
           audio_bytes,
           client_message.audio.format
       )

       # Prepare message content and metadata
       content = transcription_result.text
       metadata = {
           "is_audio_transcription": True,
           "audio_format": client_message.audio.format,
           "transcription_confidence": transcription_result.confidence,
       }
   else:
       content = client_message.content
       metadata = {}

   human_message = HumanMessage(content=content, additional_kwargs=metadata)
   ```
3. Add error handling for transcription failures
4. Log transcription events

**Phase 4: Update Message Retrieval (Message Router)**
1. Modify `get_messages_endpoint()` in `message_router.py`
2. Extract audio metadata from `additional_kwargs`
3. Include audio flags in `MessageResponse`
4. Filter/transform metadata appropriately for client consumption

**Phase 5: Optional Audio Storage**
1. Only implement if you need to store original audio files for playback
2. Create `IAudioStorageService` port
3. Implement adapter (S3, GridFS, etc.)
4. Store audio in transcription step, get file_id
5. Add file_id to metadata
6. Provide endpoint or signed URL for audio retrieval

**Phase 6: Testing**
1. Unit tests for transcription service
2. Integration tests for WebSocket flow with audio
3. End-to-end tests for complete audio message flow
4. Test error scenarios (invalid audio, transcription failure)
5. Test message retrieval with audio metadata

### Key Design Principles

**Separation of Concerns**
- Transcription service is isolated as a port/adapter
- WebSocket handler orchestrates but doesn't implement transcription
- LangGraph layer remains unchanged (text-based messages)
- Metadata flows through additional_kwargs without schema changes

**Immutability**
- Original audio can be stored immutably
- Transcribed text becomes the canonical message content
- Metadata preserves transcription history

**Fail-Safe Design**
- Transcription failures should not break the flow
- Return error message to client, allow retry
- Log failures for monitoring
- Consider fallback to manual text entry

**Performance Considerations**
- Transcription is synchronous blocking operation (may take 1-5 seconds)
- Consider showing "transcribing..." indicator to user
- Validate audio size limits before transcription (e.g., max 25MB)
- Consider audio compression on client side

## Risks and Considerations

### Data Flow Risks

**1. Transcription Latency**
- **Issue**: Speech-to-text can take 1-5 seconds depending on audio length
- **Impact**: User experiences delay between sending audio and seeing response
- **Mitigation**:
  - Show "transcribing..." status in UI
  - Set reasonable timeout limits
  - Provide feedback on transcription progress

**2. Audio Size and Network Transfer**
- **Issue**: Audio files can be large (1-2 MB per minute of audio)
- **Impact**: Slow WebSocket message transmission, increased bandwidth
- **Mitigation**:
  - Compress audio on client side (use WebM with Opus codec)
  - Set maximum audio duration limits (e.g., 5 minutes)
  - Validate size before accepting upload
  - Consider chunked upload for very long audio

**3. Transcription Error Handling**
- **Issue**: Transcription can fail (poor audio quality, unsupported language, service outage)
- **Impact**: User message is lost if not handled properly
- **Mitigation**:
  - Store original audio before transcription attempt
  - Return detailed error messages to client
  - Allow user to retry or fall back to text input
  - Log failures for monitoring and debugging

**4. Metadata Integrity**
- **Issue**: Audio metadata flows through `additional_kwargs` without schema enforcement
- **Impact**: Potential inconsistency in metadata format
- **Mitigation**:
  - Define explicit metadata schema even if stored in dict
  - Validate metadata structure in transformation layer
  - Document expected metadata fields

**5. State Consistency**
- **Issue**: Audio storage and message creation are separate operations
- **Impact**: Orphaned audio files if message creation fails
- **Mitigation**:
  - Store audio AFTER successful transcription
  - Use transaction-like pattern where possible
  - Implement cleanup job for orphaned audio files
  - Store file_id in checkpoint for traceability

### Performance Bottlenecks

**1. Synchronous Transcription in WebSocket Handler**
- **Bottleneck**: Transcription blocks the WebSocket loop
- **Solution**: Consider async transcription with status updates
- **Trade-off**: Simple synchronous vs. complex async with state management

**2. Base64 Encoding Overhead**
- **Bottleneck**: Base64 increases payload size by ~33%
- **Solution**: Consider binary WebSocket frames instead of JSON
- **Trade-off**: Complexity vs. efficiency

**3. LangGraph Checkpoint Write Performance**
- **Bottleneck**: Each message triggers checkpoint write to MongoDB
- **Solution**: LangGraph handles this efficiently with async writes
- **Note**: No action needed, just be aware of MongoDB connection pool sizing

### Data Integrity Concerns

**1. Audio File Lifecycle Management**
- **Concern**: When to delete stored audio files
- **Recommendation**:
  - Delete when conversation is deleted
  - Or implement retention policy (e.g., 30 days)
  - Reference counting if multiple messages share audio

**2. Transcription Accuracy Tracking**
- **Concern**: Transcription errors may change user intent
- **Recommendation**:
  - Store confidence scores in metadata
  - Log low-confidence transcriptions
  - Consider user correction mechanism
  - Track accuracy metrics

**3. Privacy and Compliance**
- **Concern**: Audio contains PII and may have regulatory requirements
- **Recommendation**:
  - Encrypt audio at rest
  - Use signed URLs with expiration for access
  - Document retention policy
  - Consider geographic restrictions on storage

### Async Processing Pattern Recommendation

**Option 1: Synchronous (Recommended for MVP)**
```python
# Simple, blocking transcription
transcription_result = await transcription_service.transcribe(audio_bytes, format)
human_message = HumanMessage(content=transcription_result.text, additional_kwargs=metadata)
```
**Pros**: Simple, reliable, easy to debug
**Cons**: User waits for transcription (1-5 seconds)

**Option 2: Async with Status Updates (Future Enhancement)**
```python
# Non-blocking transcription with progress updates
transcription_job = await transcription_service.start_transcription(audio_bytes, format)
await websocket.send(ServerTranscriptionStatusMessage(status="processing"))

# Poll or wait for completion
transcription_result = await transcription_job.wait()
await websocket.send(ServerTranscriptionCompleteMessage(text=transcription_result.text))

# Continue with HumanMessage creation
```
**Pros**: Better UX, non-blocking
**Cons**: Complex state management, requires background workers

**Recommendation**: Start with Option 1 for MVP. Upgrade to Option 2 if transcription latency becomes a user pain point.

## Testing Strategy

### Unit Tests

**Transcription Service Tests**
- Test transcription with various audio formats (webm, mp3, wav)
- Test error handling (invalid audio, service timeout)
- Test confidence score calculation
- Mock external transcription API

**Schema Validation Tests**
- Test ClientMessage with audio field
- Test validation (content or audio required)
- Test AudioData format validation
- Test MessageResponse with audio metadata

**Transformation Tests**
- Test audio → text transformation
- Test metadata preservation
- Test HumanMessage creation with additional_kwargs
- Test BaseMessage → MessageResponse with audio metadata

### Integration Tests

**WebSocket Flow Tests**
- Test end-to-end audio message flow
- Test audio upload → transcription → LLM response
- Test error handling (transcription failure)
- Test message retrieval with audio metadata

**Database Integration Tests**
- Test checkpoint persistence with audio metadata
- Test message retrieval from checkpoint
- Test audio storage and retrieval (if implemented)

### End-to-End Tests

**Full User Journey**
1. User records audio in frontend
2. Audio sent via WebSocket
3. Transcription occurs
4. Message appears in chat with audio indicator
5. LLM responds normally
6. Message history retrieval includes audio metadata
7. Optional: Audio playback from stored file

**Error Scenarios**
1. Transcription service unavailable
2. Invalid audio format
3. Audio too large
4. Network interruption during upload
5. Concurrent messages (text + audio)

### Performance Tests

**Latency Tests**
- Measure transcription time for various audio lengths
- Measure end-to-end message roundtrip time
- Compare audio vs text message performance

**Load Tests**
- Multiple concurrent audio transcriptions
- Large audio files (stress test)
- WebSocket connection handling under load

## Summary

The chat message data flow follows a clean LangGraph-first architecture where:

1. **Messages enter** via WebSocket as `ClientMessage` schemas
2. **Transform to** LangChain `HumanMessage` objects with metadata
3. **Process through** LangGraph graph (validation → LLM → tools)
4. **Persist automatically** via LangGraph checkpointer to MongoDB
5. **Exit** as streaming tokens (WebSocket) or MessageResponse (REST)

**For speech-to-text integration**, the cleanest insertion point is in the WebSocket handler BEFORE HumanMessage creation. This allows:
- Audio → text transformation at the API boundary
- Metadata preservation through additional_kwargs
- No changes to LangGraph state schema
- No changes to persistence layer
- Simple extension of existing schemas

**Critical success factors**:
- Isolate transcription service as port/adapter
- Handle errors gracefully (user can retry)
- Store metadata for audio origin tracking
- Consider audio file storage separately from message flow
- Test thoroughly with various audio formats and lengths

The existing data flow is well-structured for this enhancement with minimal invasive changes required.
