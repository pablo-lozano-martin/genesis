# Data Flow Analysis: Message Creation from REST Endpoint through LangGraph to Database

## Request Summary

Issue #4 proposes replacing the currently unused LangGraph infrastructure with a direct REST API integration for message creation. The WebSocket handler (`websocket_handler.py:132`) currently handles message streaming outside of the LangGraph framework, making the LangGraph nodes, state management, and graph orchestration redundant for the current use case. This analysis maps the existing data flows and proposes a cleaner REST-based alternative.

**Current State**: LangGraph infrastructure exists but is not actively used by the WebSocket handler. Message creation flows directly through repository operations without leveraging LangGraph orchestration.

**Proposed Change**: Create a REST endpoint for message creation that integrates directly with repositories and LLM providers, eliminating the unused LangGraph intermediate layer.

---

## Relevant Files & Modules

### Core Domain Models
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/message.py` - Domain model for messages, defines MessageRole enum (USER, ASSISTANT, SYSTEM) and Message/MessageResponse schemas
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/conversation.py` - Domain model for conversations with metadata (title, message_count, created_at, updated_at)

### Repository Ports (Port Interfaces)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/message_repository.py` - IMessageRepository port interface defining create(), get_by_id(), get_by_conversation_id(), delete() operations
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/conversation_repository.py` - IConversationRepository port interface defining create(), get_by_id(), get_by_user_id(), update(), increment_message_count() operations
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - ILLMProvider port interface with generate() for single response and stream() for token-by-token streaming

### Repository Implementations (Outbound Adapters)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_message_repository.py` - MongoMessageRepository implements IMessageRepository using Beanie ODM, handles MessageDocument-to-Message transformation
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_conversation_repository.py` - MongoConversationRepository implements IConversationRepository, includes increment_message_count() method (line 114-133)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_models.py` - MongoDB document models (UserDocument, ConversationDocument, MessageDocument) with indexes and validation

### Use Cases (Business Logic)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/use_cases/send_message.py` - SendMessage use case encapsulating the business logic for message creation, LLM invocation, and response persistence (complete implementation exists)

### Inbound Adapters (HTTP/WebSocket)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket handler managing real-time chat, token streaming (line 132: `async for token in llm_provider.stream(messages)`)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_router.py` - WebSocket route definition, dependency injection setup
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_router.py` - REST API endpoint for reading conversation messages (read-only GET endpoint)

### LangGraph Infrastructure (Currently Unused)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - ConversationState TypedDict defining state schema (messages, conversation_id, user_id, current_input, llm_response, error)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/process_input.py` - process_user_input node validates and formats input, creates Message with USER role
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - call_llm node invokes llm_provider.generate(), handles errors
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/format_response.py` - format_response node converts raw LLM string into Message object with ASSISTANT role
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/save_history.py` - save_to_history node persists messages to repositories and updates conversation metadata (line 12-64)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Main chat graph orchestrating node flow: START -> process_input -> call_llm -> format_response -> save_history -> END
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Streaming variant with token-by-token support (lines 34-67: call_llm_stream generator function)

### LLM Provider Port
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/provider_factory.py` - Factory for creating LLM provider instances based on configuration

---

## Current Data Flow Overview

### WebSocket Message Creation Flow (Current Implementation)

The existing message creation flow bypasses LangGraph entirely:

```
Client (WebSocket)
    ↓
websocket_handler.py:56-180 (handle_websocket_chat)
    ├─ Line 88-105: Parse ClientMessage JSON
    ├─ Line 108-117: Authorize user access to conversation
    ├─ Line 119-125: Create Message(role=USER), save via message_repository.create()
    ├─ Line 128: Load conversation history via message_repository.get_by_conversation_id()
    ├─ Line 132-135: Stream tokens via llm_provider.stream(messages)
    ├─ Line 137-146: Collect full response, create Message(role=ASSISTANT), save via message_repository.create()
    ├─ Line 148: Update conversation via conversation_repository.increment_message_count(conversation_id, 2)
    └─ Line 150-154: Send completion confirmation
    ↓
