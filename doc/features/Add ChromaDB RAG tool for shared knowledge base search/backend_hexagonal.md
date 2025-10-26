# Backend Hexagonal Architecture Analysis: ChromaDB RAG Integration

## Request Summary

Add ChromaDB integration to Genesis for Retrieval-Augmented Generation (RAG) capability, enabling the LLM to search and retrieve documents from a shared knowledge base during conversations. This feature will allow users to augment AI responses with relevant external knowledge.

## Relevant Files & Modules

### Core Ports (Interfaces)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - LLM provider interface pattern to follow
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/conversation_repository.py` - Repository port pattern to follow
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/auth_service.py` - Service port pattern to follow

### Adapters (Implementations)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/provider_factory.py` - Factory pattern for creating provider instances (model for vector store factory)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/openai_provider.py` - Provider adapter implementation pattern
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_conversation_repository.py` - Repository adapter pattern

### Infrastructure Layer
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py` - Configuration management using Pydantic Settings (model for vector store configuration)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/mongodb.py` - Database connection initialization (may need updates for vector DB)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/security/dependencies.py` - Dependency injection patterns

### LangGraph Integration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - State definition (may need to extend for retrieval context)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - LLM invocation node (where RAG context is passed to LLM)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Graph definition (where retrieval node will be added)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/web_search.py` - Tool implementation pattern

