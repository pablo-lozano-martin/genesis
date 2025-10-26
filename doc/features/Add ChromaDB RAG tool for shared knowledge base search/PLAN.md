# Implementation Plan: ChromaDB RAG Tool for Shared Knowledge Base Search

## Executive Summary

This plan provides a comprehensive, step-by-step approach to implement a ChromaDB-based RAG (Retrieval-Augmented Generation) tool that enables the LLM to search a shared knowledge base during conversations. The implementation follows Genesis's hexagonal architecture and existing patterns.

**Key Implementation Phases:**
1. **Phase 1**: ChromaDB Infrastructure & Configuration (3-4 hours)
2. **Phase 2**: Domain Models & Port Interfaces (2-3 hours)
3. **Phase 3**: Repository Implementations (4-5 hours)
4. **Phase 4**: RAG Tool Implementation (2-3 hours)
5. **Phase 5**: LangGraph Integration (2 hours)
6. **Phase 6**: Document Ingestion Script (3-4 hours)
7. **Phase 7**: Testing (6-8 hours)
8. **Phase 8** (Optional): API Endpoints for Document Management (8-11 hours)

**Total Estimated Effort**: 22-30 hours (core) + 8-11 hours (optional API)

---

## Architecture Overview

### Hexagonal Architecture Alignment

```
┌─────────────────────────────────────────────────────────────┐
│                    Inbound Adapters                         │
│  - WebSocket Handler (tool execution events)               │
│  - REST API (future: document upload endpoints)            │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   Core Domain                               │
│                                                             │
│  Ports (Interfaces):                                        │
│  - IVectorStore (search, store, delete)                    │
│                                                             │
│  Domain Models:                                             │
│  - Document, DocumentChunk, RetrievalResult                 │
│                                                             │
│  Tools:                                                     │
│  - rag_search(query: str) -> str                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                 Outbound Adapters                           │
│                                                             │
│  Vector Store:                                              │
│  - ChromaDBVectorStore (implements IVectorStore)           │
│                                                             │
│  Document Processing:                                       │
│  - TextProcessor, MarkdownProcessor, PDFProcessor          │
│                                                             │
│  Embeddings:                                                │
│  - EmbeddingsGenerator (configurable model)                │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              Infrastructure Layer                           │
│  - ChromaDB Client (singleton, lifecycle management)       │
│  - Configuration (settings.py)                             │
│  - MongoDB (metadata storage for knowledge bases)          │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

#### Document Ingestion Flow
```
Source Files (backend/data/knowledge_base/)
    ↓
Document Processors (format-specific: PDF, MD, TXT)
    ↓
Text Chunking (RecursiveCharacterTextSplitter, 512 tokens, 50 overlap)
    ↓
Embedding Generation (sentence-transformers/all-MiniLM-L6-v2)
    ↓
ChromaDB Storage (persistent collection with metadata)
    ↓
MongoDB Metadata (knowledge_base_items collection)
```

#### Query Execution Flow
```
User Message → LangGraph process_input
    ↓
LLM (call_llm node with bind_tools)
    ↓
LLM Decides: Use rag_search tool?
    ├─ YES → ToolNode executes rag_search(query)
    │          ↓
    │        ChromaDB.query(query_embedding, top_k=5)
    │          ↓
    │        Format results (source + excerpt)
    │          ↓
    │        Return ToolMessage
    │          ↓
    └────→  Loop back to call_llm with context
    │
    └─ NO → Generate response → END
```

---

## Phase 1: ChromaDB Infrastructure & Configuration

### Objectives
- Set up ChromaDB client with embedded mode
- Configure application settings for RAG
- Ensure proper lifecycle management

### Files to Create

#### 1. ChromaDB Client Manager
**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/chromadb_client.py`

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
            cls.client = None
```

**Key Design Decisions:**
- **Embedded mode by default**: Simpler deployment, no separate container needed initially
- **Singleton pattern**: Single client instance per application lifecycle
- **Class-level methods**: Matches existing MongoDB connection pattern

### Files to Modify

#### 2. Settings Configuration
**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py`

**Add these fields**:
```python
# ChromaDB Settings
chroma_mode: str = "embedded"  # "embedded" or "http"
chroma_persist_directory: str = "./chroma_db"
chroma_host: str = "localhost"
chroma_port: int = 8000
chroma_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
chroma_collection_name: str = "genesis_documents"

# Retrieval Settings
retrieval_top_k: int = 5
retrieval_similarity_threshold: float = 0.5
retrieval_chunk_size: int = 512
retrieval_chunk_overlap: int = 50
```

#### 3. Application Lifecycle
**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py`

**Update lifespan context manager**:
```python
from app.infrastructure.database.chromadb_client import ChromaDBClient

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name}")

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

#### 4. Environment Variables
**File**: `/Users/pablolozano/Mac Projects August/genesis/.env.example`

**Add**:
```bash
# ChromaDB Configuration
CHROMA_MODE=embedded
CHROMA_PERSIST_DIRECTORY=./chroma_db
CHROMA_HOST=localhost
CHROMA_PORT=8000
CHROMA_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHROMA_COLLECTION_NAME=genesis_documents

# Retrieval Settings
RETRIEVAL_TOP_K=5
RETRIEVAL_SIMILARITY_THRESHOLD=0.5
RETRIEVAL_CHUNK_SIZE=512
RETRIEVAL_CHUNK_OVERLAP=50
```