MongoDB (Messages and Conversations collections)
```

**Key characteristics of current flow:**
- Direct repository access from inbound adapter
- No intermediate use case or application layer
- No LangGraph orchestration (completely bypassed)
- Streaming handled natively by WebSocket connection
- Error handling at handler level (lines 156-176)

### LangGraph Infrastructure (Currently Unused)

The LangGraph layer exists but is not invoked from any active endpoint:

```
ConversationState (TypedDict)
    ↓
LangGraph Graph (chat_graph.py or streaming_chat_graph.py)
    ├─ START
    ├─ process_user_input node (process_input.py:11-46)
    │   └─ Creates Message(role=USER), adds to state.messages
    ├─ call_llm node (call_llm.py:11-46)
    │   └─ Invokes llm_provider.generate(state.messages)
    ├─ format_response node (format_response.py:11-44)
    │   └─ Creates Message(role=ASSISTANT), adds to state.messages
    ├─ save_to_history node (save_history.py:12-64)
    │   └─ Persists all messages and updates conversation metadata
    └─ END
```

**Problem with current design:**
- LangGraph nodes wrap simple operations that could be done more directly
- State management adds complexity without benefit for single-turn message creation
- No code path actually invokes the graph (no routes call it)
- Streaming variant (streaming_chat_graph.py) has special handling but isn't integrated

---

## Data Transformation Points

### 1. **HTTP Request to Domain Message**
**Current Implementation** (websocket_handler.py:88-123):
```
ClientMessage (WebSocket JSON)
    ↓
Message(conversation_id, role=USER, content)
    ↓
MessageRepository.create()
    ↓
MessageDocument (MongoDB)
```

**Transformation Details:**
- ClientMessage schema validated via Pydantic (line 97)
- Conversation ownership verified (lines 108-117)
- Message object created with UUID generation in MongoDB (lines 119-123)

### 2. **LLM Provider Input Preparation**
**Current Implementation** (websocket_handler.py:128):
```
Message[] (from message_repository.get_by_conversation_id)
    ↓
List[Message] (passed to llm_provider.stream())
    ↓
Token stream (AsyncGenerator[str, None])
```

**Transformation Details:**
- Full conversation history loaded from MongoDB
- Passed directly to LLM provider (no transformation)
- LLM provider formats for specific model API

### 3. **Token Stream to Persisted Message**
**Current Implementation** (websocket_handler.py:130-146):
```
AsyncGenerator[str, None] (from llm_provider.stream)
    ↓
Token accumulation (full_response = [])
    ↓
Message(conversation_id, role=ASSISTANT, content=full_response)
    ↓
MessageRepository.create()
    ↓
MessageDocument (MongoDB)
```

**Transformation Details:**
- Tokens collected into memory (line 130)
- Complete response joined into string (line 137)
- Message created with ASSISTANT role
- Persisted with auto-generated UUID and timestamp

### 4. **Conversation Metadata Update**
**Current Implementation** (websocket_handler.py:148):
```
Conversation (existing)
    ↓
increment_message_count(conversation_id, 2)  // +1 user, +1 assistant
    ↓
