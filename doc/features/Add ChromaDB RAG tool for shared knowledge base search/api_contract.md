# API Contract Analysis: ChromaDB RAG Tool for Shared Knowledge Base Search

## Request Summary

Analyze the existing FastAPI endpoint structure to determine if document ingestion for ChromaDB should be implemented as:
1. A standalone Python script
2. An API endpoint
3. Both approaches (script for batch operations, API for single/multiple uploads)

This analysis reviews authentication patterns, file upload capabilities, admin endpoints, and provides recommendations for the ingestion approach that best aligns with the existing hexagonal architecture.

## Relevant Files & Modules

### Files to Examine

**API Routes & Routers:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py` - FastAPI application entry point, middleware setup, router registration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/auth_router.py` - Authentication endpoints with user registration and login
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/user_router.py` - User profile management endpoints
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/conversation_router.py` - Conversation CRUD endpoints with authorization patterns
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_router.py` - Message retrieval endpoints with pagination

**Security & Authentication:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/security/dependencies.py` - OAuth2 dependency injection, CurrentUser type annotation, JWT validation
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/security/auth_service.py` - JWT token creation, password hashing, user authentication logic

**Domain Models & Schemas:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/user.py` - User domain model, UserCreate, UserUpdate, UserResponse schemas
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/conversation.py` - Conversation domain model, ConversationCreate, ConversationUpdate, ConversationResponse schemas

**Repository Layer (Data Access):**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/user_repository.py` - IUserRepository interface defining user data operations contract
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_user_repository.py` - MongoDB user repository implementation

**LangGraph Integration:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Tool registration and graph compilation with tools=[multiply, add, web_search]
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/web_search.py` - Example tool implementation showing DuckDuckGoSearchResults
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/__init__.py` - Tool module exports

**Configuration & Infrastructure:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py` - Environment variables, app configuration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/mongodb.py` - MongoDB connection management (AppDatabase, LangGraphDatabase)
- `/Users/pablolozano/Mac Projects August/genesis/backend/requirements.txt` - Python dependencies (note: no ChromaDB dependency yet)

**Project Configuration:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/pyproject.toml` - Ruff linter configuration, Pytest settings

### Key Endpoints & Patterns

**Authentication Pattern:**
- `POST /api/auth/register` - User registration (no special privileges required)
- `POST /api/auth/token` - OAuth2 password flow login
- `POST /api/auth/refresh` - Token refresh endpoint

**Protected Endpoint Pattern (All require JWT):**
- `GET /api/user/me` - Requires `CurrentUser` dependency
- `PATCH /api/user/me` - Requires `CurrentUser` dependency
- `GET /api/conversations` - Requires `CurrentUser` dependency
- `POST /api/conversations` - Requires `CurrentUser` dependency
- `PATCH /api/conversations/{id}` - Requires ownership validation + `CurrentUser`

**Tool Integration Pattern:**
- Tools are simple Python functions imported in `streaming_chat_graph.py` line 43
- Tools registered in ToolNode: `graph_builder.add_node("tools", ToolNode(tools))`
- No special tool ingestion infrastructure exists currently

## Current API Contract Overview

### Existing Architecture Assessment

The Genesis application follows **hexagonal architecture** with clear separation:

```
Inbound Adapters (REST API, WebSocket)
    ↓
Core Domain (Use Cases, Domain Models, Ports)
    ↓
Outbound Adapters (MongoDB, LLM Providers)
```

**Key Characteristics:**
- All REST endpoints use FastAPI with Pydantic for validation
- Authentication via JWT tokens with `CurrentUser` dependency injection
- No admin-specific endpoints or role-based authorization currently exists
- File upload capabilities: None detected (no multipart/form-data handlers)
- Message storage uses LangGraph checkpoints (not traditional API endpoints)

### Endpoints & Routes

#### User Management (Pattern for Protected Resources)
1. **POST /api/auth/register** (Line 29-72 in auth_router.py)
   - No authentication required
   - Validates unique email/username
   - Returns UserResponse (201 Created)
   - Error handling: 400, 422, 500

2. **POST /api/auth/token** (Line 75-120 in auth_router.py)
   - OAuth2 password form data required
   - Returns TokenResponse with access_token
   - Error handling: 401, 500

3. **GET /api/user/me** (Line 17-31 in user_router.py)
   - Requires `CurrentUser` dependency (JWT validation)
   - Returns UserResponse
   - Error handling: 401 (handled by dependency)

4. **PATCH /api/user/me** (Line 34-85 in user_router.py)
   - Requires `CurrentUser` dependency
   - Validates email/username uniqueness
   - Returns updated UserResponse
   - Error handling: 400, 401, 500

#### Conversation Management (Pattern with Ownership Validation)
1. **GET /api/conversations** (Line 19-48 in conversation_router.py)
   - Requires `CurrentUser` dependency
   - Supports pagination: skip, limit (max 100)
   - Returns List[ConversationResponse]

2. **POST /api/conversations** (Line 51-75 in conversation_router.py)
   - Requires `CurrentUser` dependency
   - Body: ConversationCreate (optional title)
   - Returns ConversationResponse (201 Created)

