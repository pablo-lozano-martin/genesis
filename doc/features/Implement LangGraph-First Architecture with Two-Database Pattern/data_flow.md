# Data Flow Analysis: LangGraph-First Architecture with Two-Database Pattern

## Request Summary

Issue #6 requires a fundamental architectural refactor to make Genesis truly LangGraph-first. Currently, the system treats LangGraph as an abstraction layer behind hexagonal ports, resulting in manual message persistence that bypasses LangGraph's checkpointer entirely. The refactor will separate concerns into two databases:

1. **App DB (MongoDB - metadata)**: Users, conversations (metadata only), settings
2. **LangGraph DB (MongoDB - AI state)**: Graph checkpoints, message history, execution state, memory stores

The core principle: **LangGraph owns conversation state. Hexagonal architecture owns infrastructure.**

Key mapping: `conversation.id` ← maps to → `thread_id` in LangGraph checkpoints.

---

## Relevant Files & Modules

This section provides a complete inventory of files impacted by the refactor, organized by concern.

### Files to Examine

#### Current Hexagonal Layer (Ports & Adapters)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/message_repository.py` - Message repository port interface (TO BE DELETED)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/conversation_repository.py` - Conversation repository port (TO BE UPDATED - remove increment_message_count)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/message.py` - Message domain model (TO BE DELETED - except MessageRole enum)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/conversation.py` - Conversation domain model (TO BE UPDATED - remove message_count field)

#### Current Database Adapters
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_message_repository.py` - MongoDB message repository (TO BE DELETED)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_conversation_repository.py` - MongoDB conversation repository (TO BE UPDATED - remove increment_message_count)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_models.py` - Beanie ODM models (TO BE UPDATED - remove MessageDocument, remove message_count from ConversationDocument)

#### Current LangGraph Implementation (Needs Refactoring)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - LangGraph state definition (TO BE REPLACED - use MessagesState instead of custom ConversationState)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Main chat graph (TO BE UPDATED - add checkpointer, use native message types)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Streaming graph (TO BE UPDATED - same as chat_graph)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/process_input.py` - Input validation node (TO BE UPDATED - use HumanMessage instead of custom Message)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - LLM invocation node (NO CHANGES - already uses native types from llm_provider)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/format_response.py` - Response formatting node (TO BE UPDATED - use AIMessage instead of custom Message)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/save_history.py` - Message persistence node (TO BE DELETED - checkpointer handles this)

#### WebSocket & API Handlers (Needs Refactoring)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket chat handler (TO BE REFACTORED - call graph.astream() instead of llm_provider.stream())
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_router.py` - WebSocket routing (TO BE UPDATED - dependency injection changes)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_router.py` - Message REST endpoints (TO BE UPDATED - query LangGraph state instead of message repository)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/conversation_router.py` - Conversation REST endpoints (NO MAJOR CHANGES - already uses conversation repository)

#### Use Cases (Some Deletion Required)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/use_cases/send_message.py` - SendMessage use case (TO BE DELETED - logic moves to graph nodes and WebSocket handler)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/use_cases/get_conversation_history.py` - GetConversationHistory use case (TO BE DELETED - retrieval via graph.get_state())
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/use_cases/create_conversation.py` - CreateConversation use case (NO CHANGES - still used for metadata)

#### Infrastructure (Requires New Additions)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/mongodb.py` - Database connections (TO BE UPDATED - add dual database support)
- `backend/app/infrastructure/langgraph/checkpointer.py` - (TO BE CREATED - MongoDB checkpointer configuration)

### Key Functions & Classes

#### Functions to Delete or Heavily Refactor
- `MongoMessageRepository.create()` - Delete (checkpointer handles persistence)
- `MongoMessageRepository.get_by_conversation_id()` - Delete (query graph state instead)
- `MongoConversationRepository.increment_message_count()` - Delete (no longer needed)
- `save_to_history()` node - Delete (checkpointer auto-saves)
- `SendMessage.execute()` - Delete (graph orchestrates this flow)
- `GetConversationHistory.execute()` - Delete (graph.get_state() retrieves state)

#### Functions to Create
- `AsyncMongoDBSaver` setup in `checkpointer.py` - Create checkpointer wrapper
- Graph compilation with checkpointer parameter - Update graph creation functions
- Message retrieval from LangGraph state - New function in message_router.py

#### Functions to Update (Critical Points)
- `handle_websocket_chat()` in websocket_handler.py - Replace `llm_provider.stream()` with `graph.astream()`
- `get_conversation_messages()` in message_router.py - Query `graph.get_state()` instead of message repository
- `process_user_input()` node - Use `HumanMessage` from langchain_core instead of custom `Message`
- `format_response()` node - Use `AIMessage` from langchain_core instead of custom `Message`
- `ConversationState` - Replace with `MessagesState` from langgraph

---

## Current Data Flow Overview

### High-Level Current Architecture

```
User (Frontend)
    ↓
WebSocket /ws/chat
    ↓
websocket_handler.handle_websocket_chat()
    ├─ Validate conversation ownership (App DB query)
    ├─ Save user message (MongoDB - manual)
    ├─ llm_provider.stream() [NEVER uses LangGraph graphs]
    └─ Save assistant message (MongoDB - manual)
    ↓
MongoDB Collections
├─ users: User metadata
├─ conversations: Conversation metadata + message_count
└─ messages: Full message history
```

**Critical Problem**: WebSocket handler bypasses LangGraph graphs entirely. Messages are managed manually through repositories instead of using LangGraph's checkpointer.

### Current Data Entry Points

1. **WebSocket Message Arrival** (`websocket_handler.py:85`)
   - `await websocket.receive_text()` - Raw JSON from client
   - Parse to `ClientMessage` schema
   - Extract: `conversation_id`, `content`

2. **HTTP REST Endpoints** (`conversation_router.py`, `message_router.py`)
   - Create conversation: `POST /conversations`
   - Get messages: `GET /conversations/{id}/messages`
   - List conversations: `GET /conversations`

### Current Transformation Layers

#### Layer 1: WebSocket to Domain (websocket_handler.py:119-123)
```python
user_message = Message(
    conversation_id=conversation_id,
    role=MessageRole.USER,
    content=client_message.content
)
```
- Input: `ClientMessage` (JSON from WebSocket)
- Process: Create domain `Message` object
- Output: `Message` domain model ready for persistence

#### Layer 2: Manual Persistence (websocket_handler.py:125-126)
```python
saved_user_message = await message_repository.create(user_message)
```
- Input: `Message` domain model
- Process: Convert to `MessageDocument` via adapter
- Output: MongoDB insert, return entity with ID
- **Problem**: Manual transaction, not atomic across messages

