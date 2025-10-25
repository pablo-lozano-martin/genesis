# Implementation Plan: LangGraph-First Architecture with Two-Database Pattern

## Executive Summary

This plan outlines the implementation strategy for Issue #6: transitioning from a custom message persistence pattern to a LangGraph-native architecture with dual MongoDB databases. The refactor addresses three core problems:

1. **LangGraph is currently bypassed** - The WebSocket handler calls `llm_provider.stream()` directly instead of using the LangGraph graphs
2. **Manual message persistence is redundant** - Custom message repository duplicates what LangGraph checkpointing provides
3. **Mixed responsibilities** - App metadata (conversations, users) mixed with AI execution state (messages)

**Goal:** Implement a clean separation where:
- **App Database** stores user accounts and conversation metadata (id, user_id, title, timestamps)
- **LangGraph Database** stores message history and execution state via native checkpointing
- **LangGraph graphs** handle ALL conversation flow (no bypassing)

## Architecture Vision

### Current Architecture (Problem)

```
┌──────────────────────────────────────────────────────────────┐
│                     WebSocket Handler                         │
│  ❌ Bypasses LangGraph graphs                                │
│  ❌ Calls llm_provider.stream() directly                      │
│  ❌ Manually saves messages to MongoDB via repository         │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│                   Single MongoDB Database                     │
│  • users collection                                           │
│  • conversations collection (metadata + message_count)        │
│  • messages collection (all message history)                  │
└──────────────────────────────────────────────────────────────┘
```

### Target Architecture (Solution)

```
┌──────────────────────────────────────────────────────────────┐
│                     WebSocket Handler                         │
│  ✅ Uses LangGraph graphs exclusively                        │
│  ✅ Calls graph.astream() for streaming                       │
│  ✅ Checkpointing is automatic                                │
└──────────────────────────────────────────────────────────────┘
                            ↓
            ┌───────────────┴───────────────┐
            ↓                               ↓
┌─────────────────────────┐     ┌─────────────────────────┐
│   App Database (MongoDB)│     │LangGraph DB (MongoDB)   │
│  • users                │     │ • langgraph_checkpoints │
│  • conversations        │     │ • langgraph_stores      │
│    (metadata only)      │     │   (message history)     │
└─────────────────────────┘     └─────────────────────────┘
```

### Key Architectural Principles

1. **LangGraph is NOT infrastructure** - It's the primary orchestration layer, not an abstraction to hide
2. **Hexagonal boundaries preserved** - Authorization stays in application layer (App DB), execution in LangGraph layer
3. **conversation.id = thread_id** - Simple 1:1 mapping between conversation metadata and LangGraph threads
4. **Native LangGraph types** - Use `MessagesState` and `BaseMessage` types (HumanMessage, AIMessage, SystemMessage)
5. **Automatic persistence** - LangGraph checkpointer handles all message storage, no manual repository calls

## Analysis Summary

Based on comprehensive analysis from 8 specialized agents, here are the key findings:

### Hexagonal Architecture Impact
- **Files to delete:** 5 (Message domain model, message repository port/adapter, save_history node, message router)
- **Files to modify:** 9 (conversation model, LangGraph state, graphs, WebSocket handler, database config)
- **Files to create:** 2 (checkpointer setup, potentially new graph factory pattern)
- **Authorization boundary:** Remains in App DB layer (hexagonal), messages in LangGraph layer

### Database Pattern
- **App DB:** `users`, `conversations` collections (metadata only, NO messages)
- **LangGraph DB:** `langgraph_checkpoints`, `langgraph_stores` collections
- **Configuration:** Dual MongoDB connections (`MONGODB_APP_URI`, `MONGODB_LANGGRAPH_URI`)
- **Migration strategy:** Read messages from old collection, write to LangGraph checkpoints, verify consistency

### LLM Integration Changes
- **State migration:** Custom `ConversationState` → LangGraph's native `MessagesState`
- **Message types:** Domain `Message` objects → LangChain `BaseMessage` types
- **Graph compilation:** Add `AsyncMongoDBSaver` checkpointer to `create_chat_graph()`
- **WebSocket refactor:** Remove direct `llm_provider.stream()` calls, use `graph.astream()` instead
- **Node changes:** Delete `save_history.py`, modify others to use native types

### API Contract
- **Breaking changes:** Minimal to none (message_count may be removed from conversation response)
- **GET /conversations/{id}/messages:** Backend changes (LangGraph state query), frontend unchanged
- **WebSocket protocol:** No changes to message format, internal flow different
- **thread_id:** Internal only, NEVER exposed to frontend

### Data Flow
- **Current flow:** WebSocket → manual persistence → MongoDB messages collection
- **New flow:** WebSocket → graph.astream() → automatic checkpointing → LangGraph DB
- **Conversation ownership:** Always verified in App DB before accessing LangGraph state

### Frontend Impact
- **Changes needed:** Make `message_count` optional in TypeScript interface, add null check in ConversationSidebar
- **No breaking changes expected** - API contracts remain stable
- **WebSocket protocol:** Identical from frontend perspective