3. **GET /api/conversations/{conversation_id}** (Line 78-113 in conversation_router.py)
   - Requires `CurrentUser` dependency
   - Ownership check: `conversation.user_id != current_user.id` → 403 Forbidden
   - Returns ConversationResponse or 404 Not Found

4. **PATCH /api/conversations/{conversation_id}** (Line 116-156 in conversation_router.py)
   - Requires `CurrentUser` dependency
   - Ownership check enforced
   - Body: ConversationUpdate (optional title)
   - Returns updated ConversationResponse

5. **DELETE /api/conversations/{conversation_id}** (Line 159-189 in conversation_router.py)
   - Requires `CurrentUser` dependency
   - Ownership check enforced
   - Returns 204 No Content

#### Message Retrieval (Pattern with Authorization)
1. **GET /api/conversations/{conversation_id}/messages** (Line 21-103 in message_router.py)
   - Requires `CurrentUser` dependency
   - Ownership check enforced (403 Forbidden if access denied)
   - Pagination: skip (default 0), limit (default 100, max 500)
   - Returns List[MessageResponse]

#### Health Check (Public Endpoint)
1. **GET /api/health** (Line 97-104 in main.py)
   - No authentication required
   - Returns status, app name, version (200 OK)

### Request Schemas

#### User-Related (Pydantic BaseModel in domain/user.py)
```python
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime
```

#### Conversation-Related (Pydantic BaseModel in domain/conversation.py)
```python
class ConversationCreate(BaseModel):
    title: Optional[str] = Field(default="New Conversation", max_length=200)

class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)

class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = None
```

### Response Schemas

All endpoints return standard HTTP responses with Pydantic model serialization (application/json).

**Success Responses:**
- 200 OK - Standard successful operation
- 201 Created - Resource created (POST endpoints)
- 204 No Content - Success with no body (DELETE endpoints)

**Error Responses:**
- 400 Bad Request - Invalid input data
- 401 Unauthorized - Missing or invalid JWT token
- 403 Forbidden - Access denied (owned by different user)
- 404 Not Found - Resource doesn't exist
- 422 Unprocessable Entity - Validation error (Pydantic)
- 500 Internal Server Error - Server error

All error responses use FastAPI default format:
```json
{
  "detail": "Error message description"
}
```

### Validation Rules

**Authentication & Authorization:**
1. JWT tokens verified via `oauth2_scheme` (OAuth2PasswordBearer at `/api/auth/token`)
2. `get_current_user()` dependency decodes token and retrieves user
3. `get_current_active_user()` wraps above and verifies user.is_active
4. `CurrentUser` type annotation (line 79 in dependencies.py) = Annotated[User, Depends(get_current_active_user)]

**Field Validation (Pydantic):**
1. Email validation: EmailStr type (via email-validator library)
2. Username: string type, unique check at repository layer
3. Password: string type, hashed via bcrypt at registration
4. Conversation title: string, max_length=200, optional
5. Message content: min_length=1 (enforced in message_router.py line 117)

**Authorization Patterns:**
1. Resource ownership check: `if resource.user_id != current_user.id → 403 Forbidden`
2. Non-existent resources: 404 Not Found
3. No role-based access control (RBAC) or admin privileges detected

## Impact Analysis

### Current State: No Document Ingestion Infrastructure

**What Exists:**
- JWT-based authentication system (tokens, user management)
- Protected endpoints with `CurrentUser` dependency
- Repository pattern for data persistence
- Tool integration in LangGraph (simple Python functions)

**What's Missing:**
- No file upload handlers (no multipart/form-data support)
- No document storage infrastructure (ChromaDB not in requirements.txt)
- No admin-specific endpoints or role-based access control
- No batch processing infrastructure (Celery, background tasks, etc.)
- No credentials/API key management for shared access
- No document metadata schema

### Document Ingestion Design Decisions

The ingestion approach affects:

1. **User Authorization Model**
   - Who can ingest documents? All users? Only admins? Only document owners?
   - Are documents shared across all users or per-user?
   - Does RAG tool access user-specific or shared documents?

2. **Architecture Layer**
   - Inbound adapter: Would need new router + HTTP/multipart handlers
   - Core domain: Would need document/knowledge base domain models
   - Outbound adapter: Would need ChromaDB repository implementation

3. **Deployment Model**
   - Script: Manual/automated via deployment pipeline
   - Endpoint: Dynamic, requires API contract + testing
   - Both: More operational complexity (sync ingestion methods)

## API Contract Recommendations

### Recommended Approach: Hybrid (Script + Endpoint)

**Rationale:**

1. **Script for Initial/Bulk Ingestion**
   - Batch import of documents during setup or maintenance windows
   - No real-time latency constraints
   - Easier to run with elevated privileges if needed
   - Can handle large files that might timeout via HTTP

2. **API Endpoint for Dynamic/Single-Document Uploads**
   - Users can add knowledge to RAG tool without deployment
   - Follows existing REST pattern in the application
   - Supports real-time ingestion workflow
   - Integrates with existing authentication system