### Application Entry Point
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py` - Application lifecycle management (lifespan events for vector store initialization)

### Domain Models
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/conversation.py` - Domain model structure (reference for creating document-related models)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/user.py` - User domain model

### Requirements
- `/Users/pablolozano/Mac Projects August/genesis/backend/requirements.txt` - Dependencies (where chromadb and embedding model dependencies will be added)

### Project Documentation
- `/Users/pablolozano/Mac Projects August/genesis/doc/general/ARCHITECTURE.md` - Existing architecture documentation (needs update for RAG extension point)

## Current Architecture Overview

Genesis follows **clean hexagonal architecture** with clear separation between domain core and infrastructure concerns.

```
┌──────────────────────────────────────────────────┐
│       Inbound Adapters (REST, WebSocket)        │
│    app/adapters/inbound/                        │
└──────────────────┬───────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────┐
│              Core Domain (Business Logic)        │
│                                                  │
│  Domain Models → Ports → Use Cases              │
│  (User, Conversation)  (Interfaces) (RegisterUser,│
│                                      AuthenticateUser)
│                                                  │
│  app/core/domain/ ← ports/ ← use_cases/        │
└──────────────────┬───────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────┐
│       Outbound Adapters (Implementations)       │
│                                                  │
│  - Repositories (MongoDB)                       │
│  - LLM Providers (OpenAI, Anthropic, etc.)      │
│  - Auth Service (JWT, bcrypt)                   │
│  - [FUTURE] Vector Store (ChromaDB)             │
│                                                  │
│  app/adapters/outbound/                         │
└──────────────────┬───────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────┐
│      Infrastructure Layer (Cross-cutting)       │
│                                                  │
│  - Configuration (Pydantic Settings)            │
│  - Database Connections (MongoDB, [FUTURE]      │
│    ChromaDB)                                    │
│  - Logging                                      │
│  - Security                                     │
│                                                  │
│  app/infrastructure/                            │
└──────────────────────────────────────────────────┘
```

### Domain Core

**Domain Models** (`app/core/domain/`):
- `User` - User entity with authentication fields
- `Conversation` - Conversation metadata and history tracking
- [FUTURE] `Document` - Knowledge base document entity (if storing document metadata in app DB)

**Ports (Interfaces)** (`app/core/ports/`):
- `IUserRepository` - User CRUD and lookup operations
- `IConversationRepository` - Conversation management
- `ILLMProvider` - LLM generation and streaming
- `IAuthService` - Password hashing and JWT token management
- [NEW] `IVectorStore` - Vector store operations (retrieve, store, delete documents)

**Use Cases** (`app/core/use_cases/`):
- `RegisterUser` - User registration logic
- `AuthenticateUser` - User authentication logic
- `CreateConversation` - Conversation creation logic
- [FUTURE] `SearchKnowledgeBase` - Document retrieval use case (if core business logic needed)

### Ports (Interfaces)

All ports define contracts that infrastructure adapters must implement, ensuring the domain core never depends on external services.

**Existing Ports** (models to follow):
- `ILLMProvider` - Async methods with clear error handling
- `IUserRepository`, `IConversationRepository` - CRUD operations with optional return types
- `IAuthService` - Synchronous and async methods mixed based on needs

**Port Characteristics**:
- Abstract base classes using Python's `abc` module
- Type hints for all parameters and returns
- Docstrings explaining contract semantics
- No implementation details leaked
- Error handling delegated to callers

### Adapters

**Outbound Adapters** (`app/adapters/outbound/`):

**Repository Adapters**:
- `MongoUserRepository` - Implements `IUserRepository` using Beanie ODM
- `MongoConversationRepository` - Implements `IConversationRepository` using Beanie ODM
- [NEW] `ChromaDBVectorStore` - Will implement `IVectorStore`

**LLM Provider Adapters**:
- `OpenAIProvider` - ChatOpenAI from LangChain
- `AnthropicProvider` - Claude models via LangChain
- `GeminiProvider` - Google's Gemini via LangChain
- `OllamaProvider` - Local LLM via Ollama
- [NEW] All providers will use `bind_tools()` to support tool calling

**Service Adapters**:
- `AuthService` - Implements `IAuthService` using bcrypt and python-jose

**Adapter Characteristics**:
- Implement port interfaces
- Translate between domain models and external representations
- Handle external service-specific details
- Use dependency injection for configuration

**Inbound Adapters** (`app/adapters/inbound/`):
- REST API routers (FastAPI)
- WebSocket handlers
- Schema definitions (Pydantic models)
- Translate HTTP/WebSocket requests to domain operations

## Impact Analysis

### Affected Architectural Components

**Core Domain**:
- Minimal changes - Add `IVectorStore` port interface
- Domain logic remains unchanged
- No database-specific code in domain

**Ports**:
- [NEW] Create `IVectorStore` port interface in `app/core/ports/vector_store.py`
  - Methods: `store_documents()`, `retrieve()`, `delete()`, `clear()`
  - Async operations for non-blocking I/O
  - Clear error semantics

**Adapters (Outbound)**:
- [NEW] Create `app/adapters/outbound/vector_stores/` directory
- [NEW] Create `ChromaDBVectorStore` adapter implementing `IVectorStore`
- [NEW] Create `vector_store_factory.py` for dependency injection (similar to `provider_factory.py`)

**Infrastructure**:
- [UPDATE] `app/infrastructure/config/settings.py` - Add ChromaDB configuration
  - ChromaDB connection URL or path
  - Embedding model selection (OpenAI, HuggingFace, Ollama, etc.)
  - Vector store persistence settings
  - Optional: search parameters (similarity threshold, max results)

**LangGraph**:
- [UPDATE] `app/langgraph/state.py` - Add retrieved documents to state context
- [UPDATE] `app/langgraph/nodes/call_llm.py` - Pass retrieved documents to LLM
- [NEW] `app/langgraph/nodes/retrieve_documents.py` - Retrieval node
- [UPDATE] `app/langgraph/graphs/streaming_chat_graph.py` - Add retrieval flow

**Main Application**:
- [UPDATE] `app/main.py` - Initialize ChromaDB connection in lifespan
- [UPDATE] HTTP routers if need document management APIs (optional)

**Configuration**:
- [UPDATE] `requirements.txt` - Add chromadb and embedding dependencies

## Architectural Recommendations

### 1. IVectorStore Port Interface

**Location**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/vector_store.py`

**Pattern**: Follow `ILLMProvider` and `IConversationRepository` conventions