ConversationDocument (MongoDB with updated_at and message_count)
```

**Transformation Details:**
- Atomic increment operation on MongoDB
- Updated timestamp set in repository (mongo_conversation_repository.py:130)
- No validation that messages actually exist

---

## Repository Interaction Points

### Message Repository Operations

**In current WebSocket flow:**
1. **Create user message** (websocket_handler.py:125)
   ```python
   saved_user_message = await message_repository.create(user_message)
   ```
   - Returns: Message object with id, created_at
   - MongoDB operation: insertOne(MessageDocument)

2. **Get conversation history** (websocket_handler.py:128)
   ```python
   messages = await message_repository.get_by_conversation_id(conversation_id)
   ```
   - Returns: List[Message] ordered by created_at
   - MongoDB query: find({conversation_id}) with sorting

3. **Create assistant message** (websocket_handler.py:145)
   ```python
   saved_assistant_message = await message_repository.create(assistant_message)
   ```
   - Returns: Message object with id, created_at
   - MongoDB operation: insertOne(MessageDocument)

**Unused repository methods (from IMessageRepository interface):**
- `get_by_id(message_id)` - not called in WebSocket flow
- `delete(message_id)` - not called
- `delete_by_conversation_id(conversation_id)` - not called

### Conversation Repository Operations

**In current WebSocket flow:**
1. **Get conversation** (websocket_handler.py:108)
   ```python
   conversation = await conversation_repository.get_by_id(conversation_id)
   ```
   - Returns: Conversation object
   - MongoDB query: findOne({_id: conversation_id})
   - Used for authorization check (line 110)

2. **Increment message count** (websocket_handler.py:148)
   ```python
   await conversation_repository.increment_message_count(conversation_id, 2)
   ```
   - Atomic MongoDB update: updateOne({_id}, {$inc: {message_count: 2}})
   - Also updates updated_at timestamp

**Unused conversation repository methods:**
- `create(user_id, conversation_data)` - not called
- `get_by_user_id(user_id)` - not called
- `update(conversation_id, conversation_data)` - not called
- `delete(conversation_id)` - not called

---

## LLM Provider Integration

### Current Implementation (websocket_handler.py:132-154)

**Stream Method Usage:**
```python
async for token in llm_provider.stream(messages):
    full_response.append(token)
    token_msg = ServerTokenMessage(content=token)
    await manager.send_message(websocket, token_msg.model_dump())
```

**Data flow:**
1. `llm_provider.stream()` returns `AsyncGenerator[str, None]`
2. Each token yielded is appended to in-memory list
3. Immediately sent to client via WebSocket
4. Full response reconstructed after streaming completes

**Error handling:**
- Wrapped in try-except (line 156)
- LLM errors sent as ServerErrorMessage (line 158-162)
- Connection maintained on error (broken except block line 175)

### Unused LLM Provider Method

The LangGraph `call_llm` node calls:
```python
response = await llm_provider.generate(messages)  # Single response, not streaming
```

This method is not used in WebSocket flow but is called in:
- LangGraph chat_graph.py (not invoked anywhere)
- SendMessage use case (not exposed via REST)

---

## Error Propagation & Resilience

### Current WebSocket Error Handling

**Three levels of error catching:**

1. **Message parsing** (lines 88-105):
   - Invalid JSON → ServerErrorMessage with code="INVALID_FORMAT"
   - Validation failure → Same error response

2. **Conversation authorization** (lines 108-117):
   - Not found or access denied → ServerErrorMessage with code="ACCESS_DENIED"

3. **LLM streaming** (lines 156-162):
   - Stream failure → ServerErrorMessage with code="LLM_ERROR"
   - Error message included but connection stays open

4. **General handler errors** (lines 167-176):
   - Any unexpected exception → Attempt to send INTERNAL_ERROR
   - If sending fails, break connection

### LangGraph Error Flow (Unused)

**In save_to_history node** (save_history.py:33-64):
- Database errors caught individually (lines 44-48, 54-55)
- No exception thrown; errors logged
- State updated with error message (line 62-63)
- Node returns error state without breaking

**In call_llm node** (call_llm.py:42-46):
- Exception caught and returned as error state
- Graph continues to format_response (would fail silently)

**Problem**: Error handling inconsistency - exceptions swallowed vs propagated

---

## Data Integrity Concerns

### 1. **Race Conditions in Message Count**

Current implementation (websocket_handler.py:148):
```python
await conversation_repository.increment_message_count(conversation_id, 2)
```

**Issue**: Increment happens AFTER user and assistant messages are persisted, but there's no transaction. If increment fails, messages are orphaned but count isn't updated.

**Current mitigation**: None. Count will be stale.

### 2. **Incomplete Messages on Streaming Failure**

Current implementation (websocket_handler.py:130-146):
```python
full_response = []
try:
    async for token in llm_provider.stream(messages):
        full_response.append(token)
        # ... send to client
