# Backend Hexagonal Architecture Analysis: LangGraph-First Refactor

## Request Summary

The Genesis application is currently structured as a traditional hexagonal architecture where LangGraph is treated as an infrastructure component (outbound adapter). The proposed refactor inverts this relationship: **LangGraph becomes a primary first-class layer**, with a clear separation between:

1. **Hexagonal Application Layer** - Manages app metadata (users, auth, conversation ownership, settings) in MongoDB
2. **LangGraph Layer** - Manages AI workflow state in LangGraph's checkpointer database, with conversation.id mapped to LangGraph's thread_id

This analysis examines how the current hexagonal boundaries must evolve to support this architectural shift while maintaining clean separation of concerns.

## Relevant Files & Modules

### Files to Delete (Message-related infrastructure)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/message.py` - Message domain model (moving to LangGraph)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/message_repository.py` - IMessageRepository port interface
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_message_repository.py` - MongoDB message implementation
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_router.py` - REST message endpoints (no longer needed)

### Files to Modify (Conversation & domain models)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/conversation.py` - Reduce to conversation metadata only (user_id, title, created_at, updated_at)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/conversation_repository.py` - Remove message_count increment; keep conversation ownership checks
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_conversation_repository.py` - Remove increment_message_count method
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_models.py` - Remove MessageDocument; update ConversationDocument (remove message_count field)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/conversation_router.py` - Remove message_count from responses
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - Refactor to use LangGraph executor instead of manual message saving
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_router.py` - Update dependency injection for LangGraph graph
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py` - Update lifespan to initialize LangGraph checkpointer

### Files to Modify (LangGraph layer)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - Update ConversationState to include thread_id mapping
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Remove save_to_history node; let checkpointer handle persistence
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/save_history.py` - DELETE (checkpointer handles this)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - Keep but ensure no direct message repository access
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/process_input.py` - Keep; works with state messages
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/format_response.py` - Keep; formats responses into state

### Files to Create (LangGraph infrastructure)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/checkpointer/__init__.py` - Checkpointer setup module
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/checkpointer/mongodb_checkpointer.py` - Custom MongoDB-based checkpointer implementation (NEW)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/checkpointer.py` - ICheckpointer port interface (for abstraction)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/langgraph/__init__.py` - LangGraph initialization utilities
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/langgraph/graph_factory.py` - Factory for creating/retrieving graph executors (NEW)

### Files to Modify (Use cases & adapters)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/use_cases/send_message.py` - MODIFY or DELETE (logic moves to WebSocket handler with LangGraph)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/use_cases/get_conversation_history.py` - MODIFY to fetch from LangGraph checkpointer instead

### Key Configuration Files
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py` - May need new LangGraph checkpointer configuration

---

## Current Architecture Overview

### Hexagonal Layer Structure (As It Exists Today)

```
┌────────────────────────────────────────────────────────────┐
│                    INBOUND ADAPTERS                        │
│  (FastAPI routers: REST API, WebSocket)                   │
│  - conversation_router.py                                 │
│  - message_router.py                                      │
│  - websocket_router.py → websocket_handler.py            │
└─────────────────────┬──────────────────────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────────────┐
│                    CORE DOMAIN                             │
│  - Domain Models: Conversation, Message                   │
│  - Ports: IConversationRepository, IMessageRepository      │
│  - Use Cases: CreateConversation, SendMessage             │
└─────────────────────┬──────────────────────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────────────┐
│                  OUTBOUND ADAPTERS                         │
│  - MongoDB: MongoConversationRepository,                  │
│    MongoMessageRepository                                 │
│  - LLM Providers: OpenAI, Anthropic, Gemini, Ollama       │
│  - LangGraph: graph orchestration (currently treated as   │
│    infrastructure, not primary)                           │
└─────────────────────────────────────────────────────────────┘
```

### Current Data Flow (Message Persistence)

Today, message persistence happens in the hexagonal layer:

```
1. WebSocket receives message
   ↓