```python
# ABOUTME: Vector store port interface defining the contract for document storage and retrieval
# ABOUTME: Abstract interface following hexagonal architecture principles

from abc import ABC, abstractmethod
from typing import List, Optional

class DocumentMetadata(BaseModel):
    """Metadata about a stored document."""
    id: str
    source: str  # Origin of document (upload, web scrape, etc.)
    created_at: datetime
    content_length: int

class Document(BaseModel):
    """Document entity for knowledge base."""
    id: str
    content: str  # Document text content
    metadata: DocumentMetadata

class RetrievalResult(BaseModel):
    """Result of a document retrieval."""
    document: Document
    similarity_score: float  # 0.0 to 1.0

class IVectorStore(ABC):
    """
    Vector store port interface.

    Defines the contract for document storage, retrieval, and management.
    Implementations handle embedding generation and similarity search
    without the core domain knowing about vector database details.
    """

    @abstractmethod
    async def store_documents(self, documents: List[Document]) -> List[str]:
        """
        Store documents in the vector store.

        Args:
            documents: List of Document objects to store

        Returns:
            List of stored document IDs

        Raises:
            Exception: If document storage fails
        """
        pass

    @abstractmethod
    async def retrieve(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        """
        Retrieve documents similar to the query.

        Args:
            query: Search query string
            top_k: Number of top results to return

        Returns:
            List of RetrievalResult with documents and similarity scores

        Raises:
            Exception: If retrieval fails
        """
        pass

    @abstractmethod
    async def delete(self, document_id: str) -> bool:
        """Delete a document from the store."""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all documents from the store."""
        pass
```

**Rationale**:
- Async interface matches LLM provider pattern
- Minimal surface area - only essential operations
- Domain-agnostic naming (no "ChromaDB" in interface)
- Clear return types and error semantics

### 2. ChromaDBVectorStore Adapter

**Location**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/vector_stores/chroma_vector_store.py`

**Pattern**: Follow `OpenAIProvider` and `MongoUserRepository` conventions

**Key Considerations**:
- Use LangChain's `Chroma` class if available, or chromadb client directly
- Support configurable embedding models
- Handle initialization of persistent collections
- Implement error handling and logging
- Return domain models, not ChromaDB-specific objects

**Embedding Model Options**:
- OpenAI embeddings (if OpenAI API is available)
- HuggingFace embeddings (free, offline)
- Ollama embeddings (for local deployments)
- Configurable via settings

### 3. Vector Store Configuration

**Location**: Update `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py`

**Settings to Add**:
```python
# ChromaDB Settings
chroma_persistence_dir: str = "./chroma_data"  # Path for persistent storage
chroma_collection_name: str = "genesis_documents"
chroma_embedding_model: str = "openai"  # Options: openai, huggingface, ollama

# Embedding Model Settings
openai_embedding_model: str = "text-embedding-3-small"
huggingface_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
ollama_embedding_model: str = "nomic-embed-text"

# Retrieval Settings
retrieval_top_k: int = 5
retrieval_similarity_threshold: float = 0.5  # Optional minimum score
```

**Rationale**:
- Follows existing pattern using Pydantic Settings
- Environment variable support for production
- Sensible defaults for local development
- Configurable embedding models for flexibility

### 4. Dependency Injection Pattern

**Create Vector Store Factory**:

**Location**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/vector_stores/vector_store_factory.py`

**Pattern**: Mirror `provider_factory.py`

```python
# ABOUTME: Vector store factory for creating store instances based on configuration
# ABOUTME: Currently supports ChromaDB, extensible for other vector databases

from app.core.ports.vector_store import IVectorStore
from app.infrastructure.config.settings import settings

class VectorStoreFactory:
    """Factory for creating vector store instances."""

    @staticmethod
    def create_vector_store() -> IVectorStore:
        """Create appropriate vector store based on configuration."""
        # For now, only ChromaDB supported
        from app.adapters.outbound.vector_stores.chroma_vector_store import ChromaDBVectorStore
        return ChromaDBVectorStore()

def get_vector_store() -> IVectorStore:
    """Get the configured vector store instance."""
    return VectorStoreFactory.create_vector_store()
```

**Usage in LangGraph**:
- Pass via `RunnableConfig` like `llm_provider`
- OR store in `app.state` during startup in `main.py` lifespan

### 5. LangGraph Integration

**State Enhancement** (`app/langgraph/state.py`):

```python
from langgraph.graph import MessagesState

class ConversationState(MessagesState):
    """Extended state with retrieval context."""
    conversation_id: str
    user_id: str
    retrieved_documents: Optional[List[RetrievalResult]] = None  # NEW
    retrieval_query: Optional[str] = None  # NEW
```

**Retrieval Node** (`app/langgraph/nodes/retrieve_documents.py`):

