# Database MongoDB Analysis: Two-Database Pattern for LangGraph-First Architecture

## Request Summary

This analysis examines the MongoDB database restructuring required to implement a two-database pattern where:

1. **App Database (MongoDB)**: Contains user authentication, conversation metadata (id, user_id, title, created_at, updated_at, message_count)
2. **LangGraph Database (MongoDB)**: Contains LangGraph checkpoint and state storage (langgraph_checkpoints, langgraph_stores collections)

Currently, the system uses a single MongoDB database with three collections (users, conversations, messages). The refactor separates application state from LangGraph execution state, allowing independent scaling and lifecycle management of each concern.

---

## Relevant Files & Modules

### CRITICAL: List of All Relevant Files

#### Database Configuration & Connection
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/mongodb.py` - MongoDB connection manager using Motor AsyncIO driver and Beanie ODM. Handles single connection lifecycle (connect/close). Needs modification to support dual connections.

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py` - Application settings with environment variable loading. Currently has `mongodb_url` and `mongodb_db_name`. Needs new settings: `mongodb_app_url`, `mongodb_langgraph_url`, `mongodb_app_db_name`, `mongodb_langgraph_db_name`.

- `/Users/pablolozano/Mac Projects August/genesis/.env.example` - Environment variable template. Needs two new MongoDB connection URIs and database names.

#### MongoDB Models & Schemas
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_models.py` - Beanie ODM document models. Contains three document classes:
  - `UserDocument` - stays in App DB, indexes on email and username
  - `ConversationDocument` - stays in App DB, indexes on user_id and (user_id, updated_at)
  - `MessageDocument` - **will be removed**, messages will be managed by LangGraph checkpointer

#### Repository Layer (Data Access)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_user_repository.py` - User CRUD operations using Beanie. Queries UserDocument.find() methods. Will stay connected to App DB only.

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_conversation_repository.py` - Conversation metadata CRUD. Queries ConversationDocument.find() methods. Will stay connected to App DB only.

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_message_repository.py` - Message CRUD currently stored in MongoDB. **This entire repository will be deprecated**. Message retrieval will come from LangGraph state instead.

#### Application Entry Point
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py` - FastAPI application factory. Currently initializes MongoDB connection with three document models (UserDocument, ConversationDocument, MessageDocument). Will need to initialize two separate database connections.

#### LangGraph Integration Points
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - ConversationState TypedDict. Defines state schema with messages list managed by add_messages reducer. This state will be persisted by LangGraph's checkpointer to LangGraph DB.

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Main conversation graph orchestration. References message_repository and conversation_repository. Will need to stop calling message_repository.create() since messages come from LangGraph state.

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Streaming variant of chat graph. Similar changes to chat_graph.py needed.

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/save_history.py` - Node that saves messages to MongoDB. **Will be modified or removed** since LangGraph checkpointer handles persistence.

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/process_input.py` - Input validation node. Will remain unchanged, processes current_input field.

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - LLM invocation node. Will remain unchanged, updates llm_response field.

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/format_response.py` - Response formatting node. Will remain unchanged, formats response for addition to state.

#### API Route Handlers
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/conversation_router.py` - REST endpoints for conversation CRUD. Uses MongoConversationRepository. Will remain connected to App DB.

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_router.py` - REST endpoint GET /conversations/{id}/messages. Uses MongoMessageRepository to fetch from MongoDB. **Will change to fetch from LangGraph state/checkpointer instead**.

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket message streaming. Will need to retrieve initial message history from LangGraph checkpointer instead of MongoDB.

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_router.py` - WebSocket route registration. Creates handler instances. Will remain unchanged structurally.

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py` - WebSocket message schemas. Defines message protocol. Will remain unchanged.

#### Requirements & Dependencies
- `/Users/pablolozano/Mac Projects August/genesis/backend/requirements.txt` - Python dependencies. Currently has beanie>=1.23.0, motor>=3.3.0, langgraph>=0.2.0. **Will need to add langgraph-mongo or MongoDB checkpointer package for LangGraph persistence** (e.g., langgraph>=0.3.0+ includes MongoDB support in langgraph.checkpoint_mongo).

---

## Current Database Overview

### Collections & Schemas

#### 1. **users** Collection (App DB)
```python
# Model: UserDocument
email: str (indexed, unique)
username: str (indexed, unique)
hashed_password: str
full_name: Optional[str]
is_active: bool = True
created_at: datetime
updated_at: datetime

# Indexes:
# - email (unique)
# - username (unique)
```

**Purpose**: User authentication and profile data
**Access Pattern**: By ID (get_by_id), by email (get_by_email), by username (get_by_username), list all (list_users)
**Write Pattern**: Create on registration, update on profile changes, delete on account removal

#### 2. **conversations** Collection (App DB)
```python
# Model: ConversationDocument
user_id: str (indexed)
title: str
created_at: datetime
updated_at: datetime
message_count: int

# Indexes:
# - user_id
# - (user_id, updated_at) - compound for sorting user conversations by recency
```