2. websocket_handler.py:
   - Validates via conversation_repository (hexagonal)
   - Creates Message object (domain model)
   - Saves to message_repository (hexagonal port)
   - Calls llm_provider.stream() (hexagonal port)
   - Saves assistant response via message_repository
   ↓
3. MongoMessageRepository writes to MongoDB "messages" collection
```

LangGraph is used for orchestration but doesn't persist state. The `save_to_history` node manually saves messages to MongoDB.

### Current Domain Models

**Conversation** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/conversation.py`):
- `id` - Conversation unique identifier
- `user_id` - Owner (critical for authorization)
- `title` - Conversation title
- `created_at`, `updated_at` - Timestamps
- `message_count` - Total messages (metadata only)

**Message** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/message.py`):
- `id` - Message unique identifier
- `conversation_id` - Which conversation
- `role` - user/assistant/system
- `content` - Message text
- `created_at` - Timestamp
- `metadata` - Optional additional data

### Current Ports (Interfaces)

**IConversationRepository** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/conversation_repository.py`):
```python
async def create(user_id, conversation_data) -> Conversation
async def get_by_id(conversation_id) -> Conversation
async def get_by_user_id(user_id, skip, limit) -> List[Conversation]
async def update(conversation_id, conversation_data) -> Conversation
async def delete(conversation_id) -> bool
async def increment_message_count(conversation_id, count) -> Conversation
```

**IMessageRepository** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/message_repository.py`):
```python
async def create(message_data) -> Message
async def get_by_id(message_id) -> Message
async def get_by_conversation_id(conversation_id, skip, limit) -> List[Message]
async def delete(message_id) -> bool
async def delete_by_conversation_id(conversation_id) -> int
```

**ILLMProvider** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py`):
```python
async def generate(messages: List[Message]) -> str
async def stream(messages: List[Message]) -> AsyncGenerator[str, None]
async def get_model_name() -> str
```

---

## Impact Analysis: LangGraph-First Refactor

### How the Architecture Must Change

#### 1. Message Persistence Model Shift

**Current Model:**
- Messages stored in MongoDB `messages` collection
- IMessageRepository handles all message CRUD
- Use case `SendMessage` orchestrates: save user message → call LLM → save response

**New Model:**
- Message history lives in LangGraph's checkpointer database
- LangGraph's `ConversationState.messages` is the source of truth for history
- Conversation metadata (ownership, title) remains in MongoDB
- Mapping: `conversation.id` (MongoDB) ↔ `thread_id` (LangGraph)

#### 2. Hexagonal Layer Split

**Application Hexagon (Remains):**
- **Domain**: User, Conversation (metadata only)
- **Ports**: IConversationRepository, IUserRepository, IAuthService, ILLMProvider
- **Adapters**: FastAPI routers, MongoDB repositories for users/conversations
- **Responsibility**: Authentication, authorization, conversation metadata management

**LangGraph Layer (Becomes Primary):**
- **Not** treated as an outbound adapter anymore
- **Is** a first-class orchestration layer
- Contains its own state schema (ConversationState)
- Has its own persistence (checkpointer)
- Handles all AI workflow logic and message state
- The WebSocket adapter delegates to LangGraph graph executor

#### 3. Authorization Boundary Preservation

**Critical**: User ownership checks must stay in the hexagonal layer:

```python
# In conversation_router.py (inbound adapter):
conversation = await conversation_repository.get_by_id(conversation_id)
if conversation.user_id != current_user.id:
    raise HTTPException(403, "Access denied")

# In websocket_handler.py (inbound adapter):
conversation = await conversation_repository.get_by_id(conversation_id)
if not conversation or conversation.user_id != user.id:
    raise error

# After this check, we SAFELY invoke LangGraph:
result = await graph.ainvoke(
    {"current_input": user_message, "thread_id": conversation.id},
    config={"configurable": {"thread_id": conversation.id}}
)
```

The hexagonal layer acts as a "permission gate" before LangGraph executes.

#### 4. Dependency Inversion Patterns

**Current Pattern (Message repositories):**
```
WebSocket Handler → IMessageRepository (port)
                 → MongoMessageRepository (adapter)
                 → MongoDB
```