#### Layer 3: LLM Processing (websocket_handler.py:128-135)
```python
messages = await message_repository.get_by_conversation_id(conversation_id)
async for token in llm_provider.stream(messages):
    full_response.append(token)
    token_msg = ServerTokenMessage(content=token)
    await manager.send_message(websocket, token_msg.model_dump())
```
- Input: Conversation ID
- Process:
  - Query messages from MongoDB (manual retrieval)
  - Invoke LLM provider with list of `Message` objects
  - Stream tokens to WebSocket
- **Critical Issue**: Never uses `chat_graph.py` - LangGraph graphs are dead code

#### Layer 4: Response Persistence (websocket_handler.py:139-148)
```python
assistant_message = Message(conversation_id=conversation_id, role=MessageRole.ASSISTANT, content=response_content)
saved_assistant_message = await message_repository.create(assistant_message)
await conversation_repository.increment_message_count(conversation_id, 2)
```
- Input: Full LLM response
- Process: Create `Message` object, persist to MongoDB, increment counter
- **Problem**: Three separate operations, not atomic. Message count gets out of sync if any operation fails.

### Current Persistence Layer

**App Database (MongoDB)**

Collections:
- `users` - User accounts
- `conversations` - Metadata + message count
- `messages` - Full message history (duplication issue)

**Problems**:
1. Message history is stored in App DB, not using LangGraph checkpointer
2. Message count tracking is redundant and fragile
3. No checkpoint/execution state stored
4. No time-travel history
5. No memory stores support

### Current Data Exit Points

1. **WebSocket Streaming** (websocket_handler.py:132-135)
   - Server sends `ServerTokenMessage` with each token
   - Final message: `ServerCompleteMessage` with message_id and conversation_id

2. **REST API Response** (message_router.py:59-69)
   - `GET /conversations/{id}/messages` returns list of `MessageResponse` objects
   - Query MongoDB messages collection directly

3. **REST API Response** (conversation_router.py - assumed)
   - Conversation list returns metadata from MongoDB

---

## Impact Analysis: LangGraph-First Refactor

### Data Flow Changes by Component

#### 1. WebSocket Handler Flow (MAJOR CHANGE)
**Current** → **Target**

```
BEFORE:
receive_text() → MessageDocument.insert()
             → message_repository.get_by_conversation_id()
             → llm_provider.stream() [never uses graph]
             → MessageDocument.insert()
             → increment_message_count()

AFTER:
receive_text() → validate conversation (App DB)
            → graph.astream(input, config) [uses compiled graph with checkpointer]
            → LangGraph automatically persists to LangGraph DB
            → stream tokens from graph
```

**Key Changes**:
- Line 125-126: REMOVE `await message_repository.create(user_message)` - graph handles this
- Line 128-129: REPLACE `await message_repository.get_by_conversation_id()` - state passed through graph
- Line 132-135: REPLACE `llm_provider.stream()` with `graph.astream()`
- Line 139-148: REMOVE all message persistence - checkpointer handles this
- Line 148: REMOVE `increment_message_count()` - no longer exists

#### 2. Conversation State (MAJOR CHANGE)
**Current** → **Target**

```python
# BEFORE: Custom domain model
class Message(BaseModel):
    id: Optional[str]
    conversation_id: str
    role: MessageRole
    content: str
    created_at: datetime
    metadata: Optional[dict]

class ConversationState(TypedDict):
    messages: Annotated[list[Message], add_messages]
    conversation_id: str
    user_id: str
    current_input: Optional[str]
    llm_response: Optional[str]
    error: Optional[str]

# AFTER: Native LangGraph types
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

class ConversationState(MessagesState):
    conversation_id: str
    user_id: str
    # MessagesState already provides:
    # - messages: list[BaseMessage] with add_messages reducer
```

**Impact**:
- Drop custom `Message` domain model
- Use native `HumanMessage`, `AIMessage`, `SystemMessage` from langchain
- Automatic message merging via LangGraph's `add_messages` reducer
- Better interoperability with LangGraph tools and memory stores

#### 3. LangGraph Nodes (MAJOR CHANGES)

**process_input node**:
```python
# BEFORE: Creates custom Message object
user_message = Message(
    conversation_id=state["conversation_id"],
    role=MessageRole.USER,
    content=current_input
)
return {"messages": [user_message]}

# AFTER: Creates native HumanMessage
from langchain_core.messages import HumanMessage

human_message = HumanMessage(content=current_input)
return {"messages": [human_message]}
```

**format_response node**:
```python
# BEFORE: Creates custom Message object
assistant_message = Message(
    conversation_id=state["conversation_id"],
    role=MessageRole.ASSISTANT,
    content=llm_response
)
return {"messages": [assistant_message]}

# AFTER: Creates native AIMessage
from langchain_core.messages import AIMessage

ai_message = AIMessage(content=llm_response)
return {"messages": [ai_message]}
```

**save_history node**: DELETE ENTIRELY - checkpointer handles persistence

#### 4. Graph Compilation (MAJOR CHANGE)
**Current** → **Target**

```python
# BEFORE: No checkpointer
def create_chat_graph(llm_provider, message_repository, conversation_repository):
    graph_builder = StateGraph(ConversationState)
    # ... add nodes and edges ...
    graph = graph_builder.compile()
    return graph

# AFTER: With LangGraph checkpointer
def create_chat_graph(llm_provider, checkpointer):
    graph_builder = StateGraph(ConversationState)
    # ... add nodes and edges ...
    graph = graph_builder.compile(
        checkpointer=checkpointer  # AsyncMongoDBSaver instance
    )
    return graph
```

**Impact**:
- Graph now persists all state changes automatically
- Can query state history with `graph.get_state_history(config)`
- Resume workflows from checkpoints
- No more manual persistence code

#### 5. Message Retrieval (MAJOR CHANGE)
**Current** → **Target**

```python
# BEFORE: Query MongoDB
@router.get("/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str, ...):
    messages = await message_repository.get_by_conversation_id(conversation_id)
    return [MessageResponse(...) for msg in messages]

# AFTER: Query LangGraph state
@router.get("/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str, ...):
    config = {"configurable": {"thread_id": conversation_id}}
    state = await graph.get_state(config)  # From LangGraph DB
    messages = state.values["messages"]
    return [MessageResponse.from_langchain_message(msg) for msg in messages]
```

**Impact**:
- No query to App DB for messages (faster, cleaner separation)
- Single source of truth: LangGraph DB
- Always returns latest state from checkpoint

---

## Data Flow Transformations

### Transformation 1: Message Persistence - Manual → Automatic Checkpointing

**Current Pattern**:
```
Message domain model
  ↓
MongoMessageRepository.create() (manual adapter)
  ↓
MessageDocument (database entity)
  ↓
MongoDB insert operation
```