**Purpose**: Conversation metadata and lifecycle tracking
**Access Pattern**: By ID (get_by_id), by user_id with sorting and pagination (get_by_user_id), list all conversations for user
**Write Pattern**: Create new conversation, update title, increment message_count, delete conversation

**Current Limitation**: message_count is updated in save_history node but duplicates actual message count in messages collection

#### 3. **messages** Collection (App DB) - **TO BE REMOVED**
```python
# Model: MessageDocument
conversation_id: str (indexed)
role: MessageRole ("user", "assistant", "system")
content: str
created_at: datetime
metadata: Optional[dict]

# Indexes:
# - conversation_id
# - (conversation_id, created_at) - compound for ordered retrieval
```

**Purpose**: Message storage and retrieval
**Current Access Pattern**:
- Fetch all messages for conversation: find(conversation_id) sorted by created_at
- Get single message: get_by_id
- Delete messages: delete_by_conversation_id when conversation is deleted

**Removal Impact**: Messages will be stored exclusively in LangGraph checkpoints instead

### Query Patterns

#### User Queries
```python
# mongo_user_repository.py
await UserDocument.find_one(UserDocument.email == email)  # get_by_email
await UserDocument.find_one(UserDocument.username == username)  # get_by_username
await UserDocument.get(user_id)  # get_by_id (primary key lookup)
await UserDocument.find_all().skip(skip).limit(limit).to_list()  # list_users
```

#### Conversation Queries
```python
# mongo_conversation_repository.py
await ConversationDocument.get(conversation_id)  # single fetch
await ConversationDocument.find(
    ConversationDocument.user_id == user_id
).sort(-ConversationDocument.updated_at).skip(skip).limit(limit).to_list()
# List with pagination, sorted by most recent
```

#### Message Queries - **TO CHANGE**
```python
# mongo_message_repository.py - CURRENT
await MessageDocument.find(
    MessageDocument.conversation_id == conversation_id
).sort(MessageDocument.created_at).skip(skip).limit(limit).to_list()
# Fetch messages for conversation

# FUTURE - From LangGraph State/Checkpointer
# Will use LangGraph API to retrieve saved state from checkpointer
# langgraph_checkpointer.get_tuple(thread_id=conversation_id, checkpoint_id=...)
```

### Current Indexing Strategy

**Covered Queries**:
- email lookup: exact match on indexed field
- username lookup: exact match on indexed field
- user_id lookup: exact match on indexed field
- conversations sorted by user_id and update time: compound index covers both fields

**Missing/Inefficient**:
- conversation_id + created_at compound index on messages enables ordered retrieval but will be removed

### Repository Layer Architecture

All repositories follow the hexagonal adapter pattern:

1. **Port (Interface)**: Define contract in `app/core/ports/`
2. **Adapter (Implementation)**: Implement in `app/adapters/outbound/repositories/mongo_*.py`
3. **Service Layer**: Used by routers and use cases

**Current Repositories**:
- `MongoUserRepository` implements `IUserRepository`
- `MongoConversationRepository` implements `IConversationRepository`
- `MongoMessageRepository` implements `IMessageRepository`

Each creates Beanie document instances and calls insert/save/delete methods via ODM.

---

## Impact Analysis: Two-Database Pattern

### Collections & Models Distribution

#### App Database
**Stays Connected**: Users, Conversations collections
```
App DB MongoDB
├── users (unchanged)
│   ├── email (unique index)
│   ├── username (unique index)
│   └── created_at, updated_at
├── conversations (metadata only)
│   ├── user_id (index)
│   ├── title, created_at, updated_at
│   ├── (user_id, updated_at) compound index
│   └── message_count (informational only)
```

#### LangGraph Database
**New Collections** for checkpoint persistence:
```
LangGraph DB MongoDB
├── langgraph_checkpoints (LangGraph's checkpoint storage)
│   ├── thread_id (index) - maps to conversation_id
│   ├── checkpoint_id (index)
│   ├── values (JSON state including messages list)
│   ├── metadata
│   └── created_at, updated_at
├── langgraph_stores (LangGraph's key-value store)
│   ├── thread_id (index)
│   ├── namespace (index)
│   ├── key (index)
│   ├── value (JSON)
│   └── created_at, updated_at
```

### Database Connection Management

#### Current Setup (Single Connection)
```python
# backend/app/infrastructure/database/mongodb.py
class MongoDB:
    client: AsyncIOMotorClient = None
    database = None

    @classmethod
    async def connect(cls, document_models):
        cls.client = AsyncIOMotorClient(settings.mongodb_url)
        cls.database = cls.client[settings.mongodb_db_name]
        await init_beanie(database=cls.database, document_models=document_models)
```

**Issues with Current Approach**:
- Single global class variable holds one connection
- All document models registered to same database
- Connection lifetime tied to application lifecycle