### Security
- **Thread_ID security:** NEVER expose to client, always resolve via conversation.id
- **Authorization pattern:** Verify conversation ownership in App DB BEFORE accessing LangGraph state
- **Database credentials:** Separate credentials for App DB vs LangGraph DB
- **Cascade deletion:** Delete from both databases when conversation deleted

### Testing Requirements
- **Unit tests:** Graph nodes, state management, checkpointer, RunnableConfig (>80% coverage target)
- **Integration tests:** Graph execution, WebSocket streaming, dual-database coordination
- **E2E tests:** Complete chat workflows, data persistence across restarts

## Implementation Phases

### Phase 1: Foundation - Dual Database Setup (Days 1-2)

**Objective:** Establish dual MongoDB connection infrastructure without breaking existing functionality.

**Tasks:**

1. **Update settings.py**
   - File: `backend/app/infrastructure/config/settings.py`
   - Add fields:
     ```python
     mongodb_app_url: str
     mongodb_app_db_name: str = "genesis_app"
     mongodb_langgraph_url: str
     mongodb_langgraph_db_name: str = "genesis_langgraph"
     ```
   - Keep existing `mongodb_url` for backward compatibility during migration

2. **Update .env.example**
   - File: `backend/.env.example`
   - Add:
     ```
     MONGODB_APP_URL=mongodb://localhost:27017
     MONGODB_APP_DB_NAME=genesis_app
     MONGODB_LANGGRAPH_URL=mongodb://localhost:27017
     MONGODB_LANGGRAPH_DB_NAME=genesis_langgraph
     ```

3. **Refactor database connection management**
   - File: `backend/app/infrastructure/database/mongodb.py`
   - Changes:
     - Rename `MongoDB` class to `AppDatabase`
     - Create new `LangGraphDatabase` class
     - Both implement separate `connect()` and `disconnect()` methods
     - AppDatabase manages: users, conversations (NO messages)
     - LangGraphDatabase manages: checkpoints only

4. **Update application startup**
   - File: `backend/app/main.py`
   - Changes:
     - Initialize both `AppDatabase.connect()` and `LangGraphDatabase.connect()` in lifespan
     - Initialize LangGraph checkpointer with LangGraphDatabase connection
     - Keep existing initialization for backward compatibility

5. **Create LangGraph checkpointer setup**
   - Create new file: `backend/app/infrastructure/database/langgraph_checkpointer.py`
   - Implement:
     ```python
     from langgraph.checkpoint.mongodb import AsyncMongoDBSaver

     async def get_checkpointer():
         client = LangGraphDatabase.client
         return AsyncMongoDBSaver(client)
     ```

**Testing Phase 1:**
- Unit test: AppDatabase and LangGraphDatabase connection independently
- Integration test: Both databases connect successfully on startup
- Verify: Existing functionality unchanged (still uses old mongodb_url)

**Success Criteria:**
- Both databases connect successfully
- Application starts without errors
- All existing tests pass

---

### Phase 2: LangGraph State Migration (Days 3-4)

**Objective:** Migrate from custom ConversationState to LangGraph's native MessagesState.

**Tasks:**

1. **Update LangGraph state.py**
   - File: `backend/app/langgraph/state.py`
   - Changes:
     ```python
     # BEFORE: Custom ConversationState
     class ConversationState(TypedDict):
         messages: List[Message]  # Domain Message objects
         conversation_id: str
         user_id: str
         current_input: Optional[str]
         llm_response: Optional[str]
         error: Optional[str]

     # AFTER: Use LangGraph's native MessagesState
     from langgraph.graph import MessagesState

     class ConversationState(MessagesState):
         conversation_id: str
         user_id: str
         # messages field comes from MessagesState (List[BaseMessage])
         # add_messages reducer is built-in
     ```
   - Remove custom `add_messages` reducer (now built-in)
   - Use LangChain's `HumanMessage`, `AIMessage`, `SystemMessage` types

2. **Update process_input.py node**
   - File: `backend/app/langgraph/nodes/process_input.py`
   - Changes:
     ```python
     from langchain_core.messages import HumanMessage

     async def process_user_input(state: ConversationState) -> dict:
         # Get user input from WebSocket or config
         user_input = state.get("current_input")

         if not user_input or not user_input.strip():
             return {"error": "Empty input"}

         # Create HumanMessage instead of domain Message
         message = HumanMessage(content=user_input)

         return {"messages": [message]}
     ```

3. **Update call_llm.py node**
   - File: `backend/app/langgraph/nodes/call_llm.py`
   - Changes:
     ```python
     async def call_llm(state: ConversationState, config: RunnableConfig) -> dict:
         llm_provider = config["configurable"]["llm_provider"]

         # state.messages is already List[BaseMessage]
         messages = state["messages"]

         try:
             response = await llm_provider.generate(messages)
             return {"llm_response": response}
         except Exception as e:
             return {"error": str(e)}
     ```