### Phase 1: Standalone Script (Recommended First Step)

**Why Start with Script:**
- Zero changes to API contract
- Can be developed and tested independently
- Simpler initial implementation
- Can validate ChromaDB integration before building HTTP layer

**Script Implementation:**
- Location: `/Users/pablolozano/Mac Projects August/genesis/backend/scripts/ingest_documents.py`
- Signature: `async def ingest_documents(file_paths: List[str], collection_name: str = "shared_knowledge")`
- Handles document loading, chunking, embedding, ChromaDB insertion
- Can be called from CLI: `python -m backend.scripts.ingest_documents --files docs/*.pdf --collection shared`

**Script Responsibilities:**
```
CLI Arguments (file paths, collection name, embedding model)
    ↓
Document Loader (PDF, TXT, Markdown support)
    ↓
Text Chunking (semantic boundaries, overlap)
    ↓
Embedding Generation (OpenAI, HuggingFace, Ollama)
    ↓
ChromaDB Collection Creation/Update
    ↓
Logging & Status Reporting
```

**Example Directory Structure:**
```
backend/
├── scripts/
│   ├── __init__.py
│   └── ingest_documents.py  # Main ingestion logic
├── app/
│   ├── infrastructure/
│   │   ├── chromadb/
│   │   │   ├── __init__.py
│   │   │   └── client.py  # ChromaDB client initialization
│   │   └── embeddings/
│   │       ├── __init__.py
│   │       └── provider.py  # Embedding model abstraction
│   └── ...
└── data/
    └── chromadb/  # ChromaDB persistent storage
```

### Phase 2: API Endpoint (After Validating ChromaDB Integration)

**Proposed Endpoint: POST /api/knowledge-base/documents**

**Authentication & Authorization:**
- Requires `CurrentUser` dependency (authenticated user)
- Validation: Only admin users can ingest (future RBAC)
- For MVP: Allow all authenticated users (can restrict later)

**Request Schema (Pydantic):**
```python
# Location: /Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/knowledge_base_schemas.py

from pydantic import BaseModel, Field
from typing import Optional

class DocumentIngestRequest(BaseModel):
    """Request schema for document ingestion."""

    file_name: str = Field(..., max_length=255, description="Original filename")
    content: str = Field(..., description="Document text content")
    collection_name: Optional[str] = Field(
        default="shared_knowledge",
        max_length=100,
        description="ChromaDB collection name"
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Optional metadata (source, tags, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "file_name": "python_guide.pdf",
                "content": "Python is a high-level programming language...",
                "collection_name": "technical_docs",
                "metadata": {
                    "source": "official_docs",
                    "language": "en",
                    "category": "programming"
                }
            }
        }


class DocumentIngestResponse(BaseModel):
    """Response schema for document ingestion."""

    id: str = Field(..., description="Document ID in ChromaDB")
    file_name: str
    collection_name: str
    ingested_at: datetime
    tokens_used: int = Field(..., description="Tokens used for embedding")
    status: str = Field(default="success", description="success or error")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "doc_12345_abc",
                "file_name": "python_guide.pdf",
                "collection_name": "shared_knowledge",
                "ingested_at": "2025-01-15T10:30:00Z",
                "tokens_used": 1500,
                "status": "success"
            }
        }
```

**Endpoint Implementation:**
```python
# Location: /Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/knowledge_base_router.py

from fastapi import APIRouter, HTTPException, status
from typing import List
from app.infrastructure.security.dependencies import CurrentUser
from app.adapters.inbound.knowledge_base_schemas import DocumentIngestRequest, DocumentIngestResponse

router = APIRouter(prefix="/api/knowledge-base", tags=["knowledge-base"])


@router.post("/documents", response_model=DocumentIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_document(
    request: DocumentIngestRequest,
    current_user: CurrentUser
):
    """
    Ingest a document into the shared knowledge base.

    The document is processed, embedded, and stored in ChromaDB for RAG retrieval.

    Args:
        request: Document content and metadata
        current_user: Authenticated user (authorization)

    Returns:
        DocumentIngestResponse with ingestion status and document ID

    Raises:
        HTTPException: If ingestion fails or user lacks permissions
    """
    try:
        # Future: Add admin check if RBAC implemented
        # if not current_user.is_admin:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Only administrators can ingest documents"
        #     )

        # Call use case
        from app.core.use_cases.ingest_document import IngestDocument
        from app.adapters.outbound.chromadb_repository import ChromaDBRepository

        chromadb_repo = ChromaDBRepository()
        ingest_use_case = IngestDocument(chromadb_repo)

        result = await ingest_use_case.execute(
            file_name=request.file_name,
            content=request.content,
            collection_name=request.collection_name,
            metadata=request.metadata or {}
        )

        return DocumentIngestResponse(
            id=result["document_id"],
            file_name=request.file_name,
            collection_name=request.collection_name,
            ingested_at=result["timestamp"],
            tokens_used=result["tokens"],
            status="success"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Document ingestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document ingestion failed"
        )
```