#### 5. Dependencies
**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/requirements.txt`

**Add**:
```
chromadb>=0.4.0
sentence-transformers>=2.2.0
langchain-text-splitters>=0.0.1
pypdf>=3.0.0
```

#### 6. Docker Persistence
**File**: `/Users/pablolozano/Mac Projects August/genesis/docker-compose.yml`

**Add volume**:
```yaml
volumes:
  mongodb_data:
  chroma_data:  # NEW
```

**Acceptance Criteria**:
- [ ] ChromaDB client initializes on application startup
- [ ] Configuration loaded from environment variables
- [ ] Client accessible via `app.state.chroma_client`
- [ ] Graceful shutdown on application stop
- [ ] Logs indicate successful initialization

---

## Phase 2: Domain Models & Port Interfaces

### Objectives
- Define domain models for documents and search results
- Create port interface for vector store operations
- Ensure domain independence from infrastructure

### Files to Create

#### 1. Domain Models
**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/document.py`

```python
# ABOUTME: Document domain models for knowledge base and RAG operations
# ABOUTME: Pure domain entities independent of persistence layer

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class DocumentMetadata:
    """Metadata about a stored document."""
    source: str  # Origin of document (file path, URL, etc.)
    created_at: datetime
    content_length: int
    document_type: str  # "pdf", "md", "txt"


@dataclass
class Document:
    """Document entity for knowledge base."""
    id: str
    content: str  # Full document text
    metadata: DocumentMetadata


@dataclass
class RetrievalResult:
    """Result of a document retrieval."""
    document: Document
    similarity_score: float  # 0.0 to 1.0, higher is more relevant
```

#### 2. Vector Store Port Interface
**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/vector_store.py`

```python
# ABOUTME: Vector store port interface defining the contract for document storage and retrieval
# ABOUTME: Abstract interface following hexagonal architecture principles

from abc import ABC, abstractmethod
from typing import List, Optional
from app.core.domain.document import Document, RetrievalResult


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

**Key Design Decisions:**
- **Async interface**: Matches existing LLM provider pattern in Genesis
- **Domain-agnostic naming**: No "ChromaDB" in interface (supports future Pinecone, Weaviate, etc.)
- **Minimal surface area**: Only essential operations exposed
- **Clear error semantics**: Documents what exceptions can be raised

**Acceptance Criteria**:
- [ ] Domain models created with proper typing
- [ ] Port interface follows ABC pattern
- [ ] No infrastructure dependencies in domain layer
- [ ] Clear docstrings for all methods

---

## Phase 3: Repository Implementations

### Objectives
- Implement ChromaDBVectorStore adapter
- Handle embedding generation
- Manage document chunking

### Files to Create

#### 1. ChromaDB Vector Store Adapter
**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/vector_stores/chroma_vector_store.py`

```python
# ABOUTME: ChromaDB implementation of vector store port interface
# ABOUTME: Manages document storage, embedding generation, and semantic search

from typing import List
from app.core.ports.vector_store import IVectorStore
from app.core.domain.document import Document, RetrievalResult, DocumentMetadata
from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger
from datetime import datetime

logger = get_logger(__name__)