4. **Update format_response.py node**
   - File: `backend/app/langgraph/nodes/format_response.py`
   - Changes:
     ```python
     from langchain_core.messages import AIMessage

     async def format_response(state: ConversationState) -> dict:
         llm_response = state.get("llm_response")

         if not llm_response:
             return {}

         # Create AIMessage instead of domain Message
         message = AIMessage(content=llm_response)

         return {"messages": [message], "llm_response": None}
     ```

5. **Delete save_history.py node**
   - File: `backend/app/langgraph/nodes/save_history.py`
   - Reason: LangGraph checkpointer handles persistence automatically
   - Action: Delete entire file

6. **Update LLM provider adapters**
   - Files:
     - `backend/app/adapters/outbound/llm/openai_provider.py`
     - `backend/app/adapters/outbound/llm/anthropic_provider.py`
     - `backend/app/adapters/outbound/llm/gemini_provider.py`
     - `backend/app/adapters/outbound/llm/ollama_provider.py`
   - Changes:
     - Remove `_convert_messages()` helper (BaseMessage types work natively)
     - Update `generate()` and `stream()` to accept `List[BaseMessage]` directly

**Testing Phase 2:**
- Unit test: Each node with MessagesState
- Unit test: State reducer (built-in add_messages)
- Unit test: BaseMessage serialization/deserialization
- Integration test: Full graph execution with new state

**Success Criteria:**
- All nodes work with MessagesState
- Message history preserved correctly
- All LLM providers compatible with BaseMessage types

---

### Phase 3: Graph Compilation with Checkpointer (Days 5-6)

**Objective:** Integrate AsyncMongoDBSaver checkpointer into graph compilation.

**Tasks:**

1. **Update chat_graph.py**
   - File: `backend/app/langgraph/graphs/chat_graph.py`
   - Changes:
     ```python
     from langgraph.checkpoint.mongodb import AsyncMongoDBSaver

     async def create_chat_graph(
         llm_provider: ILLMProvider,
         checkpointer: AsyncMongoDBSaver  # NEW parameter
     ) -> CompiledGraph:
         graph_builder = StateGraph(ConversationState)

         # Add nodes (NO save_history node anymore)
         graph_builder.add_node("process_input", process_user_input)
         graph_builder.add_node("call_llm", call_llm)
         graph_builder.add_node("format_response", format_response)

         # Add edges
         graph_builder.add_edge(START, "process_input")
         graph_builder.add_conditional_edges(
             "process_input",
             should_continue,
             {
                 "call_llm": "call_llm",
                 "error": END
             }
         )
         graph_builder.add_edge("call_llm", "format_response")
         graph_builder.add_edge("format_response", END)  # NO save_history

         # Compile with checkpointer
         return graph_builder.compile(checkpointer=checkpointer)
     ```

2. **Update streaming_chat_graph.py**
   - File: `backend/app/langgraph/graphs/streaming_chat_graph.py`
   - Apply same changes as chat_graph.py
   - Ensure streaming variant also uses checkpointer

3. **Update graph factory/initialization**
   - File: `backend/app/main.py` (or new graph factory)
   - Changes:
     ```python
     from backend.app.infrastructure.database.langgraph_checkpointer import get_checkpointer

     @asynccontextmanager
     async def lifespan(app: FastAPI):
         # Connect databases
         await AppDatabase.connect()
         await LangGraphDatabase.connect()

         # Initialize checkpointer
         checkpointer = await get_checkpointer()

         # Compile graphs with checkpointer
         app.state.chat_graph = await create_chat_graph(
             llm_provider=...,
             checkpointer=checkpointer
         )

         yield

         await AppDatabase.disconnect()
         await LangGraphDatabase.disconnect()
     ```

4. **Implement RunnableConfig pattern**
   - Usage in graph invocation:
     ```python
     from langgraph.config import RunnableConfig

     config = RunnableConfig(
         configurable={
             "thread_id": conversation.id,  # conversation.id = thread_id
             "llm_provider": llm_provider,
             "user_id": user.id
         }
     )

     # Use config with graph
     async for chunk in graph.astream(input_data, config):
         # Process streaming chunks
     ```

5. **Add conversation.thread_id field (optional)**
   - File: `backend/app/core/domain/conversation.py`
   - If explicit mapping needed:
     ```python
     class Conversation:
         id: str  # Primary ID
         user_id: str
         title: str
         thread_id: Optional[str] = None  # Maps to LangGraph thread
         created_at: datetime
         updated_at: datetime
         # message_count removed (count from LangGraph state)
     ```
   - Note: If conversation.id is used directly as thread_id, this field is unnecessary

**Testing Phase 3:**
- Unit test: Graph compilation with checkpointer
- Unit test: RunnableConfig thread_id mapping
- Integration test: Graph execution creates checkpoints
- Integration test: graph.get_state() retrieves checkpointed state
- Verify: Checkpoints stored in LangGraph DB

**Success Criteria:**
- Graphs compile with checkpointer
- Checkpoints created automatically after graph execution
- State retrievable via graph.get_state(config)

---

### Phase 4: WebSocket Handler Refactor (Days 7-8)