**New Pattern (LangGraph):**
```
WebSocket Handler → LangGraph Graph (first-class orchestrator)
                 → LangGraph Checkpointer (infrastructure)
                 → MongoDB (messages collection renamed or new DB)
```

The key difference: LangGraph is NOT abstracted behind a hexagonal port because:
- It's the primary orchestration engine, not a replaceable component
- Its state schema (ConversationState) is integral to the system design
- Multiple implementations of LangGraph make no architectural sense

---

## Architectural Recommendations

### 1. Proposed Domain Model Changes

**Conversation (Keep in Hexagonal):**
```python
# /Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/conversation.py
class Conversation(BaseModel):
    id: Optional[str]  # MongoDB _id, also used as thread_id
    user_id: str       # CRITICAL: Used for authorization
    title: str         # Conversation title
    created_at: datetime
    updated_at: datetime
    # REMOVE: message_count (LangGraph manages this)
```

**Message (DELETE from hexagonal, move to LangGraph):**
- Delete `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/message.py`
- The Message concept now lives only in `ConversationState.messages`
- LangGraph handles message role, content, and timestamps

### 2. Proposed Port Changes

**Keep IConversationRepository, but simplify:**
```python
# /Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/conversation_repository.py
class IConversationRepository(ABC):
    @abstractmethod
    async def create(self, user_id: str, conversation_data: ConversationCreate) -> Conversation:
        pass

    @abstractmethod
    async def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: str, skip: int = 0, limit: int = 100) -> List[Conversation]:
        pass

    @abstractmethod
    async def update(self, conversation_id: str, conversation_data: ConversationUpdate) -> Optional[Conversation]:
        pass

    @abstractmethod
    async def delete(self, conversation_id: str) -> bool:
        pass

    # REMOVE increment_message_count - LangGraph manages message count
```

**Delete IMessageRepository entirely:**
- No hexagonal port needed for messages
- Messages live in LangGraph state and checkpointer

### 3. Proposed LangGraph Checkpointer Interface

Create a new port to abstract checkpointer implementation (optional but recommended):

```python
# /Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/langgraph_checkpointer.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from langgraph.checkpoint.base import BaseCheckpointStorage

class ILangGraphCheckpointer(ABC):
    """Port interface for LangGraph checkpointer implementations."""

    @abstractmethod
    async def get_storage(self) -> BaseCheckpointStorage:
        """Get the configured checkpoint storage."""
        pass
```

**Adapter Implementation:**
```python
# /Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/langgraph/mongodb_checkpointer.py
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver

class MongoDBCheckpointerAdapter(ILangGraphCheckpointer):
    """MongoDB-based checkpointer for LangGraph state persistence."""

    async def get_storage(self) -> BaseCheckpointStorage:
        client = AsyncMongoClient(settings.mongodb_url)
        return AsyncMongoDBSaver(
            client=client,
            db_name=settings.mongodb_db,
            collection_name="langgraph_checkpoints"
        )
```

### 4. Proposed LangGraph State Update

Update `ConversationState` to include mapping information:

```python
# /Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py
from typing import Annotated, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

class ConversationState(TypedDict):
    """
    State schema for conversation flow in LangGraph.

    Mapping: Conversation.id (MongoDB) = thread_id (LangGraph)
    """
    # Message history (persisted by checkpointer)
    messages: Annotated[list, add_messages]

    # Conversation context
    conversation_id: str  # Maps to LangGraph thread_id
    user_id: str          # For authorization checks

    # Current processing
    current_input: Optional[str]
    llm_response: Optional[str]
    error: Optional[str]
```

### 5. Proposed Graph Structure

Update the chat graph to use checkpointer, remove save_to_history node:

