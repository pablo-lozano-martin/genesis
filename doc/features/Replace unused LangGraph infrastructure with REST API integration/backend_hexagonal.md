# Backend Hexagonal Architecture Analysis: REST API Integration for LangGraph

## Request Summary

Replace the current unused LangGraph infrastructure with a REST API endpoint that properly integrates LangGraph's conversation flow. The WebSocket implementation (`websocket_handler.py`) currently bypasses the LangGraph graphs and handles message processing directly. The goal is to:

1. Create a new REST endpoint `/api/conversations/{conversation_id}/messages` (POST) for sending messages
2. Integrate the LangGraph conversation graphs (`chat_graph.py`) into the request flow
3. Support streaming responses via HTTP Server-Sent Events (SSE) for real-time token streaming
4. Maintain proper hexagonal architecture principles with clean separation of concerns

---

## Relevant Files & Modules

### Files to Examine

**LangGraph Components:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Main conversation graph orchestration (lines 35-91)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Streaming graph variant (lines 70-120)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - ConversationState TypedDict schema (lines 10-31)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/process_input.py` - Input validation node (lines 11-46)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - LLM invocation node (lines 11-46)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/format_response.py` - Response formatting node (lines 11-44)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/save_history.py` - Message persistence node (lines 12-64)

**Current WebSocket Implementation (to be replaced/refactored):**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - Current chat logic (lines 56-180)
  - Directly handles message streaming without using LangGraph graphs
  - Manual message processing and LLM calls
  - No graph orchestration

**Existing REST Adapters:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_router.py` - Current message endpoints (lines 14-70)
  - Only supports GET for conversation history
  - No POST endpoint for sending messages
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/conversation_router.py` - Conversation management endpoints
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_router.py` - WebSocket router (lines 17-63)

**Core Domain & Ports:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/message.py` - Message model (lines 10-76)
  - `MessageRole` enum (USER, ASSISTANT, SYSTEM)
  - `Message` domain model
  - `MessageCreate` for creation payload
  - `MessageResponse` for API response
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/conversation.py` - Conversation model (lines 9-70)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/message_repository.py` - Message repository port (lines 10-90)
  - `IMessageRepository` interface (get, create, delete operations)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/conversation_repository.py` - Conversation repository port (lines 10-101)
  - `IConversationRepository` interface
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - LLM provider port (lines 10-61)
  - `ILLMProvider` interface with `generate()` and `stream()` methods

**Use Cases:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/use_cases/send_message.py` - SendMessage use case (lines 12-87)
  - Currently bypassed; could be extended or replaced with LangGraph-based version

**Infrastructure & Factories:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_message_repository.py` - Message persistence adapter
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_conversation_repository.py` - Conversation persistence adapter
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/provider_factory.py` - LLM provider factory
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/security/dependencies.py` - Authentication dependencies (lines 19-79)
  - `CurrentUser` dependency for protected routes

**Main Application:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py` - FastAPI app setup (lines 51-95)
  - Router registration

### Key Functions & Classes

**LangGraph Orchestration:**
- `create_chat_graph()` in `chat_graph.py` - Creates the main conversation graph (lines 35-91)
  - Takes `ILLMProvider`, `IMessageRepository`, `IConversationRepository` as parameters
  - Builds state graph with nodes: process_input → call_llm → format_response → save_history
  - Returns compiled graph instance

- `create_streaming_chat_graph()` in `streaming_chat_graph.py` - Creates streaming variant (lines 70-120)
  - Similar flow but optimized for token streaming
  - Returns tuple of (graph, call_llm_stream generator function)

**LangGraph Nodes:**
- `process_user_input()` in `process_input.py` - Validates user input (lines 11-46)
  - Takes `ConversationState`, returns dict with messages or error
  - Creates `Message` object with USER role

- `call_llm()` in `call_llm.py` - Invokes LLM (lines 11-46)
  - Takes `ConversationState` and `ILLMProvider`
  - Returns dict with llm_response or error

- `format_response()` in `format_response.py` - Formats response (lines 11-44)
  - Takes `ConversationState`
  - Creates `Message` object with ASSISTANT role

- `save_to_history()` in `save_history.py` - Persists messages (lines 12-64)
  - Takes `ConversationState`, `IMessageRepository`, `IConversationRepository`
  - Saves messages and updates conversation metadata