**Add to main.py Router Registration:**
```python
# In /Users/pablolozano/Mac Projects August/genesis/backend/app/main.py

from app.adapters.inbound.knowledge_base_router import router as knowledge_base_router

# In create_app():
app.include_router(knowledge_base_router)
```

**Alternative Endpoints (Future Expansion):**

```python
# GET /api/knowledge-base/collections
# - List all available ChromaDB collections
# - Returns: List[CollectionResponse]
# - Authentication: Required (CurrentUser)

# POST /api/knowledge-base/collections
# - Create new ChromaDB collection
# - Body: CreateCollectionRequest
# - Authentication: Required + Admin (future)

# DELETE /api/knowledge-base/documents/{document_id}
# - Remove document from knowledge base
# - Authentication: Required + Admin

# GET /api/knowledge-base/search
# - Search knowledge base (used by RAG tool, not frontend)
# - Query params: q (query), collection (name)
# - Returns: List[SearchResult]
```

### Domain Model Changes

**Create Knowledge Base Domain Model:**
```python
# Location: /Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/document.py

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class Document(BaseModel):
    """
    Document domain model representing ingested knowledge base entry.

    This is database-agnostic and focuses on document metadata and content.
    """

    id: Optional[str] = Field(default=None, description="ChromaDB document ID")
    file_name: str = Field(..., max_length=255, description="Original file name")
    collection_name: str = Field(default="shared_knowledge", max_length=100)
    content: str = Field(..., description="Full document text")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    tokens_used: int = Field(ge=0, description="Embedding tokens consumed")


class DocumentChunk(BaseModel):
    """Individual chunk of a document after semantic splitting."""

    id: str
    document_id: str
    collection_name: str
    text: str = Field(..., description="Chunk text")
    embedding: Optional[list] = Field(default=None, description="Vector embedding")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    chunk_index: int = Field(ge=0, description="Position in document chunks")


class DocumentSearchResult(BaseModel):
    """Result from RAG knowledge base search."""

    chunk_id: str
    document_id: str
    file_name: str
    text: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    metadata: Dict[str, Any]
```

### Repository/Port Pattern

**Create Port Interface:**
```python
# Location: /Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/knowledge_base_repository.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.core.domain.document import Document, DocumentChunk, DocumentSearchResult


class IKnowledgeBaseRepository(ABC):
    """
    Port interface for knowledge base operations.

    Implementations: ChromaDB, Pinecone, Weaviate, etc.
    """

    @abstractmethod
    async def ingest_document(
        self,
        file_name: str,
        content: str,
        collection_name: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ingest document and return ingestion metadata."""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5
    ) -> List[DocumentSearchResult]:
        """Search knowledge base and return relevant chunks."""
        pass

    @abstractmethod
    async def delete_document(
        self,
        document_id: str,
        collection_name: str
    ) -> bool:
        """Delete document from knowledge base."""
        pass
```

**Create Outbound Adapter (ChromaDB Implementation):**
```python
# Location: /Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/chromadb_repository.py

from app.core.ports.knowledge_base_repository import IKnowledgeBaseRepository
from typing import Dict, Any, List, Optional
import chromadb
from chromadb.config import Settings
import logging

logger = logging.getLogger(__name__)


class ChromaDBRepository(IKnowledgeBaseRepository):
    """
    ChromaDB implementation of knowledge base repository.

    Handles document ingestion, searching, and deletion using ChromaDB.
    """

    def __init__(self):
        """Initialize ChromaDB client."""
        self.client = chromadb.HttpClient(host="localhost", port=8000)
        # Or for persistent local storage:
        # self.client = chromadb.PersistentClient(
        #     path="/app/data/chromadb"
        # )

    async def ingest_document(
        self,
        file_name: str,
        content: str,
        collection_name: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ingest document into ChromaDB collection."""
        try:
            # Get or create collection
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )

            # Generate document ID
            import hashlib
            doc_id = hashlib.md5(f"{file_name}{content}".encode()).hexdigest()

            # Add to collection
            collection.add(
                documents=[content],
                metadatas=[{**metadata, "file_name": file_name}],
                ids=[doc_id]
            )

            logger.info(f"Ingested document {doc_id} to collection {collection_name}")

            return {
                "document_id": doc_id,
                "tokens": len(content.split()),  # Approximate token count
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Document ingestion failed: {e}")
            raise ValueError(f"Failed to ingest document: {str(e)}")

    async def search(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5
    ) -> List[DocumentSearchResult]:
        """Search knowledge base."""
        try:
            collection = self.client.get_collection(name=collection_name)

            results = collection.query(
                query_texts=[query],
                n_results=top_k
            )

            # Transform to DocumentSearchResult objects
            search_results = []
            for i, doc_id in enumerate(results["ids"][0]):
                search_results.append(
                    DocumentSearchResult(
                        chunk_id=doc_id,
                        document_id=doc_id,
                        file_name=results["metadatas"][0][i].get("file_name", "unknown"),
                        text=results["documents"][0][i],
                        relevance_score=1.0 - (results["distances"][0][i] / 2.0),
                        metadata=results["metadatas"][0][i]
                    )
                )

            return search_results

        except Exception as e:
            logger.error(f"Knowledge base search failed: {e}")
            raise ValueError(f"Search failed: {str(e)}")
```

