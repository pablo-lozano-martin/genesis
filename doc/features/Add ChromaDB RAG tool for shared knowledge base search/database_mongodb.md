# Database MongoDB Analysis: ChromaDB RAG Tool Integration

## Request Summary

This analysis examines the database and persistence layer patterns for integrating ChromaDB as a new vector database backend for a shared knowledge base RAG (Retrieval-Augmented Generation) tool. The feature requires:

1. **ChromaDB Integration**: Add ChromaDB as a vector database for embedding storage and semantic search
2. **Knowledge Base Storage**: Persist documents, embeddings, and metadata for the knowledge base
3. **Tool Registration**: Implement as a LangGraph tool accessible from chat conversations
4. **Shared Access**: Allow all users to search the same knowledge base (read-only access pattern)
5. **MongoDB Integration**: Store knowledge base metadata and document references in MongoDB alongside user/conversation data

This analysis examines how to add ChromaDB while respecting existing MongoDB patterns and maintaining the current database architecture.

---

## Relevant Files & Modules

### CRITICAL: List of All Relevant Files

#### Database Configuration & Connection
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/mongodb.py` - MongoDB connection manager using Motor AsyncIO driver and Beanie ODM. Currently manages two connections (AppDatabase for user/conversation data, LangGraphDatabase for checkpoints). Will need to be examined for ChromaDB coexistence patterns.

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py` - Application settings with environment variable loading. Currently has `mongodb_app_url`, `mongodb_app_db_name`, `mongodb_langgraph_url`, `mongodb_langgraph_db_name`. Will need to add ChromaDB configuration (connection type, path, persistence settings).

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/logging_config.py` - Logging configuration for application events. Will be used for ChromaDB operation logging.

#### MongoDB Models & Schemas
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_models.py` - Beanie ODM document models. Contains UserDocument, ConversationDocument. Will need new documents for knowledge base metadata: `KnowledgeBaseDocument`, `KnowledgeBaseDocumentDocument` (metadata about each document in the KB).

#### Repository Layer (Data Access)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_user_repository.py` - User CRUD operations. Will remain unchanged.

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_conversation_repository.py` - Conversation metadata CRUD. Will remain unchanged.

- **NEW Repository Needed**: Knowledge base metadata repository (e.g., `mongo_knowledge_base_repository.py`) to handle CRUD operations for knowledge base documents stored in MongoDB.

#### LangGraph Tools Integration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/__init__.py` - Tool module exports. Currently exports `multiply`, `add`. Will need to export new `rag_search` tool.

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/web_search.py` - Example tool implementation (web search using DuckDuckGo). RAG search tool will follow similar pattern.

- **NEW File Needed**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/rag_search.py` - RAG search tool implementation that queries ChromaDB.

#### LangGraph Graph Integration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Main conversation graph. Will need to register rag_search tool with graph.

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Streaming variant. Will need same tool registration.

#### Application Entry Point
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py` - FastAPI application factory. Currently initializes AppDatabase and LangGraphDatabase connections, creates LangGraph graphs. Will need to initialize ChromaDB client in lifespan.

#### API Route Handlers
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/conversation_router.py` - REST endpoints for conversation CRUD. Will remain unchanged.

- **NEW Router Needed**: Knowledge base management endpoints (create knowledge base, upload documents, list documents, delete documents). Likely `/knowledge_base_router.py` for admin/owner operations.

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket message streaming. Will remain unchanged structurally; RAG search happens within LangGraph graph execution.

#### Requirements & Dependencies
- `/Users/pablolozano/Mac Projects August/genesis/backend/requirements.txt` - Python dependencies. Currently has beanie, motor, langgraph, langchain. Will need to add `chromadb>=0.4.0` and embedding model dependencies.

#### Docker Configuration
- `/Users/pablolozano/Mac Projects August/genesis/docker-compose.yml` - Docker service definitions. MongoDB service with volume persistence already defined. Will need to determine ChromaDB persistence approach (persistent volume or embedded).

---

## Current Database Overview

### Collections & Schemas (MongoDB)

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
# - (user_id, updated_at)
```

**Purpose**: Conversation metadata and lifecycle tracking

#### 3. **langgraph_checkpoints** Collection (LangGraph DB)
Managed by LangGraph's MongoDB checkpointer; stores conversation state including messages list.

#### 4. **langgraph_stores** Collection (LangGraph DB)
Managed by LangGraph's MongoDB checkpointer; stores key-value pairs for state persistence.

### Current Persistence Setup

#### Docker Volume Configuration
```yaml
# docker-compose.yml
mongodb:
  image: mongo:7.0
  volumes:
    - mongodb_data:/data/db
```

**Pattern**:
- Named volume `mongodb_data` persists all MongoDB data across container restarts
- No explicit data directory management needed for MongoDB
- Data survives container recreation but lost on volume deletion

### Connection Management

#### Current Dual-Connection Pattern
```python
# backend/app/infrastructure/database/mongodb.py

class AppDatabase:
    client: AsyncIOMotorClient = None
    database = None

    @classmethod
    async def connect(cls, document_models):
        cls.client = AsyncIOMotorClient(settings.mongodb_app_url)
        cls.database = cls.client[settings.mongodb_app_db_name]
        await init_beanie(database=cls.database, document_models=document_models)

class LangGraphDatabase:
    client: AsyncIOMotorClient = None
    database = None

    @classmethod
    async def connect(cls):
        cls.client = AsyncIOMotorClient(settings.mongodb_langgraph_url)
        cls.database = cls.client[settings.mongodb_langgraph_db_name]
```

**Pattern Characteristics**:
- Class-level static client and database references
- Async connection in lifespan context manager
- Connection pooling handled transparently by Motor
- Graceful closure on shutdown

#### Application Lifespan
```python
# backend/app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await AppDatabase.connect(document_models=[UserDocument, ConversationDocument])
    checkpointer_context, checkpointer = await get_checkpointer()
    app.state.checkpointer_context = checkpointer_context
    app.state.checkpointer = checkpointer
    # ... graph compilation ...

    yield

    # Shutdown
    await AppDatabase.close()
    await checkpointer_context.__aexit__(None, None, None)
```

**Pattern Characteristics**:
- Single async context manager handles startup and shutdown
- Services (databases, checkpointer, graphs) attached to app.state for global access
- All services initialized before accepting requests
- All services properly cleaned up on shutdown

### Error Handling Patterns

#### Database Connection Errors
```python
# backend/app/infrastructure/database/mongodb.py
try:
    logger.info(f"Connecting to App Database at {settings.mongodb_app_url}")
    cls.client = AsyncIOMotorClient(settings.mongodb_app_url)
    cls.database = cls.client[settings.mongodb_app_db_name]
    await init_beanie(database=cls.database, document_models=document_models)
    logger.info(f"Successfully connected to App Database: {settings.mongodb_app_db_name}")
except Exception as e:
    logger.error(f"Failed to connect to App Database: {e}")
    raise
```

**Pattern**:
- Errors logged with context (which database, URL)
- Exception re-raised to fail fast on startup
- No retry logic at database level (appropriate for startup)

#### Repository Operation Errors
```python
# backend/app/adapters/outbound/repositories/mongo_user_repository.py
async def create(self, user_data: UserCreate, hashed_password: str) -> User:
    existing_email = await UserDocument.find_one(UserDocument.email == user_data.email)
    if existing_email:
        raise ValueError(f"User with email {user_data.email} already exists")

    doc = UserDocument(...)
    await doc.insert()
    return self._to_domain(doc)
```

**Pattern**:
- Business logic errors raised as ValueError or appropriate exception
- No exception wrapping or custom error types
- Exceptions bubble up to router for HTTP error conversion

#### WebSocket/Streaming Errors
```python
# backend/app/adapters/inbound/websocket_handler.py
try:
    async for event in graph.astream_events(input_data, config, version="v2"):
        # Process events