**Current WebSocket Handler:**
- `handle_websocket_chat()` in `websocket_handler.py` - Current chat logic (lines 56-180)
  - Directly processes messages without LangGraph
  - Manually calls `llm_provider.stream()`
  - Manually saves messages
  - **Issue**: Bypasses the LangGraph orchestration entirely

**REST Adapters:**
- `get_conversation_messages()` in `message_router.py` - GET endpoint (lines 20-69)
  - Retrieves conversation history
  - Returns `List[MessageResponse]`

**Authentication:**
- `get_current_active_user()` in `dependencies.py` - Current user dependency (lines 56-76)
  - Type alias `CurrentUser` for dependency injection (line 79)

---

## Current Architecture Overview

### Domain Core

**Domain Models:**
- `Message` - Pure domain model representing a conversation message
  - Fields: id, conversation_id, role (MessageRole enum), content, created_at, metadata
  - Value objects: `MessageCreate` (creation payload), `MessageResponse` (API response)

- `Conversation` - Pure domain model representing a chat session
  - Fields: id, user_id, title, created_at, updated_at, message_count
  - Value objects: `ConversationCreate`, `ConversationUpdate`, `ConversationResponse`

**Ports (Interfaces):**

Secondary Ports (Driven):
- `IMessageRepository` - Message data operations (get, create, delete, list by conversation)
- `IConversationRepository` - Conversation data operations (get, create, update, list by user, increment message count)
- `ILLMProvider` - LLM communication (generate, stream, get_model_name)

Primary Ports (Driving):
- HTTP REST routes (inbound adapters)
- WebSocket routes (inbound adapters)

**Use Cases:**
- `SendMessage` - Business logic for sending a message and getting LLM response
  - Currently bypassed by WebSocket handler
  - Could be refactored to use LangGraph graphs

**LangGraph Integration:**
- `ConversationState` - TypedDict schema for graph state
- Graph creation functions: `create_chat_graph()`, `create_streaming_chat_graph()`
- Processing nodes: process_input, call_llm, format_response, save_history
- **Current Status**: Created but not integrated with REST API

### Ports (Interfaces)

**Secondary Ports (Outbound/Driven):**

```
┌─────────────────────────────────────────┐
│ Ports (in app/core/ports/)              │
├─────────────────────────────────────────┤
│ • IMessageRepository                    │
│ • IConversationRepository               │
│ • ILLMProvider                          │
│ • IAuthService                          │
└─────────────────────────────────────────┘
```

**Primary Ports (Inbound/Driving):**

Currently:
1. REST API routes (FastAPI routers) - GET endpoints for reading
2. WebSocket route - OPEN connection for chat (bypasses LangGraph)

Proposed:
1. REST API POST endpoint - Send message with streaming response
2. Keep WebSocket for real-time connections (optional refactor)

### Adapters

**Inbound Adapters (Controllers):**
- `auth_router.py` - Authentication endpoints
- `user_router.py` - User management endpoints
- `conversation_router.py` - Conversation CRUD endpoints
- `message_router.py` - Message history retrieval (READ-ONLY)
- `websocket_router.py` - WebSocket chat connection
- `websocket_handler.py` - WebSocket message processing logic

**Outbound Adapters (Infrastructure):**

Repositories:
- `MongoMessageRepository` - MongoDB message implementation
- `MongoConversationRepository` - MongoDB conversation implementation
- `MongoUserRepository` - MongoDB user implementation

LLM Providers:
- `OpenAIProvider`, `AnthropicProvider`, `GeminiProvider`, `OllamaProvider`
- `provider_factory.py` - Factory for selecting LLM provider based on config

**LangGraph as Infrastructure:**
- Graphs are currently defined but **NOT INSTANTIATED OR USED**
- They exist as code templates without integration points

---

## Current Issues & Architectural Violations

### 1. **WebSocket Handler Bypasses LangGraph** (Lines 56-180 in websocket_handler.py)

The current WebSocket handler directly implements the conversation flow:
- Lines 128-154: Manually calls `llm_provider.stream()` without LangGraph orchestration
- Lines 119-145: Manually creates `Message` objects and saves them
- **Violation**: Direct orchestration instead of delegating to LangGraph graphs
- **Impact**: No separation between HTTP request handling and business logic orchestration