**Objective:** Replace direct LLM streaming with graph.astream() execution.

**Tasks:**

1. **Update websocket_handler.py**
   - File: `backend/app/adapters/inbound/websocket_handler.py`
   - **Current problematic flow:**
     ```python
     # ❌ WRONG: Bypasses LangGraph
     async for token in llm_provider.stream(messages):
         await websocket.send_json({"type": "token", "content": token})

     # ❌ WRONG: Manual message persistence
     await message_repository.save(user_message)
     await message_repository.save(assistant_message)
     ```

   - **New correct flow:**
     ```python
     from langgraph.config import RunnableConfig

     async def handle_websocket_chat(
         websocket: WebSocket,
         conversation_id: str,
         user: User,
         graph: CompiledGraph
     ):
         # Verify conversation ownership (App DB)
         conversation = await conversation_repository.get_by_id(conversation_id)
         if not conversation or conversation.user_id != user.id:
             await websocket.close(code=1008, reason="Access denied")
             return

         # Configure graph execution
         config = RunnableConfig(
             configurable={
                 "thread_id": conversation.id,
                 "user_id": user.id
             }
         )

         # Listen for WebSocket messages
         async for ws_message in websocket.iter_json():
             if ws_message["type"] != "message":
                 continue

             user_input = ws_message["content"]

             # Stream via LangGraph graph
             input_data = {"current_input": user_input}

             try:
                 async for event in graph.astream_events(input_data, config, version="v2"):
                     # Stream tokens to client
                     if event["event"] == "on_chat_model_stream":
                         token = event["data"]["chunk"].content
                         await websocket.send_json({
                             "type": "token",
                             "content": token
                         })

                 # Checkpointing happens automatically
                 # Send completion signal
                 await websocket.send_json({
                     "type": "complete",
                     "conversation_id": conversation.id
                 })

             except Exception as e:
                 await websocket.send_json({
                     "type": "error",
                     "message": str(e)
                 })
     ```

2. **Update websocket_router.py**
   - File: `backend/app/adapters/inbound/websocket_router.py`
   - Consider making conversation_id part of URL path:
     ```python
     @router.websocket("/ws/chat/{conversation_id}")
     async def websocket_endpoint(
         websocket: WebSocket,
         conversation_id: str
     ):
         user = await get_user_from_websocket(websocket)
         graph = app.state.chat_graph
         await handle_websocket_chat(websocket, conversation_id, user, graph)
     ```

3. **Remove manual message persistence**
   - Delete all `message_repository.save()` calls in WebSocket handler
   - Checkpointer handles persistence automatically

**Testing Phase 4:**
- Integration test: WebSocket connection with authentication
- Integration test: Send message → stream tokens → checkpoint created
- Integration test: Multi-turn conversation via WebSocket
- Integration test: Error handling (LLM failure, empty input)
- Verify: Messages stored in LangGraph DB checkpoints

**Success Criteria:**
- WebSocket streaming works via graph.astream_events()
- Checkpoints created automatically
- No manual message persistence code remains

---

### Phase 5: Message Retrieval from LangGraph (Days 9-10)

**Objective:** Replace message repository queries with LangGraph state queries.

**Tasks:**

1. **Create LangGraph state retrieval helper**
   - File: `backend/app/langgraph/state_retrieval.py` (new file)
   - Implementation:
     ```python
     from langgraph.config import RunnableConfig

     async def get_conversation_messages(
         graph: CompiledGraph,
         conversation_id: str
     ) -> List[BaseMessage]:
         """Retrieve messages from LangGraph checkpoint."""
         config = RunnableConfig(
             configurable={"thread_id": conversation_id}
         )

         state = await graph.aget_state(config)
         return state.values.get("messages", [])
     ```

2. **Update message_router.py**
   - File: `backend/app/adapters/inbound/message_router.py`
   - Changes:
     ```python
     from backend.app.langgraph.state_retrieval import get_conversation_messages

     @router.get("/{conversation_id}/messages")
     async def get_messages(
         conversation_id: str,
         current_user: User,
         conversation_repository: IConversationRepository,
         graph: CompiledGraph = Depends(lambda: app.state.chat_graph)
     ):
         # Verify ownership (App DB)
         conversation = await conversation_repository.get_by_id(conversation_id)
         if not conversation or conversation.user_id != current_user.id:
             raise HTTPException(403, "Access denied")

         # Retrieve messages from LangGraph state
         base_messages = await get_conversation_messages(graph, conversation_id)

         # Convert BaseMessage → API response format
         messages = [
             {
                 "id": str(uuid4()),  # Generate if needed
                 "conversation_id": conversation_id,
                 "role": msg.type,  # "human" | "ai" | "system"
                 "content": msg.content,
                 "created_at": msg.additional_kwargs.get("created_at", datetime.utcnow())
             }
             for msg in base_messages
         ]

         return messages
     ```