### RAG Tool Integration

**Create RAG Tool Function:**
```python
# Location: /Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/rag_search.py

from app.adapters.outbound.chromadb_repository import ChromaDBRepository
from typing import Optional


async def rag_search(
    query: str,
    collection_name: str = "shared_knowledge",
    top_k: int = 5
) -> str:
    """
    Search the shared knowledge base using RAG.

    Args:
        query: Search query string
        collection_name: ChromaDB collection to search
        top_k: Number of results to return

    Returns:
        Formatted search results as string for LLM context
    """
    try:
        repository = ChromaDBRepository()
        results = await repository.search(
            query=query,
            collection_name=collection_name,
            top_k=top_k
        )

        if not results:
            return "No relevant documents found in knowledge base."

        # Format results for LLM
        formatted = "Knowledge Base Search Results:\n\n"
        for i, result in enumerate(results, 1):
            formatted += f"{i}. [{result.file_name}] (Score: {result.relevance_score:.2f})\n"
            formatted += f"   {result.text[:200]}...\n\n"

        return formatted

    except Exception as e:
        return f"Error searching knowledge base: {str(e)}"
```

**Register in Streaming Graph:**
```python
# Location: /Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py

from app.langgraph.tools.rag_search import rag_search

# In create_streaming_chat_graph():
tools = [multiply, add, web_search, rag_search]
graph_builder.add_node("tools", ToolNode(tools))
```

**Update Tool Exports:**
```python
# Location: /Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/__init__.py

from .multiply import multiply
from .add import add
from .web_search import web_search
from .rag_search import rag_search

__all__ = ["multiply", "add", "web_search", "rag_search"]
```

### Use Case Layer

**Create Ingest Document Use Case:**
```python
# Location: /Users/pablolozano/Mac Projects August/genesis/backend/app/core/use_cases/ingest_document.py

from app.core.ports.knowledge_base_repository import IKnowledgeBaseRepository
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class IngestDocument:
    """
    Use case for ingesting documents into the shared knowledge base.

    Handles document validation, chunking, and repository interaction.
    """

    def __init__(self, knowledge_base_repository: IKnowledgeBaseRepository):
        self.knowledge_base_repository = knowledge_base_repository

    async def execute(
        self,
        file_name: str,
        content: str,
        collection_name: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute document ingestion.

        Args:
            file_name: Original document file name
            content: Document text content
            collection_name: ChromaDB collection name
            metadata: Document metadata

        Returns:
            Ingestion result with document ID and statistics

        Raises:
            ValueError: If document validation fails
        """
        # Validate inputs
        if not file_name or not file_name.strip():
            raise ValueError("File name cannot be empty")

        if not content or not content.strip():
            raise ValueError("Document content cannot be empty")

        if len(content) > 1_000_000:  # 1MB limit
            raise ValueError("Document too large (max 1MB)")

        # Ingest via repository
        logger.info(f"Ingesting document {file_name} into {collection_name}")

        result = await self.knowledge_base_repository.ingest_document(
            file_name=file_name,
            content=content,
            collection_name=collection_name,
            metadata=metadata
        )

        logger.info(f"Document ingestion complete: {result}")

        return result
```

### Configuration Changes

**Add ChromaDB Settings:**
```python
# Location: /Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... existing settings ...

    # ChromaDB Configuration
    CHROMADB_HOST: str = "localhost"
    CHROMADB_PORT: int = 8000
    CHROMADB_PERSIST_PATH: str = "/app/data/chromadb"
    CHROMADB_USE_HTTP: bool = False  # Set to False for persistent local storage

    class Config:
        env_file = ".env"
        case_sensitive = True
```

**Update .env:**
```bash
# ChromaDB Configuration
CHROMADB_HOST=localhost
CHROMADB_PORT=8000
CHROMADB_PERSIST_PATH=./data/chromadb
CHROMADB_USE_HTTP=false
```

**Update requirements.txt:**
```
# Add to existing requirements.txt
chromadb>=0.4.0
```

## Implementation Guidance

### Step-by-Step Approach: Phase 1 (Script Only)

**1. Setup ChromaDB Infrastructure (1-2 hours)**
- Add ChromaDB to requirements.txt
- Create `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/chromadb/client.py` for client initialization
- Create `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/embeddings/provider.py` for embedding abstraction
- Add ChromaDB settings to `settings.py`

**2. Create Document Domain Model (1 hour)**
- Implement `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/document.py`
- Include Document, DocumentChunk, DocumentSearchResult Pydantic models