class ChromaDBVectorStore(IVectorStore):
    """ChromaDB implementation of vector store."""

    def __init__(self, chroma_client):
        """Initialize with ChromaDB client."""
        self.client = chroma_client
        self.collection = self._get_or_create_collection()

    def _get_or_create_collection(self):
        """Get or create the knowledge base collection."""
        try:
            collection = self.client.get_or_create_collection(
                name=settings.chroma_collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Collection '{settings.chroma_collection_name}' ready")
            return collection
        except Exception as e:
            logger.error(f"Failed to get/create collection: {e}")
            raise

    async def store_documents(self, documents: List[Document]) -> List[str]:
        """
        Store documents in ChromaDB with automatic embedding.

        ChromaDB will auto-generate embeddings using configured model.
        """
        try:
            ids = [doc.id for doc in documents]
            contents = [doc.content for doc in documents]
            metadatas = [
                {
                    "source": doc.metadata.source,
                    "created_at": doc.metadata.created_at.isoformat(),
                    "content_length": doc.metadata.content_length,
                    "document_type": doc.metadata.document_type
                }
                for doc in documents
            ]

            self.collection.add(
                ids=ids,
                documents=contents,
                metadatas=metadatas
            )

            logger.info(f"Stored {len(documents)} documents in ChromaDB")
            return ids

        except Exception as e:
            logger.error(f"Failed to store documents: {e}")
            raise

    async def retrieve(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        """
        Retrieve documents similar to query using semantic search.
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )

            # Transform ChromaDB results to domain objects
            retrieval_results = []

            if not results["documents"] or not results["documents"][0]:
                return retrieval_results

            for i in range(len(results["ids"][0])):
                doc_id = results["ids"][0][i]
                content = results["documents"][0][i]
                metadata_dict = results["metadatas"][0][i]
                distance = results["distances"][0][i]

                # Convert distance to similarity score (0-1, higher is better)
                similarity_score = 1.0 - (distance / 2.0)

                metadata = DocumentMetadata(
                    source=metadata_dict.get("source", "unknown"),
                    created_at=datetime.fromisoformat(metadata_dict.get("created_at")),
                    content_length=metadata_dict.get("content_length", 0),
                    document_type=metadata_dict.get("document_type", "unknown")
                )

                document = Document(
                    id=doc_id,
                    content=content,
                    metadata=metadata
                )

                retrieval_results.append(
                    RetrievalResult(
                        document=document,
                        similarity_score=similarity_score
                    )
                )

            logger.info(f"Retrieved {len(retrieval_results)} documents for query")
            return retrieval_results

        except Exception as e:
            logger.error(f"Failed to retrieve documents: {e}")
            raise

    async def delete(self, document_id: str) -> bool:
        """Delete a document from ChromaDB."""
        try:
            self.collection.delete(ids=[document_id])
            logger.info(f"Deleted document {document_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False

    async def clear(self) -> bool:
        """Clear all documents from collection."""
        try:
            # Delete collection and recreate
            self.client.delete_collection(name=settings.chroma_collection_name)
            self.collection = self._get_or_create_collection()
            logger.info("Cleared all documents from collection")
            return True
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            return False
```

**Key Implementation Notes:**
- **Auto-embedding**: ChromaDB generates embeddings automatically using configured model
- **Error handling**: All operations wrapped in try/except with logging
- **Domain translation**: Converts ChromaDB results to domain `RetrievalResult` objects
- **Similarity score**: Transforms cosine distance to 0-1 similarity score

#### 2. Vector Store Factory
**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/vector_stores/vector_store_factory.py`

```python
# ABOUTME: Vector store factory for creating store instances based on configuration
# ABOUTME: Currently supports ChromaDB, extensible for other vector databases

from app.core.ports.vector_store import IVectorStore
from app.infrastructure.config.settings import settings


class VectorStoreFactory:
    """Factory for creating vector store instances."""

    @staticmethod
    def create_vector_store(chroma_client) -> IVectorStore:
        """Create appropriate vector store based on configuration."""
        # For now, only ChromaDB supported
        from app.adapters.outbound.vector_stores.chroma_vector_store import ChromaDBVectorStore
        return ChromaDBVectorStore(chroma_client)


def get_vector_store(chroma_client) -> IVectorStore:
    """Get the configured vector store instance."""
    return VectorStoreFactory.create_vector_store(chroma_client)
```

**Acceptance Criteria**:
- [ ] ChromaDBVectorStore implements all IVectorStore methods
- [ ] Documents stored with metadata
- [ ] Retrieval returns results sorted by similarity
- [ ] Error handling for all operations
- [ ] Logging for debugging and monitoring

---

## Phase 4: RAG Tool Implementation

### Objectives
- Create the rag_search tool function
- Format search results for LLM consumption
- Handle empty results gracefully

### Files to Create

#### 1. RAG Search Tool
**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/rag_search.py`

```python
# ABOUTME: RAG search tool for semantic knowledge base queries
# ABOUTME: Integrates with ChromaDB vector store for document retrieval

from typing import Optional
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


async def rag_search(query: str) -> str:
    """
    Search the shared knowledge base for relevant documents.

    Uses vector similarity to find documents matching the query.
    The LLM can use this to augment its responses with retrieved context.

    Args:
        query: The search query string to find relevant documents

    Returns:
        A string containing the top matching documents formatted for LLM consumption,
        or a message if no results found
    """
    try:
        # Get vector store from app context
        from app.main import app

        if not hasattr(app.state, 'vector_store'):
            return "Knowledge base service not available"

        vector_store = app.state.vector_store

        # Validate query
        if not query or not query.strip():
            return "Invalid query: Query cannot be empty"

        # Retrieve relevant documents
        from app.infrastructure.config.settings import settings
        results = await vector_store.retrieve(
            query=query.strip(),
            top_k=settings.retrieval_top_k
        )

        # Handle no results
        if not results:
            return f"No relevant documents found in knowledge base for query: '{query}'"

        # Format results for LLM
        formatted_results = "Knowledge Base Search Results:\n\n"

        for i, result in enumerate(results, 1):
            doc = result.document
            score = result.similarity_score

            # Extract excerpt (first 300 chars)
            excerpt = doc.content[:300] + "..." if len(doc.content) > 300 else doc.content

            formatted_results += f"[Result {i}] (Relevance: {score:.2%})\n"
            formatted_results += f"Source: {doc.metadata.source}\n"
            formatted_results += f"Content: {excerpt}\n\n"

        logger.info(f"RAG search found {len(results)} documents for query: '{query}'")
        return formatted_results

    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        return f"Error searching knowledge base: {str(e)}"
```

**Key Design Decisions:**
- **Simple string return**: Matches existing tool pattern (add, multiply, web_search)
- **Graceful degradation**: Returns informative messages for all error cases
- **LLM-friendly format**: Structured output with sources and relevance scores
- **Truncated excerpts**: Prevents token overflow with long documents

### Files to Modify

#### 2. Tool Module Exports
**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/__init__.py`

**Update**:
```python
from .multiply import multiply
from .add import add
from .web_search import web_search
from .rag_search import rag_search  # NEW

__all__ = ["multiply", "add", "web_search", "rag_search"]  # Add rag_search
```

**Acceptance Criteria**:
- [ ] rag_search function follows existing tool signature pattern
- [ ] Returns formatted string results
- [ ] Handles empty query validation
- [ ] Handles no results gracefully
- [ ] Handles service unavailable gracefully
- [ ] Proper logging for debugging

---

## Phase 5: LangGraph Integration

### Objectives
- Register RAG tool in streaming chat graph
- Bind tool to LLM in call_llm node
- Ensure tool execution streams to frontend

### Files to Modify

#### 1. Streaming Chat Graph
**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py`

**Update tool registration** (around line 43):
```python
from app.langgraph.tools import multiply, add, web_search, rag_search  # Add rag_search

def create_streaming_chat_graph(checkpointer: AsyncMongoDBSaver):
    """Create streaming chat graph with tool support."""

    # ... existing code ...

    # Add RAG search to tools list
    tools = [multiply, add, web_search, rag_search]  # Add rag_search

    # Register tools with ToolNode
    graph_builder.add_node("tools", ToolNode(tools))

    # ... rest of graph definition ...
```

#### 2. Call LLM Node
**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py`

**Update tool binding** (around line 36):
```python
from app.langgraph.tools import multiply, add, web_search, rag_search  # Add rag_search

async def call_llm(state: ConversationState, config: RunnableConfig) -> dict:
    """Call LLM with bound tools."""

    # ... existing code ...

    # Bind tools to LLM
    tools = [multiply, add, web_search, rag_search]  # Add rag_search
    llm_provider_with_tools = llm_provider.bind_tools(tools, parallel_tool_calls=False)

    # ... rest of node logic ...
```

#### 3. Application State Initialization
**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py`

**Initialize vector store in lifespan**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... after ChromaDB initialization ...

    # Create vector store instance
    from app.adapters.outbound.vector_stores.vector_store_factory import get_vector_store
    app.state.vector_store = get_vector_store(ChromaDBClient.client)
    logger.info("Vector store initialized")

    # ... rest of lifespan ...
```

**Key Integration Points:**
- **No WebSocket changes needed**: Existing on_tool_start/on_tool_end events handle RAG tool automatically
- **No state changes needed**: ToolMessage automatically persisted by AsyncMongoDBSaver checkpointer
- **Tool ordering**: RAG tool added at end of tools list (order doesn't affect functionality)

**Acceptance Criteria**:
- [ ] rag_search imported in both graph and call_llm files
- [ ] Tool added to tools list in both locations
- [ ] Vector store accessible from app.state
- [ ] Graph compiles without errors
- [ ] Tool callable by LLM via bind_tools

---

## Phase 6: Document Ingestion Script

### Objectives
- Create standalone script for batch document ingestion
- Support multiple file formats (txt, md, pdf)
- Implement chunking strategy
- Handle errors gracefully

### Files to Create

#### 1. Document Ingestion Script
**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/scripts/ingest_documents.py`

```python
# ABOUTME: Document ingestion script for batch loading knowledge base files
# ABOUTME: Processes files, chunks content, and stores in ChromaDB

import asyncio
import argparse
import sys
from pathlib import Path
from typing import List
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger
from app.infrastructure.database.chromadb_client import ChromaDBClient
from app.adapters.outbound.vector_stores.vector_store_factory import get_vector_store
from app.core.domain.document import Document, DocumentMetadata

logger = get_logger(__name__)


async def load_text_file(file_path: Path) -> str:
    """Load content from text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load {file_path}: {e}")
        raise


async def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks.

    Simple implementation - can be enhanced with semantic chunking later.
    """
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)

    return chunks


async def process_file(file_path: Path) -> List[Document]:
    """Process a file and return Document objects."""
    logger.info(f"Processing file: {file_path}")

    # Load content based on file type
    suffix = file_path.suffix.lower()

    if suffix in ['.txt', '.md']:
        content = await load_text_file(file_path)
    elif suffix == '.pdf':
        # TODO: Implement PDF extraction (use pypdf)
        logger.warning(f"PDF support not yet implemented, skipping {file_path}")
        return []
    else:
        logger.warning(f"Unsupported file type {suffix}, skipping {file_path}")
        return []

    # Chunk content
    chunks = await chunk_text(
        content,
        chunk_size=settings.retrieval_chunk_size,
        overlap=settings.retrieval_chunk_overlap
    )

    # Create Document objects for each chunk
    documents = []
    for i, chunk in enumerate(chunks):
        doc_id = f"{file_path.stem}_chunk_{i}"

        metadata = DocumentMetadata(
            source=str(file_path),
            created_at=datetime.utcnow(),
            content_length=len(chunk),
            document_type=suffix[1:]  # Remove the dot
        )

        document = Document(
            id=doc_id,
            content=chunk,
            metadata=metadata
        )

        documents.append(document)

    logger.info(f"Created {len(documents)} document chunks from {file_path}")
    return documents


async def ingest_directory(directory: Path, vector_store):
    """Ingest all supported files from directory."""
    logger.info(f"Scanning directory: {directory}")

    # Find all supported files
    supported_extensions = ['.txt', '.md', '.pdf']
    files = []

    for ext in supported_extensions:
        files.extend(directory.glob(f"**/*{ext}"))

    logger.info(f"Found {len(files)} files to process")

    # Process all files
    all_documents = []
    for file_path in files:
        try:
            documents = await process_file(file_path)
            all_documents.extend(documents)
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            continue

    # Store all documents in vector store
    if all_documents:
        logger.info(f"Storing {len(all_documents)} document chunks in vector store")
        await vector_store.store_documents(all_documents)
        logger.info("Ingestion complete")
    else:
        logger.warning("No documents to store")


async def main(directory_path: str):
    """Main ingestion workflow."""
    try:
        # Initialize ChromaDB
        await ChromaDBClient.initialize()

        # Create vector store
        vector_store = get_vector_store(ChromaDBClient.client)

        # Ingest directory
        directory = Path(directory_path)
        if not directory.exists():
            logger.error(f"Directory does not exist: {directory}")
            return 1

        await ingest_directory(directory, vector_store)

        return 0

    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        return 1
    finally:
        ChromaDBClient.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest documents into knowledge base"
    )
    parser.add_argument(
        "directory",
        type=str,
        help="Directory containing documents to ingest"
    )

    args = parser.parse_args()

    sys.exit(asyncio.run(main(args.directory)))
```

#### 2. Knowledge Base Directory
**Create**: `/Users/pablolozano/Mac Projects August/genesis/backend/data/knowledge_base/README.md`

```markdown
# Knowledge Base Directory

Place documents here for ingestion into the RAG knowledge base.

## Supported Formats
- `.txt` - Plain text files
- `.md` - Markdown files
- `.pdf` - PDF documents (coming soon)

## Ingestion

Run the ingestion script from the backend directory:

```bash
python scripts/ingest_documents.py data/knowledge_base/
```

## Document Guidelines
- Use clear, descriptive filenames
- Keep documents focused on specific topics
- Update regularly to maintain accuracy
```

**Usage Example**:
```bash
# From backend directory
python scripts/ingest_documents.py data/knowledge_base/

# Output:
# INFO: Scanning directory: data/knowledge_base/
# INFO: Found 5 files to process
# INFO: Processing file: data/knowledge_base/auth_guide.md
# INFO: Created 12 document chunks from auth_guide.md
# ...
# INFO: Storing 43 document chunks in vector store
# INFO: Ingestion complete
```

**Acceptance Criteria**:
- [ ] Script processes txt and md files
- [ ] Text chunked with overlap
- [ ] Each chunk stored as separate document
- [ ] Metadata includes source file and type
- [ ] Error handling for individual file failures
- [ ] Logging shows progress and results
- [ ] Can be run from command line

---

## Phase 7: Testing

### Objectives
- Comprehensive unit tests for all new components
- Integration tests for ChromaDB operations
- Tool execution tests in LangGraph context
- Achieve >85% code coverage

### Test Files to Create

#### 1. RAG Tool Unit Tests
**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_rag_tool.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.langgraph.tools.rag_search import rag_search
from app.core.domain.document import Document, DocumentMetadata, RetrievalResult
from datetime import datetime


@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing."""
    mock = AsyncMock()
    return mock


@pytest.fixture
def sample_retrieval_results():
    """Sample retrieval results for testing."""
    metadata = DocumentMetadata(
        source="test_doc.md",
        created_at=datetime.utcnow(),
        content_length=100,
        document_type="md"
    )

    doc = Document(
        id="test_1",
        content="This is a test document about Python programming.",
        metadata=metadata
    )

    return [RetrievalResult(document=doc, similarity_score=0.95)]


@pytest.mark.asyncio
class TestRAGSearch:
    """Tests for RAG search tool."""

    async def test_rag_search_found_results(self, mock_vector_store, sample_retrieval_results, monkeypatch):
        """Test RAG search with found results."""
        # Setup mock
        mock_vector_store.retrieve.return_value = sample_retrieval_results

        # Mock app.state.vector_store
        from app import main
        main.app.state.vector_store = mock_vector_store

        # Execute
        result = await rag_search("test query")

        # Assert
        assert "Knowledge Base Search Results" in result
        assert "Result 1" in result
        assert "test_doc.md" in result
        assert "95.00%" in result  # Relevance score
        mock_vector_store.retrieve.assert_called_once()

    async def test_rag_search_no_results(self, mock_vector_store, monkeypatch):
        """Test RAG search with no results."""
        mock_vector_store.retrieve.return_value = []

        from app import main
        main.app.state.vector_store = mock_vector_store

        result = await rag_search("nonexistent query")

        assert "No relevant documents found" in result

    async def test_rag_search_empty_query(self, mock_vector_store, monkeypatch):
        """Test RAG search with empty query."""
        from app import main
        main.app.state.vector_store = mock_vector_store

        result = await rag_search("")

        assert "Invalid query" in result
        mock_vector_store.retrieve.assert_not_called()

    async def test_rag_search_service_unavailable(self, monkeypatch):
        """Test RAG search when service is unavailable."""
        from app import main

        # Remove vector_store from app.state
        if hasattr(main.app.state, 'vector_store'):
            delattr(main.app.state, 'vector_store')

        result = await rag_search("test query")

        assert "service not available" in result

    async def test_rag_search_exception_handling(self, mock_vector_store, monkeypatch):
        """Test RAG search handles exceptions gracefully."""
        mock_vector_store.retrieve.side_effect = Exception("ChromaDB connection error")

        from app import main
        main.app.state.vector_store = mock_vector_store

        result = await rag_search("test query")

        assert "Error searching knowledge base" in result
```

#### 2. ChromaDB Adapter Unit Tests
**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_chroma_vector_store.py`

```python
import pytest
from unittest.mock import MagicMock, AsyncMock
from app.adapters.outbound.vector_stores.chroma_vector_store import ChromaDBVectorStore
from app.core.domain.document import Document, DocumentMetadata
from datetime import datetime


@pytest.fixture
def mock_chroma_client():
    """Mock ChromaDB client."""
    mock = MagicMock()
    mock_collection = MagicMock()
    mock.get_or_create_collection.return_value = mock_collection
    return mock


@pytest.fixture
def sample_documents():
    """Sample documents for testing."""
    metadata = DocumentMetadata(
        source="test.txt",
        created_at=datetime.utcnow(),
        content_length=50,
        document_type="txt"
    )

    return [
        Document(id="doc1", content="Content 1", metadata=metadata),
        Document(id="doc2", content="Content 2", metadata=metadata)
    ]


class TestChromaDBVectorStore:
    """Tests for ChromaDB vector store adapter."""

    @pytest.mark.asyncio
    async def test_store_documents(self, mock_chroma_client, sample_documents):
        """Test storing documents in ChromaDB."""
        store = ChromaDBVectorStore(mock_chroma_client)

        ids = await store.store_documents(sample_documents)

        assert len(ids) == 2
        assert ids == ["doc1", "doc2"]
        store.collection.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_documents(self, mock_chroma_client):
        """Test retrieving documents from ChromaDB."""
        # Setup mock response
        mock_chroma_client.get_or_create_collection().query.return_value = {
            "ids": [["doc1"]],
            "documents": [["Content 1"]],
            "distances": [[0.1]],
            "metadatas": [[{
                "source": "test.txt",
                "created_at": datetime.utcnow().isoformat(),
                "content_length": 50,
                "document_type": "txt"
            }]]
        }

        store = ChromaDBVectorStore(mock_chroma_client)
        results = await store.retrieve("test query", top_k=5)

        assert len(results) == 1
        assert results[0].document.id == "doc1"
        assert results[0].similarity_score > 0

    @pytest.mark.asyncio
    async def test_delete_document(self, mock_chroma_client):
        """Test deleting document from ChromaDB."""
        store = ChromaDBVectorStore(mock_chroma_client)

        success = await store.delete("doc1")

        assert success is True
        store.collection.delete.assert_called_once_with(ids=["doc1"])
```

#### 3. Integration Tests
**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_rag_pipeline.py`

```python
import pytest
from app.infrastructure.database.chromadb_client import ChromaDBClient
from app.adapters.outbound.vector_stores.vector_store_factory import get_vector_store
from app.core.domain.document import Document, DocumentMetadata
from datetime import datetime


@pytest.fixture
async def chromadb_instance():
    """Real ChromaDB instance for integration tests (ephemeral)."""
    import chromadb
    client = chromadb.EphemeralClient()
    yield client
    # Cleanup happens automatically with ephemeral client


@pytest.mark.integration
class TestRAGPipeline:
    """Integration tests for RAG pipeline."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve_documents(self, chromadb_instance):
        """Test full pipeline: store documents and retrieve them."""
        # Create vector store
        vector_store = get_vector_store(chromadb_instance)

        # Create test documents
        metadata = DocumentMetadata(
            source="test.md",
            created_at=datetime.utcnow(),
            content_length=100,
            document_type="md"
        )

        documents = [
            Document(id="doc1", content="Python is a programming language", metadata=metadata),
            Document(id="doc2", content="JavaScript runs in browsers", metadata=metadata)
        ]

        # Store documents
        ids = await vector_store.store_documents(documents)
        assert len(ids) == 2

        # Retrieve documents
        results = await vector_store.retrieve("programming language", top_k=5)

        # Assert results
        assert len(results) > 0
        assert results[0].document.id == "doc1"  # Should rank first
        assert results[0].similarity_score > 0.5

    @pytest.mark.asyncio
    async def test_semantic_search_quality(self, chromadb_instance):
        """Test semantic search returns relevant results."""
        vector_store = get_vector_store(chromadb_instance)

        # Index documents about different topics
        metadata = DocumentMetadata(
            source="test.md",
            created_at=datetime.utcnow(),
            content_length=100,
            document_type="md"
        )

        documents = [
            Document(id="cats", content="Cats are feline animals that meow", metadata=metadata),
            Document(id="dogs", content="Dogs are canine animals that bark", metadata=metadata),
            Document(id="cars", content="Cars are vehicles with four wheels", metadata=metadata)
        ]

        await vector_store.store_documents(documents)

        # Search for "feline animals"
        results = await vector_store.retrieve("feline animals", top_k=3)

        # Assert cat document ranks highest
        assert results[0].document.id == "cats"
        assert results[0].similarity_score > results[1].similarity_score
```

**Test Coverage Goals:**
- **Unit Tests**: 95%+ coverage
  - rag_search tool function
  - ChromaDBVectorStore adapter
  - Domain models
  - Factory patterns

- **Integration Tests**: 80%+ coverage
  - Real ChromaDB operations (ephemeral)
  - Document ingestion pipeline
  - Search quality verification

- **E2E Tests** (Post-MVP): Critical user workflows
  - RAG tool execution in conversation
  - Tool event streaming
  - Error handling

**Acceptance Criteria**:
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Code coverage >85%
- [ ] Tests follow existing patterns in conftest.py and test_tools.py
- [ ] Mock fixtures reusable across tests

---

## Phase 8 (Optional): API Endpoints for Document Management

**Note**: This phase is optional for MVP. The ingestion script (Phase 6) is sufficient for initial deployment.

### Objectives
- Provide REST API for document upload
- Enable dynamic knowledge base management
- Follow existing authentication patterns

### Files to Create

#### 1. API Schemas
**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/knowledge_base_schemas.py`

```python
# ABOUTME: Pydantic schemas for knowledge base API endpoints
# ABOUTME: Request/response models for document management

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DocumentIngestRequest(BaseModel):
    """Request schema for document ingestion."""
    file_name: str = Field(..., max_length=255)
    content: str = Field(...)
    metadata: Optional[dict] = Field(default=None)

    class Config:
        json_schema_extra = {
            "example": {
                "file_name": "python_guide.md",
                "content": "Python is a high-level programming language...",
                "metadata": {"category": "programming", "language": "en"}
            }
        }


class DocumentIngestResponse(BaseModel):
    """Response schema for document ingestion."""
    document_ids: list[str]
    chunks_created: int
    status: str = "success"


class KnowledgeBaseStatsResponse(BaseModel):
    """Response schema for knowledge base statistics."""
    total_documents: int
    total_chunks: int
    collection_name: str
```

#### 2. Knowledge Base Router
**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/knowledge_base_router.py`

```python
# ABOUTME: REST API endpoints for knowledge base management
# ABOUTME: Handles document upload and knowledge base operations

from fastapi import APIRouter, HTTPException, status
from app.infrastructure.security.dependencies import CurrentUser
from app.adapters.inbound.knowledge_base_schemas import (
    DocumentIngestRequest,
    DocumentIngestResponse,
    KnowledgeBaseStatsResponse
)
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/knowledge-base", tags=["knowledge-base"])


@router.post("/documents", response_model=DocumentIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_document(
    request: DocumentIngestRequest,
    current_user: CurrentUser
):
    """
    Ingest a document into the knowledge base.

    Requires authentication. Document is processed, chunked, and stored.
    """
    try:
        from app.main import app
        vector_store = app.state.vector_store

        # Process document (chunking logic here)
        # ... implementation ...

        return DocumentIngestResponse(
            document_ids=["id1", "id2"],
            chunks_created=2,
            status="success"
        )

    except Exception as e:
        logger.error(f"Document ingestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document ingestion failed"
        )


@router.get("/stats", response_model=KnowledgeBaseStatsResponse)
async def get_knowledge_base_stats():
    """Get knowledge base statistics (public endpoint)."""
    try:
        from app.main import app
        from app.infrastructure.config.settings import settings

        # Get collection stats
        # ... implementation ...

        return KnowledgeBaseStatsResponse(
            total_documents=0,
            total_chunks=0,
            collection_name=settings.chroma_collection_name
        )

    except Exception as e:
        logger.error(f"Failed to get KB stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve knowledge base statistics"
        )
```

#### 3. Router Registration
**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py`

**Add**:
```python
from app.adapters.inbound.knowledge_base_router import router as knowledge_base_router

# In create_app():
app.include_router(knowledge_base_router)
```

**Estimated Effort**: 8-11 hours

**Acceptance Criteria**:
- [ ] POST /api/knowledge-base/documents endpoint created
- [ ] Authentication required for document upload
- [ ] GET /api/knowledge-base/stats endpoint (public)
- [ ] Proper error handling and logging
- [ ] Integration tests for endpoints

---

## Testing Checklist

### Unit Tests
- [ ] RAG search tool function
  - [ ] Happy path with results
  - [ ] No results found
  - [ ] Empty query validation
  - [ ] Service unavailable handling
  - [ ] Exception handling

- [ ] ChromaDB Vector Store Adapter
  - [ ] Store documents
  - [ ] Retrieve documents
  - [ ] Delete documents
  - [ ] Clear collection
  - [ ] Metadata handling

- [ ] Domain Models
  - [ ] Document creation
  - [ ] DocumentMetadata validation
  - [ ] RetrievalResult structure

### Integration Tests
- [ ] RAG Pipeline
  - [ ] Store and retrieve documents
  - [ ] Semantic search quality
  - [ ] Empty knowledge base handling
  - [ ] Large document handling

- [ ] ChromaDB Connection
  - [ ] Client initialization
  - [ ] Collection creation
  - [ ] Persistent storage
  - [ ] Connection error handling

### Tool Execution Tests
- [ ] LangGraph Integration
  - [ ] Tool registered in graph
  - [ ] Tool binding in call_llm node
  - [ ] Tool execution routing
  - [ ] ToolMessage creation

### End-to-End Tests (Manual for MVP)
- [ ] Full conversation with RAG tool usage
- [ ] WebSocket tool events (TOOL_START, TOOL_COMPLETE)
- [ ] Multiple tool usage in single conversation
- [ ] Error scenarios

---

## Deployment Checklist

### Pre-Deployment
- [ ] All tests passing (unit + integration)
- [ ] Code coverage >85%
- [ ] Environment variables documented in .env.example
- [ ] Dependencies added to requirements.txt
- [ ] Docker volume for ChromaDB data configured

### Initial Deployment
- [ ] Run database migrations (if MongoDB schema changes)
- [ ] Initialize ChromaDB collection
- [ ] Run document ingestion script for initial knowledge base
- [ ] Verify application startup (check logs)
- [ ] Test RAG tool via chat interface

### Post-Deployment Verification
- [ ] RAG tool callable from chat
- [ ] Search returns relevant results
- [ ] Tool execution events stream to frontend
- [ ] Error handling works (try invalid queries)
- [ ] Performance acceptable (<2s for typical queries)

### Monitoring
- [ ] Log RAG tool invocations
- [ ] Monitor ChromaDB collection size
- [ ] Track query latency
- [ ] Monitor error rates

---

## Risk Mitigation

### Critical Risks

1. **Embedding Model Consistency**
   - **Risk**: Changing embedding model invalidates existing vectors
   - **Mitigation**: Lock model version in settings, document in README
   - **Recovery**: Re-run ingestion script if model changes

2. **ChromaDB Data Corruption**
   - **Risk**: Collection becomes corrupted or unavailable
   - **Mitigation**: Regular backups of chroma_data volume
   - **Recovery**: Restore from backup or re-run ingestion

3. **Performance Degradation**
   - **Risk**: Large knowledge bases slow down search
   - **Mitigation**: Monitor query latency, limit top_k results
   - **Optimization**: Add HNSW indexing if needed (future)

4. **Token Budget Overflow**
   - **Risk**: Retrieved documents consume too many LLM tokens
   - **Mitigation**: Limit top_k=5, truncate excerpts to 300 chars
   - **Fallback**: Reduce top_k dynamically if token limit reached

### Implementation Risks

1. **ChromaDB Dependency**
   - **Risk**: Third-party database increases operational complexity
   - **Mitigation**: Start with embedded mode (no separate container)
   - **Upgrade Path**: Move to HTTP mode when scaling needs arise

2. **Search Quality**
   - **Risk**: RAG doesn't improve conversation quality
   - **Mitigation**: Test with real documents, iterate on chunking strategy
   - **Fallback**: Disable tool if not providing value

3. **File Format Support**
   - **Risk**: PDF extraction not implemented in MVP
   - **Mitigation**: Start with txt/md only, add PDF in future
   - **Workaround**: Convert PDFs to markdown manually

---

## Success Metrics

### Functional Metrics
- RAG tool successfully executes in >95% of invocations
- Search returns results for >80% of relevant queries
- Zero application crashes due to RAG tool

### Performance Metrics
- Query latency <2 seconds (p95)
- Document ingestion <10 seconds per document
- Memory usage increase <500MB with 1000 documents

### Quality Metrics
- User feedback indicates improved answer quality (subjective)
- RAG tool invoked automatically when appropriate (not over/under-used)
- Retrieved documents relevant to query (manual spot checks)

---

## Future Enhancements (Post-MVP)

### Short-term (Next Sprint)
- [ ] PDF document support
- [ ] Per-conversation knowledge base scoping
- [ ] Document versioning and updates
- [ ] Search result caching

### Medium-term (Next Quarter)
- [ ] API endpoints for document upload (Phase 8)
- [ ] Admin UI for knowledge base management
- [ ] Multiple knowledge base collections
- [ ] Document-level access control

### Long-term (Future)
- [ ] Hybrid search (keyword + semantic)
- [ ] Query expansion and reformulation
- [ ] Automatic document summarization
- [ ] Knowledge graph integration
- [ ] Multi-modal RAG (images, tables)

---

## References

### Analysis Documents
- `backend_hexagonal.md` - Architecture guidance and patterns
- `llm_integration.md` - Tool calling and LangGraph integration
- `data_flow.md` - Data transformation and pipeline design
- `database_mongodb.md` - MongoDB schema and persistence
- `api_contract.md` - API design and endpoint patterns
- `testing_coverage.md` - Test strategy and coverage goals

### Codebase References
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/web_search.py` - Existing tool pattern
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Tool registration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_user_repository.py` - Repository pattern
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_tools.py` - Unit test patterns

### External Documentation
- ChromaDB Docs: https://docs.trychroma.com/
- LangChain Text Splitters: https://python.langchain.com/docs/modules/data_connection/document_transformers/
- Sentence Transformers: https://www.sbert.net/

---

## Implementation Timeline

### Week 1: Foundation
- **Day 1-2**: Phase 1 (ChromaDB Infrastructure)
- **Day 3**: Phase 2 (Domain Models & Ports)
- **Day 4-5**: Phase 3 (Repository Implementations)

### Week 2: Tool & Integration
- **Day 1-2**: Phase 4 (RAG Tool Implementation)
- **Day 3**: Phase 5 (LangGraph Integration)
- **Day 4-5**: Phase 6 (Document Ingestion Script)

### Week 3: Testing & Documentation
- **Day 1-3**: Phase 7 (Comprehensive Testing)
- **Day 4**: Manual E2E testing and bug fixes
- **Day 5**: Documentation updates, deployment preparation

**Total Duration**: 3 weeks (15 working days)

---

## Conclusion

This plan provides a comprehensive roadmap for implementing the ChromaDB RAG tool while maintaining Genesis's hexagonal architecture and existing patterns. The phased approach allows for incremental development and testing, with clear acceptance criteria at each stage.

**Key Success Factors:**
- Follow existing patterns (tool registration, repository adapters, domain models)
- Maintain clean architecture (ports/adapters separation)
- Comprehensive testing (unit, integration, e2e)
- Proper error handling and logging
- Clear documentation for future maintainers

The optional Phase 8 (API endpoints) can be deferred to allow for faster MVP delivery while maintaining the ability to add dynamic document management later.
