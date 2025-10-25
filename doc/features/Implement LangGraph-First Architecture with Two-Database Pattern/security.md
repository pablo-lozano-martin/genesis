# Security Analysis

## Request Summary

This refactor proposes transitioning from a single MongoDB database to a two-database pattern where:
- **App Database (MongoDB)**: Stores user accounts, conversation metadata, and ownership information
- **LangGraph Database**: Stores message history and conversation state (LangGraph's persistence layer)

This architectural change has significant security implications because:
1. Conversation ownership verification depends on querying the App DB
2. Message access control must be enforced across two separate databases
3. Thread ID mapping between conversation.id and LangGraph's thread_id must be secure
4. Database credentials and connection management must be properly isolated

## Relevant Files & Modules

### Files to Examine

#### Authentication & Authorization
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/security/auth_service.py` - JWT token generation and validation using bcrypt
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/security/dependencies.py` - OAuth2 authentication dependencies for REST endpoints
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/security/websocket_auth.py` - WebSocket-specific authentication handling

#### Conversation & Message Access Control
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/conversation_router.py` - REST endpoints with conversation ownership checks (lines 78-113)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_router.py` - GET messages endpoint with authorization (lines 20-69)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket chat with access control (lines 107-117)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_router.py` - WebSocket endpoint setup with auth integration

#### Repository/Database Access Patterns
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_conversation_repository.py` - Conversation persistence (all methods)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_message_repository.py` - Message persistence (all methods)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_models.py` - Beanie document models with indexes

#### LangGraph Integration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - Conversation state schema (lines 10-30)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Chat graph orchestration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/` - All node implementations (process_input, call_llm, format_response, save_history)

#### Domain Models
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/conversation.py` - Conversation entity with user_id field (line 18)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/message.py` - Message entity with conversation_id field (line 28)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/user.py` - User entity

#### Configuration & Database
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py` - Environment-based settings (mongodb_url, mongodb_db_name)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/mongodb.py` - MongoDB connection lifecycle management

### Key Functions & Classes

**Authentication Flow:**
- `AuthService.create_access_token()` in auth_service.py (lines 53-70) - JWT creation
- `AuthService.verify_token()` in auth_service.py (lines 72-90) - JWT verification
- `get_current_user()` in dependencies.py (lines 19-53) - REST authentication dependency
- `get_user_from_websocket()` in websocket_auth.py (lines 16-82) - WebSocket authentication

**Authorization Checks:**
- `get_conversation()` in conversation_router.py (lines 78-113) - Verifies user owns conversation
- `get_conversation_messages()` in message_router.py (lines 20-69) - Verifies conversation ownership before returning messages
- `handle_websocket_chat()` in websocket_handler.py (lines 107-117) - Conversation ownership check in WebSocket handler

**Repository Access:**
- `MongoConversationRepository.get_by_id()` in mongo_conversation_repository.py (lines 50-53) - Fetches conversation by ID
- `MongoMessageRepository.get_by_conversation_id()` in mongo_message_repository.py (lines 55-76) - Fetches messages by conversation ID
- `MongoConversationRepository.get_by_user_id()` in mongo_conversation_repository.py (lines 55-71) - Queries conversations by user

**LangGraph State Management:**
- `ConversationState` in langgraph/state.py (lines 10-30) - Contains conversation_id, user_id, and messages
- `create_chat_graph()` in langgraph/graphs/chat_graph.py (lines 35-90) - Graph compilation and node binding

## Current Security Overview

### Authentication Mechanism

**Current Implementation:**
- JWT tokens (HS256 algorithm) issued via OAuth2 password flow
- Token claims: `sub` (user_id), `exp` (expiration), `type` (access)
- Tokens extracted from Authorization header or query parameters
- Default expiration: 30 minutes
- Token verification on every authenticated request/WebSocket connection

**Files Involved:**
- JWT creation: `backend/app/infrastructure/security/auth_service.py:53-70`
- JWT verification: `backend/app/infrastructure/security/auth_service.py:72-90`
- REST endpoint protection: `backend/app/infrastructure/security/dependencies.py:19-53`
- WebSocket protection: `backend/app/infrastructure/security/websocket_auth.py:16-82`

**Strengths:**
- Stateless JWT tokens enable scalability
- Secrets managed via environment variables (`secret_key` from settings)
- User activity status checked (`is_active` field)
- Clear error messages distinguish between auth and authorization failures

**Weaknesses:**
- No token rotation mechanism in place
- WebSocket tokens exposed in query parameters (can appear in logs, browser history)
- No rate limiting on login attempts
- Single database stores both sensitive credentials (hashed) and conversation data

### Authorization Mechanism

**Current Pattern - Conversation Ownership Verification:**

Pattern repeated across three locations:
1. REST GET conversation (conversation_router.py:99-104)
2. REST GET messages (message_router.py:44-49)
3. WebSocket handler (websocket_handler.py:110-117)

```python
# Typical pattern:
conversation = await conversation_repository.get_by_id(conversation_id)
if not conversation or conversation.user_id != current_user.id:
    raise HTTPException(status_code=403, detail="Access denied")
```

**Files Involved:**
- Conversation access: `backend/app/adapters/inbound/conversation_router.py:99-104`
- Message access: `backend/app/adapters/inbound/message_router.py:44-49`
- WebSocket access: `backend/app/adapters/inbound/websocket_handler.py:110-117`

**Strengths:**
- Ownership check is explicit and readable
- Check happens before returning any data
- Consistent pattern across endpoints

**Weaknesses:**
- Ownership verification requires App DB query for every message retrieval
- No caching of conversation ownership metadata
- Direct user_id comparison vulnerable to timing attacks (though risk is minimal)
- Message repository doesn't verify ownership - relies entirely on caller to check conversation ownership

### Data Protection

**Sensitive Data Handling:**

| Data Type | Storage | Protection |
|-----------|---------|-----------|
| Passwords | App DB (MongoDB) | Bcrypt hashing (12 rounds via passlib) |
| JWT Tokens | Client-side (header/cookie) | Token expiration, HTTPS required in production |
| Message Content | App DB (MongoDB) | At rest: MongoDB's default encryption (optional) |
| User IDs | Both databases | Plaintext (database IDs are non-secret) |
| Conversation IDs | Both databases | Plaintext (UUIDs in App DB) |

**Files Involved:**
- Password hashing: `backend/app/infrastructure/security/auth_service.py:28-38`
- User model: `backend/app/core/domain/user.py`
- Message model: `backend/app/core/domain/message.py`

### Security Middleware & Validation

**Input Validation:**
- Pydantic models enforce schema validation for all inputs
- Message content: min_length=1 (message.py:30)
- Conversation title: max_length=200 (conversation.py:19)
- Pagination: limits enforced (skip >= 0, limit 1-100 for conversations, 1-500 for messages)

**CORS Configuration:**
- Configured in settings.py (lines 56-61)
- Allows localhost:3000, localhost:5173, frontend:3000, frontend:5173

**Error Handling:**
- Generic "Access denied" (403) and "Not found" (404) messages to prevent enumeration
- WebSocket errors include specific codes (ACCESS_DENIED, INVALID_FORMAT, LLM_ERROR)
- Detailed errors logged server-side, generic messages to clients

**Logging:**
- Authentication events logged at INFO level
- Failed authentication attempts logged at WARNING level
- Error conditions logged at ERROR level
- No sensitive data (passwords, tokens) logged

## Impact Analysis

### Critical Security Implications of Two-Database Pattern

The shift to two-database pattern creates four new security concerns:

#### 1. Conversation Ownership Verification Dependency

**Current State (Single MongoDB):**
- Conversation metadata and ownership are in same database as messages
- Ownership check is a single query: `ConversationDocument.get(conversation_id)`
- Response contains `user_id` immediately

**New State (App DB + LangGraph DB):**
- Conversation ownership in App DB (MongoDB)
- Message data in LangGraph DB
- Ownership check requires App DB query
- Thread ID mapping must be maintained to connect conversation.id to LangGraph thread_id

**Risk Factors:**
- **Database coupling**: Message access now depends on two separate databases being consistent
- **Stale data**: If App DB copy of conversation is deleted but messages remain in LangGraph DB, orphaned data exists
- **Query overhead**: Ownership check adds latency for every message access
- **Consistency gap**: Race condition where conversation is deleted in App DB but user continues accessing messages in LangGraph DB

**Affected Components:**
- `message_router.py:35-49` - Must query App DB before accessing LangGraph DB
- `websocket_handler.py:107-117` - Must verify ownership before processing WebSocket messages
- New LangGraph database adapter (to be created)

#### 2. Thread ID Mapping & Access Control

**New Requirement:**
LangGraph uses thread_id to organize conversations in its checkpointer. Need bidirectional mapping:
- conversation.id (App DB) ↔ thread_id (LangGraph DB)

**Security Attack Vectors:**
1. **Direct thread_id access**: Attacker guesses/increments thread_id to access other users' conversations
   - LangGraph checkpointers may auto-increment or use sequential IDs
   - No built-in user ownership concept in LangGraph

2. **Conversation ID enumeration**: Attacker enumerates conversation IDs, bypassing thread_id entirely
   - If conversation IDs are sequential UUIDs with weak generation, can be guessed
   - Ownership check must still be enforced for every access

3. **Thread_id exposure**: Thread_id leaked in error messages, logs, or network responses
   - Different from conversation_id; attacker gains direct access path

**Required Controls:**
- Explicit thread_id → conversation.id → user.id validation chain for every access
- Cannot assume LangGraph checkpointer provides any access control
- Thread ID must not be exposed to clients

#### 3. Database Credential Management

**Current State (Single MongoDB):**
- Single `mongodb_url` and `mongodb_db_name` in settings
- Single connection pool managed by Motor/Beanie
- Single set of credentials (username/password in connection string)

**New State (App DB + LangGraph DB):**
- Potentially separate MongoDB instance for LangGraph (if using MongoDB checkpointer)
- Potentially different credentials for each database
- Two separate connection pools needed

**Security Requirements:**
- Separate credentials for each database (principle of least privilege)
- Each database connection should have minimal required permissions
  - App DB connection: read/write users, conversations; read messages (for deletion)
  - LangGraph DB connection: read/write thread data only
- Credential rotation strategy needed for both databases
- Connection pooling must be independent and properly closed

**Configuration Files Affected:**
- `backend/app/infrastructure/config/settings.py` - Add LangGraph database settings
- `backend/app/infrastructure/database/mongodb.py` - Manage two connections separately

#### 4. Data Consistency & Integrity

**Problem Scenarios:**

Scenario 1: Conversation Deletion
```
1. User deletes conversation via REST API
2. App DB delete: conversation and messages removed
3. LangGraph DB deletion delayed or fails
4. Thread_id references orphaned data in LangGraph DB
5. If user is deleted, orphaned thread remains accessible to admins
```

Scenario 2: Message Retrieval Consistency
```
1. User fetches conversation messages via REST
2. Message router queries App DB: ownership OK
3. Message count = 5
4. LangGraph DB queries for messages: returns 3 (sync lag)
5. Client receives inconsistent state
```

Scenario 3: Thread_id Mapping Corruption
```
1. Conversation created in App DB, thread_id allocated in LangGraph
2. Mapping stored in App DB conversation document
3. Conversation document corrupted/lost
4. Thread_id becomes orphaned, unrecoverable
```

## Security Recommendations

### 1. Secure Conversation → Thread_ID Mapping Pattern

**Recommended Design:**

```
App Database (MongoDB):
  ConversationDocument {
    id: ObjectId                    # Primary key
    user_id: str                    # Foreign key to user
    title: str
    thread_id: str                  # REFERENCE to LangGraph thread
    created_at: datetime
    updated_at: datetime
    message_count: int
  }

Authorization Flow:
  1. Client provides conversation_id
  2. Query App DB: conversation = find_by_id(conversation_id)
  3. Verify: conversation.user_id == current_user.id
  4. Extract: thread_id = conversation.thread_id
  5. Query LangGraph: messages = get_by_thread_id(thread_id)
  6. Return authorized messages
```

**Security Properties:**
- User ownership verification always happens first
- Thread_id never exposed to client
- Cannot access LangGraph data without valid conversation_id and ownership
- Conversation deletion triggers thread_id cleanup (see deletion strategy below)

**Implementation Guidance:**
- Add `thread_id: Optional[str]` field to ConversationDocument
- Do NOT expose thread_id in ConversationResponse API schemas
- Store thread_id only for internal routing, never in API responses
- Create unique index on thread_id to prevent duplicates

### 2. Ensure All LangGraph State Access is Authorized

**Pattern: Authorization Guard Before LangGraph Access**

Every interaction with LangGraph must follow this pattern:

```python
@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    current_user: CurrentUser,
    conversation_repo: IConversationRepository,
    langgraph_repo: ILangGraphRepository  # New adapter
):
    # Step 1: Verify conversation exists AND user owns it
    conversation = await conversation_repo.get_by_id(conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(403, "Access denied")

    # Step 2: Now safe to access LangGraph using thread_id
    thread_id = conversation.thread_id
    messages = await langgraph_repo.get_messages(thread_id)

    return messages
```

**Critical Rules:**
1. NEVER accept thread_id directly from clients
2. NEVER skip ownership check to optimize performance
3. ALWAYS verify current_user.id matches conversation.user_id
4. Log access attempts with conversation_id and user_id for audit trail
5. Never expose thread_id in error messages or responses

**WebSocket-Specific Pattern:**

For WebSocket `/ws/chat`:
```python
async def handle_websocket_chat(websocket, user, conversation_id):
    # At connection time:
    conversation = await conversation_repo.get_by_id(conversation_id)
    if not conversation or conversation.user_id != user.id:
        raise WebSocketException("Access denied")

    # Store thread_id for duration of connection
    thread_id = conversation.thread_id

    # All subsequent messages use this thread_id
    # Client CANNOT change conversation_id mid-connection
```

**Files to Modify:**
- `backend/app/adapters/inbound/message_router.py` - Add thread_id resolution
- `backend/app/adapters/inbound/websocket_handler.py` - Require conversation_id at connect time
- `backend/app/langgraph/` - All nodes must receive authorized thread_id, not accept client input

### 3. Database Connection Security for Dual Setup

**Credential Isolation:**

```python
# settings.py - Add separate database configurations

class Settings(BaseSettings):
    # App Database (User, Conversation, Message metadata)
    app_db_url: str  # MongoDB URL for app data
    app_db_name: str = "genesis_app"

    # LangGraph Database (Message history, thread state)
    langgraph_db_url: str  # Separate MongoDB or other backend
    langgraph_db_name: str = "genesis_langgraph"
```

**Connection Management:**

```python
# database.py - Separate connection managers

class AppDatabase:
    """Manages App DB connection (users, conversations)."""
    client = None
    database = None

    @classmethod
    async def connect(cls):
        # Minimal permissions: read users, full access to conversations/messages
        cls.client = AsyncIOMotorClient(settings.app_db_url)
        cls.database = cls.client[settings.app_db_name]
        # Initialize only User, Conversation, Message models

class LangGraphDatabase:
    """Manages LangGraph DB connection (thread history)."""
    client = None

    @classmethod
    async def connect(cls):
        # Minimal permissions: read/write thread data only
        # No access to user or conversation collections
        cls.client = AsyncIOMotorClient(settings.langgraph_db_url)
        cls.database = cls.client[settings.langgraph_db_name]
```

**Security Properties:**
- Each database has isolated credentials
- Connection pooling is independent
- Compromise of LangGraph credentials doesn't expose user/conversation data
- Can be deployed to separate MongoDB instances for defense-in-depth

**Implementation:**
- Create new `LangGraphRepository` adapter implementing `ILangGraphRepository` port
- Inject both `AppDatabase` and `LangGraphDatabase` into handlers
- Separate Beanie initialization for each database

### 4. Conversation Deletion with Cascade Cleanup

**Challenge:**
When user deletes a conversation, both databases must be synchronized.

**Recommended Pattern:**

```python
# conversation_router.py - DELETE endpoint

@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: CurrentUser,
    conversation_repo: IConversationRepository,
    langgraph_repo: ILangGraphRepository,
    message_repo: IMessageRepository
):
    # Step 1: Fetch and verify ownership
    conversation = await conversation_repo.get_by_id(conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(403, "Access denied")

    thread_id = conversation.thread_id

    # Step 2: Delete from LangGraph DB
    try:
        await langgraph_repo.delete_thread(thread_id)
    except Exception as e:
        logger.error(f"Failed to delete thread {thread_id}: {e}")
        raise HTTPException(500, "Deletion failed")

    # Step 3: Delete from message repository (if stored in App DB)
    await message_repo.delete_by_conversation_id(conversation_id)

    # Step 4: Delete from conversation repository
    await conversation_repo.delete(conversation_id)

    return {"status": "deleted"}
```

**Error Handling Strategy:**
- If LangGraph deletion fails, abort entire operation and return error
- Do NOT delete from App DB if LangGraph deletion fails
- Ensure idempotence: can safely retry if some deletions fail
- Log all deletion attempts for audit trail

**Alternative: Soft Deletes**
If data recovery is required:
```python
class ConversationDocument:
    # ... existing fields
    deleted_at: Optional[datetime] = None  # NULL = active

# Query always filters: deleted_at is None
# Cannot access deleted conversations even with valid thread_id
```

### 5. WebSocket Authentication with Thread_ID Configuration

**Current Implementation Issue:**
WebSocket endpoint currently accepts `conversation_id` in message payload, but should validate at connection time.

**Recommended Design:**

```python
# websocket_router.py

@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    conversation_id: str  # Now in URL path, not negotiable per-message
):
    # Step 1: Authenticate user
    user = await get_user_from_websocket(websocket)

    # Step 2: Authorize conversation access
    conversation = await conversation_repo.get_by_id(conversation_id)
    if not conversation or conversation.user_id != user.id:
        await websocket.close(code=1008, reason="Access denied")
        return

    # Step 3: Extract thread_id and lock for duration of connection
    thread_id = conversation.thread_id

    # Step 4: Handle chat with authorized thread_id
    await handle_websocket_chat(
        websocket=websocket,
        user=user,
        conversation_id=conversation_id,
        thread_id=thread_id
    )
