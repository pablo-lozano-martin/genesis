# Data Flow Analysis - Orbio Onboarding Chatbot

## Request Summary

Analysis of data flow throughout the Orbio onboarding chatbot system, focusing on:
1. How conversation data flows from user input through the system to storage
2. Data extraction and validation pipeline for onboarding information
3. How structured data is generated from natural language conversations
4. Data transformations at each architectural layer
5. Key data flow patterns, boundaries, and design decisions

## Relevant Files & Modules

### Data Entry Points (API Layer)

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_router.py` - WebSocket endpoints for real-time chat streaming (`/ws/chat` and `/ws/onboarding`)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - Core WebSocket message handling and streaming orchestration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py` - WebSocket protocol message schemas (ClientMessage, ServerTokenMessage, etc.)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/transcription_router.py` - Audio upload endpoint for speech-to-text (`/api/transcribe`)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/transcription_schemas.py` - Transcription request/response schemas

### LangGraph Agent & State Management

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/onboarding_graph.py` - Factory for creating onboarding agent with ReAct pattern using `create_react_agent`
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - ConversationState schema extending MessagesState with onboarding fields
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/prompts/onboarding_prompts.py` - System prompt guiding agent behavior and data collection flow

### Agent Tools (Data Collection & Transformation)

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/read_data.py` - Query collected onboarding fields from conversation state
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/write_data.py` - Write and validate onboarding data with Pydantic schema validation
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/export_data.py` - Export onboarding data to JSON with LLM-generated summary
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/rag_search.py` - Semantic search in knowledge base for answering questions

### Domain Models (Core Layer)

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/conversation.py` - Conversation domain model and DTOs (Conversation, ConversationCreate, ConversationResponse)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/document.py` - Document domain models for RAG (Document, DocumentMetadata, RetrievalResult)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/user.py` - User domain model

### Port Interfaces (Abstraction Layer)

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/conversation_repository.py` - IConversationRepository interface
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/vector_store.py` - IVectorStore interface for RAG operations
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/transcription_service.py` - ITranscriptionService interface
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - ILLMProvider interface

### Adapter Implementations (Infrastructure Layer)

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_conversation_repository.py` - MongoDB implementation of conversation persistence
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_models.py` - Beanie ODM document models (UserDocument, ConversationDocument)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/vector_stores/chroma_vector_store.py` - ChromaDB implementation of vector store
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/transcription/openai_whisper_service.py` - OpenAI Whisper transcription service
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/provider_factory.py` - LLM provider factory (OpenAI, Anthropic, Google, Ollama)

### Persistence Infrastructure

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/langgraph_checkpointer.py` - LangGraph checkpoint persistence setup (AsyncMongoDBSaver)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/chromadb_client.py` - ChromaDB client initialization and lifecycle management
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/mongodb.py` - MongoDB connection and Beanie ODM initialization

### Application Bootstrap

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py` - FastAPI application entry point with lifespan management and dependency injection

### Key Functions & Classes

#### State Management
- `ConversationState` in `state.py` - Extends LangGraph MessagesState with onboarding fields (employee_name, employee_id, starter_kit, dietary_restrictions, meeting_scheduled, conversation_summary)
- `_initialize_onboarding_state()` in `onboarding_graph.py` - Pre-model hook ensuring state fields have default values

#### Data Collection Tools
- `read_data(field_names)` in `read_data.py` - Query specific or all onboarding fields from state
- `write_data(field_name, value, state, tool_call_id, comments)` in `write_data.py` - Validate and write data to state using Pydantic schema
- `OnboardingDataSchema` in `write_data.py` - Pydantic validation schema with field validators for starter_kit and meeting_scheduled
- `export_data(state, tool_call_id, confirmation_message)` in `export_data.py` - Validate completeness, generate summary, save to state and JSON file

#### RAG Pipeline
- `rag_search(query)` in `rag_search.py` - Semantic search using vector store
- `ChromaDBVectorStore.retrieve(query, top_k)` in `chroma_vector_store.py` - Vector similarity search with distance-to-score conversion
- `Document`, `DocumentMetadata`, `RetrievalResult` in `document.py` - Domain models for knowledge base

#### WebSocket Streaming
- `handle_websocket_chat()` in `websocket_handler.py` - Main streaming loop using `graph.astream_events()`
- `ConnectionManager` in `websocket_handler.py` - WebSocket connection lifecycle management

#### Persistence Transformations
- `MongoConversationRepository._to_domain()` - MongoDB document → Domain model transformation
- Domain models → Beanie documents (implicit via Beanie ODM)

## Current Data Flow Overview

### Architecture Pattern

The system implements **hexagonal architecture (Ports & Adapters)** with clear separation between:
1. **Core Domain** - Business logic and pure domain models (conversation, document, user)
2. **Ports** - Abstract interfaces defining contracts (IConversationRepository, IVectorStore, ITranscriptionService, ILLMProvider)
3. **Adapters** - Infrastructure implementations (MongoDB, ChromaDB, OpenAI Whisper, various LLM providers)

### Two-Database Pattern

The system uses **two separate MongoDB databases** for distinct concerns:

1. **Application Database** (`mongodb://app_db`)
   - Stores conversation metadata (ownership, titles, timestamps)
   - Contains user accounts and authentication data
   - Provides security boundary for conversation ownership verification
   - Collections: `users`, `conversations`

2. **LangGraph Database** (`mongodb://langgraph_db`)
   - Stores LangGraph checkpoints (full message history and state)
   - Managed entirely by LangGraph's AsyncMongoDBSaver
   - Contains actual message content and onboarding field values
   - Thread-based persistence keyed by conversation_id

This separation creates a **clear boundary**: conversation ownership lives in App DB, while conversation content lives in LangGraph DB.

## Data Flow Stages

### Stage 1: User Input Entry

#### Flow A: Text Input via WebSocket

```
User Browser
  ↓ WebSocket connection with JWT
ClientMessage {type: "message", conversation_id: UUID, content: "Hi, I'm John"}
  ↓ websocket_router.py → websocket_onboarding_endpoint()
  ↓ Authentication via get_user_from_websocket()
User object extracted from JWT
  ↓ websocket_handler.py → handle_websocket_chat()
  ↓ Conversation ownership verification (App DB query)
MongoConversationRepository.get_by_id(conversation_id)
  ↓ Verify conversation.user_id == current_user.id
Authorization boundary enforced
```

**Transformation Point**: Raw WebSocket message → Validated ClientMessage schema → User domain model

**Data Validation**:
- ClientMessage.content must have min_length=1
- conversation_id must exist in App DB
- User must own the conversation

#### Flow B: Audio Input via Speech-to-Text