```python
# /Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.base import BaseCheckpointStorage

def create_chat_graph(
    llm_provider: ILLMProvider,
    checkpointer: BaseCheckpointStorage
):
    """
    Create the chat graph with checkpointer persistence.

    Flow:
    1. START → process_input: Validate user input
    2. process_input → call_llm (or END): Invoke LLM
    3. call_llm → format_response: Format LLM output
    4. format_response → END: Complete

    Note: Message persistence is automatic via checkpointer.
    No explicit save_to_history node needed.
    """
    graph_builder = StateGraph(ConversationState)

    graph_builder.add_node("process_input", process_user_input)
    graph_builder.add_node("call_llm", lambda state: call_llm(state, llm_provider))
    graph_builder.add_node("format_response", format_response)

    graph_builder.add_edge(START, "process_input")
    graph_builder.add_conditional_edges(
        "process_input",
        should_continue,
        {"call_llm": "call_llm", "end": END}
    )
    graph_builder.add_edge("call_llm", "format_response")
    graph_builder.add_edge("format_response", END)

    # Compile with checkpointer for automatic state persistence
    graph = graph_builder.compile(checkpointer=checkpointer)
    return graph
```

### 6. WebSocket Handler Refactoring

The WebSocket handler becomes a thin adapter that delegates to LangGraph:

```python
# /Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py
async def handle_websocket_chat(
    websocket: WebSocket,
    user: User,
    graph: CompiledGraph,  # Injected LangGraph graph executor
    conversation_repository: IConversationRepository
):
    """
    Handle WebSocket chat with LangGraph orchestration.

    Responsibility:
    1. Authenticate user and check conversation ownership (hexagonal)
    2. Stream messages from/to client
    3. Delegate AI logic to LangGraph graph
    4. Handle streaming responses
    """
    await manager.connect(websocket, user.id)

    try:
        while True:
            data = await websocket.receive_text()
            client_message = ClientMessage.model_validate(json.loads(data))
            conversation_id = client_message.conversation_id

            # AUTHORIZATION CHECK (stays in hexagonal)
            conversation = await conversation_repository.get_by_id(conversation_id)
            if not conversation or conversation.user_id != user.id:
                await send_error(websocket, "Access denied")
                continue

            # DELEGATE TO LANGGRAPH (now primary orchestrator)
            try:
                async for event in graph.astream_events(
                    {"current_input": client_message.content},
                    config={"configurable": {"thread_id": conversation_id}},
                    stream_mode="values"
                ):
                    if event["event"] == "on_chat_model_stream":
                        # Stream token to client
                        token = event["data"]["chunk"]["content"]
                        await send_token(websocket, token)

                    elif event["event"] == "on_chain_end":
                        # Conversation complete
                        final_state = event["data"]["output"]
                        await send_complete(websocket, final_state)

            except Exception as e:
                await send_error(websocket, str(e))

    finally:
        manager.disconnect(user.id)
```

### 7. Dependency Injection Pattern

Update the application to inject LangGraph graph at startup:

```python
# /Users/pablolozano/Mac Projects August/genesis/backend/app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Genesis")

    # Setup hexagonal layer database
    from app.adapters.outbound.repositories.mongo_models import (
        UserDocument, ConversationDocument
    )
    await MongoDB.connect([UserDocument, ConversationDocument])

    # Setup LangGraph checkpointer
    checkpointer = await initialize_langgraph_checkpointer()
    app.state.langgraph_checkpointer = checkpointer

    # Initialize LangGraph graph
    llm_provider = get_llm_provider()
    graph = create_chat_graph(llm_provider, checkpointer)
    app.state.langgraph_graph = graph

    logger.info("Application startup complete")
    yield

    logger.info("Shutting down")
    await MongoDB.close()
    logger.info("Application shutdown complete")
```

### 8. Authorization Boundary Preservation

The critical pattern: **Hexagonal authorization checks must execute before LangGraph invocation**

```
┌─────────────────────────────────────────────┐
│     WebSocket Request (Inbound Adapter)     │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│  1. Authenticate User (JWT validation)      │
│     Already done by get_user_from_websocket │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│  2. Check Conversation Ownership            │
│     conversation_repository.get_by_id()     │
│     if conversation.user_id != user.id:     │
│         DENY ACCESS                         │
│     (This is HEXAGONAL authorization)       │
└────────────────┬────────────────────────────┘
                 │
                 ▼ (Only after auth check)
┌─────────────────────────────────────────────┐
│  3. Invoke LangGraph with thread_id         │
│     graph.ainvoke({...}, config={...})      │
│     (This is LANGGRAPH orchestration)       │
└─────────────────────────────────────────────┘
```