```

**Client Usage:**
```
OLD: ws://localhost:8000/ws/chat?token=xxx
     Client sends: {"type": "message", "conversation_id": "123", "content": "hi"}

NEW: ws://localhost:8000/ws/chat/123?token=xxx
     Client sends: {"type": "message", "content": "hi"}
     (conversation_id is implicit in URL path)
```

**Security Benefits:**
- Conversation_id fixed at WebSocket connection time
- Cannot switch conversations mid-connection
- Cleaner separation of authentication (URL) and authorization (connection handler)
- Prevents accidental conversation_id typos from accessing wrong conversation

### 6. LangGraph Database Adapter (New Port & Adapter)

**Port Definition:**

```python
# backend/app/core/ports/langgraph_repository.py

from typing import List, Optional
from app.core.domain.message import Message

class ILangGraphRepository:
    """Interface for accessing LangGraph message history."""

    async def get_messages(
        self,
        thread_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        """Retrieve messages for a thread."""
        pass

    async def save_state(
        self,
        thread_id: str,
        state: dict
    ) -> None:
        """Persist conversation state."""
        pass

    async def delete_thread(
        self,
        thread_id: str
    ) -> bool:
        """Delete all messages for a thread."""
        pass
```

**Adapter Implementation:**

```python
# backend/app/adapters/outbound/repositories/langgraph_repository.py

class LangGraphRepository(ILangGraphRepository):
    """Adapter for LangGraph message persistence."""

    def __init__(self, database):
        self.db = database

    async def get_messages(self, thread_id: str, skip: int = 0, limit: int = 100):
        # Query LangGraph checkpointer
        # Convert to Message domain models
        pass

    async def delete_thread(self, thread_id: str) -> bool:
        # Delete all thread history
        pass
```

**Key Property:**
- Does NOT perform user authorization
- Assumes caller has already verified access rights
- Takes thread_id only (never conversation_id)

## Testing Security Boundaries Thoroughly

### Unit Tests for Authorization

```python
# tests/unit/test_conversation_authorization.py

async def test_user_cannot_access_other_user_conversation():
    """User B cannot access User A's conversation."""
    user_a = create_test_user("a@test.com")
    user_b = create_test_user("b@test.com")
    conv = create_test_conversation(user_a.id)

    # Simulate User B accessing User A's conversation
    result = await get_conversation(conv.id, current_user=user_b)

    # Should raise 403, not return conversation
    assert result.status_code == 403

async def test_cannot_access_conversation_with_invalid_thread_id():
    """Even with valid conversation_id, invalid thread_id blocks access."""
    # Conversation points to thread_id="valid"
    # LangGraph DB doesn't have thread "valid"
    # Should return 404 or error, not expose data
    pass
```

### Integration Tests for Two-Database Consistency

```python
# tests/integration/test_dual_database_consistency.py

async def test_conversation_deletion_cascades_to_langgraph():
    """Deleting conversation also deletes its LangGraph thread."""
    user = create_test_user()
    conv = create_test_conversation(user.id)
    thread_id = conv.thread_id

    # Save messages to both DBs
    save_message_to_app_db(conv.id, "Hello")
    save_message_to_langgraph(thread_id, "Hello")

    # Delete conversation
    delete_conversation(conv.id, user.id)

    # Verify both databases cleaned up
    assert not app_db.conversations.find_one({"_id": conv.id})
    assert not langgraph_db.threads.find_one({"_id": thread_id})

async def test_cannot_access_orphaned_thread_without_conversation():
    """If conversation is deleted, thread_id cannot be used directly."""
    user = create_test_user()
    conv = create_test_conversation(user.id)
    thread_id = conv.thread_id

    # Delete conversation
    app_db.conversations.delete_one({"_id": conv.id})

    # Attempt to access thread directly (simulating attacker)
    messages = await langgraph_repo.get_messages(thread_id)
    # Should fail because NO authorization check in langgraph_repo
    # Responsibility on caller to verify conversation ownership first

    # This test documents the API contract:
    # LangGraphRepository is NOT safe to call with untrusted thread_ids
```

### WebSocket Security Tests

```python
# tests/integration/test_websocket_authorization.py

async def test_cannot_switch_conversations_mid_websocket_connection():
    """WebSocket connected to /ws/chat/conv1 cannot switch to conv2."""
    user = create_test_user()
    conv1 = create_test_conversation(user.id)
    conv2 = create_test_conversation(user.id)

    websocket = connect_websocket(f"/ws/chat/{conv1.id}", user.token)

    # Try to send message to conv2
    websocket.send({"type": "message", "conversation_id": conv2.id, "content": "hi"})

    # Should be ignored or error
    # Endpoint should not process conversation_id from message payload

async def test_websocket_rejects_unauthorized_conversation():
    """WebSocket connection to /ws/chat/other_user_conv is rejected."""
    user_a = create_test_user("a@test.com")
    user_b = create_test_user("b@test.com")
    conv = create_test_conversation(user_a.id)

    # User B tries to connect
    websocket = connect_websocket(f"/ws/chat/{conv.id}", user_b.token)

    # Should receive close frame with code 1008 (policy violation)
    frame = websocket.receive()
    assert frame.code == 1008
    assert "Access denied" in frame.reason
```

### Database Isolation Tests

```python
# tests/integration/test_database_isolation.py

async def test_app_db_credentials_cannot_access_langgraph_db():
    """App DB connection has no access to LangGraph collections."""
    app_db_conn = create_connection(settings.app_db_url)

    # Try to query LangGraph collection (should fail if credentials isolated)
    try:
        app_db_conn[settings.langgraph_db_name].threads.find_one()
        # If this succeeds, credentials are not isolated
        assert False, "App DB has access to LangGraph DB - isolation violated"
    except PermissionError:
        # Expected: app DB credentials denied access
        pass
```

## Risks and Considerations

### Risk 1: Thread_ID Enumeration / Brute Force

**Threat:**
If thread_ids are predictable (sequential, short UUIDs, weak random), attackers can enumerate and access threads.

**Mitigation:**
- Enforce cryptographically random thread_id generation
- Use UUID v4 (128-bit random)
- Never accept thread_id from client - only via conversation ownership
- No pagination by thread_id without authentication
- Rate limit thread lookups per user

**Severity:** HIGH - Could expose other users' conversations

### Risk 2: Race Condition During Conversation Deletion

**Threat:**
```
Timeline:
T1: User A deletes conversation
T2: App DB deletes conversation
T3: User B's request arrives with message to conversation
T4: Ownership check passes (race condition - not yet deleted)
T5: LangGraph deletion completes
T6: Message saved to LangGraph after deletion
```

**Mitigation:**
- Implement database transaction or two-phase commit
- Use soft deletes (deleted_at timestamp) for App DB
- Verify conversation not deleted before every write to LangGraph
- Implement checkpoints with retry logic for failed deletions
- Consider event-based cascade: deletion event → queue → async cleanup

**Severity:** MEDIUM - Could cause orphaned data or temporary inconsistency

### Risk 3: Stale Conversation Ownership Cache

**Threat:**
If conversation ownership is cached in-memory or Redis, updates to user_id (unlikely but possible in transfer scenarios) aren't reflected immediately.

**Current Risk Level:** LOW (no caching currently)
**Future Risk:** If caching is added to improve performance

**Mitigation:**
- No caching of ownership relationships
- Query App DB on every access (accept latency cost)
- If caching is required, implement TTL (e.g., 5 minutes)
- Implement cache invalidation on conversation updates

**Severity:** LOW - Mitigated by always querying DB

### Risk 4: Error Messages Exposing Thread_ID Structure

**Threat:**
```
Client: GET /api/conversations/invalid-id/messages
Error: "Thread f1e2d3c4... not found"
```
Error message reveals internal thread_id structure.

**Mitigation:**
- Generic error messages to clients
- Detailed errors in server logs only
- Do NOT include thread_id in API responses
- Do NOT include thread_id in error messages

**Affected File:**
- `backend/app/adapters/inbound/message_router.py` - Error handling

**Severity:** LOW-MEDIUM - Information disclosure

### Risk 5: Database Credential Compromise

**Threat:**
If one database credential is compromised, attacker has access to that database.

**Current Architecture:** Both databases in same MongoDB instance with same credentials
**After Refactor:** Separate databases with separate credentials (better security)

**Mitigation:**
- Use separate MongoDB credentials for App DB and LangGraph DB
- Implement principle of least privilege:
  - App DB user: read/write conversations, read/write messages, read users (for deletion cascade)
  - LangGraph DB user: read/write thread data only
- Rotate credentials regularly
- Monitor access logs for suspicious patterns
- Consider network isolation (App DB on internal network, LangGraph DB also internal)

**Severity:** HIGH - Impacts entire database

### Risk 6: Orphaned Threads in LangGraph After App DB Deletion Fails

**Threat:**
```
1. Delete /conversations/conv_id starts
2. LangGraph thread deleted successfully
3. App DB deletion fails (network issue, disk full)
4. Transaction not atomic across two databases
5. Thread_id permanently orphaned
```

**Mitigation:**
- Implement retry logic with exponential backoff
- Log failed deletions with high severity
- Create monitoring alert for orphaned threads
- Implement manual recovery process documented in runbook
- Consider dual-write log or event-sourced deletion pattern

**Severity:** MEDIUM - Data inconsistency, but not security issue (cannot be accessed)

### Risk 7: LangGraph Checkpointer Access Control Bypass

**Threat:**
LangGraph checkpointers (SQLite, PostgreSQL, MongoDB) may not provide row-level security. An attacker with database access could read any thread's history.

**Mitigation:**
- Assume LangGraph checkpointer has NO access control
- ALL authorization must be implemented at application layer
- Never expose thread_id directly to clients
- Verify conversation ownership before EVERY access to LangGraph
- Consider encrypting message content at rest in LangGraph DB
- Document that LangGraph DB must be treated as sensitive data store

**Severity:** HIGH - Shared database vulnerability

## Implementation Guidance

### Phase 1: Preparation (No Breaking Changes)

1. **Add thread_id field to ConversationDocument:**
   - Add optional field: `thread_id: Optional[str] = None`
   - Create migration to generate UUID v4 for existing conversations
   - Add unique index on thread_id

2. **Create ILangGraphRepository port:**
   - Define interface in `backend/app/core/ports/langgraph_repository.py`
   - Document that authorization is caller's responsibility

3. **Add database configuration to settings:**
   - Add `langgraph_db_url` and `langgraph_db_name`
   - Can point to same MongoDB instance initially (same credentials)
   - Support separation later

4. **Create LangGraphRepository adapter:**
   - Implement basic methods: get_messages, save_state, delete_thread
   - No authorization checks in adapter

### Phase 2: Routing Changes

5. **Update message_router.py:**
   - Resolve conversation_id → thread_id
   - Query LangGraph for messages instead of local DB
   - Maintain authorization check before LangGraph access

6. **Update websocket_handler.py:**
   - Accept thread_id as parameter instead of conversation_id
   - Verify ownership at connection time
   - Store thread_id for duration of connection

7. **Update WebSocket endpoint:**
   - Change from `/ws/chat?conversation_id=X` to `/ws/chat/{conversation_id}`
   - Validate authorization at connection

### Phase 3: Data Migration

8. **Migrate messages to LangGraph:**
   - Read from App DB messages collection
   - Write to LangGraph checkpointer
   - Verify counts match
   - Keep old data until verification complete

9. **Cutover:**
   - Switch reads to LangGraph
   - Validate consistency
   - Archive old message collection

### Phase 4: Cleanup

10. **Remove MongoMessageRepository:**
    - No longer needed if messages in LangGraph
    - Keep code for reference but mark as deprecated

11. **Add separate credentials:**
    - Create separate MongoDB users/passwords for each database
    - Update connection strings in settings

12. **Document security model:**
    - Create SECURITY.md explaining two-database design
    - Document thread_id internal use, never expose to clients
    - Create runbook for incident response

## Summary of Security Controls Required

| Control | Location | Purpose |
|---------|----------|---------|
| User authentication | `websocket_auth.py`, `dependencies.py` | Verify user identity before any access |
| Conversation ownership check | `message_router.py:44-49`, `websocket_handler.py:110-117` | Verify user owns conversation before accessing messages |
| Thread_id resolution | (New) `message_router.py` | Map conversation.id to thread_id securely |
| Thread_id verification | (New) LangGraph adapter | Never accept untrusted thread_id |
| Cascade deletion | (New) `conversation_router.py` DELETE endpoint | Delete from both databases |
| Error message sanitization | All handlers | Do NOT expose thread_id in error messages |
| Logging of access | All routers | Audit trail of who accessed which conversation |
| Database isolation | (New) `settings.py`, `database.py` | Separate credentials for each database |

## Assumptions & Open Questions

**Assumptions Made:**
1. Thread_id will be generated as UUID v4 (cryptographically random)
2. LangGraph will be deployed as separate database instance or MongoDB collection
3. Conversation deletion is synchronous (not deferred/async)
4. Current user authentication (JWT) will not change
5. Authorization pattern (ownership check) remains explicit

**Open Questions for Pablo:**
1. Should LangGraph be a separate MongoDB instance or same instance, different database/collection?
2. Should message deletion be supported (soft delete vs hard delete)?
3. Should conversation ownership be transferable to other users?
4. What is acceptable latency for ownership verification query (impacts caching decision)?
5. Should we implement message encryption at rest in LangGraph DB?
6. Is audit logging required for all message access?
7. Should deleted conversations be recoverable by admins?

---

**Document Version:** 1.0
**Analysis Date:** 2025-10-25
**Analyzer:** Security Architecture Review