except Exception as e:
    # Assistant message NOT created
```

**Issue**: If streaming fails mid-stream, no assistant message is persisted. User message already persisted (line 125). Conversation becomes inconsistent.

**Current mitigation**: Client sees error, conversation history only has user message.

### 3. **No Message Content Validation**

Message domain model (message.py:30):
```python
content: str = Field(..., min_length=1, description="Message content")
```

**Issue**: Validation only on message creation, but nothing prevents empty responses from LLM or injection attacks in metadata.

---

## Proposed REST Endpoint Data Flow

### Endpoint Design

```
POST /api/conversations/{conversation_id}/messages
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "User message content"
}

Response 202 Accepted:
{
  "message_id": "uuid",
  "conversation_id": "uuid",
  "content": "User message content",
  "role": "user",
  "created_at": "2025-01-15T10:30:00"
}
```

### Data Flow with Direct Repository Access

```
Client (REST API)
    ↓
message_router.py (new endpoint)
    ├─ Authenticate user (JWT dependency)
    ├─ Validate conversation ownership
    ├─ Create Message(role=USER, content)
    ├─ Save via message_repository.create()
    ├─ Load conversation history
    ├─ Call llm_provider.stream()
    │   └─ Stream tokens directly (no buffering if not needed)
    │   └─ Accumulate full response
    ├─ Create Message(role=ASSISTANT, content=full_response)
    ├─ Save via message_repository.create()
    ├─ Update conversation via increment_message_count()
    └─ Return Message response
    ↓
Response (200 OK with message data)
```

### Alternative: Using SendMessage Use Case

```
Client (REST API)
    ↓
message_router.py (new endpoint)
    ├─ Authenticate user (JWT dependency)
    ├─ Inject repositories and LLM provider
    ├─ Call SendMessage.execute(conversation_id, content)
    │   (line 44-87 in send_message.py)
    │   ├─ Validate non-empty content
    │   ├─ Verify conversation exists
    │   ├─ Create and persist user message
    │   ├─ Load conversation history
    │   ├─ Call llm_provider.generate()
    │   ├─ Create and persist assistant message
    │   ├─ Update message count
    │   └─ Return assistant message
    └─ Return Message response
    ↓
Response (200 OK with assistant message)
```

**Recommendation**: Use SendMessage use case (already exists, encapsulates business logic)

---

## Implementation Guidance

### Step 1: Create REST Endpoint for Message Creation

**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_router.py`

**Changes needed**:
- Add POST endpoint to existing router (currently read-only, line 14-70)
- Accept conversation_id from path, content from request body
- Inject SendMessage use case (not repositories directly)
- Handle authentication via CurrentUser dependency

**Data transformations**:
- HTTP JSON → MessageCreate domain object (manual construction)
- SendMessage returns Message with assistant response
- Message → MessageResponse for HTTP response

### Step 2: Dependency Injection Setup

**Files**:
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/security/dependencies.py`
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py`

**Changes needed**:
- Create use case instances in dependency injection
- Provide SendMessage as injectable dependency
- Or instantiate in endpoint (simpler)

### Step 3: Remove Unused LangGraph (Optional but Recommended)

**Files to deprecate**:
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py`
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py`
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/` (all nodes)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py`

**Rationale**: These are completely unused, removing them reduces code maintenance burden.