**Key Principle**: Authorization is NOT delegated to LangGraph. It remains in the hexagonal boundary.

### 9. Breaking Down the Refactor by Files

#### Phase 1: Create LangGraph Infrastructure
1. Create `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/checkpointer/mongodb_checkpointer.py`
2. Create `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/langgraph/graph_factory.py`

#### Phase 2: Update LangGraph Layer
1. Update `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - add thread_id mapping
2. Update `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - add checkpointer, remove save_to_history node
3. Delete `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/save_history.py`

#### Phase 3: Update Hexagonal Layer (Domain)
1. Update `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/conversation.py` - remove message_count
2. Update `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/conversation_repository.py` - remove increment_message_count
3. Delete `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/message.py`
4. Delete `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/message_repository.py`

#### Phase 4: Update Adapters
1. Update `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_conversation_repository.py` - remove increment_message_count
2. Update `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_models.py` - remove MessageDocument, message_count from ConversationDocument
3. Delete `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_message_repository.py`
4. Update `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/conversation_router.py` - remove message_count
5. Update `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - refactor to use graph.astream_events()
6. Update `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_router.py` - inject graph instead of repositories
7. Delete `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_router.py`

#### Phase 5: Update Main Application
1. Update `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py` - initialize checkpointer and graph in lifespan

#### Phase 6: Update/Delete Use Cases
1. Delete or significantly refactor `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/use_cases/send_message.py` (logic moves to WebSocket handler)
2. Update `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/use_cases/get_conversation_history.py` - fetch from LangGraph checkpointer instead

---

## Implementation Guidance

### Step 1: Establish Clear Boundaries

Define these principles in code comments:

```python
# Hexagonal Layer (app/core, app/adapters/inbound, app/adapters/outbound/repositories)
# ├─ Responsible for: User authentication, conversation ownership, app metadata
# ├─ Database: MongoDB (users, conversations collections)
# └─ Authorization: All user permission checks happen here BEFORE LangGraph

# LangGraph Layer (app/langgraph)
# ├─ Responsible for: AI workflow orchestration, message state management
# ├─ Database: LangGraph checkpointer (messages collection or new DB)
# └─ Authorization: ASSUMES caller has already validated permissions
```

### Step 2: Establish Database Naming

Clarify message storage location:

```python
# Option A: Same MongoDB, different collection
# - Hexagonal: db.conversations, db.users
# - LangGraph: db.langgraph_checkpoints (messages within state)

# Option B: Separate databases
# - Hexagonal: mongodb_prod (users, conversations)
# - LangGraph: mongodb_langgraph (checkpoints)

# Recommended: Option A (easier to manage, single DB instance)
```

### Step 3: Implement Thread ID Mapping

Conversation.id (MongoDB) must map to thread_id (LangGraph):

```python
# In websocket_handler.py:
conversation = await conversation_repository.get_by_id(conversation_id)
# conversation.id is now the thread_id in LangGraph

result = await graph.ainvoke(
    input_state,
    config={"configurable": {"thread_id": conversation.id}}
)
```

### Step 4: Migrate Use Case Logic

**SendMessage use case logic moves to WebSocket handler:**
- Message saving: Handled by LangGraph checkpointer
- LLM invocation: Handled by LangGraph graph
- Response streaming: Handled by graph.astream_events()

The use case can be deleted, or repurposed for:
- Batch message sending (non-WebSocket)
- Historical message retrieval (using checkpointer)

### Step 5: Test Authorization Boundaries

Ensure every test verifies:
1. User A cannot access User B's conversation
2. Invalid users cannot invoke LangGraph
3. Conversation ownership is checked before graph execution

Example test pattern:
```python
async def test_websocket_denies_cross_user_access():
    # Setup: User A creates conversation
    # Test: User B tries to access User A's conversation
    # Expect: 403 Access Denied (from websocket_handler, before graph)

    conversation = await repository.create(user_a.id, data)

    result = await handle_websocket_chat(
        websocket=ws,
        user=user_b,  # Different user
        graph=graph,
        conversation_repository=repo
    )

    # Should raise error, not invoke graph
    assert error_sent