#### New Setup (Dual Connections)
```python
# CONCEPTUAL - Needs Implementation
class MongoDB:
    # App DB connection
    app_client: AsyncIOMotorClient = None
    app_database = None

    # LangGraph DB connection (for checkpointer)
    langgraph_client: AsyncIOMotorClient = None
    langgraph_database = None

    @classmethod
    async def connect_app(cls, document_models):
        """Connect to App database (users, conversations)"""
        cls.app_client = AsyncIOMotorClient(settings.mongodb_app_url)
        cls.app_database = cls.app_client[settings.mongodb_app_db_name]
        await init_beanie(database=cls.app_database, document_models=document_models)

    @classmethod
    async def connect_langgraph(cls):
        """Connect to LangGraph database (checkpoints, stores)"""
        cls.langgraph_client = AsyncIOMotorClient(settings.mongodb_langgraph_url)
        cls.langgraph_database = cls.langgraph_client[settings.mongodb_langgraph_db_name]
        # Note: Beanie NOT used for LangGraph DB - LangGraph checkpointer handles collections directly

    @classmethod
    async def connect_all(cls, document_models):
        """Initialize both database connections"""
        await cls.connect_app(document_models)
        await cls.connect_langgraph()

    @classmethod
    async def close(cls):
        """Close both connections"""
        if cls.app_client:
            cls.app_client.close()
        if cls.langgraph_client:
            cls.langgraph_client.close()
```

### Configuration Changes Required

#### Settings File Updates
```python
# backend/app/infrastructure/config/settings.py

class Settings(BaseSettings):
    # DEPRECATED (kept for backward compatibility or removed):
    # mongodb_url: str = "mongodb://mongodb:27017"
    # mongodb_db_name: str = "genesis"

    # NEW: App Database
    mongodb_app_url: str = "mongodb://mongodb:27017"
    mongodb_app_db_name: str = "genesis_app"

    # NEW: LangGraph Database
    mongodb_langgraph_url: str = "mongodb://mongodb:27017"
    mongodb_langgraph_db_name: str = "genesis_langgraph"
```

#### Environment Variable Updates
```env
# .env.example - OLD (deprecated)
# MONGODB_URL=mongodb://mongodb:27017
# MONGODB_DB_NAME=genesis

# NEW: App Database
MONGODB_APP_URL=mongodb://mongodb:27017
MONGODB_APP_DB_NAME=genesis_app

# NEW: LangGraph Database
MONGODB_LANGGRAPH_URL=mongodb://mongodb:27017
MONGODB_LANGGRAPH_DB_NAME=genesis_langgraph

# Can be same MongoDB instance with different databases, or separate instances:
# Single instance: MONGODB_APP_URL and MONGODB_LANGGRAPH_URL point to same host
# Separate instances: MONGODB_APP_URL and MONGODB_LANGGRAPH_URL point to different hosts
```

### Repository & Query Changes

#### Repositories Staying Unchanged (Connected to App DB)
- `MongoUserRepository` - queries UserDocument in app database
- `MongoConversationRepository` - queries ConversationDocument in app database

#### MessageRepository - Deprecated Path
Current: `MongoMessageRepository.get_by_conversation_id()` fetches from messages collection
Future: No MongoDB message repository needed; fetch from LangGraph state instead

**Affected Methods to Refactor**:
```python
# REMOVE from MongoMessageRepository or DEPRECATE
async def get_by_conversation_id(conversation_id, skip, limit) -> List[Message]
    # Currently: await MessageDocument.find(...).sort(...).skip().limit().to_list()
    # Future: Fetch from LangGraph checkpointer state.messages

# REMOVE - no longer applicable
async def delete_by_conversation_id(conversation_id) -> int
    # Messages deleted via LangGraph cleanup, not MongoDB
```

#### New LangGraph Checkpointer Integration
Instead of MongoMessageRepository, use LangGraph's MongoDB checkpointer:
```python
# NEW - Instead of MongoMessageRepository
from langgraph.checkpoint.mongodb import MongoDBCheckpointer

checkpointer = MongoDBCheckpointer(
    connection_string=settings.mongodb_langgraph_url,
    db_name=settings.mongodb_langgraph_db_name
)

# Graph uses checkpointer for message state persistence:
graph = graph_builder.compile(checkpointer=checkpointer)

# Retrieving messages:
# 1. Get LangGraph state from checkpointer
checkpoint_tuple = await checkpointer.get_tuple(thread_id=conversation_id)
if checkpoint_tuple:
    state = checkpoint_tuple.values
    messages = state.get('messages', [])
```

### Message Flow Changes

#### Current Flow (Single DB)
```
1. User input → WebSocket handler
2. LangGraph processes (format_response node adds Message to state)
3. save_history node → MongoMessageRepository.create() → messages collection
4. Conversation.message_count incremented in conversations collection
5. GET /conversations/{id}/messages → MongoMessageRepository.get_by_conversation_id()
```