**Fragile aspects**:
- Three separate MongoDB writes (user message, assistant message, count increment)
- No atomic transaction
- Message count can desynchronize from actual messages
- No checkpoints for resumption

**Target Pattern**:
```
HumanMessage / AIMessage (native LangGraph)
  ↓
Graph state reducer (add_messages)
  ↓
AsyncMongoDBSaver checkpointer
  ↓
Automatic MongoDB insert to langgraph_checkpoints
```

**Robust aspects**:
- Single atomic checkpoint operation per graph execution
- Built-in consistency guarantees
- State history preserved
- Can resume from any checkpoint

### Transformation 2: Conversation Ownership Verification - Stays in App DB

**Current**:
```
WebSocket message arrives
  ↓
Get conversation from MongoDB
  ↓
Check conversation.user_id == current_user.id
```

**Target** (unchanged logic, different timing):
```
WebSocket message arrives
  ↓
Get conversation from App DB (conversation_repository)
  ↓
Check conversation.user_id == current_user.id
  ↓
If valid, execute graph with conversation.id as thread_id
```

**Important**: Ownership verification stays in hexagonal layer (App DB query). This maintains security boundary.

### Transformation 3: State Retrieval - Repository Query → Graph State Query

**Current**:
```
Request for conversation history
  ↓
message_repository.get_by_conversation_id()
  ↓
MongoDB messages collection query
  ↓
Convert MessageDocument to MessageResponse
```

**Target**:
```
Request for conversation history
  ↓
graph.get_state(config) where config has thread_id
  ↓
LangGraph retrieves checkpoint from LangGraph DB
  ↓
Extract messages: state.values["messages"]
  ↓
Convert BaseMessage to MessageResponse
```

**Benefits**:
- Latest state guaranteed
- No message duplication risk
- Supports historical state queries via get_state_history()

### Transformation 4: Conversation Metadata - Remains in App DB

**Current**:
```
create_conversation(user_id, title)
  ↓
ConversationDocument created with user_id, title, created_at, message_count=0
  ↓
MongoDB insert
```

**Target** (essentially unchanged):
```
create_conversation(user_id, title)
  ↓
ConversationDocument created with user_id, title, created_at
  ↓ (NO message_count field)
  ↓
MongoDB insert to App DB
  ↓
Returns conversation.id (which becomes thread_id in LangGraph)
```

**Change**: Remove `message_count` field from Conversation model (no longer needed)

---

## Database Pattern: App DB vs LangGraph DB

### App Database (MongoDB - existing)
```
Collections:
├─ users
│  ├─ id (ObjectId)
│  ├─ email
│  ├─ username
│  ├─ hashed_password
│  ├─ is_active
│  └─ timestamps
│
├─ conversations (MODIFIED)
│  ├─ id (ObjectId)
│  ├─ user_id (Indexed)
│  ├─ title
│  ├─ created_at
│  ├─ updated_at
│  └─ [REMOVED: message_count]
│
└─ [DELETED: messages collection]
```

**Responsibility**: User identity, access control, conversation discovery metadata

**Queries**:
- `conversations.find({user_id: "..."})` - List user conversations
- `conversations.findOne({_id: "...", user_id: "..."})` - Verify ownership
- `conversations.updateOne({_id: "..."}, {title: "..."})` - Update title

### LangGraph Database (MongoDB - new)
```
Collections:
├─ langgraph_checkpoints
│  ├─ thread_id (Indexed) [maps to conversation.id]
│  ├─ checkpoint_id (Indexed)
│  ├─ ts_created (Indexed)
│  ├─ values
│  │  ├─ messages[] (list of BaseMessage)
│  │  │  ├─ type: "human" | "ai" | "system"
│  │  │  ├─ content: string
│  │  │  └─ metadata: object
│  │  ├─ conversation_id
│  │  ├─ user_id
│  │  └─ [other graph state]
│  ├─ metadata: object
│  └─ checkpoint (serialized)
│
├─ langgraph_store (optional - for memory)
│  └─ [If memory nodes added later]
│
└─ langgraph_writes (optional - write ledger)
   └─ [For audit trail]
```

**Responsibility**: Graph execution state, message history, checkpoints, time-travel capability

**Queries** (via LangGraph API, not raw MongoDB):
- `graph.get_state(config)` - Latest state for thread
- `graph.get_state_history(config)` - State progression
- `graph.astream(input, config)` - Execute with checkpointing

**Why separate?**
1. **Operational Independence**: If LangGraph DB is down, can still list conversations
2. **Scaling**: Message history and checkpoints grow unbounded; metadata is bounded
3. **Backup Strategy**: Can backup independently with different retention policies
4. **Logical Separation**: Aligns with architectural principle: "LangGraph owns state, hexagonal owns infrastructure"

---

## Conversation.id ↔ thread_id Mapping

### How Mapping Works

**Step 1: Conversation Creation** (App DB)
```python
conversation = await conversation_repository.create(
    user_id="user_123",
    conversation_data=ConversationCreate(title="...")
)
# Returns: conversation.id = "507f1f77bcf86cd799439012" (MongoDB ObjectId as string)
```

**Step 2: WebSocket Message with that Conversation**
```python
# Client sends:
{"type": "message", "conversation_id": "507f1f77bcf86cd799439012", "content": "..."}

# Server handles:
conversation_id = client_message.conversation_id
config = {
    "configurable": {
        "thread_id": conversation_id  # MAPPING: conversation.id becomes thread_id
    }
}
async for chunk in graph.astream(input_state, config, stream_mode="values"):
    # LangGraph checkpoint stored with thread_id matching conversation_id
```

**Step 3: State Retrieval**
```python
# To get messages for a conversation:
config = {"configurable": {"thread_id": conversation_id}}
state = await graph.get_state(config)
messages = state.values["messages"]

# LangGraph looks up checkpoint with matching thread_id
# Returns latest state snapshot
```

**Step 4: Verification in Logs/Monitoring**
```
App DB: conversations.find({_id: ObjectId("507f1f77bcf86cd799439012"), user_id: "user_123"})
LangGraph DB: langgraph_checkpoints.find({thread_id: "507f1f77bcf86cd799439012"})
# Both contain same ID - enables cross-database verification
```

### Implications for Data Consistency

1. **Atomicity Boundary**: Conversation creation and graph initialization are separate
   - App DB transaction: Create conversation (atomic)
   - LangGraph: First graph execution creates first checkpoint (atomicity via graph)

2. **Orphan Prevention**: Conversation without LangGraph checkpoint
   - Possible: Conversation created but never messaged
   - Safe: Graph runs on first message, creates checkpoint
   - No data loss: Checkpoint timestamps enable recovery