**3. Create Repository Port & Implementation (2-3 hours)**
- Create port: `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/knowledge_base_repository.py`
- Implement: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/chromadb_repository.py`
- Test ChromaDB CRUD operations

**4. Create Ingestion Script (2-3 hours)**
- Create: `/Users/pablolozano/Mac Projects August/genesis/backend/scripts/ingest_documents.py`
- Implement document loading, chunking, embedding
- Add CLI argument parsing (argparse or Click)
- Test with sample documents

**5. Integrate RAG Tool (1-2 hours)**
- Create `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/rag_search.py`
- Register in `streaming_chat_graph.py`
- Test tool invocation in LangGraph

**6. Testing (3-4 hours)**
- Unit tests for document domain models
- Integration tests for ChromaDB repository
- Test ingestion script end-to-end
- Test RAG tool in chat graph

**Total Phase 1 Effort: 10-15 hours**

### Step-by-Step Approach: Phase 2 (API Endpoint)

**1. Create API Schemas (1 hour)**
- Create `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/knowledge_base_schemas.py`
- DocumentIngestRequest, DocumentIngestResponse

**2. Create Use Case (1-2 hours)**
- Create `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/use_cases/ingest_document.py`
- Implement validation and repository orchestration

**3. Create API Router (2-3 hours)**
- Create `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/knowledge_base_router.py`
- Implement POST /api/knowledge-base/documents endpoint
- Add authentication, error handling, logging

**4. Integration with FastAPI (1 hour)**
- Register router in `main.py`
- Test endpoint with actual HTTP requests

**5. Testing (2-3 hours)**
- Unit tests for use case
- Integration tests for endpoint
- Test authorization (CurrentUser dependency)
- Test error scenarios

**6. Documentation (1 hour)**
- Update API.md in doc/general/
- Add endpoint to API reference

**Total Phase 2 Effort: 8-11 hours**

## Risks and Considerations

### API Contract Risks

**1. No Admin/RBAC System Currently**
- Application has no user roles or admin privileges
- Recommendation: For MVP, allow all authenticated users to ingest (same as creating conversations)
- Future: Implement admin check when RBAC is added
- Risk: Wrong users could pollute shared knowledge base

**2. No Multi-Tenancy Controls**
- Knowledge base is shared across all users
- Different conversations use same RAG collection
- Recommendation: Start with single "shared_knowledge" collection
- Risk: One malicious user can poison the entire knowledge base

**3. File Upload Security**
- No file upload handlers currently exist
- Endpoint accepts raw text content (safer than file uploads)
- Risk: Very large documents could cause DoS if no size limits enforced
- Recommendation: Enforce 1MB size limit as shown in use case

**4. API Versioning**
- No API versioning currently implemented
- Adding new endpoints doesn't break backward compatibility
- Recommendation: Document endpoint in current version
- If breaking changes needed later, plan versioning strategy

### Data Consistency Risks

**1. ChromaDB State Drift**
- ChromaDB collection state not synchronized with MongoDB (App Database)
- If document metadata needed later, no canonical source
- Recommendation: Consider adding document registry in MongoDB
- Risk: Can't query which documents exist, audit trail, or implement soft deletes

**2. Embedding Model Changes**
- Changing embedding model invalidates existing vectors
- Recommendation: Document embedding model version in collection metadata
- Risk: If embedding model updated, need re-ingestion of all documents

**3. Stale Context in Conversations**
- New documents ingested during conversation don't affect earlier messages
- Recommendation: Document this limitation for users
- Risk: Users may expect RAG to always have latest knowledge

### Implementation Risks

**1. ChromaDB Dependency**
- Adding third-party vector database increases operational complexity
- Recommendation: Start with local persistent storage before adding HTTP server
- Risk: Production deployment complexity increases

**2. Embedding API Costs**
- If using paid embedding API (OpenAI, Cohere), ingestion costs money
- Each document ingestion makes API calls
- Recommendation: Use free embeddings (HuggingFace, Ollama) for MVP
- Risk: Scaling to many documents becomes expensive

**3. Token Counting**
- Token usage tracking not implemented
- Tokens needed for cost estimation and rate limiting
- Recommendation: Track approximate tokens (word count / 1.3)
- Risk: Not accurate for billing or auditing

**4. RAG Quality**
- Quality of RAG results depends entirely on documents and embedding quality
- No relevance feedback or human-in-the-loop evaluation
- Recommendation: Start with simple implementation, iterate based on user feedback
- Risk: RAG tool might not improve conversation quality initially

### Security Considerations

**1. Document Content Access**
- Authenticated users can access RAG results (via assistant)
- Not enforced per-document
- Recommendation: Use "shared_knowledge" as single collection initially
- Risk: Users see all knowledge even if document was meant to be restricted

**2. Input Validation**
- Document content passed to ChromaDB should be sanitized
- Recommendation: Escape special characters, validate encoding
- Risk: Malformed documents could crash embedding service

**3. API Authentication**
- Endpoint requires `CurrentUser` dependency (JWT validation)
- No additional authorization checks
- Recommendation: For MVP, this is sufficient
- Future: Add admin/role check when RBAC implemented

## Testing Strategy

### Unit Tests

**File: backend/tests/unit/test_document_domain.py** (new file)

```python
import pytest
from app.core.domain.document import Document, DocumentChunk, DocumentSearchResult