3. **Update conversation model (remove message_count)**
   - File: `backend/app/core/domain/conversation.py`
   - Changes:
     ```python
     class Conversation:
         id: str
         user_id: str
         title: str
         created_at: datetime
         updated_at: datetime
         # message_count: int  # REMOVED - count from LangGraph state if needed
     ```

   - File: `backend/app/adapters/outbound/repositories/mongo_models.py`
   - Remove `message_count` field from `ConversationDocument`

4. **Update conversation API responses**
   - File: `backend/app/adapters/inbound/conversation_router.py`
   - Make `message_count` optional in response schemas (for backward compatibility)
   - Or remove entirely if frontend updated

**Testing Phase 5:**
- Integration test: GET /conversations/{id}/messages retrieves from LangGraph
- Integration test: Message format matches API contract
- Integration test: Empty conversation returns empty list
- Integration test: Multi-message conversation returns all messages
- Verify: No queries to old messages collection

**Success Criteria:**
- Message retrieval works via LangGraph state
- API contract unchanged from frontend perspective
- message_count removed or optional

---

### Phase 6: Cleanup and Deletion (Days 11-12)

**Objective:** Remove deprecated message repository and domain models.

**Tasks:**

1. **Delete message domain model**
   - File: `backend/app/core/domain/message.py`
   - Reason: Using LangChain's BaseMessage types now
   - Action: Delete entire file

2. **Delete message repository port**
   - File: `backend/app/core/ports/message_repository.py`
   - Reason: Messages stored in LangGraph checkpoints
   - Action: Delete entire file

3. **Delete message repository adapter**
   - File: `backend/app/adapters/outbound/repositories/mongo_message_repository.py`
   - Reason: No longer needed
   - Action: Delete entire file

4. **Delete message router (if exists)**
   - File: `backend/app/adapters/inbound/message_router.py`
   - Decision: Keep if it only contains GET /messages endpoint (updated in Phase 5)
   - Or delete if GET /messages moved to conversation_router.py

5. **Remove MessageDocument from mongo_models.py**
   - File: `backend/app/adapters/outbound/repositories/mongo_models.py`
   - Delete `MessageDocument` class
   - Keep `UserDocument` and `ConversationDocument`

6. **Update dependency injection**
   - File: `backend/app/main.py`
   - Remove `message_repository` from dependency injection
   - Keep only `conversation_repository`

7. **Clean up imports**
   - Search codebase for `from app.core.domain.message import Message`
   - Replace with `from langchain_core.messages import HumanMessage, AIMessage`
   - Remove all references to old Message domain model

**Testing Phase 6:**
- Run full test suite
- Verify: No import errors
- Verify: No references to deleted files
- Verify: All functionality works without message repository

**Success Criteria:**
- All deprecated files deleted
- No import errors
- All tests pass

---

### Phase 7: Data Migration (Days 13-14)

**Objective:** Migrate existing message data from App DB to LangGraph checkpoints.

**Tasks:**

1. **Create migration script**
   - File: `backend/scripts/migrate_messages_to_langgraph.py` (new file)
   - Logic:
     ```python
     async def migrate_messages():
         # For each conversation in App DB
         conversations = await ConversationDocument.find_all().to_list()

         for conversation in conversations:
             # Get messages from old messages collection
             messages = await MessageDocument.find(
                 MessageDocument.conversation_id == conversation.id
             ).sort("+created_at").to_list()

             if not messages:
                 continue

             # Convert to BaseMessage types
             base_messages = []
             for msg in messages:
                 if msg.role == "user":
                     base_messages.append(HumanMessage(
                         content=msg.content,
                         additional_kwargs={"created_at": msg.created_at}
                     ))
                 elif msg.role == "assistant":
                     base_messages.append(AIMessage(
                         content=msg.content,
                         additional_kwargs={"created_at": msg.created_at}
                     ))
                 elif msg.role == "system":
                     base_messages.append(SystemMessage(
                         content=msg.content,
                         additional_kwargs={"created_at": msg.created_at}
                     ))

             # Create checkpoint in LangGraph DB
             config = RunnableConfig(
                 configurable={"thread_id": conversation.id}
             )

             state = ConversationState(
                 messages=base_messages,
                 conversation_id=conversation.id,
                 user_id=conversation.user_id
             )

             # Save checkpoint
             await checkpointer.aput(config, state, {})

             print(f"Migrated {len(messages)} messages for conversation {conversation.id}")
     ```

2. **Run migration script**
   - Execute: `python backend/scripts/migrate_messages_to_langgraph.py`
   - Verify: All messages migrated
   - Check: Message counts match

3. **Verify migration**
   - Test message retrieval via API for existing conversations
   - Ensure message order preserved
   - Ensure all message content intact

4. **Keep old messages collection temporarily**
   - Do NOT drop messages collection yet
   - Keep as backup until verification complete

**Testing Phase 7:**
- Verify: All conversations have checkpoints
- Verify: Message counts match old vs new
- Verify: Message content identical
- Integration test: Retrieve messages from migrated conversations

**Success Criteria:**
- All existing messages migrated to LangGraph checkpoints
- Message counts match
- No data loss

---

### Phase 8: Frontend Updates (Days 15-16)