```python
# NEW FILE - Handles document retrieval from knowledge base

async def retrieve_documents(state: ConversationState, config: RunnableConfig) -> dict:
    """
    Retrieve relevant documents for the current conversation.

    Extracts a retrieval query from user input or conversation context,
    then uses the vector store to find similar documents.
    """
    messages = state["messages"]
    vector_store = config["configurable"]["vector_store"]

    # Extract query (could be simple - last user message, or complex - LLM-extracted)
    last_message = messages[-1].content if messages else ""

    # Retrieve documents
    results = await vector_store.retrieve(last_message, top_k=settings.retrieval_top_k)

    return {
        "retrieved_documents": results,
        "retrieval_query": last_message
    }
```

**LLM Node Update** (`app/langgraph/nodes/call_llm.py`):

Inject retrieved documents into the LLM prompt:

```python
async def call_llm(state: ConversationState, config: RunnableConfig) -> dict:
    """Call LLM with optional RAG context."""
    messages = state["messages"]
    retrieved_docs = state.get("retrieved_documents")

    # Build context message if documents retrieved
    if retrieved_docs:
        context = "\n\n".join([
            f"Document: {doc.metadata.source}\n{doc.content}"
            for doc in retrieved_docs
        ])
        context_msg = SystemMessage(f"Use the following documents to answer:\n\n{context}")
        messages = [context_msg] + messages

    # Rest of LLM call...
```

**Graph Update** (`app/langgraph/graphs/streaming_chat_graph.py`):

```python
def create_streaming_chat_graph(checkpointer):
    """Include retrieval node in graph."""

    graph_builder = StateGraph(ConversationState)

    # Add nodes
    graph_builder.add_node("retrieve", retrieve_documents)  # NEW
    graph_builder.add_node("call_llm", call_llm)
    graph_builder.add_node("tools", ToolNode(tools))

    # Define edges - retrieve before LLM
    graph_builder.add_edge(START, "retrieve")  # NEW
    graph_builder.add_edge("retrieve", "call_llm")  # NEW
    # ... rest of edges
```

**Rationale**:
- Retrieval node executes before LLM invocation
- Documents stored in state for reference/debugging
- Optional context injection - gracefully handles empty results
- Follows existing LangGraph patterns

### 6. Application Initialization