3. **Ownership Checks**: Must query App DB before running graph
   - Verify `conversation.user_id == current_user.id` (App DB)
   - Then run `graph.astream()` with conversation.id as thread_id
   - Prevents unauthorized graph executions

---

## Data Consistency Patterns

### Atomic Operations

**Graph Execution (Atomic)**
```
graph.astream(input, config) =
    ├─ Node 1 executes (process_input)
    ├─ Node 2 executes (call_llm)
    ├─ Node 3 executes (format_response)
    └─ Checkpointer saves complete state [ATOMIC]
       └─ If save fails: astream() raises exception
```

**Conversation Creation (Atomic within App DB)**
```
conversation_repository.create() =
    └─ MongoDB insert [ATOMIC]
       └─ Returns created conversation with ID
```

**Problem: Graph execution failure after LLM response**
```
If checkpointer fails after format_response:
  ├─ User receives streamed tokens (optimistic send)
  ├─ Checkpoint save fails
  └─ Retry logic: Can resume from previous checkpoint
```

### Data Validation Boundaries

**Ownership Validation** (App DB Layer)
```python
conversation = await conversation_repository.get_by_id(conversation_id)
if not conversation or conversation.user_id != current_user.id:
    raise AccessDenied()
# BEFORE running graph - security check
```

**Input Validation** (Graph Layer - process_input node)
```python
current_input = state.get("current_input", "").strip()
if not current_input:
    return {"error": "Input cannot be empty"}
# Inside graph execution
```

**State Validation** (Implicit in graph structure)
```python
# StateGraph type checking ensures:
# - messages is list[BaseMessage]
# - conversation_id is string
# - user_id is string
# Type validation at graph definition time
```

### Eventual Consistency Scenarios

**Scenario 1: Conversation created, no messages sent**
- App DB: Conversation exists with metadata
- LangGraph DB: No checkpoint (first message creates it)
- State: Eventual consistency - acceptable, no data loss

**Scenario 2: Graph execution fails to checkpoint**
- User receives partial tokens (bad UX)
- State not persisted (recovery: restart graph from beginning)
- Mitigation: Implement retry with exponential backoff

**Scenario 3: Conversation deleted from App DB, checkpoint exists in LangGraph DB**
- Access denied on next query (ownership check fails)
- Checkpoint orphaned (cleanup: delete checkpoint by thread_id on conversation deletion)
- Mitigation: Implement cascading delete logic

---

## Failure Scenarios & Recovery

### Failure Mode 1: LangGraph DB Connection Failure

**Scenario**:
```
graph.astream() called
  → process_input executes successfully
  → call_llm executes successfully
  → format_response executes successfully
  → checkpointer.put() fails [LangGraph DB unavailable]
  → astream() raises exception
```

**User Impact**: WebSocket receives tokens, then error message

**Recovery**:
```python
try:
    async for chunk in graph.astream(input_state, config):
        await websocket.send(chunk)
except Exception as e:
    logger.error(f"Graph execution failed: {e}")
    error_msg = ServerErrorMessage(
        message="Failed to save state",
        code="CHECKPOINT_FAILED"
    )
    await websocket.send(error_msg)
    # User can retry - graph will reload from previous checkpoint
```

**Critical**: User's message NOT saved in LangGraph state. Must handle gracefully.

### Failure Mode 2: App DB Connection Failure (Ownership Check)

**Scenario**:
```
WebSocket message arrives
  → conversation_repository.get_by_id() fails [App DB unavailable]
  → Cannot verify ownership
  → Graph not executed
```

**User Impact**: All conversations blocked (cannot verify ownership)

**Recovery**:
```python
# Circuit breaker pattern
try:
    conversation = await conversation_repository.get_by_id(conversation_id)
    if not conversation:
        raise AccessDenied()
except AppDBUnavailable:
    error_msg = ServerErrorMessage(
        message="Service temporarily unavailable",
        code="SERVICE_UNAVAILABLE"
    )
    await websocket.send(error_msg)
```

**Design Consideration**: Cannot bypass ownership check even if LangGraph DB available - security must not degrade

### Failure Mode 3: LLM Provider Failure

**Scenario**:
```
graph.astream() called
  → process_input succeeds
  → call_llm fails [LLM API unavailable]
  → error state set
  → conditional edge routes to END
  → checkpoint saved WITHOUT assistant message
```

**User Impact**: WebSocket receives error, no assistant message in state

**Recovery**: Standard LLM retry logic (already implemented in llm_provider)

### Failure Mode 4: Partial Message Streaming

**Scenario**:
```
streaming iteration:
  Token 1 → sent to WebSocket ✓
  Token 2 → sent to WebSocket ✓
  Token 3 → WebSocket write fails (client disconnected)
  Tokens 4-N → not sent
  Checkpointer saves FULL message
```

**User Impact**: User sees partial response, but server has complete state

**Recovery**: User refreshes or loads conversation history - sees full message in `GET /conversations/{id}/messages`

---

## Testing Strategy for Data Flows

### Unit Tests (Data Transformation)

**Test 1: Conversation creation produces valid thread_id**
```python
async def test_conversation_creation_produces_thread_id():
    # Create conversation via repository
    conversation = await conversation_repository.create(
        user_id="user_123",
        conversation_data=ConversationCreate(title="Test")
    )

    # Assert conversation has ID suitable for thread_id
    assert conversation.id is not None
    assert isinstance(conversation.id, str)
    assert len(conversation.id) > 0
```

**Test 2: Message transformation from ClientMessage to HumanMessage**
```python
async def test_process_input_creates_human_message():
    state = ConversationState(
        messages=[],
        conversation_id="conv_123",
        user_id="user_123",
        current_input="Hello"
    )

    result = await process_user_input(state)

    assert len(result["messages"]) == 1
    message = result["messages"][0]
    assert isinstance(message, HumanMessage)
    assert message.content == "Hello"
```

**Test 3: LLM response transformation to AIMessage**
```python
async def test_format_response_creates_ai_message():
    state = ConversationState(
        messages=[],
        conversation_id="conv_123",
        user_id="user_123",
        llm_response="I can help with that"
    )

    result = await format_response(state)

    assert len(result["messages"]) == 1
    message = result["messages"][0]
    assert isinstance(message, AIMessage)
    assert message.content == "I can help with that"
```

### Integration Tests (Multi-Database Flow)