#### New Flow (Two DB Pattern)
```
1. User input → WebSocket handler
2. LangGraph checkpointer saves state (ConversationState.messages) → langgraph_checkpoints
3. Conversation.message_count still updated in conversations collection (App DB)
   - But can be computed from LangGraph state instead of stored
4. GET /conversations/{id}/messages → Fetch from LangGraph checkpointer via API:
   - checkpointer.get_tuple(thread_id=conversation_id)
   - Extract messages from state.values['messages']
```

**Key Difference**: Messages are source-of-truth in LangGraph state, not duplicated in App DB

### Migration Strategy

#### Phase 1: Dual Connection Setup
1. Add new settings for two database URLs and names
2. Modify `MongoDB` class to maintain two connections
3. Initialize both in `main.py` lifespan

#### Phase 2: LangGraph Checkpointer Integration
1. Add checkpointer to graph compilation
2. Stop calling `MongoMessageRepository.create()`
3. Test state persistence to LangGraph DB

#### Phase 3: Message Retrieval Refactor
1. Modify `message_router.py` to fetch from LangGraph state
2. Modify `websocket_handler.py` to fetch from LangGraph state
3. Remove or deprecate `MongoMessageRepository`

#### Phase 4: Cleanup (Optional)
1. Delete `messages` collection from App DB
2. Delete `MessageDocument` from mongo_models.py
3. Delete `MongoMessageRepository` class

#### Data Migration Considerations
- **No active migration needed** for existing messages if starting fresh
- **For production migration**: Export messages from App DB messages collection and seed into LangGraph checkpoints (complex, consider data archival strategy)
- **message_count field**: Can remain in conversations (denormalized for performance) or recompute from LangGraph state on demand

---

## Database Recommendations

### 1. Proposed Schema Changes

#### Add New Collections to LangGraph DB (Auto-created by LangGraph)
```javascript
// langgraph_checkpoints collection
{
  _id: ObjectId,
  thread_id: string,  // maps to conversation_id
  checkpoint_id: string,
  values: {
    messages: [
      { id, conversation_id, role, content, created_at, metadata }
    ],
    conversation_id: string,
    user_id: string,
    current_input: string,
    llm_response: string,
    error: null
  },
  metadata: {
    source: "langgraph",
    step: number,
    ts: timestamp
  },
  created_at: datetime,
  updated_at: datetime
}

// langgraph_stores collection (for key-value persistence)
{
  _id: ObjectId,
  thread_id: string,
  namespace: string,
  key: string,
  value: any,
  created_at: datetime,
  updated_at: datetime
}
```

#### Keep Existing Collections in App DB (No Changes to Schema)
- `users` - unchanged
- `conversations` - unchanged (message_count becomes informational only)
- **DELETE** `messages` collection once migration complete

### 2. Proposed Indexes

#### App DB Indexes (Unchanged)
```python
# users collection
Index on email (unique)
Index on username (unique)

# conversations collection
Index on user_id (for finding user's conversations)
Compound index on (user_id, updated_at) (for sorted pagination)
```

#### LangGraph DB Indexes (Auto-created by LangGraph Checkpointer)
```javascript
// langgraph_checkpoints collection
Index on thread_id (for conversation lookup)
Index on checkpoint_id (for specific checkpoint retrieval)
Compound index on (thread_id, created_at) for checkpoint history

// langgraph_stores collection
Index on thread_id (for conversation lookup)
Compound index on (thread_id, namespace, key) for key-value retrieval
```

**LangGraph Handles Index Creation**: The MongoDB checkpointer automatically creates necessary indexes. No manual index management needed.

### 3. Repository Changes

#### Keep As-Is
- `MongoUserRepository` - no changes, connects to App DB
- `MongoConversationRepository` - no changes, connects to App DB

#### Remove or Deprecate
- `MongoMessageRepository` - entirely remove, replace with LangGraph checkpointer calls

#### New LangGraph Integration Point
Create new adapter for LangGraph state retrieval (optional, can inline in routers):
```python
# NEW: app/adapters/outbound/langgraph/langgraph_state_adapter.py
class LangGraphStateAdapter:
    """Fetch messages and state from LangGraph checkpointer"""

    def __init__(self, checkpointer: MongoDBCheckpointer):
        self.checkpointer = checkpointer

    async def get_messages(self, thread_id: str) -> List[Message]:
        """Retrieve messages from LangGraph state"""
        checkpoint_tuple = await self.checkpointer.get_tuple(thread_id)
        if not checkpoint_tuple:
            return []

        messages = checkpoint_tuple.values.get('messages', [])
        return messages

    async def get_state(self, thread_id: str) -> Optional[ConversationState]:
        """Retrieve full conversation state"""
        checkpoint_tuple = await self.checkpointer.get_tuple(thread_id)
        return checkpoint_tuple.values if checkpoint_tuple else None
```

### 4. Query Optimization

#### Current N+1 Problem
1. GET /conversations/{id} fetches ConversationDocument
2. GET /conversations/{id}/messages fetches all MessageDocuments
3. Each message access hits MongoDB separately