**Update `main.py` lifespan**:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with vector store initialization."""
    logger.info(f"Starting {settings.app_name}")

    # ... existing database connections ...

    # Initialize vector store
    from app.adapters.outbound.vector_stores.vector_store_factory import get_vector_store
    vector_store = get_vector_store()
    app.state.vector_store = vector_store
    logger.info("Vector store initialized")

    # Compile graphs with vector store in config
    app.state.chat_graph = create_streaming_chat_graph(
        checkpointer,
        vector_store=vector_store  # Pass to graph
    )

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application")
    # ... existing cleanup ...
```

## Dependency Flow Diagram

**Correct Dependency Direction** (Domain-centric):

```
┌─────────────────────────────────────────┐
│   LangGraph (Tool for orchestration)    │
│   - Uses IVectorStore port              │
│   - Retrieves documents before LLM call │
└─────────────────┬───────────────────────┘
                  │ depends on
                  ↓
┌─────────────────────────────────────────┐
│  IVectorStore (Port Interface)          │
│  - Lives in app/core/ports/             │
│  - No implementation details            │
└─────────────────┬───────────────────────┘
                  │ implemented by
                  ↓
┌─────────────────────────────────────────┐
│  ChromaDBVectorStore (Adapter)          │
│  - Lives in app/adapters/outbound/      │
│  - Implements IVectorStore              │
│  - Uses chromadb client directly        │
│  - Handles embedding generation         │
└─────────────────┬───────────────────────┘
                  │ uses
                  ↓
┌─────────────────────────────────────────┐
│  ChromaDB (External Service)            │
│  - Vector database                      │
│  - Persistent collection storage        │
└─────────────────────────────────────────┘
```

**Critical**: Dependencies ALWAYS point inward toward the domain core.
- LangGraph depends on `IVectorStore` (interface), not `ChromaDBVectorStore` (implementation)
- `ChromaDBVectorStore` depends on `chromadb` package, not on domain code
- Domain core (`IVectorStore` port) has ZERO dependencies on infrastructure

## Implementation Guidance

### Phase 1: Port Definition (Foundation)

1. Create `IVectorStore` interface in `app/core/ports/vector_store.py`
2. Define domain models for `Document`, `DocumentMetadata`, `RetrievalResult`
3. Write clear docstrings explaining contract
4. No implementation yet - interface only

### Phase 2: Adapter Implementation (Infrastructure)

1. Create `app/adapters/outbound/vector_stores/` directory
2. Implement `ChromaDBVectorStore` using chromadb library
3. Create `vector_store_factory.py` for dependency injection
4. Handle embedding model configuration and initialization
5. Add error handling and logging

### Phase 3: Configuration (Settings)

1. Update `settings.py` with ChromaDB configuration
2. Support environment variable overrides
3. Add defaults suitable for local development

### Phase 4: LangGraph Integration (Orchestration)

1. Create retrieval node: `retrieve_documents.py`
2. Update `ConversationState` to include retrieved documents
3. Update `call_llm` node to inject document context
4. Update graph definition to include retrieval flow
5. Ensure correct node ordering (retrieve before LLM)

### Phase 5: Application Initialization (Lifecycle)

1. Update `main.py` lifespan to initialize vector store
2. Store vector store in `app.state` for access in graph invocation
3. Add shutdown cleanup if needed
4. Test initialization flow

### Phase 6: API Endpoints (Optional - Secondary Adapters)

If user-facing document management needed:
1. Create `document_router.py` in `app/adapters/inbound/`
2. Implement endpoints for:
   - POST `/api/documents` - Upload/store documents
   - DELETE `/api/documents/{id}` - Delete document
   - GET `/api/documents/search?q=...` - Manual search (optional)
3. Use dependency injection to access vector store

### Phase 7: Testing (Behavior Verification)

1. Unit tests for `IVectorStore` interface implementation
2. Integration tests with actual ChromaDB
3. LangGraph node tests with mock vector store
4. End-to-end tests through WebSocket
5. Test document retrieval in conversation flow

## Risks and Considerations

### Architectural Risks

1. **Embedding Model Lock-in**
   - If using OpenAI embeddings, adds dependency on OpenAI API availability
   - **Mitigation**: Make embedding model configurable; support HuggingFace for offline use

2. **Document Storage Location**
   - ChromaDB can use persistent filesystem or in-memory
   - **Consideration**: Document management API may be needed later
   - **Mitigation**: Design `IVectorStore` to support batching and deletion

3. **Retrieval Context Size**
   - Large documents may inflate token usage
   - **Mitigation**: Implement document chunking and size limits
   - **Consideration**: May need separate chunking service later

4. **Similarity Threshold Tuning**
   - Too high: misses relevant documents
   - Too low: includes irrelevant documents
   - **Mitigation**: Make configurable; monitor in production

### Implementation Considerations

1. **Async/Sync Mismatch**
   - chromadb may not have full async API
   - **Solution**: Use `asyncio.to_thread()` for blocking calls if needed
   - **Alternative**: Run in thread pool executor

2. **Port Completeness**
   - `IVectorStore` should support updates, not just adds
   - **Consider**: `update_document()`, `get_document()` methods
   - **Trade-off**: Simpler interface vs. completeness

3. **Document Schema Flexibility**
   - Different documents may have different metadata
   - **Solution**: Keep metadata flexible (dict-based) in adapter
   - **Domain Model**: Strict typed models for what core knows about

4. **Persistence vs. Performance**
   - Persistent storage on filesystem slower than in-memory
   - **Consideration**: Local dev uses in-memory, production uses persistent
   - **Mitigation**: Configurable via settings

### Deployment Considerations

1. **Vector Store Data Migration**
   - Moving documents between environments
   - **Mitigation**: Document export/import functionality later
   - **For MVP**: Accept as manual process

2. **Knowledge Base Updates**
   - How documents get added to knowledge base
   - **Mitigation**: Defer complex document management to Phase 6
   - **MVP**: Store endpoint for manual uploads

3. **Embedding Model Updates**
   - Changing embedding models invalidates existing vectors
   - **Mitigation**: Version embeddings with model name
   - **Consideration**: Document this clearly

## Testing Strategy

### Unit Tests (Domain-Centric)

**Test Port Interface** (`test_vector_store_port.py`):
- Test interface contracts (all methods present)
- Verify async nature
- Check error types match documentation

**Test Factory** (`test_vector_store_factory.py`):
- Verify correct adapter created based on config
- Ensure singleton pattern if needed

### Integration Tests (Adapter-Focused)

**Test ChromaDBVectorStore** (`test_chroma_vector_store.py`):
```python
# Pseudo-test structure

async def test_store_and_retrieve_documents():
    """Test storing documents and retrieving them."""
    store = ChromaDBVectorStore()

    documents = [
        Document(id="1", content="Python is a programming language", ...),
        Document(id="2", content="Python snakes are reptiles", ...),
    ]

    ids = await store.store_documents(documents)
    assert len(ids) == 2

    # Retrieve similar to "Python programming"
    results = await store.retrieve("Python programming", top_k=1)
    assert results[0].document.id == "1"
    assert results[0].similarity_score > 0.7

async def test_delete_document():
    """Test document deletion."""
    store = ChromaDBVectorStore()
    # ... store documents ...

    success = await store.delete("1")
    assert success is True

    # Verify deletion
    results = await store.retrieve("old content")
    assert len([r for r in results if r.document.id == "1"]) == 0

async def test_clear_all_documents():
    """Test clearing vector store."""
    # ...
```

### LangGraph Node Tests

**Test Retrieval Node** (`test_retrieve_documents_node.py`):
```python
async def test_retrieve_documents_node():
    """Test retrieval node execution."""
    # Create mock vector store
    mock_store = AsyncMock(spec=IVectorStore)
    mock_store.retrieve.return_value = [
        RetrievalResult(document=Document(...), similarity_score=0.9)
    ]

    state = ConversationState(
        messages=[HumanMessage(content="How to learn Python?")],
        conversation_id="conv1",
        user_id="user1"
    )

    config = {"configurable": {"vector_store": mock_store}}

    result = await retrieve_documents(state, config)

    assert len(result["retrieved_documents"]) == 1
    mock_store.retrieve.assert_called_once()
```

### End-to-End Tests

**Test Through Graph** (`test_rag_graph_execution.py`):
```python
async def test_conversation_with_retrieval():
    """Test full conversation flow with RAG."""
    # Real or embedded ChromaDB
    vector_store = ChromaDBVectorStore()

    # Store test documents
    documents = [Document(...), ...]
    await vector_store.store_documents(documents)

    # Create graph with vector store
    graph = create_streaming_chat_graph(checkpointer, vector_store)

    # Execute conversation
    input_state = {
        "messages": [HumanMessage(content="How to use Python?")],
        "conversation_id": "test_conv",
        "user_id": "test_user"
    }

    config = {"configurable": {"thread_id": "test_conv"}}

    # Use graph (mock checkpointer if needed)
    result = await graph.ainvoke(input_state, config)

    # Verify response includes RAG context
    response_message = result["messages"][-1]
    assert "relevant" in response_message.content.lower()
```

### Test Coverage Checklist

- [ ] Port interface follows conventions (abstract, async-first, typed)
- [ ] Adapter implements all port methods
- [ ] Embedding model configuration works
- [ ] Document storage and retrieval works
- [ ] Similarity search returns reasonable results
- [ ] Document deletion works
- [ ] Clear all documents works
- [ ] Retrieval node integrates with graph
- [ ] Documents appear in LLM context
- [ ] Error handling for missing vector store
- [ ] Error handling for invalid documents
- [ ] Concurrent retrieval requests handled safely
- [ ] Configuration overrides work correctly

## Key Architectural Principles to Preserve

### 1. Dependency Inversion
- Domain never imports from adapters
- LangGraph uses `IVectorStore` interface, not `ChromaDBVectorStore`
- Configuration drives adapter selection

### 2. Port Completeness
- Port defines ALL operations needed from vector store
- Adapter handles HOW to do them
- Domain doesn't care about ChromaDB internals

### 3. Error Semantics
- `IVectorStore` exceptions defined clearly
- Adapters convert library-specific errors to port exceptions
- LangGraph doesn't catch ChromaDB-specific exceptions

### 4. Testability
- Mock implementations of `IVectorStore` easy to create
- Graph and nodes testable with fake vector store
- No external service calls in unit tests

### 5. Extensibility
- If need multiple vector stores (Weaviate, Pinecone, etc.), add to factory
- New embedding models: just update configuration
- New retrieval strategies: new node implementation

## Summary of Changes Required

### New Files (8 files)
1. `app/core/ports/vector_store.py` - Port interface
2. `app/adapters/outbound/vector_stores/__init__.py`
3. `app/adapters/outbound/vector_stores/chroma_vector_store.py` - Adapter
4. `app/adapters/outbound/vector_stores/vector_store_factory.py` - Factory
5. `app/langgraph/nodes/retrieve_documents.py` - Retrieval node
6. `app/langgraph/nodes/__init__.py` - Update exports
7. Tests (multiple test files - see testing strategy)

### Updated Files (5 files)
1. `app/infrastructure/config/settings.py` - Add ChromaDB config
2. `app/langgraph/state.py` - Add retrieved_documents field
3. `app/langgraph/nodes/call_llm.py` - Inject document context
4. `app/langgraph/graphs/streaming_chat_graph.py` - Add retrieval node
5. `app/main.py` - Initialize vector store in lifespan
6. `backend/requirements.txt` - Add chromadb, embedding libraries
7. `doc/general/ARCHITECTURE.md` - Document RAG extension point

### No Changes Needed
- Core domain models (User, Conversation)
- Use case implementations
- Existing port interfaces (except new IVectorStore)
- Repository implementations
- LLM provider implementations
- Authentication/security layer

## Assumptions and Questions

### Clarifications Needed

1. **Embedding Model Preference**
   - Use OpenAI embeddings (requires API key)?
   - Use open-source embeddings (HuggingFace, Ollama)?
   - Configurable choice?
   - **Impact**: Affects dependencies and configuration

2. **Knowledge Base Source**
   - Where do documents come from initially?
   - User uploads API endpoint needed?
   - Batch import from files?
   - External source (Wikipedia, documentation)?
   - **Impact**: May need document management router

3. **Shared Knowledge Base Scope**
   - Shared by all users or per-conversation?
   - Can users contribute documents?
   - Who manages documents (admins only)?
   - **Impact**: May need authorization checks in document APIs

4. **Retrieval Strategy**
   - Always retrieve (every message)?
   - On-demand (only certain conversation states)?
   - Query expansion or simple vector search?
   - **Impact**: Affects graph node logic

5. **Production Persistence**
   - Use ChromaDB file persistence or cloud option (Chroma Cloud)?
   - Same MongoDB setup or separate infrastructure?
   - Backup/recovery strategy?
   - **Impact**: Infrastructure and deployment decisions

6. **Performance Requirements**
   - Expected knowledge base size (documents, tokens)?
   - Expected query latency (ms)?
   - Concurrent users?
   - **Impact**: May affect vector store choice or indexing strategy

## Next Steps for Implementation

1. **Clarify assumptions** with Pablo regarding embedding models and knowledge base source
2. **Define port interface** starting with minimal viable operations
3. **Implement ChromaDB adapter** with sensible defaults
4. **Create retrieval node** and integrate into graph
5. **Add configuration** to settings
6. **Write comprehensive tests** covering all layers
7. **Document in ARCHITECTURE.md** how to extend with other vector stores
8. **Consider document management APIs** if user uploads needed

## References to Similar Patterns in Codebase

### Port Interface Pattern
- See `ILLMProvider` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py`
- See `IConversationRepository` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/conversation_repository.py`
- Uses ABC, abstractmethod, clear docstrings

### Adapter Implementation Pattern
- See `OpenAIProvider` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/openai_provider.py`
- See `MongoConversationRepository` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_conversation_repository.py`
- Implements port interface, translates between domain and external types

### Factory Pattern
- See `LLMProviderFactory` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/provider_factory.py`
- Uses settings to select implementation
- Provides factory method and convenience function

### LangGraph Node Pattern
- See `call_llm` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py`
- Async function receiving state and config
- Returns dict with state updates

### Configuration Pattern
- See `Settings` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py`
- Uses Pydantic BaseSettings with model_config
- Loads from .env file with env_file_encoding
- Type hints for all fields
- Sensible defaults

### Initialization Pattern
- See `create_app()` and `lifespan` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py`
- Uses asynccontextmanager for startup/shutdown
- Initializes services and stores in app.state
- Proper logging at each stage

---

**Analysis completed by hexagonal-backend-analyzer**

This document provides a comprehensive roadmap for adding ChromaDB RAG capability while maintaining clean hexagonal architecture. The pattern follows existing conventions in the codebase and ensures the core domain remains independent of vector store implementation details.