**Keep**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/__init__.py` for consistency (can be empty)

### Step 4: Test Data Persistence

**Critical paths to test**:
1. User message persisted with correct conversation_id, role=USER
2. Assistant message persisted with correct conversation_id, role=ASSISTANT
3. Both messages have unique IDs and timestamps
4. Conversation message_count incremented by 2
5. Conversation updated_at timestamp updated

---

## Data Model Summary

### Message (Domain Model)
```python
# File: backend/app/core/domain/message.py

class Message(BaseModel):
    id: Optional[str]              # Auto-generated by MongoDB
    conversation_id: str           # Foreign key to Conversation
    role: MessageRole              # Enum: USER, ASSISTANT, SYSTEM
    content: str                   # Non-empty validation
    created_at: datetime           # UTC timestamp
    metadata: Optional[dict]       # Extensible field (unused currently)
```

### Conversation (Domain Model)
```python
# File: backend/app/core/domain/conversation.py

class Conversation(BaseModel):
    id: Optional[str]              # Auto-generated by MongoDB
    user_id: str                   # Foreign key to User
    title: str                     # Default "New Conversation"
    created_at: datetime           # UTC timestamp
    updated_at: datetime           # Updated on message addition
    message_count: int             # Incremented atomically
```

### MongoDB Collections
```
messages:
  - _id: ObjectId
  - conversation_id: indexed
  - role: enum
  - content: string
  - created_at: indexed (composite with conversation_id)
  - metadata: optional

conversations:
  - _id: ObjectId
  - user_id: indexed (composite with updated_at)
  - title: string
  - created_at: datetime
  - updated_at: datetime (sorted descending)
  - message_count: integer
```

---

## Repository Interface Summary

### IMessageRepository
```python
async def create(message_data: MessageCreate) -> Message
  # Creates message, returns with generated id and timestamp

async def get_by_conversation_id(
    conversation_id: str,
    skip: int = 0,
    limit: int = 100
) -> List[Message]
  # Returns ordered by created_at ascending

async def get_by_id(message_id: str) -> Optional[Message]
  # Single message lookup

async def delete(message_id: str) -> bool
async def delete_by_conversation_id(conversation_id: str) -> int
```

### IConversationRepository
```python
async def get_by_id(conversation_id: str) -> Optional[Conversation]
  # Used for authorization checks

async def increment_message_count(conversation_id: str, count: int = 1) -> Optional[Conversation]
  # Atomic operation updating message_count and updated_at

async def create(user_id: str, conversation_data: ConversationCreate) -> Conversation
  # Creates conversation with user_id

async def get_by_user_id(user_id: str, skip: int = 0, limit: int = 100) -> List[Conversation]
  # Lists user's conversations