**Test 4: Full conversation flow with checkpointing**
```python
async def test_complete_conversation_flow_with_checkpointing():
    # Setup: Create conversation in App DB
    conversation = await conversation_repository.create(
        user_id="user_123",
        conversation_data=ConversationCreate(title="Test Chat")
    )

    # Verify: No checkpoint exists yet
    config = {"configurable": {"thread_id": conversation.id}}
    state_before = await graph.get_state(config)
    assert state_before is None or state_before.values["messages"] == []

    # Execute: Run graph with input
    input_state = ConversationState(
        messages=[],
        conversation_id=conversation.id,
        user_id="user_123",
        current_input="What is Python?"
    )

    result_messages = []
    async for chunk in graph.astream(input_state, config):
        result_messages.extend(chunk["messages"])

    # Verify: Checkpoint created in LangGraph DB
    state_after = await graph.get_state(config)
    assert state_after is not None
    assert len(state_after.values["messages"]) == 2  # HumanMessage + AIMessage
    assert state_after.values["conversation_id"] == conversation.id

    # Verify: App DB unchanged
    conversation_updated = await conversation_repository.get_by_id(conversation.id)
    assert conversation_updated.title == "Test Chat"
    assert "message_count" not in conversation_updated.model_dump()
```

**Test 5: Message retrieval from LangGraph state**
```python
async def test_get_conversation_messages_from_langgraph():
    # Setup: Execute graph to create checkpoint with messages
    conversation = await conversation_repository.create(
        user_id="user_123",
        conversation_data=ConversationCreate(title="Test")
    )

    # Create state with 2 messages
    input_state = ConversationState(
        messages=[],
        conversation_id=conversation.id,
        user_id="user_123",
        current_input="Hello"
    )
    config = {"configurable": {"thread_id": conversation.id}}

    async for _ in graph.astream(input_state, config):
        pass  # Run to completion

    # Query: Retrieve messages via endpoint
    # (In real test: call HTTP GET endpoint)
    state = await graph.get_state(config)
    messages = state.values["messages"]

    # Verify: Messages come from LangGraph DB, not App DB
    assert len(messages) == 2
    assert isinstance(messages[0], HumanMessage)
    assert isinstance(messages[1], AIMessage)

    # Verify: App DB has NO messages collection
    app_db_messages = await app_db.messages.find_one()
    assert app_db_messages is None
```

**Test 6: Ownership check prevents unauthorized access**
```python
async def test_ownership_check_prevents_graph_execution():
    # Setup: Create conversation for user_123
    conversation = await conversation_repository.create(
        user_id="user_123",
        conversation_data=ConversationCreate(title="Private")
    )

    # Attempt: User_456 tries to run graph
    # (In real test: websocket message from different user)

    # Should fail at ownership check BEFORE graph execution
    with pytest.raises(AccessDenied):
        conversation_check = await conversation_repository.get_by_id(conversation.id)
        if conversation_check.user_id != "user_456":
            raise AccessDenied()

    # Verify: No checkpoint created for unauthorized user
    config = {"configurable": {"thread_id": conversation.id}}
    # Graph should NOT be executed by user_456 - verify via audit log or state history
```

### End-to-End Tests (WebSocket to Database)

**Test 7: WebSocket message flow end-to-end**
```python
async def test_websocket_message_flow_end_to_end():
    # Setup
    user = User(id="user_123", ...)
    conversation = await conversation_repository.create(
        user_id=user.id,
        conversation_data=ConversationCreate(title="E2E Test")
    )

    # Simulate WebSocket connection and message
    client_message = ClientMessage(
        conversation_id=conversation.id,
        content="Explain machine learning"
    )

    # Simulate websocket_handler logic
    config = {"configurable": {"thread_id": conversation.id}}
    input_state = ConversationState(
        messages=[],
        conversation_id=conversation.id,
        user_id=user.id,
        current_input=client_message.content
    )

    streamed_chunks = []
    async for chunk in graph.astream(input_state, config, stream_mode="values"):
        streamed_chunks.append(chunk)

    # Verify: Streamed tokens received
    assert len(streamed_chunks) > 0
    assert "messages" in streamed_chunks[-1]

    # Verify: State persisted in LangGraph DB
    final_state = await graph.get_state(config)
    assert len(final_state.values["messages"]) == 2

    # Verify: Can retrieve via GET endpoint
    messages_response = await client.get(f"/conversations/{conversation.id}/messages")
    assert messages_response.status_code == 200
    messages = messages_response.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"

    # Verify: App DB metadata intact
    conversation_check = await conversation_repository.get_by_id(conversation.id)
    assert conversation_check.title == "E2E Test"
```

### Data Independence Tests

**Test 8: LangGraph DB failure doesn't affect conversation listing**
```python
async def test_langgraph_db_failure_allows_conversation_listing():
    # Setup: Conversations in App DB
    conversation = await conversation_repository.create(
        user_id="user_123",
        conversation_data=ConversationCreate(title="Test")
    )

    # Simulate LangGraph DB down
    with mock.patch("app.infrastructure.langgraph.checkpointer.AsyncMongoDBSaver") as mock_saver:
        mock_saver.side_effect = ConnectionError("LangGraph DB unavailable")

        # Should still list conversations
        conversations = await conversation_repository.get_by_user_id("user_123")
        assert len(conversations) == 1
        assert conversations[0].title == "Test"

        # Should fail on graph execution
        with pytest.raises(ConnectionError):
            config = {"configurable": {"thread_id": conversation.id}}
            input_state = ConversationState(...)
            async for _ in graph.astream(input_state, config):
                pass
```

**Test 9: App DB failure prevents conversation access but not LangGraph queries**
```python
async def test_app_db_failure_blocks_ownership_check():
    # Setup: Checkpoint exists in LangGraph DB
    # (Simulated by creating checkpoint directly)

    # Simulate App DB down
    with mock.patch("app.adapters.outbound.repositories.mongo_conversation_repository.MongoConversationRepository") as mock_repo:
        mock_repo.get_by_id.side_effect = ConnectionError("App DB unavailable")

        # Should fail on ownership check
        with pytest.raises(ConnectionError):
            conversation_id = "conv_123"
            # Ownership check before graph execution
            conversation = await conversation_repository.get_by_id(conversation_id)
```

### Data Migration Tests

**Test 10: Migrate existing messages to LangGraph checkpoints**
```python
async def test_migration_existing_messages_to_langgraph_checkpoints():
    # Pre-refactor: Messages in App DB
    conversation = await conversation_repository.create(
        user_id="user_123",
        conversation_data=ConversationCreate(title="Old Conversation")
    )

    # Manually insert old messages into temporary collection
    old_messages = [
        MessageCreate(conversation_id=conversation.id, role="user", content="Old message 1"),
        MessageCreate(conversation_id=conversation.id, role="assistant", content="Old response 1"),
    ]

    # Run migration script (to be implemented)
    await migrate_messages_to_langgraph_checkpoints(conversation.id, old_messages)

    # Verify: Checkpoint created with migrated messages
    config = {"configurable": {"thread_id": conversation.id}}
    state = await graph.get_state(config)
    assert len(state.values["messages"]) == 2
    assert state.values["messages"][0].content == "Old message 1"
    assert state.values["messages"][1].content == "Old response 1"

    # Verify: Can retrieve via new endpoint
    messages_response = await client.get(f"/conversations/{conversation.id}/messages")
    assert len(messages_response.json()) == 2
```