def test_document_creation():
    """Test creating document domain object."""
    doc = Document(
        file_name="test.pdf",
        content="Test content",
        collection_name="test_collection"
    )
    assert doc.file_name == "test.pdf"
    assert doc.tokens_used >= 0


def test_document_chunk_validation():
    """Test document chunk validation."""
    chunk = DocumentChunk(
        id="chunk_1",
        document_id="doc_1",
        collection_name="test",
        text="Chunk text",
        chunk_index=0
    )
    assert chunk.chunk_index >= 0


def test_search_result_score_validation():
    """Test search result relevance score bounds."""
    result = DocumentSearchResult(
        chunk_id="chunk_1",
        document_id="doc_1",
        file_name="test.pdf",
        text="Result text",
        relevance_score=0.95
    )
    assert 0.0 <= result.relevance_score <= 1.0
```

**File: backend/tests/unit/test_ingest_use_case.py** (new file)

```python
import pytest
from app.core.use_cases.ingest_document import IngestDocument
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_ingest_document_validates_content():
    """Test that IngestDocument validates empty content."""
    mock_repo = AsyncMock()
    use_case = IngestDocument(mock_repo)

    with pytest.raises(ValueError, match="content cannot be empty"):
        await use_case.execute(
            file_name="test.pdf",
            content="",  # Invalid: empty
            collection_name="test",
            metadata={}
        )


@pytest.mark.asyncio
async def test_ingest_document_enforces_size_limit():
    """Test that IngestDocument rejects oversized documents."""
    mock_repo = AsyncMock()
    use_case = IngestDocument(mock_repo)

    large_content = "x" * 1_001_000  # Over 1MB limit

    with pytest.raises(ValueError, match="too large"):
        await use_case.execute(
            file_name="huge.txt",
            content=large_content,
            collection_name="test",
            metadata={}
        )


@pytest.mark.asyncio
async def test_ingest_document_success():
    """Test successful document ingestion."""
    mock_repo = AsyncMock()
    mock_repo.ingest_document.return_value = {
        "document_id": "doc_123",
        "tokens": 100,
        "timestamp": "2025-01-15T10:30:00Z"
    }

    use_case = IngestDocument(mock_repo)

    result = await use_case.execute(
        file_name="test.pdf",
        content="Valid document content",
        collection_name="test",
        metadata={"source": "test"}
    )

    assert result["document_id"] == "doc_123"
    assert result["tokens"] == 100
    mock_repo.ingest_document.assert_called_once()
```

### Integration Tests

**File: backend/tests/integration/test_chromadb_repository.py** (new file)

```python
import pytest
from app.adapters.outbound.chromadb_repository import ChromaDBRepository


@pytest.fixture
async def chromadb_repo():
    """Fixture providing ChromaDB repository with test collection."""
    repo = ChromaDBRepository()
    yield repo
    # Cleanup: delete test collection


@pytest.mark.asyncio
async def test_ingest_and_search_document(chromadb_repo):
    """Test ingesting and searching for document."""
    # Ingest
    result = await chromadb_repo.ingest_document(
        file_name="python_basics.pdf",
        content="Python is a high-level programming language.",
        collection_name="test_docs",
        metadata={"source": "test"}
    )

    assert "document_id" in result
    assert result["tokens"] > 0

    # Search
    search_results = await chromadb_repo.search(
        query="What is Python?",
        collection_name="test_docs",
        top_k=5
    )

    assert len(search_results) > 0
    assert search_results[0].relevance_score > 0


@pytest.mark.asyncio
async def test_delete_document(chromadb_repo):
    """Test deleting document from knowledge base."""
    # Ingest
    result = await chromadb_repo.ingest_document(
        file_name="test.pdf",
        content="Test content",
        collection_name="test_docs",
        metadata={}
    )

    doc_id = result["document_id"]

    # Delete
    deleted = await chromadb_repo.delete_document(
        document_id=doc_id,
        collection_name="test_docs"
    )

    assert deleted is True
```

**File: backend/tests/integration/test_knowledge_base_api.py** (new file, for Phase 2)

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_post_knowledge_base_document_requires_auth(client: AsyncClient):
    """Test that document ingestion requires authentication."""
    response = await client.post(
        "/api/knowledge-base/documents",
        json={
            "file_name": "test.pdf",
            "content": "Test content"
        }
        # No Authorization header
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_post_knowledge_base_document_success(client: AsyncClient):
    """Test successful document ingestion."""
    headers = await create_user_and_login(client)

    response = await client.post(
        "/api/knowledge-base/documents",
        json={
            "file_name": "python_guide.pdf",
            "content": "Python is a programming language.",
            "collection_name": "shared_knowledge",
            "metadata": {"source": "official_docs"}
        },
        headers=headers
    )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["file_name"] == "python_guide.pdf"
    assert data["status"] == "success"


@pytest.mark.asyncio
async def test_post_knowledge_base_document_validation(client: AsyncClient):
    """Test document validation."""
    headers = await create_user_and_login(client)

    # Missing required field
    response = await client.post(
        "/api/knowledge-base/documents",
        json={
            "file_name": "test.pdf"
            # Missing "content"
        },
        headers=headers
    )

    assert response.status_code == 422  # Validation error
```