async def update(conversation_id: str, conversation_data: ConversationUpdate) -> Optional[Conversation]
async def delete(conversation_id: str) -> bool
```

---

## Risk Analysis

### Risks of Removing LangGraph

**Low Risk** (safe to remove):
- No existing code paths use LangGraph
- No clients depend on LangGraph behavior
- Simpler architecture without it
- Easy to re-introduce if needed

**Mitigation**: Keep git history; document decision in ARCHITECTURE.md

### Risks of New REST Endpoint

**Potential Issues**:
1. **Rate limiting**: No protection against rapid message creation (client-side is only control)
   - Mitigation: Add rate limiting middleware

2. **Token streaming for REST**: REST/HTTP doesn't support streaming responses well
   - Mitigation: Accept full response (already happens in WebSocket)

3. **Conversation access**: Must verify user owns conversation before allowing message
   - Mitigation: Done in all code paths (websocket_handler.py:110, etc.)

---

## Testing Strategy

### Unit Tests Needed

1. **Endpoint Authorization**
   - Unauthenticated request → 401 Unauthorized
   - Wrong user's conversation → 403 Forbidden
   - Conversation doesn't exist → 404 Not Found

2. **Message Persistence**
   - User message saved with correct fields
   - Assistant message saved with correct fields
   - Message IDs are unique
   - Created_at timestamps are reasonable

3. **Conversation Metadata**
   - Message count incremented by 2
   - Updated_at timestamp changed
   - Invalid conversation_id handled gracefully

4. **LLM Provider Integration**
   - LLM errors handled and returned to client
   - Empty LLM response handled
   - Token accumulation works correctly

### Integration Tests Needed

1. **End-to-end message creation**
   - Create conversation
   - Send message via REST
   - Verify message in database
   - Verify conversation metadata updated

2. **Multiple messages in sequence**
   - Send first message → verify count = 2
   - Send second message → verify count = 4
   - Verify message history ordering

3. **Error recovery**
   - LLM provider failure → conversation still updatable
   - Database failure → proper error response

### Data Integrity Tests

1. **Race condition testing** (if concurrent messages)
   - Multiple simultaneous messages
   - Verify final count is accurate
   - Verify all messages persisted

2. **Partial failure scenarios**
   - Message persisted but count not updated
   - Count updated but message not persisted
   - LLM streaming interrupted

---

## Dependencies & Assumptions

### Assumed to Exist (Used)
- `ILLMProvider` port interface with `generate()` and `stream()` methods
- `IMessageRepository` with `create()` and `get_by_conversation_id()`
- `IConversationRepository` with `get_by_id()` and `increment_message_count()`
- `SendMessage` use case with `execute(conversation_id, content)` method
- JWT authentication via `CurrentUser` dependency
- MongoDB with Beanie ODM

### To Be Created
- REST endpoint in message_router.py (POST /api/conversations/{conversation_id}/messages)
- Proper error handling and validation
- Request/response schemas if not using domain models directly

### To Be Removed (Recommended)
- LangGraph state, nodes, and graphs
- Streaming chat graph implementation
- Process input node (validation logic)
- Format response node (simple transformation)
- Save to history node (repository wrapper)

---

## Key Metrics & Performance Notes

### Current WebSocket Implementation
- **Latency**: Token streaming provides real-time feedback
- **Memory**: Full response buffered in memory before persistence (line 130: `full_response = []`)
- **Database writes**: 2 (user message, assistant message) + 1 (conversation count)
- **Database reads**: 1 conversation check + 1 history load = 2 queries

### Proposed REST Implementation
- **Latency**: Full response returned at end (no streaming without special handling)
- **Memory**: Same buffering in accumulator
- **Database writes**: Same as current (2 + 1)
- **Database reads**: Same as current (2)

### Optimization Opportunities
1. **Batch metadata updates**: Update timestamp and count in single query
2. **Cache conversation check**: Verify ownership only on first request
3. **Lazy history loading**: Only load messages if needed by LLM provider
4. **Pagination**: Get_by_conversation_id already supports skip/limit

---

## Summary

**Current State:**
- WebSocket handler directly manages message creation without LangGraph
- LangGraph infrastructure (state, nodes, graphs) completely unused
- Message flow: WebSocket → Repositories → MongoDB
- No application/use case layer (business logic in inbound adapter)

**Proposed State:**
- REST endpoint for message creation
- Uses SendMessage use case (reusable business logic)
- Same repository and LLM provider interfaces
- Cleaner separation: Inbound → Use Case → Repositories → Database

**Key Changes:**
1. Add POST endpoint to message_router.py
2. Inject and call SendMessage.execute()
3. Remove LangGraph module entirely
4. Keep all domain models, repositories, and providers unchanged

**No Breaking Changes:**
- Existing GET /api/conversations/{conversation_id}/messages unaffected
- WebSocket endpoint can coexist with REST endpoint
- Database schema unchanged
- Domain models unchanged

**Benefits:**
- Simpler codebase (fewer abstractions)
- Reuses existing SendMessage use case
- Aligns with hexagonal architecture (inbound → use case → outbound)
- Easier to test (use case is testable without HTTP/WebSocket)