```
User Browser (MediaRecorder API)
  ↓ POST /api/transcribe with multipart/form-data
UploadFile {audio_file: bytes, language: Optional, conversation_id: Optional}
  ↓ transcription_router.py → transcribe_audio()
  ↓ JWT authentication → CurrentUser dependency
  ↓ Conversation ownership verification (if conversation_id provided)
  ↓ Audio validation (validate_audio_file)
File size check (max 25MB), MIME type validation (webm, wav, mp3, m4a, ogg)
  ↓ OpenAIWhisperService.transcribe()
  ↓ Temporary file creation → OpenAI Whisper API call
TranscriptionResponse {text: str, language: str, duration: float}
  ↓ Returned to frontend
  ↓ Frontend inserts text into chat input
[Continues to Flow A as text input]
```

**Transformation Points**:
1. Binary audio → Temporary file with secure handler
2. Audio file → OpenAI Whisper API request
3. Whisper response → TranscriptionResponse schema
4. Transcribed text → User message content

**Data Validation**:
- Audio file size limit: 25MB
- Supported MIME types: webm, wav, mp3, m4a, ogg
- Conversation ownership check (if conversation_id provided)

### Stage 2: LangGraph Agent Processing

#### ReAct Loop Initialization

```
handle_websocket_chat() prepares input:
  ↓ Create HumanMessage from ClientMessage.content
HumanMessage(content="Hi, I'm John")
  ↓ Prepare input_data dict
{
  "messages": [HumanMessage],
  "conversation_id": UUID,
  "user_id": UUID
}
  ↓ Create RunnableConfig for checkpointing
RunnableConfig(configurable={"thread_id": conversation_id, "user_id": user_id})
  ↓ graph.astream_events(input_data, config, version="v2")
LangGraph ReAct agent starts execution
```

**Key Design Decision**: The onboarding graph uses `create_react_agent` (LangGraph prebuilt) rather than custom nodes. This simplifies implementation and provides:
- Automatic ReAct loop (Reasoning → Acting → Observation → Repeat)
- Built-in system prompt injection via `prompt` parameter
- Native streaming support via `astream_events()`
- Automatic checkpoint persistence after each step

#### State Initialization Hook

```
graph.astream_events() begins
  ↓ Before each LLM call
_initialize_onboarding_state(state) hook
  ↓ Ensures all onboarding fields exist in state
{
  employee_name: None,
  employee_id: None,
  starter_kit: None,
  dietary_restrictions: None,
  meeting_scheduled: None,
  conversation_summary: None
}
  ↓ Returns update dict if fields missing
State updated with defaults
```

**Purpose**: LangGraph's `create_react_agent` requires custom state fields to be initialized before tools can access them. This hook prevents KeyError exceptions when tools query state.

#### Agent Reasoning & Tool Selection

```
LLM receives:
  ↓ System prompt (ONBOARDING_SYSTEM_PROMPT)
  ↓ Conversation history (from checkpoint)
  ↓ Current HumanMessage
  ↓ Available tools: [read_data, write_data, rag_search, export_data]
  ↓ LLM reasoning (internal to model)
Agent decides: "User introduced themselves as John. I should write employee_name."
  ↓ LLM returns tool call
{
  "name": "write_data",
  "args": {
    "field_name": "employee_name",
    "value": "John"
  }
}
  ↓ LangGraph dispatches to tool
```

**Transformation Point**: Natural language input → Structured tool call with typed arguments