### End-to-End Tests

**File: backend/tests/e2e/test_rag_in_conversation.py** (new file)

```python
import pytest


@pytest.mark.asyncio
async def test_rag_tool_used_in_conversation(websocket_client, authenticated_user):
    """Test that RAG tool is invoked and results provided to LLM."""

    # Setup: Ingest a document
    response = await authenticated_user.client.post(
        "/api/knowledge-base/documents",
        json={
            "file_name": "python_tips.pdf",
            "content": "Python list comprehensions are efficient: [x for x in range(10)]"
        },
        headers=authenticated_user.headers
    )
    assert response.status_code == 201

    # Create conversation
    conv_response = await authenticated_user.client.post(
        "/api/conversations",
        headers=authenticated_user.headers
    )
    conversation_id = conv_response.json()["id"]

    # Send message that should trigger RAG
    await websocket_client.connect(
        f"/ws/chat?token={authenticated_user.token}"
    )

    await websocket_client.send_json({
        "type": "message",
        "conversation_id": conversation_id,
        "content": "How do I use list comprehensions in Python?"
    })

    # Collect response
    response_content = ""
    while True:
        msg = await websocket_client.receive_json()

        if msg["type"] == "token":
            response_content += msg["content"]
        elif msg["type"] == "complete":
            break

    # Verify LLM had context from RAG
    # Note: This is a heuristic check; actual verification depends on LLM output
    assert len(response_content) > 0

    await websocket_client.disconnect()
```

## Summary

### Key Recommendations

1. **Start with Phase 1 (Script Only)**
   - Zero API changes
   - Validate ChromaDB integration
   - Can be deployed independently
   - Estimated effort: 10-15 hours

2. **Phase 2 (API Endpoint) When Ready**
   - Adds dynamic ingestion capability
   - Follows existing REST patterns
   - User-friendly interface
   - Estimated effort: 8-11 hours

3. **Use Hybrid Approach Long-Term**
   - Script for bulk/batch operations
   - API for single-document uploads
   - Both share same domain models and repositories

### Implementation Order

1. **Week 1: Core Infrastructure**
   - ChromaDB setup and configuration
   - Document domain models
   - Repository implementation
   - Basic testing

2. **Week 2: Script Integration**
   - Ingestion script with CLI
   - RAG tool function
   - LangGraph registration
   - End-to-end testing

3. **Week 3: API Endpoint (Optional)**
   - API schemas and router
   - Use case for ingestion
   - Authentication integration
   - Comprehensive testing

### Architecture Decisions

**All Changes Follow Hexagonal Pattern:**
- ✓ Domain layer: Document model, IKnowledgeBaseRepository port
- ✓ Outbound adapter: ChromaDBRepository implementation
- ✓ Inbound adapter: knowledge_base_router (Phase 2 only)
- ✓ Use cases: IngestDocument orchestration
- ✓ Tools: rag_search function in LangGraph
- ✓ Infrastructure: ChromaDB client, embeddings provider

**No Changes to Existing Contracts:**
- ✓ Authentication remains JWT-based with CurrentUser dependency
- ✓ Conversation API unchanged
- ✓ Message storage remains in LangGraph checkpoints
- ✓ WebSocket protocol unaffected

### Files to Create/Modify

**Phase 1 (Script):**
- Create: `backend/app/infrastructure/chromadb/client.py`
- Create: `backend/app/infrastructure/embeddings/provider.py`
- Create: `backend/app/core/domain/document.py`
- Create: `backend/app/core/ports/knowledge_base_repository.py`
- Create: `backend/app/adapters/outbound/chromadb_repository.py`
- Create: `backend/app/langgraph/tools/rag_search.py`
- Create: `backend/scripts/ingest_documents.py`
- Modify: `backend/app/langgraph/graphs/streaming_chat_graph.py` (add rag_search to tools)
- Modify: `backend/app/langgraph/tools/__init__.py` (export rag_search)
- Modify: `backend/requirements.txt` (add chromadb)
- Modify: `backend/app/infrastructure/config/settings.py` (ChromaDB config)

**Phase 2 (API Endpoint):**
- Create: `backend/app/core/use_cases/ingest_document.py`
- Create: `backend/app/adapters/inbound/knowledge_base_router.py`
- Create: `backend/app/adapters/inbound/knowledge_base_schemas.py`
- Modify: `backend/app/main.py` (register knowledge_base_router)
- Modify: `doc/general/API.md` (document new endpoint)

### Testing Files to Create

**All Phases:**
- Create: `backend/tests/unit/test_document_domain.py`
- Create: `backend/tests/unit/test_ingest_use_case.py`
- Create: `backend/tests/integration/test_chromadb_repository.py`
- Create: `backend/tests/integration/test_knowledge_base_api.py` (Phase 2)
- Create: `backend/tests/e2e/test_rag_in_conversation.py`