---

## Implementation Guidance: Phase-by-Phase

### Phase 1: Infrastructure Setup (Days 1-2)

**Database Configuration**
1. Add dual MongoDB connection support to `backend/app/infrastructure/database/mongodb.py`
   - Keep existing connection as App DB
   - Add new connection for LangGraph DB
   - Handle both async connections properly

2. Create `backend/app/infrastructure/langgraph/checkpointer.py`
   - Implement `AsyncMongoDBSaver` wrapper using `langgraph-checkpoint-mongodb`
   - Configure connection to LangGraph DB
   - Add error handling for checkpoint failures

**Environment Setup**
3. Update `.env.example` with `MONGODB_LANGGRAPH_URI`
4. Update `docker-compose.yml` to support dual MongoDB instances (for local development)

**Test Coverage**: Unit tests for connection setup, checkpointer initialization

### Phase 2: State & Domain Model Updates (Days 2-3)

**Replace Custom State**
1. Update `backend/app/langgraph/state.py`
   - Replace `ConversationState` custom TypedDict with `MessagesState` from langgraph
   - Keep conversation_id and user_id fields
   - Test that add_messages reducer works correctly

**Update Domain Models**
2. Modify `backend/app/core/domain/conversation.py`
   - Remove `message_count` field
   - Update docstrings to clarify messages stored in LangGraph DB