#### Optimized Two-DB Pattern
1. GET /conversations/{id} fetches ConversationDocument from App DB (fast)
2. GET /conversations/{id}/messages fetches from LangGraph checkpointer (single atomic fetch of state)
3. Pagination applied in-memory or via checkpoint query parameters

**Performance Benefit**: Single LangGraph checkpoint fetch replaces MongoDB message query, reduces network round-trips

#### Conversation List Optimization
**Current**:
```python
# Get user conversations
conversations = await ConversationDocument.find(
    ConversationDocument.user_id == user_id
).sort(-ConversationDocument.updated_at).skip(skip).limit(limit).to_list()
# Uses compound index (user_id, updated_at) - O(log n) + O(limit) after seek
```

**New** (same query, no change):
```python
# Still same - conversations metadata remains in App DB
# Only messages move to LangGraph DB
# Compound index still covers this query efficiently
```

No query changes needed for conversation listing.

### 5. Connection Management & Error Handling

#### Dual Connection Initialization
```python
# main.py lifespan
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name}")

    from app.adapters.outbound.repositories.mongo_models import (
        UserDocument,
        ConversationDocument
        # MessageDocument removed
    )

    try:
        # Initialize both database connections
        await MongoDB.connect_all(
            document_models=[UserDocument, ConversationDocument]
        )
        logger.info("Both App and LangGraph databases connected")
    except Exception as e:
        logger.error(f"Failed to connect to databases: {e}")
        raise

    yield

    # Shutdown: Close both connections
    logger.info("Closing database connections")
    await MongoDB.close()
    logger.info("Databases closed")
```

#### Separate Error Handling
```python
# If App DB is down: User, Conversation operations fail
# If LangGraph DB is down: New messages can't be saved, but users can still:
#   - See conversation list (App DB still works)
#   - See message history temporarily cached in state
#   - Cannot persist new messages

# Recommended: Check both DB health in middleware
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "app_db": await check_app_db_health(),
        "langgraph_db": await check_langgraph_db_health()
    }
```

#### Graceful Degradation
For WebSocket message streaming, if LangGraph DB unavailable:
```python
# Option 1: Buffer messages in memory, retry persistence
# Option 2: Fail the connection with user notification
# Option 3: Use in-memory checkpointer fallback temporarily

# Recommend Option 2: Clear error messaging > silent data loss
```

### 6. Environment Variable Setup

Update `.env.example`:
```env
# REMOVED (use new settings below):
# MONGODB_URL=mongodb://mongodb:27017
# MONGODB_DB_NAME=genesis

# NEW: App Database (users, conversations)
MONGODB_APP_URL=mongodb://mongodb:27017
MONGODB_APP_DB_NAME=genesis_app

# NEW: LangGraph Database (checkpoints, stores)
MONGODB_LANGGRAPH_URL=mongodb://mongodb:27017
MONGODB_LANGGRAPH_DB_NAME=genesis_langgraph

# Notes:
# - Both can point to same MongoDB instance with different database names
# - Or separate MongoDB instances for high-scale deployments
# - Use environment-specific URIs for production (authentication, replica sets, etc.)
```

---

## Implementation Guidance

### Step 1: Update Settings (No DB Changes Yet)

**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py`

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Database Settings - NEW
    mongodb_app_url: str = "mongodb://mongodb:27017"
    mongodb_app_db_name: str = "genesis_app"

    mongodb_langgraph_url: str = "mongodb://mongodb:27017"
    mongodb_langgraph_db_name: str = "genesis_langgraph"

    # DEPRECATED (for backward compatibility):
    # mongodb_url: str = "mongodb://mongodb:27017"
    # mongodb_db_name: str = "genesis"
```

**File**: `/Users/pablolozano/Mac Projects August/genesis/.env.example`

Add new environment variables and mark old ones deprecated.

### Step 2: Modify MongoDB Connection Manager

**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/mongodb.py`

Refactor to manage two connections:
```python
class MongoDB:
    app_client: AsyncIOMotorClient = None
    app_database = None

    langgraph_client: AsyncIOMotorClient = None
    langgraph_database = None

    @classmethod
    async def connect_app(cls, document_models):
        """Connect to App database and register Beanie models"""
        # Identical to current connect() but uses mongodb_app_url

    @classmethod
    async def connect_langgraph(cls):
        """Connect to LangGraph database for checkpointer"""
        # Create connection but don't initialize Beanie
        # LangGraph checkpointer will use this connection directly

    @classmethod
    async def connect_all(cls, document_models):
        """Initialize both connections"""
        await asyncio.gather(
            cls.connect_app(document_models),
            cls.connect_langgraph()
        )

    @classmethod
    async def close(cls):
        """Close both connections"""
        if cls.app_client:
            cls.app_client.close()
        if cls.langgraph_client:
            cls.langgraph_client.close()