**Critical Pattern**: The agent uses **proactive data collection** guided by system prompt. The prompt instructs:
1. Guide conversation naturally (don't feel like a form)
2. Use `read_data` to check what's been collected
3. Use `write_data` to save each field after extraction
4. Use `rag_search` to answer user questions
5. Use `export_data` to finalize (only after required fields collected)

### Stage 3: Tool Execution & Data Validation

#### Tool: write_data (Primary Data Collection)

```
write_data(field_name="employee_name", value="John", state={...}, tool_call_id="xyz")
  ↓ Validate field_name exists in valid_fields list
["employee_name", "employee_id", "starter_kit", "dietary_restrictions", "meeting_scheduled", "conversation_summary"]
  ↓ Build validation_data dict
{field_name: value} → {"employee_name": "John"}
  ↓ Pydantic validation
OnboardingDataSchema(**validation_data)
  ↓ Field-specific validators
- employee_name: min_length=1, max_length=255
- employee_id: min_length=1, max_length=50
- starter_kit: must be in ["mouse", "keyboard", "backpack"] (case-insensitive)
- dietary_restrictions: max_length=500
- meeting_scheduled: must be boolean
- conversation_summary: no restrictions
  ↓ Validation success
validated_value = "John"
  ↓ Return Command to update state
Command(update={
  "employee_name": "John",
  "messages": [ToolMessage(content="Successfully recorded employee_name: John")]
})
```

**Transformation Points**:
1. Raw agent-provided value → Pydantic-validated value
2. Validation result → Command object for state update
3. State update → Automatic checkpoint persistence (handled by LangGraph)

**Validation Error Handling**:
```
If validation fails (e.g., starter_kit="laptop"):
  ↓ Pydantic raises ValidationError
  ↓ write_data catches exception
  ↓ Return Command with error ToolMessage
ToolMessage(content="Validation error for starter_kit: Invalid starter_kit value 'laptop'. Must be one of: mouse, keyboard, backpack")
  ↓ Agent receives error in next reasoning step
  ↓ Agent adapts: "I see the validation failed. Let me ask for a valid option."
```

**Critical Design**: Validation errors return as **ToolMessage** to the agent, allowing it to self-correct by asking clarifying questions or re-extracting data.

#### Tool: read_data (State Inspection)

```
read_data(state={...}, field_names=["employee_name", "employee_id"])
  ↓ Validate requested fields exist
  ↓ Extract values from state
  ↓ Format as human-readable string
"Current onboarding data:
- employee_name: John
- employee_id: (not collected yet)"
  ↓ Return to agent as string
```

**Purpose**: Allows agent to check progress without exposing full state. Agent uses this to:
- Verify what's been collected before asking next question
- Confirm data before calling export_data
- Avoid asking for data already collected

#### Tool: rag_search (Knowledge Base Query)

```
rag_search(query="What starter kit options are available?")
  ↓ Access vector_store from app.state.vector_store
ChromaDBVectorStore instance
  ↓ Call retrieve() method
vector_store.retrieve(query, top_k=settings.retrieval_top_k)
  ↓ ChromaDB semantic search
collection.query(query_texts=[query], n_results=top_k)
  ↓ Results with cosine distances
{
  "ids": [["doc_001", "doc_002"]],
  "documents": [["content1", "content2"]],
  "metadatas": [[{...}, {...}]],
  "distances": [[0.15, 0.23]]
}
  ↓ Transform to domain models
For each result:
  - Create DocumentMetadata from metadata dict
  - Create Document with id, content, metadata
  - Convert distance to similarity_score = 1.0 - (distance / 2.0)
  - Create RetrievalResult(document, similarity_score)
  ↓ Format for agent consumption
"Knowledge Base Search Results:

[Result 1] (Relevance: 92.5%)
Source: starter_kit_options.md
Content: We offer three starter kit options: mouse, keyboard, or backpack..."
  ↓ Return to agent as string
```

**Transformation Points**:
1. Natural language query → Vector embedding (automatic in ChromaDB)
2. Vector search → Cosine distance scores
3. Cosine distances → Similarity percentages (0-100%)
4. ChromaDB results → Domain models (Document, RetrievalResult)
5. Domain models → Formatted string for LLM

**Data Flow Note**: Vector embeddings are generated automatically by ChromaDB's default embedding model. Documents are pre-ingested during application startup from `/backend/knowledge_base/` markdown files.

#### Tool: export_data (Finalization & Summary Generation)

```
export_data(state={...}, tool_call_id="xyz", confirmation_message=None)
  ↓ Extract required fields from state
required_fields = {
  "employee_name": state.get("employee_name"),
  "employee_id": state.get("employee_id"),
  "starter_kit": state.get("starter_kit")
}
  ↓ Check completeness
missing_required = [k for k, v in required_fields.items() if v is None]
  ↓ If missing fields exist
Return error ToolMessage
  ↓ If all required fields present
  ↓ Generate LLM-powered summary
llm_provider = get_llm_provider()
summary_prompt = "Summarize this onboarding conversation in 2-3 concise bullet points.

Employee Information:
- Name: John Smith
- ID: EMP12345
- Starter Kit: keyboard
- Dietary: vegetarian
- Meeting: True"
  ↓ LLM generates summary
summary_messages = [HumanMessage(content=summary_prompt)]
summary_response = await llm_provider.generate(summary_messages)
summary_text = summary_response.content
  ↓ Export to JSON file (Docker volume)
export_dir = Path("/app/onboarding_data")
filepath = export_dir / f"{conversation_id}.json"
export_data_dict = {
  "conversation_id": UUID,
  "user_id": UUID,
  "employee_name": "John Smith",
  "employee_id": "EMP12345",
  "starter_kit": "keyboard",
  "dietary_restrictions": "vegetarian",
  "meeting_scheduled": True,
  "conversation_summary": "- New employee John Smith onboarded...",
  "exported_at": "2025-10-30T12:34:56.789012"
}
  ↓ Write JSON file
json.dump(export_data_dict, file, indent=2)
  ↓ Update state with summary
Command(update={
  "conversation_summary": summary_text,
  "messages": [ToolMessage(content="Onboarding data exported successfully...")]
})
```

**Transformation Points**:
1. State fields → Structured data dict
2. Structured data → Natural language summary (via LLM)
3. Data + summary → JSON file (persistent export)
4. Summary → State update (for future reference)

**Critical Pattern**: The summary is generated **inside the tool** rather than by the main agent. This ensures:
- Summary generation happens atomically with export
- Agent doesn't need separate tool call for summarization
- Summary is persisted both to state (checkpoint) and JSON file

### Stage 4: State Persistence (Automatic Checkpointing)

```
After each tool execution:
  ↓ Tool returns Command with state updates
Command(update={field_name: value, "messages": [ToolMessage]})
  ↓ LangGraph applies update to ConversationState
state.employee_name = "John"
state.messages.append(ToolMessage(...))
  ↓ AsyncMongoDBSaver.aput() called automatically
Checkpoint saved to LangGraph MongoDB:
{
  "thread_id": conversation_id,
  "checkpoint": {
    "messages": [...all messages...],
    "employee_name": "John",
    "employee_id": None,
    ...
  },
  "metadata": {...},
  "parent_checkpoint_id": previous_checkpoint_id
}
```

**Key Design**: Checkpointing is **fully automatic** with LangGraph's `create_react_agent`. Every state modification is persisted to MongoDB immediately. This provides:
- **Durability**: Conversation survives server restarts
- **History**: Full message lineage with parent pointers
- **Recovery**: Can resume from any checkpoint
- **Isolation**: Each conversation has independent state (keyed by thread_id)

**Checkpoint Storage Schema** (MongoDB):
```javascript
{
  _id: ObjectId("..."),
  thread_id: "conv_12345",  // Maps to conversation_id
  checkpoint_ns: "",
  checkpoint_id: "checkpoint_67890",
  parent_checkpoint_id: "checkpoint_67889",
  type: "checkpoint",
  checkpoint: {
    // Full ConversationState serialized
    messages: [
      {type: "human", content: "Hi, I'm John"},
      {type: "ai", content: "Great to meet you, John!"},
      {type: "tool", name: "write_data", content: "Successfully recorded..."}
    ],
    conversation_id: "conv_12345",
    user_id: "user_789",
    employee_name: "John",
    employee_id: null,
    starter_kit: null,
    // ... other fields
  },
  metadata: {
    source: "update",
    step: 3,
    writes: {/* state updates */}
  },
  created_at: ISODate("2025-10-30T12:34:56Z")
}
```

### Stage 5: Response Streaming to Client

```
graph.astream_events(input_data, config, version="v2")
  ↓ Async generator yielding events
Event stream:
  - on_chat_model_stream (LLM token)
  - on_chat_model_stream (LLM token)
  - on_chat_model_end (complete message with tool_calls)
  - on_tool_start
  - on_tool_end
  - on_chat_model_stream (LLM token after tool result)
  - ...

For each event:
  ↓ handle_websocket_chat() processes event

  If event_type == "on_chat_model_stream":
    ↓ Extract chunk.content
    ↓ Create ServerTokenMessage
    ServerTokenMessage(type="token", content="Great")
    ↓ Send to WebSocket
    await manager.send_message(websocket, token_msg.model_dump())

  If event_type == "on_chat_model_end" (with tool_calls):
    ↓ Cache tool call information
    current_tool_call = output.tool_calls[0]
    {name: "write_data", args: {field_name: "employee_name", value: "John"}}

  If event_type == "on_tool_start":
    ↓ Create ServerToolStartMessage
    ServerToolStartMessage(
      type="tool_start",
      tool_name="write_data",
      tool_input='{"field_name": "employee_name", "value": "John"}',
      source="local"
    )
    ↓ Send to WebSocket

  If event_type == "on_tool_end":
    ↓ Create ServerToolCompleteMessage
    ServerToolCompleteMessage(
      type="tool_complete",
      tool_name="write_data",
      tool_result="Successfully recorded employee_name: John",
      source="local"
    )
    ↓ Send to WebSocket
    current_tool_call = None  # Reset

  ↓ After stream completes
  ↓ Send completion message
  ServerCompleteMessage(
    type="complete",
    message_id="unknown",
    conversation_id=UUID
  )
```

**Transformation Points**:
1. LangGraph events → WebSocket message schemas
2. AI message chunks → ServerTokenMessage (streaming)
3. Tool execution → ServerToolStartMessage + ServerToolCompleteMessage
4. Stream completion → ServerCompleteMessage

**Critical Pattern**: The system streams **both LLM tokens AND tool events** to the frontend. This provides:
- Real-time user feedback during LLM generation
- Visibility into agent reasoning (what tools are being called)
- Transparency for debugging and trust-building

**Data Flow Note**: Message persistence happens via checkpointing (Stage 4), not explicitly in the streaming handler. The handler only orchestrates streaming, not storage.

## Data Transformation Boundaries

### Boundary 1: API → Domain (Inbound Adapters)

**Location**: `/backend/app/adapters/inbound/`

**Transformations**:
1. **WebSocket JSON → Pydantic Schema**
   - Raw JSON string → `ClientMessage.model_validate()`
   - Validates message format and required fields
   - Raises validation error if malformed

2. **Multipart Form Data → Domain Types**
   - `UploadFile` → `bytes` (audio_content)
   - Form fields → Optional[str] (language, conversation_id)

3. **JWT Token → User Domain Model**
   - JWT payload → `User(id, email, username, full_name, is_active)`
   - Handled by `get_user_from_websocket()` and `CurrentUser` dependency

**Validation Rules**:
- ClientMessage.content: non-empty string
- Audio file: max 25MB, specific MIME types
- JWT: valid signature, not expired

**Error Handling**:
- Invalid message format → `ServerErrorMessage(code="INVALID_FORMAT")`
- Invalid audio → `HTTPException(status=400)`
- Invalid JWT → `WebSocketException(code=1008)` or `HTTPException(status=401)`

### Boundary 2: Domain → Infrastructure (Outbound Adapters)

**Location**: `/backend/app/adapters/outbound/`

#### Conversation Persistence

```
Domain Model (Conversation):
{
  id: "conv_123",
  user_id: "user_456",
  title: "Onboarding Chat",
  created_at: datetime,
  updated_at: datetime,
  message_count: 5
}
  ↓ _to_domain() [MongoDB → Domain]
  ↓ create() [Domain → MongoDB]
MongoDB Document (ConversationDocument):
{
  _id: ObjectId("..."),
  user_id: "user_456",
  title: "Onboarding Chat",
  created_at: ISODate(...),
  updated_at: ISODate(...)
}
```

**Transformation Logic**:
- Domain `id` (string) ↔ MongoDB `_id` (ObjectId)
- Domain datetime ↔ MongoDB ISODate
- `message_count` field is optional (deprecated, tracked via checkpoints instead)

**Adapter**: `MongoConversationRepository`
- Implements `IConversationRepository` port
- Uses Beanie ODM for MongoDB operations
- Provides clean separation: domain models never know about MongoDB

#### Vector Store (RAG Pipeline)

```
Knowledge Base Document (Markdown):
# Starter Kit Options

We offer three starter kit options:
1. Mouse - wireless mouse
2. Keyboard - mechanical keyboard
3. Backpack - laptop backpack
  ↓ Document ingestion script
Domain Model (Document):
{
  id: "doc_001",
  content: "# Starter Kit Options\n\nWe offer...",
  metadata: {
    source: "starter_kit_options.md",
    created_at: datetime,
    content_length: 234,
    document_type: "markdown"
  }
}
  ↓ ChromaDBVectorStore.store_documents()
ChromaDB Storage:
{
  id: "doc_001",
  embedding: [0.123, -0.456, ...],  // Auto-generated
  document: "# Starter Kit Options...",
  metadata: {
    source: "starter_kit_options.md",
    created_at: "2025-10-30T12:00:00",
    content_length: 234,
    document_type: "markdown"
  }
}
```

**Query Flow** (Reverse transformation):
```
Query: "What starter kits are available?"
  ↓ ChromaDB embeds query (automatic)
  ↓ Cosine similarity search
  ↓ Returns results with distances
ChromaDB Result:
{
  ids: [["doc_001"]],
  documents: [["# Starter Kit Options..."]],
  metadatas: [[{source: "...", ...}]],
  distances: [[0.15]]
}
  ↓ ChromaDBVectorStore.retrieve()
  ↓ Transform to domain models
Domain Model (RetrievalResult):
{
  document: Document(...),
  similarity_score: 0.925  // 1.0 - (0.15 / 2.0)
}
```

**Transformation Logic**:
- Embedding generation: Automatic (ChromaDB default model)
- Distance → Similarity: `1.0 - (distance / 2.0)` for cosine space
- Metadata: ISO string → datetime when retrieving

**Adapter**: `ChromaDBVectorStore`
- Implements `IVectorStore` port
- Hides vector database details from domain
- Automatic embedding generation (no manual embeddings)

#### Transcription Service

```
Audio File (Binary):
<webm audio bytes>
  ↓ secure_temp_file() creates temporary file
Temporary File:
/tmp/tmpXYZ.webm
  ↓ OpenAI Whisper API
API Response:
{
  text: "Hello, my name is John Smith",
  language: "en",
  duration: 2.3,
  segments: [...]
}
  ↓ OpenAIWhisperService.transcribe()
Domain Response (dict):
{
  text: "Hello, my name is John Smith",
  language: "en",
  duration: 2.3
}
  ↓ FastAPI response model
TranscriptionResponse:
{
  text: "Hello, my name is John Smith",
  language: "en",
  duration: 2.3
}
```

**Transformation Logic**:
- Binary audio → Temporary file (secure handler auto-deletes)
- Whisper verbose_json → Simplified dict (only text, language, duration)
- Domain dict → Pydantic response model

**Adapter**: `OpenAIWhisperService`
- Implements `ITranscriptionService` port
- Could be swapped for other providers (Google, Azure)
- Handles temporary file lifecycle

### Boundary 3: Agent State → Persistence (LangGraph Checkpointing)

**Location**: Automatic boundary managed by LangGraph

```
ConversationState (Python object):
{
  messages: [HumanMessage(...), AIMessage(...), ToolMessage(...)],
  conversation_id: "conv_123",
  user_id: "user_456",
  employee_name: "John Smith",
  employee_id: "EMP12345",
  starter_kit: "keyboard",
  dietary_restrictions: "vegetarian",
  meeting_scheduled: True,
  conversation_summary: None,
  remaining_steps: 10
}
  ↓ AsyncMongoDBSaver serialization (automatic)
MongoDB Checkpoint Document:
{
  thread_id: "conv_123",
  checkpoint_id: "...",
  checkpoint: {
    v: 1,
    ts: "2025-10-30T12:34:56",
    id: "...",
    channel_values: {
      messages: [
        {lc: 1, type: "constructor", id: ["langchain", "schema", "HumanMessage"], kwargs: {...}},
        // ... serialized LangChain messages
      ],
      conversation_id: "conv_123",
      user_id: "user_456",
      employee_name: "John Smith",
      employee_id: "EMP12345",
      starter_kit: "keyboard",
      dietary_restrictions: "vegetarian",
      meeting_scheduled: true,
      conversation_summary: null,
      remaining_steps: 10
    }
  }
}
```

**Transformation Logic**:
- LangChain messages → Serialized LangChain format (preserves message types)
- Python types → JSON-compatible types (datetime → ISO string, etc.)
- State schema → `channel_values` dict
- Checkpoint versioning and parent linking (automatic)

**Critical Design**: This transformation is **fully managed by LangGraph**. Application code never directly serializes/deserializes state. This ensures:
- Consistent checkpoint format
- Proper message type preservation
- Backward compatibility with LangGraph updates

### Boundary 4: Agent Tools → State (Tool Return Values)

**Location**: Tools in `/backend/app/langgraph/tools/`

**Pattern**: Tools use `Command` objects to specify state updates

```
Tool Execution:
write_data(field_name="employee_name", value="John", ...)
  ↓ Tool logic (validation, processing)
  ↓ Return Command
Command(update={
  "employee_name": "John",
  "messages": [ToolMessage(
    content="Successfully recorded employee_name: John",
    tool_call_id="xyz"
  )]
})
  ↓ LangGraph applies update
state.employee_name = "John"
state.messages.append(ToolMessage(...))
  ↓ Checkpoint saved (automatic)
```

**Transformation Logic**:
- Tool logic → Command dict
- Command dict → State field updates (merge semantics)
- `messages` field: Append (MessagesState reducer)
- Other fields: Replace (default reducer)

**Critical Pattern**: Tools use **declarative state updates** via Command objects rather than mutating state directly. This allows LangGraph to:
- Track what changed in each step
- Checkpoint with metadata about updates
- Potentially rollback or replay

## Data Integrity Concerns

### 1. Conversation Ownership Security

**Concern**: Users must only access conversations they own.

**Mitigation**:
```
WebSocket message received
  ↓ Extract conversation_id from ClientMessage
  ↓ Query App DB: MongoConversationRepository.get_by_id(conversation_id)
  ↓ Verify: conversation.user_id == authenticated_user.id
  ↓ If mismatch: Return ServerErrorMessage(code="ACCESS_DENIED")
  ↓ If match: Proceed with LangGraph invocation
```

**Boundary**: Authorization check happens at **API layer** (websocket_handler.py) before any state access.

**Risk**: LangGraph DB contains message content but has no user ownership data. Security relies on App DB ownership verification.

### 2. Onboarding Data Validation

**Concern**: Invalid data must not be persisted to state.

**Mitigation**:
```
write_data() tool
  ↓ Pydantic validation with OnboardingDataSchema
  ↓ Field validators for constrained fields (starter_kit, meeting_scheduled)
  ↓ If validation fails: Return error ToolMessage to agent
  ↓ If validation succeeds: Return Command to update state
  ↓ State update → Checkpoint (validated data persisted)
```

**Boundary**: Validation happens **inside the tool** before state update.

**Critical Pattern**: Agent can retry with corrected data based on validation error messages.

### 3. Required Fields Completeness

**Concern**: Onboarding export should only succeed with all required fields.

**Mitigation**:
```
export_data() tool
  ↓ Check required_fields: employee_name, employee_id, starter_kit
  ↓ If any is None: Return error ToolMessage
  ↓ If all present: Proceed with summary generation and export
```

**Boundary**: Completeness check happens **inside export_data** before file write.

**Design Note**: System prompt instructs agent to verify completeness via `read_data` before calling `export_data`, providing defense in depth.

### 4. Checkpoint Consistency

**Concern**: State must remain consistent across checkpoint saves.

**Mitigation**:
- LangGraph manages checkpointing atomically
- Each checkpoint links to parent (full history)
- State updates are transactional within LangGraph
- MongoDB write concerns ensure durability

**Risk Scenario**: Server crash between state update and checkpoint save
**Mitigation**: LangGraph's AsyncMongoDBSaver uses MongoDB transactions (if available) or atomic document updates.

### 5. JSON Export Idempotency

**Concern**: Multiple `export_data` calls could create duplicate files.

**Current Behavior**:
- File path: `/app/onboarding_data/{conversation_id}.json`
- Overwrite on each call (latest wins)

**Potential Issue**: If agent calls `export_data` multiple times, only final export persists.

**Recommendation**: Consider:
1. Add timestamp to filename: `{conversation_id}_{timestamp}.json`
2. OR: Track export status in state to prevent duplicate calls
3. OR: Accept overwrite behavior if summaries are idempotent

## Performance Bottlenecks

### 1. LLM Latency

**Bottleneck**: LLM API calls (OpenAI, Anthropic, etc.) have variable latency (500ms - 5s per call).

**Impact**:
- Each tool call requires LLM reasoning → agent reasoning time accumulates
- Complex onboarding flows (5+ tool calls) can take 10-20 seconds

**Mitigation Strategies**:
- ✅ **Streaming**: Token-by-token streaming provides perceived responsiveness
- ✅ **Tool visibility**: ServerToolStartMessage shows progress during tool execution
- 🔄 **Potential**: Use faster models for simple validation (e.g., GPT-4o-mini vs GPT-4)
- 🔄 **Potential**: Cache common RAG results (e.g., "what starter kits are available?")

### 2. Checkpoint Write Latency

**Bottleneck**: MongoDB checkpoint writes after each state update.

**Current Behavior**:
- Every tool execution → State update → MongoDB write
- MongoDB write: ~10-50ms (local), ~50-200ms (remote)

**Impact**: Minimal in streaming mode (writes happen in background while LLM generates next response)

**Mitigation**:
- ✅ **Async writes**: AsyncMongoDBSaver uses async I/O (non-blocking)
- ✅ **Indexed queries**: thread_id indexed for fast lookup
- 🔄 **Potential**: Use MongoDB connection pooling for concurrent conversations

**Measurement**:
```python
# Current checkpoint write time (observable in logs)
logger.info(f"Checkpoint saved for thread {thread_id}")
# Typical: 10-30ms for local MongoDB
```

### 3. Vector Search Latency

**Bottleneck**: ChromaDB semantic search with embedding generation.

**Current Behavior**:
- Query embedding generation: ~100-300ms (default model)
- Vector search: ~10-50ms (6 documents, embedded mode)
- Total: ~150-400ms per RAG query

**Impact**: Noticeable but acceptable for knowledge base queries.

**Mitigation Strategies**:
- ✅ **Small dataset**: 6 documents → fast search
- ✅ **Embedded mode**: No network overhead
- 🔄 **Potential**: Cache frequently asked queries (e.g., benefits, starter kits)
- 🔄 **Potential**: Use faster embedding models (e.g., small sentence transformers)

**Scaling Considerations**:
- Embedded ChromaDB limits: ~10K documents (current: 6)
- For 100K+ documents: Migrate to production vector DB (Pinecone, Weaviate)

### 4. Audio Transcription Latency

**Bottleneck**: OpenAI Whisper API transcription time.

**Current Behavior**:
- Audio upload: ~100-500ms (depends on size)
- Whisper transcription: ~1-3 seconds per 10 seconds of audio
- Total: ~2-5 seconds for typical voice message

**Impact**: Users wait for transcription before message appears in chat.

**Mitigation Strategies**:
- ✅ **Loading indicator**: Frontend shows "Transcribing..." while waiting
- 🔄 **Potential**: Stream partial transcription results (requires different API)
- 🔄 **Potential**: Use faster transcription models (e.g., Whisper small vs large)

**Design Trade-off**: High transcription quality (Whisper large) vs speed (Whisper small).

### 5. WebSocket Connection Overhead

**Bottleneck**: WebSocket connection establishment and authentication.

**Current Behavior**:
- WebSocket handshake: ~50-100ms
- JWT verification: ~10-20ms
- Conversation ownership query: ~10-30ms
- Total connection setup: ~100-200ms

**Impact**: One-time cost per conversation session.

**Mitigation**:
- ✅ **Keep-alive**: WebSocket stays open for entire conversation
- ✅ **Single auth**: JWT verified once on connection (not per message)
- 🔄 **Potential**: Connection pooling for multiple concurrent users

## Implementation Guidance

### Adding New Onboarding Fields

**Scenario**: Add `department` field to onboarding data collection.

**Steps**:

1. **Update State Schema** (`state.py`):
```python
class ConversationState(MessagesState):
    # ... existing fields
    department: Optional[str] = None  # NEW
```

2. **Update State Initialization Hook** (`onboarding_graph.py`):
```python
def _initialize_onboarding_state(state):
    onboarding_fields = {
        # ... existing fields
        "department": None,  # NEW
    }
    # ... rest of logic
```

3. **Update Validation Schema** (`write_data.py`):
```python
class OnboardingDataSchema(BaseModel):
    # ... existing fields
    department: Optional[str] = Field(None, min_length=1, max_length=100)  # NEW

    @field_validator("department")
    @classmethod
    def validate_department(cls, v):
        if v is not None:
            valid_departments = ["engineering", "sales", "marketing", "hr"]
            if v.lower() not in valid_departments:
                raise ValueError(
                    f"Invalid department '{v}'. "
                    f"Must be one of: {', '.join(valid_departments)}"
                )
            return v.lower()
        return v
```

4. **Update System Prompt** (`onboarding_prompts.py`):
```python
ONBOARDING_SYSTEM_PROMPT = """...
**Your responsibilities:**
1. Collect required information: employee_name, employee_id, starter_kit, department
2. Optionally collect: dietary_restrictions, meeting_scheduled
..."""
```

5. **Update Export Data** (`export_data.py`):
```python
required_fields = {
    "employee_name": state.get("employee_name"),
    "employee_id": state.get("employee_id"),
    "starter_kit": state.get("starter_kit"),
    "department": state.get("department"),  # NEW (if required)
}
```

**Data Flow Impact**:
- New field flows through same validation pipeline
- Automatically persisted to checkpoints (no schema migration needed)
- Included in JSON export
- Agent will proactively ask for department based on updated prompt

### Adding New RAG Knowledge Sources

**Scenario**: Add 10 new company policy documents.

**Steps**:

1. **Add Documents** to `/backend/knowledge_base/`:
```
knowledge_base/
  - benefits_and_perks.md
  - starter_kit_options.md
  - new_policy_001.md  # NEW
  - new_policy_002.md  # NEW
  ...
```

2. **Run Ingestion Script**:
```bash
cd backend
python scripts/ingest_documents.py
```

**Script Logic**:
```python
# scripts/ingest_documents.py
from pathlib import Path
from app.core.domain.document import Document, DocumentMetadata
from app.adapters.outbound.vector_stores.vector_store_factory import get_vector_store
from app.infrastructure.database.chromadb_client import ChromaDBClient

await ChromaDBClient.initialize()
vector_store = get_vector_store(ChromaDBClient.client)

kb_dir = Path("knowledge_base")
documents = []

for md_file in kb_dir.glob("*.md"):
    content = md_file.read_text()
    doc = Document(
        id=md_file.stem,
        content=content,
        metadata=DocumentMetadata(
            source=md_file.name,
            created_at=datetime.utcnow(),
            content_length=len(content),
            document_type="markdown"
        )
    )
    documents.append(doc)

await vector_store.store_documents(documents)
```

**Data Flow Impact**:
- New documents automatically embedded by ChromaDB
- Available immediately for `rag_search` tool
- Agent can reference new policies in responses
- No code changes needed (documents loaded on ingestion)

### Implementing Data Export to External System

**Scenario**: Send onboarding data to HR system API after export.

**Recommendation**: Create new tool `submit_to_hr` or extend `export_data`.

**Approach 1**: New Tool (Preferred)

```python
# langgraph/tools/submit_to_hr.py

@tool
async def submit_to_hr(
    state: Annotated[Dict[str, Any], InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Submit onboarding data to HR system API.

    Prerequisites:
    - All required fields must be collected
    - export_data must have been called (conversation_summary exists)
    """

    # Check prerequisites
    summary = state.get("conversation_summary")
    if not summary:
        return Command(update={
            "messages": [ToolMessage(
                content="Error: Must call export_data before submitting to HR system",
                tool_call_id=tool_call_id
            )]
        })

    # Prepare payload
    payload = {
        "employee_name": state.get("employee_name"),
        "employee_id": state.get("employee_id"),
        "starter_kit": state.get("starter_kit"),
        "dietary_restrictions": state.get("dietary_restrictions"),
        "meeting_scheduled": state.get("meeting_scheduled"),
        "summary": summary
    }

    # Call HR API
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://hr-api.orbio.com/onboarding",
                json=payload,
                headers={"Authorization": f"Bearer {settings.hr_api_key}"}
            )
            response.raise_for_status()

        return Command(update={
            "messages": [ToolMessage(
                content=f"Successfully submitted to HR system. Ticket ID: {response.json()['ticket_id']}",
                tool_call_id=tool_call_id
            )]
        })
    except Exception as e:
        logger.error(f"HR submission failed: {e}")
        return Command(update={
            "messages": [ToolMessage(
                content=f"Failed to submit to HR system: {str(e)}",
                tool_call_id=tool_call_id
            )]
        })
```

**Register Tool** in `main.py`:
```python
from app.langgraph.tools.submit_to_hr import submit_to_hr

onboarding_tools = [read_data, write_data, rag_search, export_data, submit_to_hr]
```

**Update System Prompt**:
```python
**Tools available:**
- read_data: Check what fields have been collected
- write_data: Save collected data
- rag_search: Answer questions about Orbio
- export_data: Generate summary and save to JSON
- submit_to_hr: Submit onboarding data to HR system (call after export_data)

**Conversation flow:**
...
7. After export_data completes, call submit_to_hr to notify HR team
8. Confirm submission success to user
```

**Data Flow Impact**:
- New boundary: LangGraph state → External HR API
- Transformation: State fields → HR API JSON payload
- Error handling: HR API errors returned to agent as ToolMessage
- Agent can inform user of submission status

## Risks and Considerations

### 1. Data Leakage Between Conversations

**Risk**: Different users' conversations could access each other's data if thread_id collision occurs.

**Current Mitigation**:
- thread_id = conversation_id (UUID v4, collision probability negligible)
- Conversation ownership verified at API layer before LangGraph invocation
- LangGraph DB has no cross-conversation queries

**Recommendation**: Add integration test verifying isolation:
```python
async def test_conversation_isolation():
    # Create two conversations with different users
    conv1 = await create_conversation(user_id="user_1")
    conv2 = await create_conversation(user_id="user_2")

    # Add data to conv1
    await invoke_graph(conv1.id, "My name is Alice", user_id="user_1")

    # Verify conv2 cannot see conv1 data
    state2 = await get_state(conv2.id)
    assert state2.get("employee_name") is None
```

### 2. Checkpoint Storage Growth

**Risk**: Unlimited conversation history → unbounded MongoDB storage.

**Current Behavior**:
- Each message creates new checkpoint
- Checkpoints link to parents → full history preserved
- No cleanup or pruning

**Scaling Projection**:
- Average conversation: 10-20 messages
- Checkpoint size: ~5-10KB each
- 1000 conversations: ~50-200MB
- 10000 conversations: ~500MB-2GB

**Recommendations**:
1. **Implement retention policy**: Delete checkpoints older than 90 days
2. **Implement pruning**: Keep only last N checkpoints per conversation
3. **Implement archival**: Move old checkpoints to cold storage (S3)

**Example Retention Policy**:
```python
# Scheduled job (daily cron)
async def cleanup_old_checkpoints():
    cutoff_date = datetime.utcnow() - timedelta(days=90)

    # Query LangGraph MongoDB
    db = langgraph_mongodb_client["langgraph_db"]
    result = await db.checkpoints.delete_many({
        "created_at": {"$lt": cutoff_date}
    })

    logger.info(f"Deleted {result.deleted_count} old checkpoints")
```

### 3. Validation Logic Duplication

**Risk**: Validation rules exist in multiple places (frontend, backend, Pydantic, agent prompt).

**Current State**:
- Frontend: Client-side validation (minimal, for UX)
- Backend: Pydantic validation in `write_data` tool
- Agent: Prompt instructions for data collection

**Concern**: Validation rules could drift (e.g., frontend allows 100-char name, backend allows 255).

**Recommendation**:
1. **Single source of truth**: Define validation schema in shared module
2. **Generate constraints**: Use Pydantic schema to generate frontend validation
3. **Explicit validation docs**: Document validation rules in `/doc/general/DATA_VALIDATION.md`

**Example**:
```python
# core/domain/validation_rules.py
VALIDATION_RULES = {
    "employee_name": {
        "type": "string",
        "min_length": 1,
        "max_length": 255,
        "description": "Employee full name"
    },
    "starter_kit": {
        "type": "enum",
        "values": ["mouse", "keyboard", "backpack"],
        "description": "Starter kit choice"
    }
}
```

### 4. Agent Prompt Drift

**Risk**: System prompt changes over time → inconsistent agent behavior across conversations.

**Current Behavior**:
- System prompt injected at graph creation (application startup)
- All conversations use same prompt version
- Prompt changes require application restart

**Concern**: Long-running conversations started before prompt update use old behavior.

**Recommendations**:
1. **Version prompts**: Add version metadata to prompts
2. **Track prompt version**: Store in checkpoint metadata
3. **Prompt migration**: Detect old versions and update on next message

**Example**:
```python
ONBOARDING_SYSTEM_PROMPT_V2 = """...  # Updated prompt
PROMPT_VERSION: 2
"""

def _initialize_onboarding_state(state):
    # Check prompt version in state
    current_version = state.get("prompt_version", 1)

    if current_version < 2:
        # Apply prompt migration logic
        logger.info(f"Migrating prompt from v{current_version} to v2")
        return {"prompt_version": 2}

    return {}
```

### 5. Export File Access Control

**Risk**: Exported JSON files in `/app/onboarding_data/` have no access control.

**Current Behavior**:
- Files written to Docker volume
- No API endpoint to retrieve files
- Only accessible via file system

**Security Gap**: If file system is compromised, all onboarding data is exposed.

**Recommendations**:
1. **Encrypt at rest**: Use volume encryption
2. **Add access control**: Create authenticated API endpoint for file retrieval
3. **Implement audit logging**: Track who accesses which files
4. **Set retention policy**: Auto-delete files after 30 days

**Example Secure Retrieval**:
```python
@router.get("/api/onboarding/export/{conversation_id}")
async def get_onboarding_export(
    conversation_id: str,
    current_user: CurrentUser
):
    # Verify conversation ownership
    conv = await conversation_repo.get_by_id(conversation_id)
    if conv.user_id != current_user.id:
        raise HTTPException(status=403)

    # Read file
    filepath = Path("/app/onboarding_data") / f"{conversation_id}.json"
    if not filepath.exists():
        raise HTTPException(status=404)

    # Audit log
    logger.info(f"User {current_user.id} accessed export {conversation_id}")

    return FileResponse(filepath)
```

## Testing Strategy

### Unit Tests (Data Transformations)

**Test Scope**: Individual transformation functions in isolation.

**Examples**:

1. **Test Pydantic Validation** (`test_onboarding_data_schema.py`):
```python
def test_starter_kit_validation_valid():
    schema = OnboardingDataSchema(starter_kit="keyboard")
    assert schema.starter_kit == "keyboard"

def test_starter_kit_validation_case_insensitive():
    schema = OnboardingDataSchema(starter_kit="KEYBOARD")
    assert schema.starter_kit == "keyboard"  # Lowercased

def test_starter_kit_validation_invalid():
    with pytest.raises(ValidationError) as exc:
        OnboardingDataSchema(starter_kit="laptop")
    assert "Invalid starter_kit value" in str(exc.value)
```

2. **Test Domain Transformations** (`test_mongo_conversation_repository.py`):
```python
async def test_to_domain_transformation():
    doc = ConversationDocument(
        id=ObjectId("507f1f77bcf86cd799439011"),
        user_id="user_123",
        title="Test Conversation"
    )

    repo = MongoConversationRepository()
    domain_model = repo._to_domain(doc)

    assert domain_model.id == "507f1f77bcf86cd799439011"
    assert domain_model.user_id == "user_123"
    assert isinstance(domain_model, Conversation)
```

3. **Test Vector Store Transformations** (`test_chroma_vector_store.py`):
```python
async def test_distance_to_similarity_conversion():
    # Mock ChromaDB result with distance=0.2
    chroma_result = {
        "ids": [["doc_1"]],
        "documents": [["content"]],
        "metadatas": [[{"source": "test.md"}]],
        "distances": [[0.2]]
    }

    # Transform using vector store logic
    similarity_score = 1.0 - (0.2 / 2.0)

    assert similarity_score == 0.9  # 90% similarity
```

### Integration Tests (Data Flow Pipelines)

**Test Scope**: End-to-end data flow through multiple components.

**Examples**:

1. **Test WebSocket Message Flow** (`test_websocket_data_flow.py`):
```python
async def test_message_to_checkpoint_flow():
    # Setup: Create conversation, connect WebSocket
    conversation = await create_test_conversation()
    client = TestClient(app)

    with client.websocket_connect(f"/ws/onboarding?token={token}") as ws:
        # Send message
        ws.send_json({
            "type": "message",
            "conversation_id": conversation.id,
            "content": "My name is John"
        })

        # Receive tokens and completion
        messages = []
        while True:
            msg = ws.receive_json()
            messages.append(msg)
            if msg["type"] == "complete":
                break

        # Verify checkpoint was saved
        checkpointer = app.state.checkpointer
        state = await checkpointer.aget({"configurable": {"thread_id": conversation.id}})

        # Should have human message and AI response in state
        assert len(state["channel_values"]["messages"]) >= 2
        assert any("John" in str(msg) for msg in state["channel_values"]["messages"])
```

2. **Test Onboarding Data Collection Flow** (`test_onboarding_persistence.py`):
```python
async def test_complete_onboarding_flow():
    # Simulate agent collecting all required fields
    conversation = await create_test_conversation()
    graph = app.state.onboarding_graph
    config = {"configurable": {"thread_id": conversation.id}}

    # Simulate conversation with tool calls
    messages = [
        HumanMessage(content="Hi, I'm Alice Smith"),
        # ... agent reasoning and write_data call
        HumanMessage(content="My employee ID is EMP001"),
        # ... agent reasoning and write_data call
        HumanMessage(content="I'll take the keyboard starter kit"),
        # ... agent reasoning and write_data call
        HumanMessage(content="Yes, please schedule a meeting"),
        # ... agent reasoning and export_data call
    ]

    # Invoke graph with all messages
    for msg in messages:
        await graph.ainvoke({"messages": [msg]}, config)

    # Verify final state
    final_state = await graph.aget_state(config)
    assert final_state["values"]["employee_name"] == "Alice Smith"
    assert final_state["values"]["employee_id"] == "EMP001"
    assert final_state["values"]["starter_kit"] == "keyboard"
    assert final_state["values"]["meeting_scheduled"] is True
    assert final_state["values"]["conversation_summary"] is not None

    # Verify JSON export exists
    export_path = Path(f"/app/onboarding_data/{conversation.id}.json")
    assert export_path.exists()

    export_data = json.loads(export_path.read_text())
    assert export_data["employee_name"] == "Alice Smith"
    assert "conversation_summary" in export_data
```

3. **Test RAG Pipeline** (`test_rag_data_flow.py`):
```python
async def test_rag_search_to_agent_flow():
    # Ingest test document
    vector_store = app.state.vector_store
    test_doc = Document(
        id="test_doc_1",
        content="Orbio offers three starter kits: mouse, keyboard, backpack",
        metadata=DocumentMetadata(
            source="test.md",
            created_at=datetime.utcnow(),
            content_length=60,
            document_type="markdown"
        )
    )
    await vector_store.store_documents([test_doc])

    # Invoke rag_search tool
    result = await rag_search.ainvoke({"query": "What starter kits are available?"})

    # Verify result contains document
    assert "mouse" in result
    assert "keyboard" in result
    assert "backpack" in result
    assert "Relevance:" in result  # Should include similarity score
```

### Property-Based Tests (Invariants)

**Test Scope**: Verify system invariants hold across many inputs.

**Examples**:

1. **Test Validation Idempotence**:
```python
from hypothesis import given
from hypothesis.strategies import text

@given(text(min_size=1, max_size=255))
def test_employee_name_validation_idempotent(name):
    # Valid name should validate successfully
    schema1 = OnboardingDataSchema(employee_name=name)

    # Re-validating same name should produce same result
    schema2 = OnboardingDataSchema(employee_name=schema1.employee_name)

    assert schema1.employee_name == schema2.employee_name
```

2. **Test State Merge Semantics**:
```python
@given(text(), text())
def test_state_update_merge(value1, value2):
    # Applying two updates sequentially
    state = {"employee_name": value1}
    update = {"employee_name": value2}

    # Latest update should win (replace semantics)
    merged = {**state, **update}
    assert merged["employee_name"] == value2
```

## Summary

### Key Data Flow Characteristics

1. **Hexagonal Architecture**: Clear separation between domain logic and infrastructure via port interfaces
2. **Two-Database Pattern**: Conversation ownership (App DB) separate from message content (LangGraph DB)
3. **Agent-Driven Collection**: LLM agent proactively collects data via tool calls rather than form-based flow
4. **Validation-First**: Pydantic validation ensures data integrity before state persistence
5. **Checkpoint-Based Persistence**: LangGraph automatically persists full conversation state after each update
6. **Streaming Architecture**: Real-time token and tool event streaming to frontend via WebSocket
7. **RAG Integration**: Vector search provides knowledge base augmentation for agent responses

### Data Transformation Summary

| Boundary | From | To | Mechanism |
|----------|------|----| --------- |
| API → Domain | WebSocket JSON | ClientMessage schema | Pydantic validation |
| API → Domain | Audio bytes | TranscriptionResponse | OpenAI Whisper + schema |
| Domain → MongoDB | Conversation model | ConversationDocument | Beanie ODM + manual transform |
| Domain → ChromaDB | Document model | Vector + metadata | ChromaDB embedding + storage |
| Agent → State | Tool execution | Command update | LangGraph Command pattern |
| State → Checkpoint | ConversationState | MongoDB document | LangGraph serialization |
| State → Export | State fields | JSON file | Manual dict construction |

### Critical Dependencies

- **LangGraph**: Agent orchestration, state management, checkpointing
- **MongoDB**: Dual databases (App DB + LangGraph DB)
- **ChromaDB**: Vector storage for RAG
- **Pydantic**: Data validation and serialization
- **OpenAI**: Whisper transcription + LLM provider (configurable)
- **FastAPI**: WebSocket streaming and REST endpoints

### Performance Characteristics

- **Average latency per message**: 2-5 seconds (LLM dependent)
- **Checkpoint write time**: 10-30ms (async, non-blocking)
- **RAG search time**: 150-400ms (6 documents, embedded mode)
- **Transcription time**: 1-3 seconds per 10 seconds of audio
- **WebSocket connection setup**: 100-200ms (one-time per session)

### Scalability Limits

- **Embedded ChromaDB**: Recommended max ~10K documents (current: 6)
- **Checkpoint growth**: No automatic pruning (manual cleanup needed)
- **Concurrent conversations**: Limited by MongoDB connection pool and LLM rate limits
- **File exports**: No cleanup policy (manual deletion needed)