```

---

## Risks and Considerations

### 1. Message History Retrieval

**Risk**: Frontend needs to load message history. Where does it come from now?

**Solution Options**:
- **Option A**: Create new endpoint that queries LangGraph checkpointer
  ```python
  @router.get("/api/conversations/{conversation_id}/history")
  async def get_conversation_history(conversation_id: str, current_user: CurrentUser):
      # 1. Check ownership (hexagonal)
      conversation = await conversation_repository.get_by_id(conversation_id)
      if conversation.user_id != current_user.id:
          raise HTTPException(403)

      # 2. Fetch from LangGraph checkpointer
      state = await checkpointer.get_state(
          values=None,
          checkpoint_id=conversation_id  # thread_id
      )
      return state.values["messages"]
  ```

- **Option B**: Modify websocket handler to send full history on connect
  ```python
  @router.websocket("/ws/chat")
  async def websocket_endpoint(websocket: WebSocket):
      # ... auth checks ...

      # Send existing conversation history
      state = await checkpointer.get_state(values=None, checkpoint_id=conversation_id)
      existing_messages = state.values.get("messages", [])
      for message in existing_messages:
          await send_message(websocket, {"type": "history", "message": message})

      # Then continue with new messages
  ```

**Recommendation**: Use Option A for flexibility. Create a separate "fetch history" endpoint distinct from "stream new messages" WebSocket.

### 2. Dual Database Concerns

**Risk**: Messages now split between:
- Hexagonal MongoDB (conversation metadata)
- LangGraph checkpointer database (actual messages)

**Mitigation**:
- Use same MongoDB instance for both (simpler)
- Establish clear naming: `conversations` collection vs `langgraph_checkpoints` collection
- Document this split clearly in architecture diagrams
- Consider future unification if LangGraph adds better MongoDB support

### 3. Message Metadata

**Current**: Messages can have metadata field (arbitrary JSON)

**New**: LangGraph messages are part of ConversationState

**Solution**:
- Keep metadata in LangGraph message objects if LangGraph's Message class supports it
- Or store metadata separately in MongoDB with message ID reference

### 4. Message Deletion

**Current**: IMessageRepository.delete() allows deleting individual messages

**New**: LangGraph doesn't support deleting individual messages from checkpoint

**Solution**:
- Document that message deletion is not supported in new architecture
- If needed, implement at LangGraph level by resetting conversation
- Or keep a separate MongoDB collection for "deleted messages" metadata

### 5. Transaction Consistency

**Risk**: What if hexagonal layer creates conversation but LangGraph fails to initialize?

**Mitigation**:
- Conversation creation is transactional (MongoDB)
- LangGraph initialization happens lazily on first message (not in transaction)
- First WebSocket message will initialize LangGraph state

**Trade-off**: Conversation might exist but not be usable until first message sent. This is acceptable.

### 6. Use Case Layer

**Decision**: What happens to SendMessage use case?

**Options**:
- **Delete entirely**: Logic now lives in WebSocket handler
- **Keep for non-WebSocket scenarios**: E.g., async message sending
- **Refactor as adapter**: Convert to LangGraph graph invocation adapter

**Recommendation**: Keep structure but refactor to use LangGraph directly instead of repositories.

### 7. Streaming Support

**Current**: LangGraph streaming_chat_graph.py exists

**New**: Must work with checkpointer and WebSocket streaming

**Consideration**: Ensure `graph.astream_events()` properly persists state while streaming tokens.

---

## Testing Strategy

### Unit Tests

**Test Domain Models:**
- Conversation model (no message_count)
- Remove Message model tests

**Test Ports:**
- IConversationRepository (no message count increment)
- Remove IMessageRepository tests

**Test LangGraph State:**
- ConversationState schema with thread_id mapping
- Message aggregation via add_messages reducer

### Integration Tests

**Test Authorization Boundary:**
```python
async def test_conversation_ownership_enforced():
    """User B cannot access User A's conversation."""
    # Setup
    conv_a = await repo.create(user_a.id, data)

    # Test: WebSocket handler should deny User B
    with pytest.raises(HTTPException) as exc:
        await handle_websocket_chat(
            ws, user_b, graph, repo
        )
    assert exc.value.status_code == 403