```

### Step 3: Update Application Startup

**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py`

Modify lifespan:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    from app.adapters.outbound.repositories.mongo_models import (
        UserDocument,
        ConversationDocument
        # Remove: MessageDocument
    )

    # Initialize both databases
    await MongoDB.connect_all(document_models=[
        UserDocument,
        ConversationDocument
    ])

    # Initialize LangGraph checkpointer
    from langgraph.checkpoint.mongodb import MongoDBCheckpointer
    app.state.checkpointer = MongoDBCheckpointer(
        connection_string=settings.mongodb_langgraph_url,
        db_name=settings.mongodb_langgraph_db_name
    )

    logger.info("Application startup complete")
    yield

    logger.info("Shutting down application")
    await MongoDB.close()
    logger.info("Application shutdown complete")
```

### Step 4: Update LangGraph Graph Integration

**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py`

Modify graph compilation to use checkpointer:
```python
def create_chat_graph(
    llm_provider: ILLMProvider,
    message_repository: IMessageRepository,  # Still passed but not used for persistence
    conversation_repository: IConversationRepository,
    checkpointer  # NEW
):
    """
    Create and compile the chat conversation graph.

    Messages are now persisted via checkpointer, not MongoMessageRepository.
    """
    graph_builder = StateGraph(ConversationState)

    # ... add nodes as before ...

    # Compile WITH checkpointer
    graph = graph_builder.compile(checkpointer=checkpointer)

    return graph
```

### Step 5: Refactor Message Retrieval