except Exception as e:
    logger.error(f"LangGraph streaming failed for user {user.id}: {e}")
    error_msg = ServerErrorMessage(
        message=f"Failed to generate response: {str(e)}",
        code="LLM_ERROR"
    )
    await manager.send_message(websocket, error_msg.model_dump())
```

**Pattern**:
- Streaming errors caught and converted to structured error messages
- WebSocket connection remains open; error sent to client
- No retry logic; errors propagated to user immediately

### Repository/Adapter Pattern

All repositories follow hexagonal architecture:

1. **Port (Interface)**: Abstract interface in `app/core/ports/`
   - Defines contract for data operations
   - Example: `IUserRepository` with methods like `create()`, `get_by_id()`, `list_users()`

2. **Adapter (Implementation)**: Concrete implementation in `app/adapters/outbound/repositories/`
   - Uses Beanie ODM to access MongoDB
   - Translates between domain models and MongoDB documents
   - Example: `MongoUserRepository` implements `IUserRepository`

3. **Domain Models**: Business logic entities in `app/core/domain/`
   - Pure Python dataclasses or Pydantic models
   - No database awareness

4. **Document Models**: MongoDB schema definitions in `app/adapters/outbound/repositories/mongo_models.py`
   - Beanie Document classes
   - Define indexes and field types

### Tool Integration Pattern

Tools are registered with LangGraph graphs:

```python
# backend/app/langgraph/tools/web_search.py
def web_search(query: str) -> str:
    """Perform a web search using DuckDuckGo."""
    search = DuckDuckGoSearchResults(output_format="json")
    return search.run(query)

# backend/app/langgraph/tools/__init__.py
from .web_search import web_search
__all__ = ["web_search", "add", "multiply"]

# In graph definition
tools = [web_search, add, multiply]
graph.add_node("call_llm", llm_with_tools)
```

**Pattern Characteristics**:
- Tools are simple Python functions with docstrings
- Can be called by LLM model
- Results returned as strings or structured data
- Errors propagate back to LLM for handling

---

## Impact Analysis: ChromaDB RAG Tool Integration

### New Components Required

#### 1. ChromaDB Client & Initialization
**New**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/chromadb_client.py`

```python
# Conceptual structure
class ChromaDBClient:
    """ChromaDB vector database client manager"""

    client = None

    @classmethod
    async def initialize(cls, persist_directory: str = None, host: str = None):
        """Initialize ChromaDB client (embedded or remote)"""
        # Embedded: chromadb.PersistentClient(path=persist_directory)
        # Remote: chromadb.HttpClient(host=host, port=port)
        pass

    @classmethod
    async def close(cls):
        """Close ChromaDB client if needed"""
        pass
```

**Decision Required**: Embedded vs. Remote?
- **Embedded**: ChromaDB runs in-process, data persisted to disk/volume, simpler deployment
- **Remote**: ChromaDB runs in separate container/service, accessed via HTTP, better isolation

**Recommendation**: Start with embedded ChromaDB for simplicity

#### 2. Knowledge Base Collections (MongoDB)
**New Document Models**: Add to `mongo_models.py`

```python
class KnowledgeBaseDocument(Document):
    """Knowledge base metadata"""
    name: str
    description: Optional[str]
    created_by: str  # user_id of creator
    is_public: bool = True
    embedding_model: str  # e.g., "sentence-transformers/all-MiniLM-L6-v2"
    created_at: datetime
    updated_at: datetime

    class Settings:
        name = "knowledge_bases"
        indexes = [
            "name",
            "created_by",
        ]

class KnowledgeBaseItemDocument(Document):
    """Stores references to documents in ChromaDB"""
    knowledge_base_id: str (indexed)
    chroma_id: str  # ID in ChromaDB
    source: str  # e.g., "file", "url", "text"
    source_url: Optional[str]
    title: str
    metadata: dict  # Custom metadata
    created_at: datetime

    class Settings:
        name = "knowledge_base_items"
        indexes = [
            "knowledge_base_id",
            [("knowledge_base_id", 1), ("created_at", -1)],
        ]
```

**Purpose**:
- Metadata about knowledge bases (created_by for access control, embedding model for consistency)
- References to documents in ChromaDB (enables MongoDB-side document tracking)
- Supports future features like knowledge base deletion, access control, usage analytics

#### 3. ChromaDB Collection Management
**New**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/chroma_knowledge_base_repository.py`

```python
# Conceptual repository interface
class ChromaKnowledgeBaseRepository:
    """Repository for knowledge base operations in ChromaDB"""

    def __init__(self, chroma_client):
        self.client = chroma_client

    async def create_collection(self, kb_id: str, name: str, metadata: dict = None):
        """Create ChromaDB collection for knowledge base"""
        collection = self.client.create_collection(
            name=name,
            metadata=metadata,
            get_or_create=False
        )
        return collection

    async def add_documents(self, kb_id: str, documents: List[dict]):
        """Add documents to knowledge base collection"""
        collection = self.client.get_collection(name=kb_id)
        collection.add(
            ids=documents['ids'],
            documents=documents['documents'],
            metadatas=documents['metadatas'],
            embeddings=documents.get('embeddings')  # Optional; ChromaDB auto-embeds
        )

    async def search(self, kb_id: str, query: str, n_results: int = 5):
        """Search knowledge base with semantic similarity"""
        collection = self.client.get_collection(name=kb_id)
        results = collection.query(query_texts=[query], n_results=n_results)
        return results

    async def delete_collection(self, kb_id: str):
        """Delete knowledge base collection"""
        self.client.delete_collection(name=kb_id)
```

**Responsibilities**:
- Create ChromaDB collections for each knowledge base
- Add/update documents with embeddings
- Query collections for semantic similarity
- Delete collections when knowledge base is removed

#### 4. RAG Search Tool
**New**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/rag_search.py`

```python
# Tool function signature
def rag_search(query: str, knowledge_base_id: str = None) -> str:
    """
    Search shared knowledge base using semantic similarity.

    Args:
        query: Search query string
        knowledge_base_id: Optional specific knowledge base ID. If not provided, searches default.

    Returns:
        Formatted search results as string
    """
    # Get ChromaDB client from app context
    # Query knowledge base
    # Format results with document snippets and metadata
    # Return formatted string
    pass
```

**Characteristics**:
- Async wrapper around ChromaDB repository
- Returns results as formatted string (LLM-friendly)
- Handles no results gracefully
- Includes source attribution (document name, section, etc.)