```

**Test LangGraph Integration:**
```python
async def test_langgraph_invocation_with_checkpointer():
    """Graph properly persists state and retrieves messages."""
    # Send message through graph
    state = await graph.ainvoke(
        {"current_input": "Hello"},
        config={"configurable": {"thread_id": "test-conv-1"}}
    )

    # Retrieve from checkpointer
    checkpoint = await checkpointer.get_state(
        values=None,
        checkpoint_id="test-conv-1"
    )

    # Verify messages persisted
    assert len(checkpoint.values["messages"]) >= 2  # user + assistant
```

**Test WebSocket Handler:**
```python
async def test_websocket_streams_langgraph_responses():
    """WebSocket properly streams LangGraph responses."""
    # Connect, send message, receive tokens
    # Verify tokens come from graph streaming
    # Verify conversation persisted in MongoDB
    # Verify state persisted in LangGraph checkpointer
```

### End-to-End Tests

**Test Full Conversation Flow:**
1. User creates conversation (REST)
2. User connects WebSocket
3. User sends message
4. Server streams response (LangGraph)
5. User fetches history (REST)
6. Verify message appears in history

---

## Key Architectural Principles Summary

### 1. Clear Separation of Concerns

- **Hexagonal Layer**: User/conversation metadata, authentication, authorization
- **LangGraph Layer**: AI workflow, message history, state management

### 2. Authorization Stays in Hexagonal

Conversation ownership checks happen BEFORE LangGraph invocation. No permission verification in LangGraph.

### 3. LangGraph is Not an Adapter

It's not abstracted behind a port interface because:
- It's the primary orchestration engine
- ConversationState is integral (not replaceable)
- Multiple implementations provide no architectural benefit

### 4. Thread ID Mapping

- MongoDB: `Conversation.id` (string)
- LangGraph: `thread_id` (same value)
- Message.conversation_id → ConversationState.messages (in checkpointer)

### 5. Dual Database Pattern

- **MongoDB**: User, Conversation, other app metadata
- **LangGraph Checkpointer**: Message state and workflow checkpoints

This enables:
- Clear domain boundaries
- Independent scaling
- Different consistency requirements

---

## Dependencies and Imports to Update

### Files That Import IMessageRepository
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py`
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_router.py`
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/use_cases/send_message.py`
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/save_history.py`

### Files That Import Message Domain Model
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py`
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/process_input.py`
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/format_response.py`
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py`
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_domain_models.py`
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_conversation_api.py`

### Files That Reference increment_message_count()
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py`
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/use_cases/send_message.py`
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/save_history.py`

All these imports and method calls must be removed or refactored.

---

## Summary for Implementation Team

This refactor represents a fundamental shift in how the application manages state:

1. **Delete Message as a domain concept**: It only exists in LangGraph state now
2. **Simplify Conversation**: Keep only metadata (user_id, title, timestamps)
3. **Create checkpointer infrastructure**: Use LangGraph's built-in persistence
4. **Refactor WebSocket handler**: Delegate to graph.astream_events()
5. **Preserve authorization**: Hexagonal layer checks permissions BEFORE LangGraph
6. **Update dependency injection**: Pass graph instance instead of repositories

The result is a cleaner separation where:
- Hexagonal architecture manages identity and access
- LangGraph manages intelligence and conversation flow
- Each layer has its own persistence and concerns

This is a significant change but the modular structure makes it implementable in phases.