**Objective:** Update frontend to handle message_count removal (if applicable).

**Tasks:**

1. **Update Conversation TypeScript interface**
   - File: `frontend/src/services/conversationService.ts`
   - Changes:
     ```typescript
     export interface Conversation {
       id: string;
       user_id: string;
       title: string;
       created_at: string;
       updated_at: string;
       message_count?: number;  // Optional now
     }
     ```

2. **Update ConversationSidebar component**
   - File: `frontend/src/components/chat/ConversationSidebar.tsx`
   - Changes:
     ```tsx
     {/* Before */}
     <div className="text-xs text-gray-500 mt-1">
       {conv.message_count} messages
     </div>

     {/* After */}
     {conv.message_count !== undefined && (
       <div className="text-xs text-gray-500 mt-1">
         {conv.message_count} messages
       </div>
     )}
     ```

3. **Test frontend compatibility**
   - Test: Conversation list loads without errors
   - Test: Conversation detail works
   - Test: WebSocket streaming works
   - Verify: No console errors

**Testing Phase 8:**
- Manual test: Load frontend with updated backend
- Verify: No TypeScript errors
- Verify: Conversation list renders
- Verify: Message sending and streaming work

**Success Criteria:**
- Frontend works with backend changes
- No console errors
- Graceful handling of missing message_count

---

### Phase 9: Testing and Validation (Days 17-18)

**Objective:** Achieve >80% test coverage and validate all functionality.

**Tasks:**

1. **Create unit tests**
   - `tests/unit/test_langgraph_state.py` - State and reducer tests
   - `tests/unit/test_langgraph_nodes.py` - Node transformation tests
   - `tests/unit/test_langgraph_graphs.py` - Graph compilation tests
   - `tests/unit/test_checkpointer_adapter.py` - Checkpoint persistence tests
   - `tests/unit/test_runnable_config.py` - Config routing tests

2. **Create integration tests**
   - `tests/integration/test_langgraph_execution.py` - Graph execution tests
   - `tests/integration/test_websocket_langgraph.py` - WebSocket streaming tests
   - `tests/integration/test_checkpoint_retrieval.py` - State restoration tests
   - `tests/integration/test_dual_database.py` - Database independence tests

3. **Create E2E tests**
   - `tests/e2e/test_chat_workflows.py` - Full user journeys
   - `tests/e2e/test_data_persistence.py` - Cross-restart consistency

4. **Run coverage report**
   - Command: `pytest --cov=app --cov-report=term-missing`
   - Target: >80% coverage
   - Fix: Add tests for any gaps

5. **Validate all features**
   - User registration and login
   - Conversation creation
   - Message sending (WebSocket)
   - Message streaming
   - Message history retrieval
   - Conversation deletion
   - Multi-turn conversations
   - Error handling

**Testing Phase 9:**
- Run: `pytest` (all tests)
- Run: `pytest --cov=app --cov-report=html`
- Review: Coverage report
- Fix: Any failing tests
- Add: Tests for uncovered code

**Success Criteria:**
- All tests pass
- Coverage >80%
- All features validated

---

### Phase 10: Production Readiness (Days 19-20)

**Objective:** Prepare for deployment with documentation and monitoring.

**Tasks:**

1. **Update documentation**
   - Update: `doc/general/ARCHITECTURE.md` - Describe two-database pattern
   - Update: `doc/general/API.md` - Note message_count removal
   - Update: `doc/general/DEVELOPMENT.md` - Add migration instructions
   - Create: `doc/general/LANGGRAPH.md` - Explain LangGraph integration

2. **Create deployment guide**
   - Document: Environment variables needed
   - Document: Migration script execution
   - Document: Database backup strategy
   - Document: Rollback procedure

3. **Add monitoring and logging**
   - Add: Checkpoint creation logging
   - Add: Graph execution time metrics
   - Add: Database connection health checks
   - Add: Error rate monitoring for LangGraph failures

4. **Security review**
   - Verify: thread_id never exposed to client
   - Verify: Conversation ownership always checked
   - Verify: Database credentials separated
   - Verify: Error messages don't leak thread_id

5. **Performance testing**
   - Test: WebSocket streaming latency
   - Test: Message retrieval from LangGraph
   - Test: Concurrent conversation handling
   - Test: Database connection pooling

6. **Final cleanup**
   - Drop old messages collection (after backup)
   - Remove old mongodb_url from settings
   - Clean up commented-out code
   - Update .gitignore if needed

**Success Criteria:**
- Documentation complete
- Deployment guide ready
- Monitoring in place
- Security verified
- Performance acceptable

---

## File Changes Summary

### Files to Delete (5 files)

1. `backend/app/core/domain/message.py` - Using LangChain BaseMessage types
2. `backend/app/core/ports/message_repository.py` - Messages in LangGraph checkpoints
3. `backend/app/adapters/outbound/repositories/mongo_message_repository.py` - No longer needed
4. `backend/app/langgraph/nodes/save_history.py` - Checkpointer handles persistence
5. `backend/app/adapters/inbound/message_router.py` - Optional (if merged into conversation_router)