#### 5. Knowledge Base Router
**New**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/knowledge_base_router.py`

```python
# REST endpoints for knowledge base management
@router.post("/knowledge_bases", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(
    name: str,
    description: Optional[str],
    current_user: User = Depends(get_current_user)
):
    """Create new knowledge base (admin only)"""
    pass

@router.post("/knowledge_bases/{kb_id}/documents", response_model=DocumentResponse)
async def upload_documents(
    kb_id: str,
    files: List[UploadFile],
    current_user: User = Depends(get_current_user)
):
    """Upload documents to knowledge base"""
    pass

@router.get("/knowledge_bases/{kb_id}/search")
async def search_knowledge_base(
    kb_id: str,
    query: str,
    limit: int = 5
):
    """Search knowledge base (public endpoint, no auth required)"""
    pass

@router.get("/knowledge_bases")
async def list_knowledge_bases():
    """List available knowledge bases"""
    pass
```

**Access Patterns**:
- Create/manage: Admin or owner only
- Search: Public (all users)
- Delete: Admin or owner only

### Docker Persistence Strategy

#### Option 1: Embedded ChromaDB with Named Volume
```yaml
# docker-compose.yml
services:
  backend:
    # ... existing config ...
    volumes:
      - ./backend:/app
      - chroma_data:/app/chroma_db  # ChromaDB persistent directory

volumes:
  chroma_data:
```

**Pros**:
- Runs in backend container, no separate service
- Data persists to named volume
- Simpler deployment

**Cons**:
- Data only survives container restarts (volume preserved)
- Tightly coupled to backend lifecycle
- Cannot independently scale ChromaDB

#### Option 2: Separate ChromaDB Container
```yaml
# docker-compose.yml
services:
  chroma:
    image: ghcr.io/chroma-core/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/data
    networks:
      - genesis-network

  backend:
    environment:
      - CHROMA_HOST=chroma
      - CHROMA_PORT=8000
    depends_on:
      - chroma

volumes:
  chroma_data:
```

**Pros**:
- Independent service lifecycle
- Can scale independently
- Decoupled from backend

**Cons**:
- Additional container to manage
- Network communication overhead
- More complex deployment

**Recommendation**: Start with Option 1 (embedded) for initial development; migrate to Option 2 if scaling needs arise

### MongoDB Collection Distribution

#### App Database (users, conversations, knowledge_base metadata)
```
App DB MongoDB
├── users (unchanged)
├── conversations (unchanged)
├── knowledge_bases (NEW)
│   ├── name (index)
│   ├── created_by (index)
│   ├── description
│   ├── embedding_model
│   ├── is_public
│   └── created_at, updated_at
└── knowledge_base_items (NEW)
    ├── knowledge_base_id (index)
    ├── chroma_id
    ├── source, source_url, title
    ├── metadata
    └── created_at
```

**Purpose**:
- `knowledge_bases`: Tracks knowledge base ownership, metadata, embedding configuration
- `knowledge_base_items`: Tracks documents loaded into each KB (enables deletion, usage stats, access control)

#### LangGraph Database (unchanged)
Continues to store checkpoints and state; no ChromaDB changes here.

### Configuration & Settings

#### New Environment Variables
```env
# .env
# ChromaDB Configuration
CHROMA_MODE=embedded  # or "http"
CHROMA_PERSIST_DIRECTORY=/app/chroma_db  # For embedded mode
CHROMA_HOST=localhost  # For http mode
CHROMA_PORT=8000  # For http mode
CHROMA_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Knowledge Base Settings
KB_ALLOW_PUBLIC_UPLOAD=false  # Who can create knowledge bases
KB_MAX_FILE_SIZE_MB=10
KB_SUPPORTED_FORMATS=txt,pdf,md  # Comma-separated
```

#### Settings Class Updates
```python
# backend/app/infrastructure/config/settings.py
class Settings(BaseSettings):
    # ... existing settings ...

    # ChromaDB Settings
    chroma_mode: str = "embedded"  # "embedded" or "http"
    chroma_persist_directory: str = "./chroma_db"
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Knowledge Base Settings
    kb_allow_public_upload: bool = False
    kb_max_file_size_mb: int = 10
    kb_supported_formats: str = "txt,pdf,md"
```

---

## Database Recommendations

### 1. Proposed Schema Changes

#### New MongoDB Collections
```javascript
// knowledge_bases collection
{
  _id: ObjectId,
  name: string,                          // "Technical Documentation", "FAQ"
  description: string,
  created_by: string,                    // user_id
  is_public: boolean,
  embedding_model: string,               // "sentence-transformers/all-MiniLM-L6-v2"
  created_at: datetime,
  updated_at: datetime
}

// knowledge_base_items collection
{
  _id: ObjectId,
  knowledge_base_id: string,             // Reference to knowledge_bases._id
  chroma_id: string,                     // ID in ChromaDB collection
  source: string,                        // "file", "url", "text"
  source_url: string,                    // Original URL if applicable
  title: string,                         // Display name
  metadata: {
    // Custom metadata from document processing
    page_number: number,                 // For PDFs
    chunk_index: number,                 // If document chunked
    tags: [string],                      // User-assigned tags
    ...
  },
  created_at: datetime
}
```

#### ChromaDB Collections (Auto-created)
Each knowledge base gets its own collection in ChromaDB:

```python
# ChromaDB collection structure (internal)
collection_name = f"kb_{knowledge_base_id}"

# Documents stored as:
{
  ids: ["doc_1", "doc_2", ...],
  documents: ["text chunk 1", "text chunk 2", ...],
  metadatas: [
    {"source": "file.pdf", "page": 1},
    {"source": "file.pdf", "page": 2},
    ...
  ],
  embeddings: [[0.1, 0.2, ...], [0.3, 0.4, ...], ...]  # Auto-generated
}
```

**Purpose**:
- `knowledge_bases`: Single record per knowledge base, minimal metadata
- `knowledge_base_items`: Track individual documents/chunks in ChromaDB, enable retrieval and deletion
- ChromaDB collections: Store embeddings and semantic content, queried by LLM tool

### 2. Proposed Indexes

#### MongoDB Indexes
```python
# knowledge_bases collection
Index on name
Index on created_by
Index on is_public (for listing public KBs)

# knowledge_base_items collection
Index on knowledge_base_id (for finding items in a KB)
Compound index on (knowledge_base_id, created_at) (for pagination)
```

#### ChromaDB Indexes
ChromaDB manages its own indexes internally. No explicit configuration needed from application layer.

### 3. Repository Changes

#### New Repositories
1. **`MongoKnowledgeBaseRepository`** (implements `IKnowledgeBaseRepository`)
   - `create(name, description, created_by)` → KnowledgeBase
   - `get_by_id(kb_id)` → Optional[KnowledgeBase]
   - `list_public()` → List[KnowledgeBase]
   - `list_user_owned(user_id)` → List[KnowledgeBase]
   - `delete(kb_id)` → bool

2. **`MongoKnowledgeBaseItemRepository`** (implements `IKnowledgeBaseItemRepository`)
   - `add_item(kb_id, chroma_id, source, title, metadata)` → KnowledgeBaseItem
   - `get_items(kb_id, skip, limit)` → List[KnowledgeBaseItem]
   - `delete_item(item_id)` → bool
   - `delete_by_knowledge_base(kb_id)` → int (count deleted)

3. **`ChromaKnowledgeBaseRepository`** (implements `IChromaRepository`)
   - `create_collection(kb_id, name)` → Collection
   - `add_documents(kb_id, documents)` → None
   - `search(kb_id, query, n_results)` → Dict with results
   - `delete_collection(kb_id)` → bool

#### Existing Repositories
- `MongoUserRepository` - unchanged
- `MongoConversationRepository` - unchanged

### 4. Query Optimization

#### Knowledge Base Queries
```python
# List public knowledge bases
docs = await KnowledgeBaseDocument.find(
    KnowledgeBaseDocument.is_public == True
).to_list()
# Covered by index on is_public

# Find knowledge bases created by user
docs = await KnowledgeBaseDocument.find(
    KnowledgeBaseDocument.created_by == user_id
).to_list()
# Covered by index on created_by

# Paginate knowledge base items
items = await KnowledgeBaseItemDocument.find(
    KnowledgeBaseItemDocument.knowledge_base_id == kb_id
).sort(-KnowledgeBaseItemDocument.created_at).skip(skip).limit(limit).to_list()
# Covered by compound index (knowledge_base_id, created_at)
```

#### ChromaDB Search
```python
# Vector similarity search in ChromaDB
results = collection.query(
    query_texts=["user query"],
    n_results=5
)
# Returns: {"ids": [...], "distances": [...], "documents": [...], "metadatas": [...]}
```

**Performance Characteristics**:
- MongoDB queries: O(log n) for indexed lookups, O(n) for collection scans
- ChromaDB queries: O(n) for brute-force similarity (acceptable for typical KB sizes < 10k docs)
- Both databases operate independently; no join queries needed

### 5. Connection Management & Error Handling

#### ChromaDB Client Initialization
```python
# backend/app/infrastructure/database/chromadb_client.py
class ChromaDBClient:
    client = None

    @classmethod
    async def initialize(cls):
        """Initialize ChromaDB client based on configuration"""
        try:
            if settings.chroma_mode == "embedded":
                logger.info(f"Initializing embedded ChromaDB at {settings.chroma_persist_directory}")
                cls.client = chromadb.PersistentClient(
                    path=settings.chroma_persist_directory
                )
            else:  # http mode
                logger.info(f"Connecting to ChromaDB at {settings.chroma_host}:{settings.chroma_port}")
                cls.client = chromadb.HttpClient(
                    host=settings.chroma_host,
                    port=settings.chroma_port
                )
            logger.info("ChromaDB initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    @classmethod
    async def close(cls):
        """Close ChromaDB client if needed"""
        if cls.client:
            # PersistentClient and HttpClient don't require explicit close
            # but may want to log shutdown
            logger.info("ChromaDB client closed")
```

#### Application Lifespan Integration
```python
# backend/app/main.py - Updated lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name}")

    try:
        # Initialize databases
        await AppDatabase.connect([UserDocument, ConversationDocument, KnowledgeBaseDocument, KnowledgeBaseItemDocument])

        # Initialize ChromaDB
        await ChromaDBClient.initialize()

        # Initialize LangGraph checkpointer
        checkpointer_context, checkpointer = await get_checkpointer()
        app.state.checkpointer_context = checkpointer_context
        app.state.checkpointer = checkpointer

        # Compile graphs with tools
        from app.langgraph.graphs.streaming_chat_graph import create_streaming_chat_graph
        app.state.streaming_chat_graph = create_streaming_chat_graph(
            checkpointer=checkpointer,
            chroma_client=ChromaDBClient.client
        )

        logger.info("Application startup complete")
        yield

        # Shutdown
        logger.info("Closing database connections")
        await AppDatabase.close()
        await checkpointer_context.__aexit__(None, None, None)
        ChromaDBClient.close()
        logger.info("Application shutdown complete")

    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
```

#### Error Handling for RAG Search
```python
# In RAG search tool or router
async def rag_search(query: str, kb_id: str = None) -> str:
    """Search knowledge base with error handling"""
    try:
        if not kb_id:
            # Use default knowledge base
            kb = await kb_repository.get_default()
            if not kb:
                return "No default knowledge base configured"
            kb_id = kb.id

        # Verify knowledge base exists and is accessible
        kb = await kb_repository.get_by_id(kb_id)
        if not kb or (not kb.is_public and kb.created_by != current_user.id):
            return "Knowledge base not found or access denied"

        # Search ChromaDB
        results = await chroma_repository.search(kb_id, query, n_results=5)

        if not results.get("documents"):
            return f"No documents found in knowledge base matching query: {query}"

        # Format results for LLM
        formatted = _format_search_results(results, kb)
        return formatted

    except Exception as e:
        logger.error(f"RAG search failed for query '{query}': {e}")
        return f"Error searching knowledge base: {str(e)}"
```

#### RAG Search Tool Registration
```python
# backend/app/langgraph/tools/rag_search.py

def rag_search(query: str, knowledge_base_id: str = None) -> str:
    """
    Search shared knowledge base using semantic similarity.
    Returns relevant document excerpts found in the knowledge base.

    Args:
        query: The search query
        knowledge_base_id: Optional specific knowledge base to search

    Returns:
        Formatted search results with document excerpts and sources
    """
    # Get current app context
    from app.main import app

    # Access repositories from app state
    chroma_repo = app.state.chroma_repository
    kb_repo = app.state.kb_repository

    # Perform search (synchronous wrapper around async)
    import asyncio
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(
        _async_rag_search(query, knowledge_base_id, chroma_repo, kb_repo)
    )
    return results

async def _async_rag_search(query, kb_id, chroma_repo, kb_repo):
    """Async implementation of RAG search"""
    try:
        if not kb_id:
            kb = await kb_repo.get_default_public()
        else:
            kb = await kb_repo.get_by_id(kb_id)

        if not kb:
            return "No knowledge base available"

        results = await chroma_repo.search(kb.id, query, n_results=5)
        return _format_for_llm(results, kb)
    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        return f"Search failed: {str(e)}"
```

**Tool Registration in Graph**:
```python
# backend/app/langgraph/graphs/streaming_chat_graph.py

def create_streaming_chat_graph(checkpointer, chroma_client):
    """Create streaming chat graph with tools"""
    from langchain.tools import Tool
    from app.langgraph.tools import rag_search, web_search, add, multiply

    # Define RAG search tool
    rag_tool = Tool(
        name="rag_search",
        func=rag_search,
        description="Search shared knowledge base for relevant information"
    )

    # Bind tools to LLM
    tools = [rag_tool, web_search, add, multiply]
    llm_with_tools = llm.bind_tools(tools)

    # Build graph with tools
    graph_builder = StateGraph(ConversationState)
    graph_builder.add_node("call_llm", lambda state: {"llm_response": llm_with_tools.invoke(state)})
    # ... continue graph definition ...
```

### 6. File Organization & Directory Structure

```
backend/
├── app/
│   ├── infrastructure/
│   │   ├── database/
│   │   │   ├── mongodb.py                      (existing - add ChromaDB client init)
│   │   │   ├── chromadb_client.py              (NEW)
│   │   │   └── langgraph_checkpointer.py       (existing)
│   │   └── config/
│   │       └── settings.py                     (existing - add chroma settings)
│   │
│   ├── adapters/
│   │   ├── outbound/
│   │   │   ├── repositories/
│   │   │   │   ├── mongo_models.py             (existing - add KB documents)
│   │   │   │   ├── mongo_knowledge_base_repository.py   (NEW)
│   │   │   │   ├── chroma_knowledge_base_repository.py  (NEW)
│   │   │   │   └── [existing repositories]
│   │   │   └── ...
│   │   ├── inbound/
│   │   │   ├── knowledge_base_router.py        (NEW)
│   │   │   ├── websocket_handler.py            (existing - unchanged)
│   │   │   └── [existing routers]
│   │   └── ...
│   │
│   ├── langgraph/
│   │   ├── tools/
│   │   │   ├── rag_search.py                   (NEW)
│   │   │   ├── web_search.py                   (existing)
│   │   │   ├── __init__.py                     (existing - add rag_search export)
│   │   │   └── [other tools]
│   │   ├── graphs/
│   │   │   ├── streaming_chat_graph.py         (existing - add rag_search tool)
│   │   │   ├── chat_graph.py                   (existing - unchanged)
│   │   │   └── ...
│   │   └── ...
│   │
│   ├── core/
│   │   ├── ports/
│   │   │   ├── knowledge_base_repository.py    (NEW - interface)
│   │   │   ├── chroma_repository.py            (NEW - interface)
│   │   │   └── [existing ports]
│   │   ├── domain/
│   │   │   ├── knowledge_base.py               (NEW - domain model)
│   │   │   └── [existing domains]
│   │   └── ...
│   │
│   └── main.py                                 (existing - update lifespan)
│
├── docker-compose.yml                          (existing - add chroma volume)
├── requirements.txt                            (existing - add chromadb)
└── .env.example                                (existing - add chroma env vars)
```

---

## Implementation Guidance

### Phase 1: MongoDB Schema & Configuration (No ChromaDB Yet)

**Step 1: Add Knowledge Base Document Models**

File: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_models.py`

Add two new Beanie document classes:
```python
class KnowledgeBaseDocument(Document):
    name: str
    description: Optional[str] = None
    created_by: str
    is_public: bool = True
    embedding_model: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "knowledge_bases"
        indexes = ["name", "created_by", "is_public"]

class KnowledgeBaseItemDocument(Document):
    knowledge_base_id: Indexed(str)
    chroma_id: str
    source: str
    source_url: Optional[str] = None
    title: str
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "knowledge_base_items"
        indexes = [
            "knowledge_base_id",
            [("knowledge_base_id", 1), ("created_at", -1)],
        ]
```

**Step 2: Update Settings for ChromaDB Configuration**

File: `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py`

Add new settings class fields:
```python
# ChromaDB Settings
chroma_mode: str = "embedded"
chroma_persist_directory: str = "./chroma_db"
chroma_host: str = "localhost"
chroma_port: int = 8000
chroma_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

# Knowledge Base Settings
kb_allow_public_upload: bool = False
kb_max_file_size_mb: int = 10
kb_supported_formats: str = "txt,pdf,md"
```

**Step 3: Update MongoDB Initialization**

File: `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py`

Update lifespan to include new document models:
```python
await AppDatabase.connect(document_models=[
    UserDocument,
    ConversationDocument,
    KnowledgeBaseDocument,
    KnowledgeBaseItemDocument
])
```

### Phase 2: ChromaDB Client Initialization

**Step 4: Create ChromaDB Client Manager**

File: `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/chromadb_client.py`

```python
# ABOUTME: ChromaDB vector database client initialization and lifecycle management
# ABOUTME: Manages connection to ChromaDB (embedded or HTTP) and provides global access

import chromadb
from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

class ChromaDBClient:
    """ChromaDB vector database client manager."""

    client = None

    @classmethod
    async def initialize(cls):
        """Initialize ChromaDB client based on configuration."""
        try:
            if settings.chroma_mode == "embedded":
                logger.info(f"Initializing embedded ChromaDB at {settings.chroma_persist_directory}")
                cls.client = chromadb.PersistentClient(
                    path=settings.chroma_persist_directory
                )
            elif settings.chroma_mode == "http":
                logger.info(f"Connecting to ChromaDB at {settings.chroma_host}:{settings.chroma_port}")
                cls.client = chromadb.HttpClient(
                    host=settings.chroma_host,
                    port=settings.chroma_port
                )
            else:
                raise ValueError(f"Invalid chroma_mode: {settings.chroma_mode}")

            logger.info("ChromaDB initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    @classmethod
    def close(cls):
        """Close ChromaDB client if needed."""
        if cls.client:
            logger.info("Closing ChromaDB client")
            # PersistentClient doesn't require explicit cleanup
            # HttpClient may benefit from cleanup in future versions
            cls.client = None
```

**Step 5: Update Application Lifespan**

File: `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py`

Import and initialize ChromaDB:
```python
from app.infrastructure.database.chromadb_client import ChromaDBClient

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    try:
        # ... existing database initialization ...

        # Initialize ChromaDB
        await ChromaDBClient.initialize()
        app.state.chroma_client = ChromaDBClient.client

        # ... rest of initialization ...

        logger.info("Application startup complete")
        yield

        # Shutdown
        logger.info("Shutting down application")
        # ... existing cleanup ...
        ChromaDBClient.close()
        logger.info("Application shutdown complete")

    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise
```

### Phase 3: Repository Layer Implementation

**Step 6: Create Knowledge Base Repository Ports**

File: `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/knowledge_base_repository.py` (NEW)

```python
# ABOUTME: Knowledge base repository port interface for MongoDB storage
# ABOUTME: Abstract interface for knowledge base metadata operations

from abc import ABC, abstractmethod
from typing import Optional, List
from app.core.domain.knowledge_base import KnowledgeBase

class IKnowledgeBaseRepository(ABC):
    """Port for knowledge base metadata operations."""

    @abstractmethod
    async def create(self, name: str, description: str, created_by: str, is_public: bool = True) -> KnowledgeBase:
        """Create a new knowledge base."""
        pass

    @abstractmethod
    async def get_by_id(self, kb_id: str) -> Optional[KnowledgeBase]:
        """Retrieve knowledge base by ID."""
        pass

    @abstractmethod
    async def list_public(self, skip: int = 0, limit: int = 100) -> List[KnowledgeBase]:
        """List public knowledge bases."""
        pass

    @abstractmethod
    async def list_user_owned(self, user_id: str, skip: int = 0, limit: int = 100) -> List[KnowledgeBase]:
        """List knowledge bases created by user."""
        pass

    @abstractmethod
    async def delete(self, kb_id: str) -> bool:
        """Delete a knowledge base."""
        pass
```

**Step 7: Create ChromaDB Repository Port**

File: `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/chroma_repository.py` (NEW)

```python
# ABOUTME: ChromaDB repository port interface for vector operations
# ABOUTME: Abstract interface for document storage and semantic search

from abc import ABC, abstractmethod
from typing import Dict, List

class IChromaRepository(ABC):
    """Port for ChromaDB vector database operations."""

    @abstractmethod
    async def create_collection(self, kb_id: str, name: str) -> None:
        """Create collection for knowledge base."""
        pass

    @abstractmethod
    async def add_documents(self, kb_id: str, documents: Dict[str, List]) -> None:
        """Add documents to knowledge base collection."""
        pass

    @abstractmethod
    async def search(self, kb_id: str, query: str, n_results: int = 5) -> Dict:
        """Search knowledge base with semantic similarity."""
        pass

    @abstractmethod
    async def delete_collection(self, kb_id: str) -> bool:
        """Delete collection."""
        pass
```

**Step 8: Create Domain Models**

File: `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/knowledge_base.py` (NEW)

```python
# ABOUTME: Knowledge base domain models for business logic
# ABOUTME: Pure Python dataclasses representing knowledge base entities

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class KnowledgeBase:
    """Knowledge base domain model."""
    id: str
    name: str
    description: Optional[str]
    created_by: str
    is_public: bool
    embedding_model: str
    created_at: datetime
    updated_at: datetime

@dataclass
class KnowledgeBaseItem:
    """Knowledge base document item."""
    id: str
    knowledge_base_id: str
    chroma_id: str
    source: str
    source_url: Optional[str]
    title: str
    metadata: dict
    created_at: datetime
```

**Step 9: Create MongoDB Repository Implementation**

File: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_knowledge_base_repository.py` (NEW)

```python
# ABOUTME: MongoDB implementation of knowledge base repository
# ABOUTME: Persists knowledge base metadata using Beanie ODM

from typing import Optional, List
from datetime import datetime
from app.core.ports.knowledge_base_repository import IKnowledgeBaseRepository
from app.core.domain.knowledge_base import KnowledgeBase
from app.adapters.outbound.repositories.mongo_models import KnowledgeBaseDocument

class MongoKnowledgeBaseRepository(IKnowledgeBaseRepository):
    """MongoDB implementation of knowledge base repository."""

    def _to_domain(self, doc: KnowledgeBaseDocument) -> KnowledgeBase:
        """Convert MongoDB document to domain model."""
        return KnowledgeBase(
            id=str(doc.id),
            name=doc.name,
            description=doc.description,
            created_by=doc.created_by,
            is_public=doc.is_public,
            embedding_model=doc.embedding_model,
            created_at=doc.created_at,
            updated_at=doc.updated_at
        )

    async def create(self, name: str, description: str, created_by: str, is_public: bool = True) -> KnowledgeBase:
        """Create new knowledge base."""
        doc = KnowledgeBaseDocument(
            name=name,
            description=description,
            created_by=created_by,
            is_public=is_public,
            embedding_model="sentence-transformers/all-MiniLM-L6-v2"  # Default model
        )
        await doc.insert()
        return self._to_domain(doc)

    async def get_by_id(self, kb_id: str) -> Optional[KnowledgeBase]:
        """Retrieve knowledge base by ID."""
        doc = await KnowledgeBaseDocument.get(kb_id)
        return self._to_domain(doc) if doc else None

    async def list_public(self, skip: int = 0, limit: int = 100) -> List[KnowledgeBase]:
        """List public knowledge bases."""
        docs = await KnowledgeBaseDocument.find(
            KnowledgeBaseDocument.is_public == True
        ).skip(skip).limit(limit).to_list()
        return [self._to_domain(doc) for doc in docs]

    async def list_user_owned(self, user_id: str, skip: int = 0, limit: int = 100) -> List[KnowledgeBase]:
        """List knowledge bases created by user."""
        docs = await KnowledgeBaseDocument.find(
            KnowledgeBaseDocument.created_by == user_id
        ).skip(skip).limit(limit).to_list()
        return [self._to_domain(doc) for doc in docs]

    async def delete(self, kb_id: str) -> bool:
        """Delete knowledge base."""
        doc = await KnowledgeBaseDocument.get(kb_id)
        if not doc:
            return False
        await doc.delete()
        return True
```

**Step 10: Create ChromaDB Repository Implementation**

File: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/chroma_knowledge_base_repository.py` (NEW)

```python
# ABOUTME: ChromaDB implementation of vector database repository
# ABOUTME: Manages embeddings and semantic search for knowledge bases

from typing import Dict, List, Optional
from app.core.ports.chroma_repository import IChromaRepository
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

class ChromaKnowledgeBaseRepository(IChromaRepository):
    """ChromaDB implementation for vector storage and search."""

    def __init__(self, chroma_client):
        """Initialize with ChromaDB client."""
        self.client = chroma_client

    async def create_collection(self, kb_id: str, name: str) -> None:
        """Create ChromaDB collection for knowledge base."""
        try:
            collection_name = f"kb_{kb_id}"
            self.client.create_collection(
                name=collection_name,
                metadata={"kb_id": kb_id, "display_name": name},
                get_or_create=True
            )
            logger.info(f"Created ChromaDB collection: {collection_name}")
        except Exception as e:
            logger.error(f"Failed to create ChromaDB collection: {e}")
            raise

    async def add_documents(self, kb_id: str, documents: Dict[str, List]) -> None:
        """Add documents with embeddings to knowledge base."""
        try:
            collection_name = f"kb_{kb_id}"
            collection = self.client.get_collection(name=collection_name)

            # ChromaDB auto-embeds if embeddings not provided
            collection.add(
                ids=documents.get("ids", []),
                documents=documents.get("documents", []),
                metadatas=documents.get("metadatas", []),
                embeddings=documents.get("embeddings")  # Optional
            )
            logger.info(f"Added {len(documents.get('ids', []))} documents to {collection_name}")
        except Exception as e:
            logger.error(f"Failed to add documents to ChromaDB: {e}")
            raise

    async def search(self, kb_id: str, query: str, n_results: int = 5) -> Dict:
        """Search knowledge base using semantic similarity."""
        try:
            collection_name = f"kb_{kb_id}"
            collection = self.client.get_collection(name=collection_name)

            results = collection.query(
                query_texts=[query],
                n_results=n_results
            )

            logger.debug(f"Search in {collection_name} returned {len(results.get('documents', [[]])[0])} results")
            return results
        except Exception as e:
            logger.error(f"Failed to search ChromaDB: {e}")
            raise

    async def delete_collection(self, kb_id: str) -> bool:
        """Delete knowledge base collection."""
        try:
            collection_name = f"kb_{kb_id}"
            self.client.delete_collection(name=collection_name)
            logger.info(f"Deleted ChromaDB collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete ChromaDB collection: {e}")
            return False
```

### Phase 4: Tool Implementation

**Step 11: Create RAG Search Tool**

File: `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/rag_search.py` (NEW)

```python
# ABOUTME: RAG search tool for semantic knowledge base queries
# ABOUTME: Integrates ChromaDB for vector similarity search within LangGraph

from typing import Optional
import asyncio
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

def rag_search(query: str, knowledge_base_id: Optional[str] = None) -> str:
    """
    Search shared knowledge base using semantic similarity.

    This tool searches the knowledge base using vector embeddings
    and returns relevant document excerpts found in the KB.

    Args:
        query: The search query string
        knowledge_base_id: Optional specific knowledge base ID to search.
                          If not provided, searches default public KB.

    Returns:
        Formatted search results with document excerpts and source information,
        or error message if search fails or no results found.
    """
    try:
        # Get app context and repositories
        from app.main import app

        chroma_repo = getattr(app.state, 'chroma_repository', None)
        kb_repo = getattr(app.state, 'kb_repository', None)

        if not chroma_repo or not kb_repo:
            return "Knowledge base service not available"

        # Run async search in event loop
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(
            _async_rag_search(query, knowledge_base_id, chroma_repo, kb_repo)
        )
        return results

    except Exception as e:
        logger.error(f"RAG search tool error: {e}")
        return f"Error performing knowledge base search: {str(e)}"

async def _async_rag_search(query: str, kb_id: Optional[str], chroma_repo, kb_repo) -> str:
    """Async implementation of RAG search."""
    try:
        # Determine which knowledge base to search
        if kb_id:
            kb = await kb_repo.get_by_id(kb_id)
        else:
            # Get first public KB
            kbs = await kb_repo.list_public(limit=1)
            kb = kbs[0] if kbs else None

        if not kb:
            return "No knowledge base available for search"

        # Search ChromaDB
        results = await chroma_repo.search(kb.id, query, n_results=5)

        # Format results for LLM
        if not results.get("documents") or not results["documents"][0]:
            return f"No documents found in '{kb.name}' matching your query"

        formatted = _format_search_results(results, kb)
        return formatted

    except Exception as e:
        logger.error(f"Async RAG search failed: {e}")
        raise

def _format_search_results(chroma_results: dict, kb) -> str:
    """Format ChromaDB results for LLM consumption."""
    formatted_lines = [f"Knowledge Base: {kb.name}"]

    documents = chroma_results.get("documents", [[]])[0]
    metadatas = chroma_results.get("metadatas", [[]])[0]
    distances = chroma_results.get("distances", [[]])[0]

    for i, (doc, meta, distance) in enumerate(zip(documents, metadatas, distances)):
        source = meta.get("source", "Unknown")
        title = meta.get("title", "Untitled")

        formatted_lines.append(f"\n[Result {i+1}] {title} (from {source})")
        formatted_lines.append(f"Relevance: {1 - distance:.2%}")
        formatted_lines.append(f"Content: {doc[:300]}...")

    return "\n".join(formatted_lines)
```

**Step 12: Register RAG Tool with LangGraph**

File: `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/__init__.py`

Update exports:
```python
# Expose tools for import
from .multiply import multiply
from .add import add
from .web_search import web_search
from .rag_search import rag_search

__all__ = ["multiply", "add", "web_search", "rag_search"]
```

**Step 13: Update Chat Graphs to Include RAG Tool**

File: `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py`

Register rag_search tool with LLM:
```python
# In create_streaming_chat_graph function:
from langchain.tools import Tool
from app.langgraph.tools import rag_search, web_search, add, multiply

def create_streaming_chat_graph(checkpointer, chroma_client):
    """Create streaming chat graph with tools."""

    # Define RAG search tool
    rag_tool = Tool(
        name="rag_search",
        func=rag_search,
        description="Search the shared knowledge base for information using natural language queries. Returns relevant documents and excerpts."
    )

    # Bind all tools to LLM
    tools = [rag_tool, web_search, add, multiply]
    llm_with_tools = llm.bind_tools(tools)

    # Build graph with tool support
    graph_builder = StateGraph(ConversationState)

    # ... add nodes ...

    # Use LLM with tools for LLM node
    def call_llm_with_tools(state):
        response = llm_with_tools.invoke(state)
        return {"llm_response": response}

    graph_builder.add_node("call_llm", call_llm_with_tools)

    # ... rest of graph setup ...
```

### Phase 5: API Routes for Knowledge Base Management

**Step 14: Create Knowledge Base Router**

File: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/knowledge_base_router.py` (NEW)

```python
# ABOUTME: REST API routes for knowledge base management and search
# ABOUTME: Handles knowledge base CRUD and document upload operations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List, Optional
from app.core.domain.user import User
from app.infrastructure.security.dependencies import get_current_user
from app.core.ports.knowledge_base_repository import IKnowledgeBaseRepository
from app.core.ports.chroma_repository import IChromaRepository
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/knowledge_bases", tags=["knowledge_bases"])

@router.post("/", response_model=dict)
async def create_knowledge_base(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    kb_repo: IKnowledgeBaseRepository = Depends(lambda: app.state.kb_repository)
):
    """Create new knowledge base (authenticated users only)."""
    try:
        kb = await kb_repo.create(
            name=name,
            description=description or "",
            created_by=current_user.id,
            is_public=True
        )
        logger.info(f"User {current_user.id} created knowledge base: {kb.id}")
        return {"id": kb.id, "name": kb.name, "created_by": kb.created_by}
    except Exception as e:
        logger.error(f"Failed to create knowledge base: {e}")
        raise HTTPException(status_code=500, detail="Failed to create knowledge base")

@router.get("/")
async def list_knowledge_bases(
    skip: int = 0,
    limit: int = 100,
    kb_repo: IKnowledgeBaseRepository = Depends(lambda: app.state.kb_repository)
):
    """List public knowledge bases."""
    try:
        kbs = await kb_repo.list_public(skip=skip, limit=limit)
        return [{"id": kb.id, "name": kb.name, "description": kb.description} for kb in kbs]
    except Exception as e:
        logger.error(f"Failed to list knowledge bases: {e}")
        raise HTTPException(status_code=500, detail="Failed to list knowledge bases")

@router.post("/{kb_id}/documents")
async def upload_documents(
    kb_id: str,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    kb_repo: IKnowledgeBaseRepository = Depends(lambda: app.state.kb_repository),
    chroma_repo: IChromaRepository = Depends(lambda: app.state.chroma_repository)
):
    """Upload documents to knowledge base."""
    try:
        # Verify knowledge base exists and user owns it
        kb = await kb_repo.get_by_id(kb_id)
        if not kb or kb.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to modify this knowledge base")

        # Process files
        # TODO: Implement file processing (extract text, chunk, embed)

        logger.info(f"User {current_user.id} uploaded {len(files)} documents to KB {kb_id}")
        return {"status": "success", "documents_added": len(files)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload documents")

@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    current_user: User = Depends(get_current_user),
    kb_repo: IKnowledgeBaseRepository = Depends(lambda: app.state.kb_repository),
    chroma_repo: IChromaRepository = Depends(lambda: app.state.chroma_repository)
):
    """Delete knowledge base and all documents (owner only)."""
    try:
        kb = await kb_repo.get_by_id(kb_id)
        if not kb or kb.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Delete from ChromaDB
        await chroma_repo.delete_collection(kb_id)

        # Delete from MongoDB
        await kb_repo.delete(kb_id)

        logger.info(f"User {current_user.id} deleted knowledge base {kb_id}")
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete knowledge base: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete knowledge base")
```

**Step 15: Register Knowledge Base Router**

File: `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py`

Add router import and include:
```python
from app.adapters.inbound.knowledge_base_router import router as knowledge_base_router

def create_app() -> FastAPI:
    # ... existing code ...

    # Include routers
    app.include_router(auth_router)
    app.include_router(user_router)
    app.include_router(conversation_router)
    app.include_router(message_router)
    app.include_router(websocket_router)
    app.include_router(knowledge_base_router)  # NEW

    return app
```

### Phase 6: Docker & Environment Setup

**Step 16: Update docker-compose.yml**

File: `/Users/pablolozano/Mac Projects August/genesis/docker-compose.yml`

Add ChromaDB data volume:
```yaml
volumes:
  mongodb_data:
  chroma_data:  # NEW
```

(Embedded ChromaDB doesn't need separate container for dev, but volume persists data)

**Step 17: Update .env.example**

Add ChromaDB configuration:
```env
# ChromaDB Configuration
CHROMA_MODE=embedded
CHROMA_PERSIST_DIRECTORY=./chroma_db
CHROMA_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Knowledge Base Settings
KB_ALLOW_PUBLIC_UPLOAD=false
KB_MAX_FILE_SIZE_MB=10
KB_SUPPORTED_FORMATS=txt,pdf,md
```

**Step 18: Update requirements.txt**

Add ChromaDB and dependencies:
```
chromadb>=0.4.0
sentence-transformers>=2.2.0
```

---

## Risks and Considerations

### 1. Vector Embedding Consistency

**Risk**: Using different embedding models (configured per KB) can cause inconsistency
- **Mitigation**: Enforce single embedding model globally or validate on KB creation
- **Recommendation**: Set `CHROMA_EMBEDDING_MODEL` as default; allow override only with validation

**Risk**: ChromaDB auto-embedding may not match expected model
- **Mitigation**: Explicitly set embedding model during collection creation
- **Testing**: Verify embedding dimension consistency across operations

### 2. Document Lifecycle Management

**Risk**: Documents deleted from MongoDB (knowledge_base_items) but still in ChromaDB
- **Mitigation**: Implement cascading delete in knowledge_base_delete operation
- **Recommendation**: Delete ChromaDB collection before deleting MongoDB records

**Risk**: Large document uploads consume memory
- **Mitigation**: Implement chunking strategy (max chunk size, overlap)
- **Recommendation**: Process files in batches, not all at once

### 3. Query Performance at Scale

**Risk**: ChromaDB similarity search with large collections (>100k docs) may slow
- **Characteristic**: O(n) brute-force by default; acceptable for most use cases
- **Optimization Path**: Add HNSW indexing for very large collections (future)

**Risk**: Paginating similarity results is non-trivial
- **Impact**: Can't page through search results by offset
- **Recommendation**: Return top N results (5-10); user refines query if needed

### 4. Authorization & Access Control

**Risk**: All users can search all public knowledge bases
- **This is intended**: Shared knowledge base pattern
- **Mitigation**: Implement knowledge base ownership/sharing model if needed later

**Risk**: No fine-grained access control on document level
- **Impact**: User sees all document excerpts in search results
- **Recommendation**: Implement document-level sensitivity marking if needed

### 5. Data Consistency Between Databases

**Risk**: MongoDB (knowledge_base_items) and ChromaDB collections can drift
- **Example**: Item deleted from MongoDB but remains in ChromaDB
- **Mitigation**: Implement transaction-like semantics (delete ChromaDB first, then MongoDB)
- **Fallback**: Periodic reconciliation job to sync states

### 6. Error Handling & Graceful Degradation

**Risk**: ChromaDB unavailable breaks RAG tool
- **Impact**: Tool fails; LLM cannot use it
- **Mitigation**: Catch ChromaDB errors in rag_search tool; return friendly error message
- **Recommendation**: Log errors; monitor ChromaDB availability

**Risk**: MongoDB metadata unavailable but ChromaDB works
- **Impact**: Can't create/delete KBs but search still works (orphaned documents)
- **Mitigation**: Validate KB existence before returning search results

### 7. Embedding Model Initialization

**Risk**: Downloading embedding model on first use blocks startup
- **Impact**: Application takes time to start (sentence-transformers downloads model)
- **Mitigation**: Pre-download model in Docker image or during initialization
- **Recommendation**: Run model init in startup, log progress

### 8. Persistence & Disaster Recovery

**Risk**: Embedded ChromaDB data lost if volume deleted
- **Mitigation**: Regular backup strategy (volume snapshots, MongoDB backup separate from ChromaDB)
- **Recommendation**: For production, consider separate ChromaDB service with replication

**Risk**: MongoDB backup doesn't include ChromaDB vectors
- **Impact**: Restore from MongoDB backup without corresponding vectors
- **Mitigation**: Backup ChromaDB persistence directory separately
- **Recommendation**: Coordinate backup of both databases

---

## Testing Strategy

### Unit Tests

#### ChromaDB Client Tests
```python
# tests/infrastructure/test_chromadb_client.py
@pytest.mark.asyncio
async def test_embedded_chromadb_initialization():
    """Verify embedded ChromaDB initializes correctly"""
    # Mock settings
    # Call ChromaDBClient.initialize()
    # Assert client is not None
    # Assert client is PersistentClient

@pytest.mark.asyncio
async def test_chromadb_http_initialization():
    """Verify HTTP ChromaDB initializes with host/port"""
    # Mock settings for HTTP mode
    # Mock HttpClient
    # Assert client created with correct host/port
```

#### Repository Tests
```python
# tests/adapters/test_mongo_knowledge_base_repository.py
@pytest.mark.asyncio
async def test_create_knowledge_base():
    """Verify KB creation stores in MongoDB"""
    repo = MongoKnowledgeBaseRepository()
    kb = await repo.create("Test KB", "Test", "user123")
    assert kb.id is not None
    assert kb.name == "Test KB"

# tests/adapters/test_chroma_knowledge_base_repository.py
@pytest.mark.asyncio
async def test_create_collection():
    """Verify collection creation in ChromaDB"""
    repo = ChromaKnowledgeBaseRepository(mock_chroma_client)
    await repo.create_collection("kb_123", "Test Collection")
    # Verify client.create_collection called with correct params
```

### Integration Tests

#### RAG Search Integration
```python
# tests/integration/test_rag_search_integration.py
@pytest.mark.asyncio
async def test_rag_search_end_to_end():
    """Test creating KB, adding documents, searching"""
    # 1. Create knowledge base in MongoDB
    kb = await kb_repository.create("Test KB", "", "user1")

    # 2. Create ChromaDB collection
    await chroma_repository.create_collection(kb.id, "Test KB")

    # 3. Add documents
    docs = {
        "ids": ["doc1", "doc2"],
        "documents": ["Python is a programming language", "JavaScript runs in browsers"],
        "metadatas": [{"source": "test"}, {"source": "test"}]
    }
    await chroma_repository.add_documents(kb.id, docs)

    # 4. Search
    results = await chroma_repository.search(kb.id, "What is Python?", n_results=5)

    # 5. Verify results
    assert len(results["documents"][0]) > 0
    assert "Python" in results["documents"][0][0]
```

#### Knowledge Base API Tests
```python
# tests/api/test_knowledge_base_endpoints.py
def test_list_public_knowledge_bases():
    """Test GET /api/knowledge_bases returns public KBs"""
    response = client.get("/api/knowledge_bases")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_knowledge_base_requires_auth():
    """Test POST /api/knowledge_bases requires authentication"""
    response = client.post("/api/knowledge_bases", json={"name": "Test"})
    assert response.status_code == 401

def test_upload_documents_requires_ownership():
    """Test only KB owner can upload documents"""
    # Create KB as user1
    # Try to upload as user2
    # Should fail with 403
```

### Tool Integration Tests
```python
# tests/langgraph/test_rag_search_tool.py
@pytest.mark.asyncio
async def test_rag_search_tool_in_graph():
    """Test RAG search tool integrated in LangGraph"""
    # Create KB with sample documents
    # Compile graph with RAG tool
    # Run graph with message asking for knowledge
    # Verify RAG tool was called
    # Verify LLM received search results

@pytest.mark.asyncio
async def test_rag_search_tool_no_results():
    """Test graceful handling when no documents match"""
    # Search for query with no matching documents
    # Verify tool returns "No documents found" message
    # Verify LLM can handle absence gracefully
```

### Performance Tests
```python
# tests/performance/test_chroma_search_performance.py
@pytest.mark.asyncio
async def test_search_performance_small_collection():
    """Verify search is fast for typical collection sizes"""
    # Add 100 documents to ChromaDB
    # Run search
    # Assert search completes in < 100ms

@pytest.mark.asyncio
async def test_search_performance_large_collection():
    """Test search performance with larger collection"""
    # Add 10000 documents
    # Run search
    # Should still be < 1 second
```

---

## Summary of Critical Points for Main Agent

### New MongoDB Collections
1. **knowledge_bases** - Knowledge base metadata (name, description, owner, embedding_model)
2. **knowledge_base_items** - References to documents in ChromaDB (enables tracking and deletion)

### New ChromaDB Collections
- Dynamically created per knowledge base as `kb_{kb_id}`
- Auto-creates indexes for semantic search
- Stores embeddings and document text

### New File Structure
```
Backend Changes:
- /infrastructure/database/chromadb_client.py (NEW)
- /infrastructure/config/settings.py (ADD chroma settings)
- /adapters/outbound/repositories/mongo_models.py (ADD KB documents)
- /adapters/outbound/repositories/mongo_knowledge_base_repository.py (NEW)
- /adapters/outbound/repositories/chroma_knowledge_base_repository.py (NEW)
- /core/ports/knowledge_base_repository.py (NEW)
- /core/ports/chroma_repository.py (NEW)
- /core/domain/knowledge_base.py (NEW)
- /langgraph/tools/rag_search.py (NEW)
- /langgraph/tools/__init__.py (ADD rag_search export)
- /langgraph/graphs/streaming_chat_graph.py (ADD rag_tool registration)
- /adapters/inbound/knowledge_base_router.py (NEW)
- /main.py (ADD ChromaDB init, KB router)
- docker-compose.yml (ADD chroma_data volume)
- requirements.txt (ADD chromadb, sentence-transformers)
- .env.example (ADD chroma env vars)
```

### Key Design Decisions
1. **Embedded ChromaDB**: Runs in backend container initially (simpler deployment)
2. **Shared Knowledge Base**: All users can search (no per-user isolation)
3. **MongoDB as Source of Truth**: KB metadata stored in MongoDB; ChromaDB as index/cache
4. **Vector Auto-Embedding**: Let ChromaDB generate embeddings (no manual embedding code)
5. **Single Embedding Model**: Fixed model for all KBs (can be made configurable per KB)

### Dependencies
- `chromadb>=0.4.0`
- `sentence-transformers>=2.2.0`

### Critical Assumptions
1. ChromaDB embedded mode suitable for development/deployment
2. Single embedding model sufficient (configurable later)
3. Vector similarity search performance acceptable for KB sizes < 10k documents
4. Users trust knowledge base content (no document-level access control)
5. MongoDB and ChromaDB synchronized (no complex distributed transactions)

### Known Gaps (Document for Main Agent Clarification)
1. **File Processing**: How to extract text from PDF/DOC files? (Use PyPDF2, python-docx?)
2. **Document Chunking**: Should long documents be split into chunks? (Strategy needed)
3. **Embedding Dimension**: Verify sentence-transformers output dimensions (typically 384)
4. **Search Result Formatting**: How detailed should excerpts be? (Recommendation: 300 chars)
5. **Knowledge Base Access Control**: Should users be able to create private KBs? (Future feature)
6. **Embedding Model Download**: Should happen on startup or lazily? (Recommendation: startup)