**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_router.py`

Replace MongoDB message fetch with LangGraph state fetch:
```python
@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: str,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    checkpointer = Depends(lambda: app.state.checkpointer)  # NEW
):
    """Get messages for a conversation from LangGraph state"""

    # Verify user owns conversation
    conversation = await conversation_repository.get_by_id(conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Fetch from LangGraph checkpointer
    try:
        checkpoint_tuple = await checkpointer.get_tuple(thread_id=conversation_id)
        if not checkpoint_tuple:
            return []

        messages = checkpoint_tuple.values.get('messages', [])
        # Apply pagination
        return messages[skip:skip+limit]

    except Exception as e:
        logger.error(f"Failed to fetch messages from LangGraph: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve messages")
```

### Step 6: Update WebSocket Handler

**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py`

Load initial message history from LangGraph state:
```python
async def websocket_endpoint(websocket, conversation_id, current_user, checkpointer):
    """Handle WebSocket connection and streaming"""

    # ... connection setup ...

    # Load initial message history from LangGraph
    try:
        checkpoint_tuple = await checkpointer.get_tuple(thread_id=conversation_id)
        initial_messages = checkpoint_tuple.values.get('messages', []) if checkpoint_tuple else []
    except Exception as e:
        logger.error(f"Failed to load message history: {e}")
        initial_messages = []

    # Initialize graph state with loaded messages
    initial_state = {
        'messages': initial_messages,
        'conversation_id': conversation_id,
        'user_id': current_user.id,
        'current_input': None,
        'llm_response': None,
        'error': None
    }

    # ... stream graph execution with initial_state ...
```

### Step 7: Remove MessageDocument & MongoMessageRepository

**Delete or Deprecate**:
1. `MessageDocument` class from `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_models.py`
2. Entire `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_message_repository.py`
3. Remove save_history node that called MongoMessageRepository or refactor it to no-op

**Timeline**: Can be done immediately or after full LangGraph integration testing

---

## Risks and Considerations

### 1. Data Consistency Risks

**Risk**: Messages in two stores (LangGraph state AND potentially MongoDB for backward compat)
- **Mitigation**: Stop writing to messages collection immediately
- **Testing**: Verify no code paths still write to messages collection

**Risk**: message_count field in conversations may become stale if computed from LangGraph
- **Mitigation**: Recompute message_count from LangGraph state on demand OR keep synchronized via event
- **Recommendation**: Keep as denormalized field, update when LangGraph saves state

### 2. Migration Complexity

**Risk**: Dual databases add operational complexity
- **Production Only**: Keep single MongoDB for dev/test if acceptable
- **Separate Instances**: Manage two connection pools, authentication, monitoring

**Risk**: Existing message data not automatically migrated
- **Decision Needed**:
  - Archive old messages before migration?
  - Export to LangGraph format?
  - Start fresh with new architecture?

**Recommendation**: Plan data archival strategy before production deployment

### 3. Query Performance

**Risk**: Network latency with two databases
- **Mitigation**: Both databases likely on same MongoDB instance initially
- **Optimization**: As scale grows, can separately scale App DB (read-heavy) vs LangGraph DB (write-heavy)

**Benefit**: Isolation allows different replication/backup strategies per database

### 4. Connection Pool Management

**Risk**: Doubling connection pools from 2 to 4 (app client + app db, langgraph client + langgraph db)
- **Current**: AsyncIOMotorClient handles connection pooling automatically
- **No Action Needed**: Motor manages pools transparently

**Risk**: One database down affects partial functionality
- **User Impact**: If LangGraph DB down → users can see conversations but not message history
- **Recommended**: Health check endpoint reports status of both DBs

### 5. LangGraph Checkpointer Behavior

**Risk**: LangGraph checkpoint data structure may not perfectly match Message domain model
- **Solution**: Adapter layer (LangGraphStateAdapter) normalizes state to Message objects
- **Testing**: Ensure serialization/deserialization works correctly

**Risk**: LangGraph checkpointer may not have all features of custom MongoMessageRepository
- **Comparison**:
  - MongoMessageRepository: get_by_id, get_by_conversation_id, delete, delete_by_conversation_id
  - LangGraph Checkpointer: get_tuple (full state), put_writes (batch save), list (enumerate checkpoints)
- **Impact**: Limited ability to delete individual messages (but this feature rarely used in chat)

### 6. Backward Compatibility

**Risk**: Old client code still expects messages from MongoDB
- **Frontend**: Needs update to fetch from new endpoint behavior
- **API Contract**: GET /conversations/{id}/messages returns same schema, just sourced differently

### 7. Testing Requirements

**Critical Tests**:
1. Dual database connection setup and teardown
2. Message persistence to LangGraph checkpoints
3. Message retrieval from LangGraph state
4. Conversation metadata updates (still in App DB)
5. WebSocket streaming with LangGraph state
6. Error handling when one DB is down
7. Pagination of large message histories

---

## Testing Strategy

### Unit Tests

**Database Connection Tests**:
```python
# tests/infrastructure/test_mongodb_dual_connection.py

@pytest.mark.asyncio
async def test_app_database_connection():
    """Verify App database connects and Beanie models initialized"""
    await MongoDB.connect_app([UserDocument, ConversationDocument])
    assert MongoDB.app_database is not None
    assert MongoDB.app_client is not None
    await MongoDB.app_client.close()

@pytest.mark.asyncio
async def test_langgraph_database_connection():
    """Verify LangGraph database connects for checkpointer"""
    await MongoDB.connect_langgraph()
    assert MongoDB.langgraph_database is not None
    assert MongoDB.langgraph_client is not None
    await MongoDB.langgraph_client.close()

@pytest.mark.asyncio
async def test_both_databases_close():
    """Verify both connections close cleanly"""
    await MongoDB.connect_all([UserDocument, ConversationDocument])
    await MongoDB.close()
    # Verify connections are closed
    assert MongoDB.app_client is None or not MongoDB.app_client.alive
```

**Repository Tests** (unchanged):
```python
# tests/adapters/test_mongo_conversation_repository.py
# Tests remain the same, now connecting to App DB only
```

**LangGraph State Tests**:
```python
# tests/langgraph/test_checkpointer_integration.py

@pytest.mark.asyncio
async def test_checkpointer_saves_state():
    """Verify LangGraph checkpointer persists conversation state"""
    checkpointer = MongoDBCheckpointer(connection_string=..., db_name=...)

    state = {
        'messages': [Message(...), Message(...)],
        'conversation_id': 'test-conv-123',
        ...
    }

    # Save state
    await checkpointer.put_writes([PutWrite(...)])

    # Verify state saved
    checkpoint = await checkpointer.get_tuple(thread_id='test-conv-123')
    assert checkpoint.values['messages'] == state['messages']

@pytest.mark.asyncio
async def test_graph_compiles_with_checkpointer():
    """Verify chat graph compiles and uses checkpointer"""
    checkpointer = MongoDBCheckpointer(...)
    graph = create_chat_graph(..., checkpointer=checkpointer)

    # Execute graph and verify state saved to checkpointer
    result = await graph.ainvoke(initial_state)

    # Verify messages in checkpointer
    checkpoint = await checkpointer.get_tuple(thread_id=...)
    assert len(checkpoint.values['messages']) > len(initial_state['messages'])
```

### Integration Tests

**Message Retrieval Integration**:
```python
# tests/api/test_message_endpoint_langgraph.py

@pytest.mark.asyncio
async def test_get_messages_from_langgraph():
    """End-to-end: Fetch messages from LangGraph via API"""
    # Setup: Create conversation, add messages via graph
    conversation = await conversation_repository.create(user_id, ConversationCreate())

    # Stream graph with checkpointer
    graph = create_chat_graph(..., checkpointer=checkpointer)
    await graph.ainvoke({'conversation_id': conversation.id, ...})

    # Fetch via API endpoint
    response = client.get(f"/api/conversations/{conversation.id}/messages")
    assert response.status_code == 200
    messages = response.json()
    assert len(messages) > 0

@pytest.mark.asyncio
async def test_conversation_metadata_separate_from_messages():
    """Verify conversation metadata stays in App DB, messages in LangGraph DB"""
    conversation = await conversation_repository.create(...)

    # Verify in App DB (fast query)
    app_conv = await ConversationDocument.get(conversation.id)
    assert app_conv.user_id == conversation.user_id

    # Verify NOT in messages collection (removed)
    with pytest.raises(Exception):  # or assert count == 0
        await MessageDocument.find(...).to_list()
```

**Dual Database Failure Tests**:
```python
# tests/infrastructure/test_database_resilience.py

@pytest.mark.asyncio
async def test_app_db_down_blocks_conversation_operations():
    """If App DB down, can't access conversations"""
    # Simulate App DB down
    # Attempt conversation fetch → fails
    # Attempt to create conversation → fails

@pytest.mark.asyncio
async def test_langgraph_db_down_blocks_message_operations():
    """If LangGraph DB down, can't fetch messages"""
    # Simulate LangGraph DB down
    # Attempt to get messages → fails gracefully
    # Can still list conversations (App DB works)

@pytest.mark.asyncio
async def test_health_check_reports_both_db_status():
    """Health endpoint shows status of both databases"""
    response = client.get("/api/health")
    assert response.json()['app_db']['status'] == 'healthy'
    assert response.json()['langgraph_db']['status'] == 'healthy'
```

### WebSocket Integration Tests

```python
# tests/websocket/test_langgraph_websocket.py

@pytest.mark.asyncio
async def test_websocket_loads_initial_message_history():
    """WebSocket loads messages from LangGraph on connect"""
    # Setup: Create conversation with message history in LangGraph
    conversation = await create_conversation_with_history(...)

    # Connect WebSocket
    with client.websocket_connect(f"/ws/chat?conversation_id={conversation.id}") as ws:
        # Verify initial state includes loaded messages
        state = ws.receive_json()
        assert len(state['messages']) > 0

@pytest.mark.asyncio
async def test_websocket_streaming_persists_to_langgraph():
    """New messages during WebSocket session persist to LangGraph"""
    with client.websocket_connect("/ws/chat?conversation_id=...") as ws:
        ws.send_json({'type': 'message', 'content': 'Hello'})

        # Receive streamed response
        response = ws.receive_json()

    # Verify saved to LangGraph checkpointer
    checkpoint = await checkpointer.get_tuple(thread_id='conversation_id')
    assert any(m.content == 'Hello' for m in checkpoint.values['messages'])
```

### Performance Tests

```python
# tests/performance/test_two_db_performance.py

@pytest.mark.asyncio
async def test_message_retrieval_performance():
    """Verify LangGraph state fetch is performant"""
    # Create conversation with 1000 messages
    large_conversation = await create_large_conversation(1000)

    # Measure LangGraph fetch time
    start = time.time()
    checkpoint = await checkpointer.get_tuple(thread_id=large_conversation.id)
    messages = checkpoint.values['messages']
    elapsed = time.time() - start

    # Should be < 100ms even with large history
    assert elapsed < 0.1
    assert len(messages) == 1000
```

---

## Summary of Critical Points for Main Agent

### Files Requiring Modification

1. **Configuration**:
   - `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py` - Add dual DB URLs and names
   - `/Users/pablolozano/Mac Projects August/genesis/.env.example` - Add new environment variables

2. **Database Connection**:
   - `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/mongodb.py` - Refactor for dual connections

3. **Application Startup**:
   - `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py` - Initialize both databases and checkpointer

4. **Models** (Removal):
   - `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_models.py` - Remove MessageDocument

5. **LangGraph Integration**:
   - `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Add checkpointer to compilation
   - `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Same as above
   - `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/save_history.py` - Remove or refactor to no-op

6. **API Routes**:
   - `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_router.py` - Fetch from LangGraph instead of MongoDB
   - `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - Load initial messages from LangGraph

7. **Deprecation**:
   - `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_message_repository.py` - Remove entirely

### Collections Overview

**App Database**:
- users (unchanged)
- conversations (unchanged)
- ~~messages~~ (deleted)

**LangGraph Database**:
- langgraph_checkpoints (created by LangGraph)
- langgraph_stores (created by LangGraph)

### Key Decision: Single MongoDB Instance vs. Dual Instances

The two-database pattern can use:
1. **Single MongoDB with two database names** (simpler, suitable for most deployments)
2. **Two separate MongoDB instances** (more complex, needed for extreme scale or isolation)

Current recommendation: Start with single instance (both `MONGODB_APP_URL` and `MONGODB_LANGGRAPH_URL` point to same host, different database names).

### Dependencies

Add to `requirements.txt`:
- Ensure `langgraph>=0.3.0` (includes MongoDB checkpointer)
- No additional dependencies needed for MongoDBCheckpointer

### Critical Assumptions

1. **LangGraph Version**: Assumes langgraph>=0.3.0 with MongoDBCheckpointer support
2. **Thread ID Mapping**: Uses conversation_id as thread_id for checkpointer
3. **Message Count**: Remains in conversations collection but becomes denormalized (recomputable from LangGraph state)
4. **Backward Compatibility**: Old message queries don't need to work; API endpoint changes are acceptable