3. Mark `backend/app/core/domain/message.py` for deletion (plan deletion, don't delete yet)
   - Keep `MessageRole` enum temporarily (may be needed for migration)

**Test Coverage**: Unit tests for state transformation, type checking

### Phase 3: Graph Updates (Days 3-4)

**Update Nodes**
1. Update `backend/app/langgraph/nodes/process_input.py`
   - Replace `Message(role=MessageRole.USER)` with `HumanMessage`
   - Import from `langchain_core.messages`
   - Test input validation still works

2. Update `backend/app/langgraph/nodes/format_response.py`
   - Replace `Message(role=MessageRole.ASSISTANT)` with `AIMessage`
   - Test response formatting still works

3. Delete `backend/app/langgraph/nodes/save_history.py`
   - Remove all save_history node code
   - Add comment explaining checkpointer handles this

**Update Graph Compilation**
4. Update `backend/app/langgraph/graphs/chat_graph.py`
   - Accept `checkpointer` as parameter (DI)
   - Compile with `checkpointer=checkpointer`
   - Remove `save_history` node from graph
   - Test compilation succeeds with and without checkpointer

5. Update `backend/app/langgraph/graphs/streaming_chat_graph.py`
   - Same changes as chat_graph.py

**Test Coverage**:
- Unit tests for each node with native message types
- Integration tests for graph compilation with checkpointer
- Streaming tests to verify token flow works

### Phase 4: Repository Updates (Days 4-5)

**Update Conversation Repository**
1. Remove `increment_message_count()` method from port interface
2. Update MongoDB adapter to remove implementation
3. Update any code calling this method

**Remove Message Repository**
2. Delete message repository port and adapter
   - This is the big breaking change
   - Update imports throughout codebase

**Update Repository Tests**
3. Remove tests for message persistence
4. Update conversation tests to not expect message_count

**Test Coverage**:
- Unit tests for remaining repository methods
- Integration tests for conversation CRUD without message_count

### Phase 5: WebSocket Refactor (Days 5-6)

**Update Handler**
1. Rewrite `backend/app/adapters/inbound/websocket_handler.py`
   - Keep ownership check against App DB
   - Remove manual message persistence code (lines 125-126, 139-148)
   - Replace `llm_provider.stream()` with `graph.astream()`
   - Pass `config = {"configurable": {"thread_id": conversation_id}}`
   - Handle checkpoint failures gracefully

**Update Router**
2. Update `backend/app/adapters/inbound/websocket_router.py`
   - Inject checkpointer instead of message_repository
   - Update dependency injection pattern

**Test Coverage**:
- Unit tests for ownership check still works
- Integration tests for full WebSocket flow with checkpointing
- Tests for error handling (checkpoint failures, LLM failures)

### Phase 6: API Endpoint Updates (Days 6-7)

**Update Message Endpoint**
1. Refactor `backend/app/adapters/inbound/message_router.py`
   - Replace message_repository query with graph.get_state()
   - Convert BaseMessage objects to MessageResponse DTOs
   - Keep ownership verification
   - Test pagination (get_state returns full history by default)

**Update Conversation Endpoints**
2. Review `backend/app/adapters/inbound/conversation_router.py`
   - Ensure create_conversation still works
   - Remove any message count increment calls
   - List conversations still queries App DB only (correct)

**Test Coverage**:
- Unit tests for message retrieval from state
- Integration tests for message pagination
- E2E tests for full conversation lifecycle

### Phase 7: Use Case Cleanup (Days 7-8)

**Delete/Update Use Cases**
1. Delete `backend/app/core/use_cases/send_message.py`
   - Logic now distributed in graph nodes + WebSocket handler

2. Delete `backend/app/core/use_cases/get_conversation_history.py`
   - Logic now in message_router (calls graph.get_state())

3. Keep `backend/app/core/use_cases/create_conversation.py`
   - No changes needed

**Test Coverage**:
- Verify no code references deleted use cases
- Update any use case tests

### Phase 8: Testing & Data Migration (Days 8-10)

**Comprehensive Testing**
1. Unit tests (80% minimum coverage)
   - State transformations
   - Node functions with native messages
   - Graph compilation

2. Integration tests
   - Full conversation flow with checkpointing
   - Message retrieval from state
   - Ownership checks
   - Database independence
   - Error scenarios

3. E2E tests
   - WebSocket chat end-to-end
   - Frontend compatibility (no API changes for clients)

**Data Migration (Optional - depends on existing data)**
4. Create migration script
   - Migrate existing messages from App DB to LangGraph checkpoints
   - Map conversation.id to thread_id
   - Verify migration completeness

**Test Coverage**: >80% overall, all new paths covered

### Phase 9: Documentation (Days 10-11)

**Update Project Docs**
1. Update `/doc/general/ARCHITECTURE.md`
   - Add diagram showing two-database pattern
   - Explain LangGraph-first principle
   - Document conversation.id ↔ thread_id mapping

2. Update `/doc/general/DEVELOPMENT.md`
   - Local setup with two MongoDB URIs
   - How to add new graph nodes
   - How to add tools/memory stores

3. Add inline code comments
   - Explain checkpointer pattern
   - Clarify hexagonal vs LangGraph responsibilities

**Test Coverage**: Documentation reviews, manual testing checklist

### Phase 10: Code Review & Deployment (Days 11-12)

**Pre-Merge**
1. Code review by Pablo
2. CI/CD checks pass
3. Manual testing checklist completed

**Post-Merge**
1. Monitor logs for checkpointer issues
2. Verify LangGraph DB performance
3. Celebrate LangGraph-first architecture achieved!

---

## Risks and Considerations

### Risk 1: Checkpoint Size Growth (Mitigation: Archival Strategy)

**Risk**: LangGraph checkpoints grow unbounded as conversations get longer

**Manifestation**:
```
Year 1: conversations with 100-500 messages = normal
Year 5: power users with 10,000+ messages per conversation = massive checkpoints
```

**Mitigation Strategy**:
```python
# Implement checkpoint pruning:
1. Set MongoDB TTL index on langgraph_checkpoints after 90 days
2. Archive old checkpoints to separate collection
3. Keep recent N checkpoints per thread

# In checkpointer configuration:
checkpointer = AsyncMongoDBSaver(
    db_connection=langgraph_db,
    collection="langgraph_checkpoints",
    ttl_days=90,  # Auto-delete after 90 days
    keep_recent=100  # Keep 100 most recent checkpoints per thread
)
```

**Monitoring**:
- Alert if average checkpoint size > 10MB
- Track checkpoint creation rate per thread
- Monitor LangGraph DB disk usage

### Risk 2: Dual Database Consistency Window

**Risk**: App DB and LangGraph DB can be out of sync for brief moments

**Scenario 1: Conversation created but user never sends message**
- App DB: Conversation exists
- LangGraph DB: No checkpoint
- Window: Until first message sent
- Impact: Benign - first message creates checkpoint
- Mitigation: None needed, acceptable eventual consistency

**Scenario 2: Checkpoint created while App DB has stale connection**
- Thread 1: Create checkpoint in LangGraph DB ✓
- Thread 2: Query conversation from App DB (sees old version)
- Window: Milliseconds
- Impact: User sees stale title
- Mitigation: Refresh conversation metadata before serving to client

**Scenario 3: Conversation deleted from App DB but checkpoint exists**
- App DB: Conversation deleted
- LangGraph DB: Checkpoint still exists
- Window: Until cleanup runs
- Impact: Checkpoint orphaned, wastes space
- Mitigation: Implement cascading delete, archive old checkpoints

**General Mitigation**:
```python
# Always verify consistency on critical operations:
@app.on_event("startup")
async def verify_consistency():
    """Periodically verify App DB ↔ LangGraph DB consistency"""
    # Find orphaned checkpoints (no conversation in App DB)
    # Find conversations without initial checkpoints
    # Log mismatches for manual review
```

### Risk 3: Message Deduplication in Stream-Based State Reducer

**Risk**: LangGraph's `add_messages` reducer might not handle duplicates correctly

**Scenario**:
```
Message arrives at WebSocket
  → process_input creates HumanMessage
  → add_messages reducer processes it
  → Checkpoint saved

User resends same message (duplicate detection failure)
  → New HumanMessage created
  → add_messages reducer... keeps both? or dedupes?
```

**Testing Required**:
```python
async def test_add_messages_reducer_deduplication():
    state = ConversationState(
        messages=[HumanMessage(content="Hello")],
        conversation_id="conv_123"
    )

    # Attempt to add duplicate
    updates = {"messages": [HumanMessage(content="Hello")]}
    new_messages = add_messages(state["messages"], updates["messages"])

    # Verify: No duplicates
    assert len(new_messages) == 1
    assert new_messages[0].content == "Hello"
```

**Mitigation**: Test `add_messages` behavior thoroughly before production, consider message ID uniqueness

### Risk 4: WebSocket Connection Loss During Graph Execution

**Risk**: User disconnects while graph is executing (tokens partially streamed)

**Scenario**:
```
Graph executing, streaming tokens
  ├─ Token 1-50: sent successfully
  ├─ Token 51: WebSocket write fails (connection lost)
  ├─ Tokens 52-N: not sent
  └─ Graph continues to completion
  └─ Checkpoint saved with FULL message
```

**Impact**: Server has full message, client never saw complete response

**Mitigation**:
```python
async for chunk in graph.astream(input_state, config):
    try:
        await websocket.send_text(json.dumps(chunk))
    except ConnectionError:
        logger.warning(f"WebSocket disconnected during streaming")
        # Continue graph execution? Or cancel?
        # Option 1: Continue (state fully saved, client can refresh)
        # Option 2: Cancel remaining tokens (but checkpoint still saved)
        # Recommended: Continue (robustness over efficiency)
        continue
```

**Testing**:
```python
async def test_websocket_disconnect_during_streaming():
    # Simulate connection loss mid-stream
    # Verify: Graph execution completes
    # Verify: Checkpoint saved
    # Verify: Client-side recovery works (refresh loads full message)
```

### Risk 5: Performance: Two Database Queries on Message Retrieval

**Risk**: Message retrieval requires graph.get_state() from LangGraph DB (could be slow)

**Scenario**:
```
GET /conversations/{id}/messages
  → Verify ownership (App DB query) - fast
  → Get state (LangGraph DB query) - potentially slow if checkpoint large
  → Return messages to client
```

**Mitigation Strategies**:
```python
# Strategy 1: Pagination within state
state = await graph.get_state(config)
all_messages = state.values["messages"]
paginated = all_messages[skip:skip+limit]
return paginated

# Strategy 2: Caching layer (future enhancement)
# Add Redis cache for recent message lists
# Invalidate on new graph execution

# Strategy 3: Message streaming endpoint (future enhancement)
# For very long conversations, stream messages instead of returning all
```

**Monitoring**:
- Track GET /messages response time
- Alert if > 1 second (indicates performance issues)
- Monitor LangGraph DB query performance

### Risk 6: TypedDict vs Pydantic State Validation

**Risk**: Switching from Pydantic `Message` domain model to `HumanMessage`/`AIMessage` loses validation

**Current** (Pydantic validation):
```python
class Message(BaseModel):
    content: str = Field(..., min_length=1)  # Validated

# When creating: Message(content="") raises ValidationError
```

**Target** (LangChain types):
```python
human_message = HumanMessage(content="")  # No validation!
```

**Mitigation**:
```python
# Validate BEFORE creating message:
async def process_user_input(state: ConversationState) -> dict:
    current_input = state.get("current_input", "").strip()

    if not current_input:  # Explicit validation
        return {"error": "Input cannot be empty"}

    # Now safe to create message
    human_message = HumanMessage(content=current_input)
    return {"messages": [human_message]}
```

**Testing**: Ensure input validation tests still pass with new message types

### Risk 7: Dependency Injection Complexity

**Risk**: Graph compilation needs checkpointer at runtime (new dependency)

**Current Pattern** (in chat_graph.py):
```python
def create_chat_graph(
    llm_provider: ILLMProvider,
    message_repository: IMessageRepository,
    conversation_repository: IConversationRepository
):
    # 3 dependencies
```

**Target Pattern**:
```python
def create_chat_graph(
    llm_provider: ILLMProvider,
    checkpointer: AsyncMongoDBSaver
):
    # 2 dependencies, but checkpointer is internal
```

**Mitigation**:
```python
# Create single function to initialize graph:
async def initialize_graph() -> Graph:
    """Initialize compiled graph with all dependencies"""

    llm_provider = get_llm_provider()  # From config
    checkpointer = get_langgraph_checkpointer()  # From infrastructure

    return create_chat_graph(llm_provider, checkpointer)

# WebSocket router uses pre-initialized graph:
graph = await initialize_graph()  # On startup
```

**Testing**: Test graph initialization with all dependency combinations

### Risk 8: Migration Path for Existing Conversations

**Risk**: Existing conversations in App DB have messages that need migrating

**Challenge**:
```
Old conversation.id: "507f1f77bcf86cd799439012" (in App DB)
Old messages: In messages collection
New home: LangGraph checkpoint with thread_id: "507f1f77bcf86cd799439012"
```

**Migration Strategy**:
```python
async def migrate_conversation_to_langgraph(conversation_id: str):
    """Migrate old messages to LangGraph checkpoint"""

    # 1. Get conversation from App DB
    conversation = await conversation_repository.get_by_id(conversation_id)

    # 2. Get old messages from temporary collection
    old_messages = await get_old_messages(conversation_id)

    # 3. Convert to native LangGraph messages
    native_messages = []
    for msg in old_messages:
        if msg.role == "user":
            native_messages.append(HumanMessage(content=msg.content))
        else:
            native_messages.append(AIMessage(content=msg.content))

    # 4. Create initial checkpoint in LangGraph DB
    config = {"configurable": {"thread_id": conversation.id}}
    state = ConversationState(
        messages=native_messages,
        conversation_id=conversation.id,
        user_id=conversation.user_id
    )
    await checkpointer.put(config, state)

    # 5. Verify migration
    migrated_state = await graph.get_state(config)
    assert len(migrated_state.values["messages"]) == len(native_messages)

    # 6. Mark old messages as migrated (or delete)
    await mark_messages_migrated(conversation_id)
```

**Testing**: Test migration with various conversation sizes and edge cases

---

## Summary of Key Changes

### What Gets Deleted
1. `backend/app/core/ports/message_repository.py` - Interface gone
2. `backend/app/adapters/outbound/repositories/mongo_message_repository.py` - Implementation gone
3. `MessageDocument` from `mongo_models.py` - Database entity gone
4. `backend/app/langgraph/nodes/save_history.py` - Node gone (checkpointer does this)
5. `backend/app/core/domain/message.py` - Custom domain model gone (except MessageRole)
6. `backend/app/core/use_cases/send_message.py` - Use case gone
7. `backend/app/core/use_cases/get_conversation_history.py` - Use case gone

### What Gets Updated (Major)
1. `backend/app/langgraph/state.py` - Replace ConversationState with MessagesState
2. `backend/app/langgraph/graphs/chat_graph.py` - Add checkpointer, remove save_history node
3. `backend/app/langgraph/nodes/process_input.py` - Use HumanMessage instead of Message
4. `backend/app/langgraph/nodes/format_response.py` - Use AIMessage instead of Message
5. `backend/app/adapters/inbound/websocket_handler.py` - Call graph.astream() instead of llm_provider.stream()
6. `backend/app/adapters/inbound/message_router.py` - Query graph.get_state() instead of repository
7. `backend/app/core/domain/conversation.py` - Remove message_count field
8. `backend/app/adapters/outbound/repositories/mongo_conversation_repository.py` - Remove increment_message_count()
9. `backend/app/infrastructure/database/mongodb.py` - Add dual connection support

### What Gets Created (New)
1. `backend/app/infrastructure/langgraph/checkpointer.py` - AsyncMongoDBSaver setup
2. `backend/app/infrastructure/langgraph/__init__.py` - Package init

### What Stays Mostly Unchanged
1. `backend/app/core/use_cases/create_conversation.py` - App DB conversation creation
2. `backend/app/adapters/inbound/conversation_router.py` - Conversation REST endpoints
3. `backend/app/core/ports/conversation_repository.py` - Interface stays (method removal only)
4. `backend/app/adapters/outbound/repositories/mongo_models.py` - ConversationDocument stays (field removal only)
5. `backend/app/adapters/inbound/websocket_router.py` - Routing stays (DI change only)

---

## Data Flow Comparison Table

| Aspect | Current Pattern | New Pattern |
|--------|-----------------|------------|
| **Message Persistence** | Manual via `message_repository.create()` | Automatic via LangGraph checkpointer |
| **Message Retrieval** | Query MongoDB `messages` collection | Query LangGraph state via `graph.get_state()` |
| **LLM Invocation** | Direct: `llm_provider.stream(messages)` | Via graph: `graph.astream(input, config)` |
| **Conversation State** | Custom `ConversationState` TypedDict | Native `MessagesState` from LangGraph |
| **Message Types** | Custom `Message` domain model | Native `HumanMessage`, `AIMessage` from LangChain |
| **State Persistence** | Manual: 3 separate DB operations | Atomic: 1 checkpoint operation |
| **Message Count** | Field in Conversation model | Not needed (count from state.messages length) |
| **Ownership Check** | Same (App DB query before operation) | Same (App DB query before operation) |
| **DB Separation** | All data in one App DB | Metadata in App DB, state in LangGraph DB |
| **Thread/Conversation Link** | N/A | `conversation.id` ← → `thread_id` mapping |
| **Checkpointing** | None | Full graph state persisted after each execution |
| **Time-Travel** | Not possible | Possible via `graph.get_state_history()` |
| **Error Recovery** | Partial state on failure | State rolled back to last checkpoint |

---

## Conclusion

The refactor transforms Genesis from fighting LangGraph's design into embracing it as a first-class workflow layer. By separating App DB (metadata) from LangGraph DB (AI state), the architecture becomes clearer, more maintainable, and unlocks advanced LangGraph features like checkpointing, human-in-the-loop, and time-travel debugging.

**Key architectural principle**: LangGraph owns conversation state. Hexagonal architecture owns infrastructure and user identity.

The mapping of `conversation.id` to `thread_id` creates a clean bridge between the two worlds, enabling independent scaling and failure isolation while maintaining strong ownership verification.