### Files to Modify (Major Changes - 9 files)

1. `backend/app/infrastructure/config/settings.py`
   - Add: mongodb_app_url, mongodb_app_db_name, mongodb_langgraph_url, mongodb_langgraph_db_name

2. `backend/app/infrastructure/database/mongodb.py`
   - Refactor: AppDatabase and LangGraphDatabase classes
   - Add: Dual connection management

3. `backend/app/langgraph/state.py`
   - Change: ConversationState extends MessagesState
   - Remove: Custom add_messages reducer

4. `backend/app/langgraph/graphs/chat_graph.py`
   - Add: checkpointer parameter to create_chat_graph()
   - Remove: save_history node

5. `backend/app/langgraph/graphs/streaming_chat_graph.py`
   - Add: checkpointer parameter
   - Remove: save_history node

6. `backend/app/langgraph/nodes/process_input.py`
   - Change: Create HumanMessage instead of domain Message

7. `backend/app/langgraph/nodes/call_llm.py`
   - Change: Accept List[BaseMessage] from state

8. `backend/app/langgraph/nodes/format_response.py`
   - Change: Create AIMessage instead of domain Message

9. `backend/app/adapters/inbound/websocket_handler.py`
   - Refactor: Use graph.astream_events() instead of llm_provider.stream()
   - Remove: Manual message persistence

### Files to Modify (Minor Changes - 6 files)

10. `backend/app/main.py`
    - Add: Dual database connection in lifespan
    - Add: Checkpointer initialization
    - Update: Graph compilation with checkpointer

11. `backend/app/adapters/inbound/conversation_router.py`
    - Update: GET /messages endpoint to use LangGraph state
    - Optional: Remove message_count from responses

12. `backend/app/core/domain/conversation.py`
    - Remove: message_count field

13. `backend/app/adapters/outbound/repositories/mongo_models.py`
    - Remove: MessageDocument class
    - Remove: message_count from ConversationDocument

14. `backend/app/adapters/outbound/llm/*.py` (all 4 providers)
    - Remove: _convert_messages() helper
    - Update: Accept List[BaseMessage] directly

15. `backend/.env.example`
    - Add: MONGODB_APP_URL, MONGODB_APP_DB_NAME, MONGODB_LANGGRAPH_URL, MONGODB_LANGGRAPH_DB_NAME

### Files to Create (3 files)

1. `backend/app/infrastructure/database/langgraph_checkpointer.py`
   - Create: get_checkpointer() factory

2. `backend/app/langgraph/state_retrieval.py`
   - Create: get_conversation_messages() helper

3. `backend/scripts/migrate_messages_to_langgraph.py`
   - Create: Migration script

### Frontend Files to Modify (2 files)

1. `frontend/src/services/conversationService.ts`
   - Change: Make message_count optional

2. `frontend/src/components/chat/ConversationSidebar.tsx`
   - Add: Null check for message_count display

---

## Testing Strategy

### Unit Tests (70% of tests)

**test_langgraph_state.py:**
- State initialization
- Message reducer behavior
- Error field handling

**test_langgraph_nodes.py:**
- process_input: HumanMessage creation, empty input handling
- call_llm: LLM invocation, error handling
- format_response: AIMessage creation, response formatting

**test_langgraph_graphs.py:**
- Graph compilation
- Conditional routing (should_continue)
- Dependency injection

**test_checkpointer_adapter.py:**
- Checkpoint put/get/delete
- State serialization/deserialization
- Thread-safe operations

**test_runnable_config.py:**
- Conversation ID mapping
- Config propagation through nodes
- Graph invocation with config

### Integration Tests (25% of tests)

**test_langgraph_execution.py:**
- Single-turn conversation
- Multi-turn conversation
- Checkpoint creation and retrieval
- Dual-database coordination

**test_websocket_langgraph.py:**
- WebSocket connection and authentication
- Token streaming via graph.astream_events()
- Checkpoint creation after streaming
- Error handling

**test_checkpoint_retrieval.py:**
- State restoration from checkpoints
- Message history reconstruction
- Empty conversation handling

**test_dual_database.py:**
- App DB independence from LangGraph DB
- Conversation ownership verification
- Cascade deletion across both DBs

### E2E Tests (5% of tests)

**test_chat_workflows.py:**
- Complete user journey: register → create conversation → send message → stream response
- Multi-turn conversations
- Error recovery

**test_data_persistence.py:**
- Conversation history survives server restart
- Message count accuracy
- Checkpoint consistency

### Coverage Goals

| Phase | Target Coverage |
|-------|-----------------|
| After Phase 9 | >80% |
| Final | >85% |

---

## Risk Mitigation

### Risk 1: Checkpoint Serialization Issues
**Risk:** ConversationState with BaseMessage objects may not serialize correctly.

**Mitigation:**
- Test serialization early in Phase 2
- Use LangChain's built-in serialization for BaseMessage
- Add unit tests for checkpoint put/get roundtrip

### Risk 2: WebSocket Streaming Breaks
**Risk:** graph.astream_events() may not stream tokens as expected.

