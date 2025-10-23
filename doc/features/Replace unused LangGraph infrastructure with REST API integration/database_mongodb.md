# Database MongoDB Analysis

## Request Summary

This analysis covers the MongoDB database operations for the feature "Replace unused LangGraph infrastructure with REST API integration" (Issue #4). The task involves replacing the LangGraph-based message orchestration with a direct REST API implementation. The primary database concerns involve:

1. Message creation and persistence
2. Conversation metadata updates (specifically `message_count`)
3. Transaction consistency during message creation and conversation updates
4. Query performance for message retrieval
5. How the current repository patterns will transition from LangGraph node usage to REST API endpoint handling

## Relevant Files & Modules

### Files to Examine

**MongoDB Models & Schemas:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_models.py` - Beanie ODM document models for all collections (UserDocument, ConversationDocument, MessageDocument)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/mongodb.py` - MongoDB connection manager and Beanie initialization
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py` - MongoDB connection settings and configuration

**Repository Implementations:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_message_repository.py` - MongoDB implementation of IMessageRepository (message CRUD operations)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_conversation_repository.py` - MongoDB implementation of IConversationRepository (conversation operations and message_count management)

**Repository Port Interfaces:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/message_repository.py` - IMessageRepository port interface (contract for message operations)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/conversation_repository.py` - IConversationRepository port interface (contract for conversation operations including increment_message_count)

**Domain Models:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/message.py` - Message domain model, MessageRole enum, and message schemas
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/conversation.py` - Conversation domain model and conversation schemas

**Use Cases:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/use_cases/send_message.py` - Business logic for message creation, LLM invocation, and conversation metadata updates
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/use_cases/create_conversation.py` - Business logic for conversation creation
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/use_cases/get_conversation_history.py` - Business logic for retrieving conversation messages with pagination

**API Routers (Inbound Adapters):**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/conversation_router.py` - REST API endpoints for conversation CRUD operations
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_router.py` - REST API endpoints for message retrieval

**LangGraph Infrastructure (to be replaced):**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - LangGraph state schema (lines 1-31)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/save_history.py` - Node that saves messages to database (lines 12-64)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/process_input.py` - Node for input validation
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - Node for LLM invocation
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/format_response.py` - Node for response formatting
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Main graph definition (lines 35-90)

**Tests:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_conversation_api.py` - Integration tests for conversation operations (shows current API patterns)

### Key Functions & Classes

**Document Models:**
- `UserDocument` (mongo_models.py, lines 12-32) - User collection schema with unique indexes on email and username
- `ConversationDocument` (mongo_models.py, lines 35-53) - Conversation collection with user_id index and composite index on (user_id, updated_at)
- `MessageDocument` (mongo_models.py, lines 56-74) - Message collection with conversation_id index and composite index on (conversation_id, created_at)

**Repository Implementations:**
- `MongoMessageRepository.create()` (mongo_message_repository.py, lines 30-48) - Creates individual message documents
- `MongoMessageRepository.get_by_conversation_id()` (mongo_message_repository.py, lines 55-76) - Retrieves paginated messages sorted by creation time
- `MongoMessageRepository.delete_by_conversation_id()` (mongo_message_repository.py, lines 95-109) - Deletes all messages for a conversation
- `MongoConversationRepository.create()` (mongo_conversation_repository.py, lines 31-48) - Creates conversation document
- `MongoConversationRepository.update()` (mongo_conversation_repository.py, lines 73-95) - Updates conversation and its updated_at timestamp
- `MongoConversationRepository.increment_message_count()` (mongo_conversation_repository.py, lines 114-133) - **CRITICAL**: Increments message_count and updates timestamp

**Use Case Implementations:**
- `SendMessage.execute()` (send_message.py, lines 44-87) - Orchestrates user message save, LLM call, assistant message save, and conversation update
- `GetConversationHistory.execute()` (get_conversation_history.py, lines 35-65) - Retrieves paginated messages for a conversation

**LangGraph Database Interaction:**
- `save_to_history()` (save_history.py, lines 12-64) - Node that persists messages to database and increments message_count
  - Lines 43-46: Saves each message individually
  - Lines 50-55: Increments message_count for conversation

## Current Database Overview

### Collections & Schemas

**users Collection**
```
{
  _id: ObjectId,
  email: String (unique index),
  username: String (unique index),
  hashed_password: String,
  full_name: Optional[String],
  is_active: Boolean (default: true),
  created_at: DateTime,
  updated_at: DateTime
}

Indexes:
- Single field: email (unique)
- Single field: username (unique)
```

**conversations Collection**
```
{
  _id: ObjectId,
  user_id: String (indexed),
  title: String (default: "New Conversation"),
  created_at: DateTime,
  updated_at: DateTime,
  message_count: Integer (default: 0)
}

Indexes:
- Single field: user_id
- Composite: [(user_id, 1), (updated_at, -1)] for efficient listing with sort
```

**messages Collection**
```
{
  _id: ObjectId,
  conversation_id: String (indexed),
  role: Enum["user", "assistant", "system"],
  content: String,
  created_at: DateTime,
  metadata: Optional[Object]
}

Indexes:
- Single field: conversation_id
- Composite: [(conversation_id, 1), (created_at, 1)] for efficient sorting in history retrieval
```

### Indexes

**Optimization Strategy:**

The schema uses a two-tier indexing approach:

1. **Single-field indexes** for basic lookups:
   - `user_id` on conversations (used in get_by_user_id queries)
   - `conversation_id` on messages (used in conversation_id lookups)

2. **Composite indexes** for covered queries:
   - `(user_id, updated_at DESC)` on conversations - Covers the list_conversations query without additional lookups
   - `(conversation_id, created_at ASC)` on messages - Covers message history retrieval with natural chronological ordering

**Query Coverage Analysis:**

| Query | Index Used | Notes |
|-------|-----------|-------|
| Find conversation by ID | `_id` (primary key) | MongoDB uses _id index automatically |
| List conversations by user | `(user_id, -updated_at)` | Covered query, single index lookup |
| Find messages by conversation | `(conversation_id, created_at)` | Covered query with natural sort order |
| Increment message_count | None (document update) | Updates _id lookup then modifies document |
| Delete conversation | `_id` (primary key) | Uses MongoDB primary key |

### Repository Layer

**Pattern: Document-to-Domain Mapping**

All repositories follow the same pattern:

```python
# Domain model conversion (e.g., MongoMessageRepository._to_domain, line 19-28)
doc: MessageDocument → Message (domain model)
  - Converts ObjectId to string (id=str(doc.id))
  - Maps all fields 1:1
  - No data transformation or calculation

# CRUD Operations follow standard Beanie patterns
create():    await doc.insert()
get():       await MessageDocument.get(id)
find():      await MessageDocument.find().to_list()
update():    await doc.save()
delete():    await doc.delete()
```

**No Transaction Support**

The current Beanie implementation does not use MongoDB transactions. Each operation is atomic at the document level but not coordinated across multiple documents:

- Message creation: Single insert (atomic)
- Conversation update: Single document update (atomic)
- Message count increment: Single document update (atomic)
- BUT: Creating 2 messages + incrementing count = 3 separate operations (no ACID guarantee)

### Query Patterns

**Message Retrieval with Pagination (message_router.py, lines 20-69):**

```python
# Read the conversation first (validation)
conversation = await conversation_repository.get_by_id(conversation_id)

# Retrieve paginated messages, ordered by creation time
messages = await message_repository.get_by_conversation_id(
    conversation_id=conversation_id,
    skip=skip,
    limit=limit
)
# Uses index: (conversation_id, created_at)
# Beanie query: MessageDocument.find(...).sort(...).skip(...).limit(...)
```

**Conversation List with Sorting (conversation_router.py, lines 19-48):**

```python
# Retrieve user's conversations, sorted by most recent update
conversations = await conversation_repository.get_by_user_id(
    user_id=current_user.id,
    skip=skip,
    limit=limit
)
# Uses index: (user_id, -updated_at)
# Beanie query: ConversationDocument.find(...).sort(-ConversationDocument.updated_at)
```

**Message Count Update (mongo_conversation_repository.py, lines 114-133):**

```python
doc = await ConversationDocument.get(conversation_id)
if not doc:
    return None

doc.message_count += count  # In-memory increment
doc.updated_at = datetime.utcnow()
await doc.save()  # Single document write
```

## Impact Analysis

### Current LangGraph Message Flow

The `save_to_history` node (lines 12-64 of save_history.py) currently handles:

1. **Individual message saves** (lines 43-46):
   ```python
   for message in messages:
       await message_repository.create(message)
   ```
   - Saves user message
   - Saves assistant message
   - 2 separate insert operations

2. **Conversation metadata update** (lines 50-55):
   ```python
   await conversation_repository.increment_message_count(conversation_id, len(messages))
   ```
   - Increments by 2 (user + assistant message)
   - Updates updated_at timestamp
   - 1 separate update operation

3. **Error handling** (lines 33-64):
   - Graceful error handling without flow disruption
   - Errors logged but don't fail the entire operation

### REST API Replacement Impact

**Current SendMessage Use Case (send_message.py, lines 44-87):**

```python
# 1. Create user message
await self.message_repository.create(user_message)

# 2. Retrieve history for LLM context
messages = await self.message_repository.get_by_conversation_id(conversation_id)

# 3. Call LLM (external service - outside database scope)
response = await self.llm_provider.generate(messages)

# 4. Create assistant message
await self.message_repository.create(assistant_message)

# 5. Update conversation metadata
await self.conversation_repository.increment_message_count(conversation_id, 2)
```

**Issues with Current Implementation:**

1. **No transaction consistency**: If step 4 fails after step 1, user message exists but assistant message doesn't, and message_count is not incremented
2. **Race condition potential**: Between steps 3-5, another request could modify the conversation
3. **Message count accuracy**: The increment relies on application logic, not database constraints

### New REST API Endpoint Requirements

To replace LangGraph, a new REST endpoint will be created that:

```
POST /api/conversations/{conversation_id}/send-message
{
  "content": "user message text"
}
```

This endpoint must:

1. Create user message in `messages` collection
2. Retrieve conversation history from `messages` collection
3. Call external LLM provider
4. Create assistant message in `messages` collection
5. Update `conversations.message_count` and `updated_at`
6. Return the assistant message to the client

**Database Operations Required:**

- Insert: 2 messages (user + assistant)
- Read: 1 conversation lookup + message history retrieval
- Update: 1 conversation update (message_count + updated_at)

## Database Recommendations

### Proposed Schema Changes

**No schema changes required.** The current schema is well-designed for this use case:

- `MessageDocument` has all required fields for REST API response
- `ConversationDocument` correctly tracks message_count for conversation summaries
- Indexes cover all query patterns needed

### Proposed Indexes

**No new indexes required.** Current indexes are optimal:

| Index | Purpose | Used By |
|-------|---------|---------|
| `users: (email, username)` | User lookups | Authentication |
| `conversations: (user_id)` | Filter by owner | Authorization checks |
| `conversations: (user_id, -updated_at)` | List user conversations | REST GET /api/conversations |
| `messages: (conversation_id)` | Filter by conversation | Authorization checks |
| `messages: (conversation_id, created_at)` | Get message history | REST GET /api/conversations/{id}/messages |

### Repository Changes

**No changes to repository interfaces required.** The `IMessageRepository` and `IConversationRepository` ports already provide all necessary operations:

- `message_repository.create(message_data)` - Insert message ✓
- `message_repository.get_by_conversation_id(conversation_id)` - Retrieve history ✓
- `conversation_repository.get_by_id(conversation_id)` - Validate conversation exists ✓
- `conversation_repository.increment_message_count(conversation_id, 2)` - Update metadata ✓

**Consideration: Transaction Support**

Evaluate whether to add transaction support by:

1. **Option A (Recommended for now)**: Keep current atomic-per-document pattern
   - Use MongoDB's default isolation level (read committed)
   - Accept that race conditions are possible but unlikely in practice
   - Document this limitation for future scaling

2. **Option B (For future high-load scenarios)**: Add transaction wrapper
   ```python
   async def create_message_with_conversation_update(
       self,
       conversation_id: str,
       user_message: MessageCreate,
       assistant_message: MessageCreate
   ) -> tuple[Message, Message, Conversation]:
       """
       Create two messages and update conversation in a single transaction.
       Requires MongoDB 4.0+ replica set.
       """
       async with await AsyncIOMotorClient.start_session() as session:
           async with session.start_transaction():
               # Operations here are atomic
   ```

### Query Optimization

**Current Performance is Good**

All queries use covered indexes:

1. **Message history retrieval** - O(log n) index lookup + O(k) scan of k results
   - Query: `{ conversation_id: id }` + `SORT created_at` + `LIMIT 100`
   - Index: `(conversation_id, created_at)`
   - Result: No collection scans, efficient pagination

2. **Conversation listing** - O(log n) index lookup + O(k) scan of k results
   - Query: `{ user_id: id }` + `SORT -updated_at` + `LIMIT 100`
   - Index: `(user_id, -updated_at)`
   - Result: No collection scans, efficient pagination

3. **Conversation update** - O(log n) index lookup + O(1) document write
   - Query: `{ _id: ObjectId }` + `UPDATE message_count, updated_at`
   - Index: Primary `_id` index
   - Result: Direct document access, single write operation

**No N+1 Query Issues**

- Message history is fetched in single query (not per-message lookups)
- Conversation listing is single query with join on user_id
- No nested population of related documents required

## Implementation Guidance

### Step 1: Create New REST Message Send Endpoint

Location: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_router.py`

Add endpoint:
```
POST /api/conversations/{conversation_id}/send-message
```

This endpoint will:
1. Extract conversation_id from path
2. Extract message content from request body
3. Call existing `SendMessage` use case (which already exists in send_message.py)
4. Return the assistant message response

**Database Impact**: Uses existing repositories, no changes needed

### Step 2: Verify SendMessage Use Case is Correct

Location: `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/use_cases/send_message.py`

Review lines 44-87 to ensure:
- User message is created (line 70)
- Conversation history is retrieved (lines 72-74)
- LLM is called with history (line 76)
- Assistant message is created (lines 83)
- Conversation message_count is incremented by 2 (line 85)
- Assistant message is returned (line 87)

**Database Impact**: This use case already handles all database operations correctly

### Step 3: Update API Router for Message Creation

The `send` endpoint should NOT go in message_router.py (which is read-only) but rather:

Option A: Create new endpoint in a send_message router or in conversation_router.py

Option B: Add to conversation_router.py under the conversation object:
```
POST /api/conversations/{conversation_id}/send-message
```

### Step 4: Test Database Consistency

Add integration tests (in test_conversation_api.py or new test file) to verify:

1. **Message creation succeeds**:
   ```python
   response = await client.post(
       f"/api/conversations/{conversation_id}/send-message",
       json={"content": "Hello"},
       headers=headers
   )
   assert response.status_code == 201
   assert response.json()["role"] == "assistant"
   ```

2. **Message count increments by 2**:
   ```python
   await client.post(f"/api/conversations/{conversation_id}/send-message", ...)
   conversation = await client.get(f"/api/conversations/{conversation_id}")
   assert conversation.json()["message_count"] == 2
   ```

3. **Both messages are retrievable**:
   ```python
   messages = await client.get(f"/api/conversations/{conversation_id}/messages")
   assert len(messages.json()) == 2
   assert messages.json()[0]["role"] == "user"
   assert messages.json()[1]["role"] == "assistant"
   ```

4. **Updated timestamp is current**:
   ```python
   conv = await client.get(f"/api/conversations/{conversation_id}")
   updated_at = datetime.fromisoformat(conv.json()["updated_at"].replace('Z', '+00:00'))
   assert updated_at > original_updated_at
   ```

## Risks and Considerations

### 1. Transaction Consistency Risk (MEDIUM)

**Problem**: No ACID transactions across multiple collections

**Scenario**:
- User message created successfully
- LLM call fails
- Assistant message never created
- But user message persists in database

**Current Impact**: Low, because:
- LLM failures are handled gracefully in use case
- User message without assistant response is valid state
- Message count won't be wrong if message isn't created

**Mitigation**:
- Keep current atomic-per-document approach
- Document in code that orphaned messages may exist
- Consider adding cleanup logic if message_count doesn't match actual message count

### 2. Race Condition Risk (MEDIUM)

**Problem**: Between steps 1 and 5, another request could modify message_count

**Scenario**:
- Thread A: User message created (message_count = 0)
- Thread B: User message created + assistant created + count incremented to 2
- Thread A: Increment count by 2 → overwrites to 2 (should be 4)

**Current Impact**: Low to Medium, depends on traffic load

**Mitigation**:
- MongoDB 4.0+ supports transactions; consider implementing for high-traffic scenarios
- For now, document this limitation in README
- Monitor message_count accuracy in production

### 3. Message History Performance Risk (LOW)

**Problem**: As conversation grows, message history retrieval could slow down

**Current State**:
- 100 message limit (default)
- Composite index: `(conversation_id, created_at)`
- No pagination issues identified

**Mitigation**:
- Current pagination limit of 100 is reasonable
- Index is optimal
- Monitor query performance with large conversations (1000+ messages)

### 4. LangGraph Dependency Removal (HIGH IMPACT)

**What's being removed**:
- `/app/langgraph/` directory
- All LangGraph nodes (process_input, call_llm, format_response, save_to_history)
- LangGraph graph definitions
- ConversationState TypedDict

**What remains**:
- Repository layer (unchanged)
- Use cases (unchanged)
- Domain models (unchanged)
- REST API (to be created/updated)

**No database impact**, as LangGraph only orchestrated the use cases; database operations remain the same

### 5. Message Metadata Field (MEDIUM)

**Current State**: `MessageDocument.metadata` is optional dict field (line 67 of mongo_models.py)

**REST API Consideration**:
- Should REST endpoint accept metadata in request?
- Currently, metadata is populated by LLM providers (token counts, etc.)
- REST API may not have metadata to store initially
- Option: Allow optional metadata in request, default to None

## Testing Strategy

### Unit Tests

**Repository Layer** (test mongo_models.py):
```python
# Ensure indexes are defined correctly
assert "email" in UserDocument.Settings.indexes
assert ("user_id", -1), ("updated_at", -1) in ConversationDocument.Settings.indexes
```

**Use Case** (test send_message.py):
```python
# Mock repositories, test business logic
async def test_send_message_increments_count_by_2():
    message_repo = MockMessageRepository()
    conversation_repo = MockConversationRepository()
    llm_provider = MockLLMProvider()

    use_case = SendMessage(message_repo, conversation_repo, llm_provider)
    result = await use_case.execute(conversation_id, "test message")

    # Verify 2 messages created
    assert message_repo.create.call_count == 2
    # Verify count incremented by 2
    assert conversation_repo.increment_message_count.call_args[0][1] == 2
```

### Integration Tests

**API Endpoint** (add to test_conversation_api.py):
```python
async def test_send_message_endpoint():
    """Test the new send-message REST endpoint"""
    headers = await create_user_and_login(client)
    conv = await client.post("/api/conversations", ...)
    conversation_id = conv.json()["id"]

    response = await client.post(
        f"/api/conversations/{conversation_id}/send-message",
        json={"content": "Hello, assistant"},
        headers=headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "assistant"
    assert "content" in data

    # Verify conversation message count
    conv_check = await client.get(f"/api/conversations/{conversation_id}", headers=headers)
    assert conv_check.json()["message_count"] == 2
```

**Message Order** (ensure created_at ordering):
```python
async def test_message_history_ordered_by_created_at():
    """Verify messages returned in chronological order"""
    # Create multiple messages
    for i in range(5):
        await client.post(f"/api/conversations/{conv_id}/send-message", ...)

    messages = await client.get(f"/api/conversations/{conv_id}/messages", headers=headers)
    data = messages.json()

    # Verify timestamps are ascending
    for i in range(len(data) - 1):
        current = datetime.fromisoformat(data[i]["created_at"])
        next_msg = datetime.fromisoformat(data[i+1]["created_at"])
        assert current <= next_msg
```

### Load Testing

**Message Creation Under Load**:
```python
# Test race conditions with concurrent requests
import asyncio

async def stress_test():
    """Create messages concurrently to test race conditions"""
    tasks = []
    for i in range(10):
        task = client.post(
            f"/api/conversations/{conv_id}/send-message",
            json={"content": f"Message {i}"}
        )
        tasks.append(task)

    await asyncio.gather(*tasks)

    # Verify all messages exist
    messages = await client.get(f"/api/conversations/{conv_id}/messages")
    assert len(messages.json()) >= 20  # 10 pairs of user + assistant

    # Verify message count is correct
    conv = await client.get(f"/api/conversations/{conv_id}")
    assert conv.json()["message_count"] >= 20
```

## Code References with Line Numbers

### Critical Database Operations

| Operation | File | Lines | Purpose |
|-----------|------|-------|---------|
| Message insert | mongo_message_repository.py | 40-47 | Create new message document |
| Message retrieval | mongo_message_repository.py | 72-76 | Fetch paginated messages with sort |
| Message count increment | mongo_conversation_repository.py | 129-131 | Update conversation metadata |
| Conversation update | mongo_conversation_repository.py | 88-93 | Save changes and update timestamp |
| Use case orchestration | send_message.py | 70, 83, 85 | Coordinate 3 separate database calls |
| LangGraph persistence | save_history.py | 43-55 | Current database write pattern |
| Index definition | mongo_models.py | 50-52, 72-74 | Composite indexes for query optimization |
| Beanie initialization | mongodb.py | 33-36 | Register document models and create indexes |
| Settings | settings.py | 27-29 | MongoDB connection configuration |

### Key Classes & Methods

```
MongoMessageRepository:
  - create(message_data) → Message [insert operation]
  - get_by_conversation_id(conversation_id, skip, limit) → List[Message] [read with index]
  - delete_by_conversation_id(conversation_id) → int [bulk delete]

MongoConversationRepository:
  - create(user_id, conversation_data) → Conversation [insert]
  - update(conversation_id, conversation_data) → Conversation [update with timestamp]
  - increment_message_count(conversation_id, count) → Conversation [atomic increment]
  - get_by_user_id(user_id, skip, limit) → List[Conversation] [read with composite index]

SendMessage Use Case:
  - execute(conversation_id, user_message_content) → Message [orchestrates 5 ops]

ConversationDocument:
  - message_count: int [tracks count without querying messages collection]
  - updated_at: datetime [for sorting in list operations]
  - Composite index: (user_id, -updated_at) [enables efficient listing]

MessageDocument:
  - conversation_id: str [groups messages by conversation]
  - created_at: datetime [natural sort order for history]
  - Composite index: (conversation_id, created_at) [enables efficient retrieval]
```

## Summary

The MongoDB database architecture is well-designed for the REST API transition. The current schema, indexes, and repository patterns require no changes. The `SendMessage` use case already correctly handles the necessary database operations. The main task is creating a new REST endpoint that calls the existing use case, which will transparently use the same repository layer.

**Critical Points for Implementation**:

1. **No schema changes needed** - Current model supports all REST requirements
2. **No index changes needed** - Composite indexes are optimal for all queries
3. **No repository interface changes** - All required operations exist
4. **Transaction consistency trade-off** - Accept atomic-per-document model for now; document limitation
5. **Keep SendMessage use case** - It already orchestrates database operations correctly
6. **Test thoroughly** - Focus on consistency between user+assistant message creation and count increment

**Next Steps**:

1. Create REST endpoint that calls `SendMessage` use case
2. Add integration tests for message creation and conversation updates
3. Verify message ordering with composite index
4. Monitor message_count accuracy in production
5. Document transaction limitation in README for future reference