```python
# Current flow (websocket_handler.py, lines 132-145):
async for token in llm_provider.stream(messages):
    full_response.append(token)
    token_msg = ServerTokenMessage(content=token)
    await manager.send_message(websocket, token_msg.model_dump())

response_content = "".join(full_response)
assistant_message = Message(...)
saved_assistant_message = await message_repository.create(assistant_message)
```

This should be orchestrated by LangGraph graph instead.

### 2. **No REST Endpoint for Message Sending**

Current API structure:
- GET `/api/conversations/{conversation_id}/messages` - List messages (READ-ONLY)
- No POST endpoint to send a message

The domain and ports support message sending via `IMessageRepository`, but the REST adapter doesn't expose it.

### 3. **LangGraph Graphs Defined But Unused**

- `create_chat_graph()` and `create_streaming_chat_graph()` are implemented
- No code path instantiates or invokes these graphs
- They remain as unused infrastructure

### 4. **SendMessage Use Case Not Used**

- `SendMessage` use case defined in `core/use_cases/send_message.py` (lines 12-87)
- Implements proper domain logic with dependency injection
- Not used by any adapter (WebSocket bypasses it, REST doesn't exist)

---

## Architectural Recommendations

### 1. Proposed Ports & Adapters Structure

**New Inbound Adapter: REST Message POST Endpoint**

Create a new function in `message_router.py` (or extend it):

```python
# Proposed endpoint structure
POST /api/conversations/{conversation_id}/messages

Request Body:
{
    "content": "What is Python?"
}

Response (with streaming via Server-Sent Events):
event: token
data: "What"

event: token
data: " is"

event: token
data: " Python"

event: complete
data: {"message_id": "...", "conversation_id": "..."}
```

**New Service Layer: LangGraph Orchestrator**

Create a new service to bridge REST adapter and LangGraph:

```
app/core/services/conversation_orchestrator.py
```

This service:
- Takes conversation_id, user_id, message content
- Creates `ConversationState`
- Invokes LangGraph graph
- Yields tokens for streaming response
- Depends only on ports (ILLMProvider, IMessageRepository, IConversationRepository)
- Returns complete message for response

### 2. Dependency Flow (Corrected)

Current flow (BROKEN):
```
REST/WebSocket Adapter
    ↓ (direct calls, no abstraction)
ILLMProvider (Port)
    ↓
OpenAI/Anthropic/etc (Adapter)
```

Proposed flow (CORRECT):
```
REST Adapter (Inbound)
    ↓
ConversationOrchestrator (Service Layer)
    ↓
LangGraph Graph (Business Logic Orchestrator)
    ↓ (delegates to)
    ├─→ ILLMProvider (Port) → LLM Adapter (Outbound)
    ├─→ IMessageRepository (Port) → MongoMessageRepository (Outbound)
    └─→ IConversationRepository (Port) → MongoConversationRepository (Outbound)
```

**Key principle**: All dependencies point INWARD toward domain. Adapters never call other adapters.

### 3. Files to Create

#### A. Service Layer: `backend/app/core/services/conversation_orchestrator.py`

**Purpose**: Bridge between REST adapter and LangGraph

**Responsibilities**:
- Create `ConversationState` from request parameters
- Invoke LangGraph graph with state
- Yield streaming tokens from graph execution
- Handle errors gracefully

**Signature**:
```python
class ConversationOrchestrator:
    def __init__(
        self,
        llm_provider: ILLMProvider,
        message_repository: IMessageRepository,
        conversation_repository: IConversationRepository
    ):
        # Dependency injection of ports

    async def stream_message(
        self,
        conversation_id: str,
        user_id: str,
        content: str
    ) -> AsyncGenerator[dict, None]:
        # Create ConversationState
        # Invoke LangGraph graph
        # Yield tokens
        # Yield completion event
```

**Why a service?**
- Service layer sits between adapters and domain use cases
- Responsible for orchestration (which graph to use, how to invoke it)
- Not part of domain core (too infrastructure-aware)
- Not part of adapter (too business logic-aware)
- Follows Hexagonal Architecture principle of separation

#### B. REST Endpoint: `backend/app/adapters/inbound/message_router.py` (NEW POST METHOD)

**Purpose**: HTTP handler for sending messages with streaming response

**Signature**:
```python
@router.post("/{conversation_id}/messages", status_code=200)
async def send_message(
    conversation_id: str,
    current_user: CurrentUser,
    request: SendMessageRequest,
    background_tasks: BackgroundTasks
) -> StreamingResponse:
    # Validate user owns conversation
    # Create orchestrator with injected dependencies
    # Return streaming response (Server-Sent Events)
```

**Request Model**:
```python
class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
```

**Response**: Server-Sent Events stream with message tokens

#### C. Streaming Response Adapter: `backend/app/adapters/inbound/streaming.py`

**Purpose**: Utility for handling Server-Sent Events streaming

**Responsibilities**:
- Format tokens for SSE protocol
- Handle streaming errors
- Send completion event with metadata

### 4. Integration Points

**Where to inject dependencies:**

In `message_router.py`:
```python
@router.post("/{conversation_id}/messages")
async def send_message(...):
    # Instantiate adapters
    llm_provider = get_llm_provider()
    message_repository = MongoMessageRepository()
    conversation_repository = MongoConversationRepository()

    # Create service
    orchestrator = ConversationOrchestrator(
        llm_provider,
        message_repository,
        conversation_repository
    )

    # Use orchestrator to stream response
    async def event_generator():
        async for event in orchestrator.stream_message(...):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Why this structure?**
- Adapters instantiate concrete implementations
- Service receives port interfaces (dependency inversion)
- Service doesn't know about HTTP/WebSocket details
- Easy to test service in isolation with mock ports

### 5. LangGraph Graph Integration

**Which graph to use?**

For REST endpoint with SSE streaming:
- Use `create_streaming_chat_graph()` from `streaming_chat_graph.py`
- But modify it to:
  - Support streaming token yields directly
  - Not require WebSocket-specific message types
  - Return structured completion event

**Current issue with streaming_chat_graph.py (lines 70-120)**:
- Returns tuple of (graph, call_llm_stream generator)
- `call_llm_stream` is never actually called
- Graph nodes expect `ConversationState` with specific fields

**Proposed changes to streaming_chat_graph.py**:
1. Make `call_llm_stream` a proper graph node (not separate generator)
2. Or create a new graph variant: `create_http_streaming_graph()` that:
   - Explicitly handles streaming tokens
   - Returns completion event with message metadata
   - Compatible with REST API Server-Sent Events protocol

### 6. State Management Between Layers

**ConversationState fields** (from `state.py`, lines 10-31):
```python
class ConversationState(TypedDict):
    messages: Annotated[list[Message], add_messages]
    conversation_id: str
    user_id: str
    current_input: Optional[str]
    llm_response: Optional[str]
    error: Optional[str]
```

**Mapping from REST request to ConversationState**:
```python
# REST Request
SendMessageRequest:
    content: str

# ConversationState (created by orchestrator)
ConversationState:
    conversation_id: from URL parameter
    user_id: from current_user dependency
    current_input: from request.content
    messages: fetched from message_repository by conversation_id
    llm_response: None (filled by graph)
    error: None (filled by graph if error occurs)
```

### 7. Response Format for Streaming

**Server-Sent Events (SSE) Protocol**:

```
event: token
data: {"content": "What"}

event: token
data: {"content": " is"}

event: complete
data: {
    "message_id": "507f1f77bcf86cd799439015",
    "conversation_id": "507f1f77bcf86cd799439012",
    "role": "assistant",
    "content": "What is Python?..."
}

event: error
data: {"message": "LLM error", "code": "LLM_ERROR"}
```

**Why SSE over WebSocket?**
- RESTful, stateless (better for scalability)
- Built on HTTP (standard web protocol)
- Browser native support
- Works through proxies/load balancers
- Can use same authentication (JWT in Authorization header)

---

## Implementation Guidance

### Phase 1: Create Service Layer (FOUNDATION)

**Step 1**: Create `backend/app/core/services/` directory

**Step 2**: Create `backend/app/core/services/conversation_orchestrator.py`
- Implement `ConversationOrchestrator` class
- Depends on: `ILLMProvider`, `IMessageRepository`, `IConversationRepository`
- Method: `async def stream_message(conversation_id, user_id, content) -> AsyncGenerator[dict, None]`
- Logic:
  1. Fetch conversation (validate user owns it)
  2. Fetch conversation message history
  3. Create `ConversationState`
  4. Invoke LangGraph graph
  5. Stream tokens from graph execution
  6. Return completion event

**Step 3**: Update `LangGraph streaming_chat_graph.py`
- Current issue: `call_llm_stream` generator not integrated with graph
- Decision point: Modify existing or create new graph variant?
  - Option A: Modify `create_streaming_chat_graph()` to return proper streaming interface
  - Option B: Create new `create_http_streaming_graph()` specifically for REST API
  - **Recommendation**: Option A (single source of truth, less code duplication)

### Phase 2: Create REST Endpoint (INTEGRATION)

**Step 4**: Extend `backend/app/adapters/inbound/message_router.py`
- Add `SendMessageRequest` Pydantic model
- Add POST endpoint handler
- Import and use `ConversationOrchestrator`
- Return `StreamingResponse` with SSE events

**Step 5**: Create streaming utility `backend/app/adapters/inbound/streaming.py`
- Helper functions for:
  - Formatting token events
  - Formatting completion event
  - Formatting error events
  - Converting async generator to SSE format

### Phase 3: Refactor WebSocket (OPTIONAL)

**Step 6**: Optionally refactor WebSocket to use orchestrator
- Replace direct LLM calls in `websocket_handler.py`
- Use `ConversationOrchestrator` for message processing
- Benefit: Consistent logic between REST and WebSocket
- Trade-off: WebSocket needs different event format (JSON message types)

### Phase 4: Testing

**Step 7**: Write tests for `ConversationOrchestrator`
- Mock `ILLMProvider`, `IMessageRepository`, `IConversationRepository`
- Test token streaming
- Test error handling
- Test conversation history retrieval

**Step 8**: Write integration tests for REST endpoint
- Test full flow: request → orchestrator → graph → streaming response
- Test authentication/authorization
- Test error scenarios

---

## Risks and Considerations

### 1. **Graph State Management** (HIGH RISK)

**Issue**: `ConversationState` expects specific field structure
- `messages`: List of `Message` domain objects
- `current_input`: User message content
- LangGraph `add_messages` reducer automatically merges messages

**Risk**: Mismatch between:
- REST request format (JSON with `content` string)
- `ConversationState` format (Message domain objects)
- LangGraph node expectations

**Mitigation**:
- `ConversationOrchestrator.stream_message()` responsible for mapping
- Create `ConversationState` with correct structure before invoking graph
- Ensure `Message` objects loaded from DB are properly typed

**Example**:
```python
# Correct state creation
state = ConversationState(
    conversation_id=conversation_id,
    user_id=user_id,
    current_input=content,  # String from REST request
    messages=messages_from_db,  # List[Message] from repository
    llm_response=None,
    error=None
)
```

### 2. **Streaming Token Aggregation** (MEDIUM RISK)

**Issue**: LangGraph processes messages through nodes, but streaming happens in `call_llm_stream`
- Tokens are streamed during LLM invocation (call_llm node)
- But graph structure expects node to return complete state update
- Current `streaming_chat_graph.py` doesn't properly handle token yields during graph execution

**Current code (streaming_chat_graph.py, lines 34-68)**:
```python
async def call_llm_stream(state, llm_provider) -> AsyncGenerator[str, None]:
    # This is NOT used as a graph node
    # It's a separate generator function
    async for token in llm_provider.stream(messages):
        full_response.append(token)
        yield token
```

**Problem**: Generator function never invoked; graph takes different path

**Mitigation**:
- Either make `call_llm_stream` a proper graph node that yields to parent
- Or redesign streaming to collect full response then yield tokens afterwards
- OR: Stream tokens outside graph execution, just get final response from graph

**Recommended approach**:
```python
# Option: Stream tokens during graph execution without being graph node
async def stream_message(self, ...):
    state = ConversationState(...)

    # Graph execution returns complete state
    final_state = graph.invoke(state)

    # Stream tokens from final LLM response
    for token in final_state["llm_response"]:  # If response was streamed
        yield {"type": "token", "content": token}

    yield {"type": "complete", "message_id": final_message.id}
```

This avoids complex streaming inside graph execution.

### 3. **Dependency Injection Consistency** (MEDIUM RISK)

**Current WebSocket** (websocket_router.py, lines 45-47):
```python
llm_provider = get_llm_provider()
message_repository = MongoMessageRepository()
conversation_repository = MongoConversationRepository()
```

- Creates new instances per request
- Uses factory for LLM provider, direct instantiation for repositories

**REST endpoint should follow same pattern**:
- Don't instantiate `ConversationOrchestrator` at module level (would be reused across requests)
- Instantiate per-request in endpoint handler
- Ensures fresh connections and isolation

### 4. **Error Handling in Streaming** (MEDIUM RISK)

**Challenge**: Error can occur during streaming response
- User receives partial tokens
- Then error event
- Client must handle this gracefully

**Mitigation**:
- Wrap orchestrator calls in try-except
- Send error event if exception occurs
- Include error code and message
- Log error for debugging

```python
async def event_generator():
    try:
        async for event in orchestrator.stream_message(...):
            yield format_sse_event(event)
    except Exception as e:
        logger.error(f"Error in message streaming: {e}")
        yield format_sse_event({
            "type": "error",
            "message": str(e),
            "code": "STREAMING_ERROR"
        })
```

### 5. **Message Persistence Race Condition** (LOW RISK)

**Issue**: Messages saved during graph execution
- User message saved by `process_input` node (indirectly)
- Assistant message saved by `save_history` node
- But REST response returned before database write completes?

**Current implementation** (save_history.py, lines 12-64):
- Saves messages asynchronously
- Returns completion event
- Client sees completion before DB commit confirmed

**Risk**: Client query for messages before saved
- But `MongoMessageRepository.create()` awaits completion
- So timing should be fine (async doesn't mean non-blocking)

**Mitigation**: Ensure `save_history` node completes before graph returns

### 6. **LangGraph Graph Compilation** (LOW RISK)

**Current code** (chat_graph.py, lines 86):
```python
graph = graph_builder.compile()
return graph
```

- Graphs compiled once on function call
- Should they be cached/singletons?

**Decision**:
- For simplicity: Compile per request in service
- For performance: Cache compiled graphs in `ConversationOrchestrator.__init__()`
- **Recommendation**: Cache during service initialization

```python
class ConversationOrchestrator:
    def __init__(self, ...):
        self.graph = create_streaming_chat_graph(...)
        # Compile once, reuse across method calls
```

---

## Testing Strategy

### Unit Tests

**Test ConversationOrchestrator in isolation**:
```python
class TestConversationOrchestrator:

    def test_stream_message_yields_tokens():
        # Mock ports
        llm_provider = MockLLMProvider()
        message_repo = MockMessageRepository()
        convo_repo = MockConversationRepository()

        # Create service
        orchestrator = ConversationOrchestrator(llm_provider, message_repo, convo_repo)

        # Execute
        events = list(orchestrator.stream_message("convo1", "user1", "Hello"))

        # Assert
        assert any(e["type"] == "token" for e in events)
        assert events[-1]["type"] == "complete"
        assert events[-1]["role"] == "assistant"

    def test_stream_message_saves_messages():
        # Verify save_history node called with correct data

    def test_stream_message_error_handling():
        # Mock LLM provider to raise exception
        # Verify error event sent

    def test_validates_conversation_ownership():
        # Mock conversation with different user_id
        # Verify error returned
```

### Integration Tests

**Test REST endpoint end-to-end**:
```python
class TestSendMessageEndpoint:

    async def test_post_messages_returns_sse_stream():
        # Make POST request
        response = await client.post(
            "/api/conversations/convo1/messages",
            json={"content": "Hello"},
            headers={"Authorization": "Bearer token"}
        )

        # Assert streaming response
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"

        # Parse SSE events
        events = parse_sse_stream(response.body)
        assert len(events) > 0
        assert events[-1]["type"] == "complete"

    async def test_requires_authentication():
        # Request without token
        response = await client.post(
            "/api/conversations/convo1/messages",
            json={"content": "Hello"}
        )
        assert response.status_code == 401

    async def test_validates_user_owns_conversation():
        # Request for conversation owned by different user
        response = await client.post(
            "/api/conversations/other_user_convo/messages",
            json={"content": "Hello"},
            headers={"Authorization": "Bearer user1_token"}
        )
        assert response.status_code == 403

    async def test_empty_content_rejected():
        response = await client.post(
            "/api/conversations/convo1/messages",
            json={"content": ""},
            headers={"Authorization": "Bearer token"}
        )
        assert response.status_code == 422  # Validation error
```

### Architecture Tests

**Verify dependency flow is correct**:
```python
def test_adapter_does_not_import_from_adapter():
    # message_router.py should not import from repositories or providers
    # Should only import ports and use dependency injection

def test_service_layer_depends_only_on_ports():
    # ConversationOrchestrator should not import MongoDB/OpenAI/etc
    # Should only import ILLMProvider, IMessageRepository, etc
```

---

## Specific Code References

### ConversationState Schema
- **File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py`
- **Lines**: 10-31
- **Required fields for orchestrator**: conversation_id, user_id, current_input, messages

### Current Message Router
- **File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_router.py`
- **Lines**: 14-70
- **Current functionality**: GET endpoint for conversation messages (READ-ONLY)
- **Where to add**: POST endpoint handler near line 20

### LangGraph Graphs
- **Chat Graph**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` lines 35-91
- **Streaming Graph**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` lines 70-120
- **Decision**: Use streaming graph for REST API with streaming response

### Current Authentication Dependency
- **File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/security/dependencies.py`
- **Lines**: 56-76 (get_current_active_user), 79 (CurrentUser type alias)
- **Usage**: Add `current_user: CurrentUser` parameter to POST endpoint

### WebSocket Current Implementation (for reference/migration)
- **File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py`
- **Lines**: 56-180 (handle_websocket_chat function)
- **Current approach**: Direct LLM calls, manual message saving
- **Pattern to follow**: Fetch messages, invoke orchestrator, handle streaming

---

## Summary of Changes Required

### Create (New Files)
1. `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/services/conversation_orchestrator.py`
   - `ConversationOrchestrator` class
   - `stream_message()` async generator method
   - Dependency on ports

2. `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/streaming.py`
   - SSE formatting utilities
   - Event conversion helpers

### Modify (Existing Files)
1. `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_router.py`
   - Add `SendMessageRequest` model
   - Add POST endpoint handler
   - Import `ConversationOrchestrator`
   - Dependency injection of ports

2. `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py`
   - Consider: Update streaming implementation if needed
   - Current structure may need adjustment for proper token streaming
   - **Decision pending**: Verify graph execution returns properly formatted state

### Consider (Refactoring)
1. `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py`
   - Optional: Refactor to use `ConversationOrchestrator` for consistency
   - Benefit: Single source of truth for message processing
   - Trade-off: WebSocket uses different event types (JSON vs SSE)

---

## Architectural Principles Maintained

### Hexagonal Architecture (Ports & Adapters)
- **Domain Core**: Message, Conversation models; SendMessage use case
- **Ports**: ILLMProvider, IMessageRepository, IConversationRepository (unchanged)
- **Adapters Inbound**: New REST POST endpoint
- **Adapters Outbound**: Existing repositories and LLM providers (unchanged)

### Dependency Inversion
- Service layer depends on ports (interfaces), not concrete adapters
- Adapters instantiate concrete implementations
- Flow: Adapter → Service → Ports → Adapters (correct inward flow)

### Separation of Concerns
- HTTP handling (adapter) ≠ Business logic (service) ≠ Data access (ports/adapters)
- LangGraph orchestration isolated in service layer
- REST adapter only handles HTTP formatting

### Testability
- Service layer testable in isolation with mock ports
- Endpoints testable without real database/LLM
- Graph logic unchanged (already testable)

---

## Key Takeaways

1. **Current State**: LangGraph graphs built but unused; WebSocket bypasses them
2. **Goal**: Integrate LangGraph via new REST endpoint with streaming response
3. **Solution**: Create `ConversationOrchestrator` service layer as bridge
4. **Benefits**:
   - Clean separation between HTTP and business logic
   - Consistent message processing (can reuse for WebSocket)
   - Proper use of LangGraph for orchestration
   - Maintains hexagonal architecture principles
5. **Implementation Order**: Service → REST endpoint → Optional WebSocket refactor