**Mitigation:**
- Test streaming early in Phase 4
- Use LangGraph's recommended streaming patterns
- Add integration tests for streaming

### Risk 3: Data Loss During Migration
**Risk:** Message migration script fails or loses data.

**Mitigation:**
- Backup messages collection before migration
- Verify message counts after migration
- Keep old collection until verification complete
- Test migration script on dev environment first

### Risk 4: Frontend Breaking Changes
**Risk:** API contract changes break frontend.

**Mitigation:**
- Make message_count optional (not removed)
- Test frontend compatibility early
- Deploy backend and frontend together

### Risk 5: Performance Degradation
**Risk:** LangGraph state retrieval slower than direct MongoDB queries.

**Mitigation:**
- Performance test message retrieval early
- Add caching if needed
- Monitor query times in production

### Risk 6: Dual Database Consistency
**Risk:** App DB and LangGraph DB get out of sync.

**Mitigation:**
- Add consistency checks in tests
- Implement cascade deletion properly
- Add monitoring for orphaned data

---

## Success Metrics

### Technical Metrics
- Test coverage: >80%
- All unit tests pass
- All integration tests pass
- All E2E tests pass
- No breaking API changes (except optional message_count)

### Functional Metrics
- WebSocket streaming works
- Message retrieval works
- Multi-turn conversations work
- Conversation deletion works
- All LLM providers work (OpenAI, Anthropic, Gemini, Ollama)

### Performance Metrics
- WebSocket streaming latency: <100ms
- Message retrieval latency: <500ms
- Checkpoint creation time: <1s
- Database connection time: <2s

### Data Integrity Metrics
- Zero data loss during migration
- Message counts match (old vs new)
- All conversations have checkpoints
- Orphaned data: 0

---

## Rollback Plan

If critical issues arise during deployment:

1. **Stop deployment** - Halt any ongoing migration
2. **Revert code** - Deploy previous version
3. **Restore database** - Use backup if needed
4. **Verify** - Test that old system works
5. **Investigate** - Analyze what went wrong
6. **Fix** - Address issues in dev environment
7. **Re-deploy** - Try again with fixes

**Backup Strategy:**
- Backup messages collection before migration
- Backup conversations collection
- Backup entire MongoDB instance
- Keep backups for 30 days

---

## Timeline Summary

| Phase | Duration | Days |
|-------|----------|------|
| Phase 1: Dual Database Setup | 2 days | 1-2 |
| Phase 2: LangGraph State Migration | 2 days | 3-4 |
| Phase 3: Graph Compilation with Checkpointer | 2 days | 5-6 |
| Phase 4: WebSocket Handler Refactor | 2 days | 7-8 |
| Phase 5: Message Retrieval from LangGraph | 2 days | 9-10 |
| Phase 6: Cleanup and Deletion | 2 days | 11-12 |
| Phase 7: Data Migration | 2 days | 13-14 |
| Phase 8: Frontend Updates | 2 days | 15-16 |
| Phase 9: Testing and Validation | 2 days | 17-18 |
| Phase 10: Production Readiness | 2 days | 19-20 |
| **Total** | **20 days** | **~4 weeks** |

---

## Key Decisions and Assumptions

### Decisions
1. **conversation.id = thread_id** - Use conversation ID directly as LangGraph thread ID (no separate mapping field)
2. **Remove message_count** - Don't maintain message count in App DB (can calculate from LangGraph state if needed)
3. **Same MongoDB instance** - Use same MongoDB instance with two databases (can separate later if needed)
4. **Delete message domain model** - Use LangChain's BaseMessage types exclusively
5. **No backward compatibility for messages collection** - Old messages collection will be deprecated after migration

### Assumptions
1. **LangGraph checkpointer is reliable** - Assumes AsyncMongoDBSaver works as documented
2. **Frontend can handle optional message_count** - Assumes frontend gracefully handles missing field
3. **Migration can be done offline** - Assumes downtime acceptable for migration (or implement zero-downtime strategy)
4. **Same MongoDB instance sufficient** - Assumes performance adequate with two databases in same instance
5. **All LLM providers support BaseMessage** - Assumes LangChain providers work with native types

---

## References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [AsyncMongoDBSaver Documentation](https://langchain-ai.github.io/langgraph/reference/checkpoints/#asyncmongodbsaver)
- [LangChain BaseMessage Types](https://python.langchain.com/docs/modules/model_io/messages/)
- [RunnableConfig Documentation](https://python.langchain.com/docs/expression_language/how_to/configure)

---

## Next Steps

1. **Review this plan with Pablo** - Discuss any concerns or questions
2. **Set up development environment** - Ensure all dependencies installed
3. **Create feature branch** - `git checkout -b feature/langgraph-first-architecture`
4. **Begin Phase 1** - Dual database setup
5. **Daily standups** - Track progress and blockers

---

**Plan Version:** 1.0
**Created:** 2025-10-25
**Last Updated:** 2025-10-25
**Author:** Analysis by 8 specialized agents + synthesis
