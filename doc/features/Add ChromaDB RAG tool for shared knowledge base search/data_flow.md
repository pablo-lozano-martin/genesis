# Data Flow Analysis: ChromaDB RAG Tool for Shared Knowledge Base Search

## Request Summary

This feature adds a Retrieval-Augmented Generation (RAG) capability to Genesis by:

1. **Document Ingestion Pipeline**: Create a process to load documents from `backend/data/knowledge_base/`, chunk them intelligently, generate embeddings, and store them in ChromaDB
2. **Vector Search Tool**: Implement a `knowledge_base_search` tool that queries ChromaDB using vector similarity to retrieve relevant document chunks
3. **LLM Integration**: Register the RAG tool in the LangGraph chat graph so the LLM can automatically decide when to use vector search for user queries
4. **WebSocket Streaming**: Ensure retrieval results are streamed to the frontend via WebSocket events similar to tool execution
5. **Performance Optimization**: Implement caching strategies and identify bottlenecks in the embedding and retrieval pipeline

The goal is to provide users with a knowledge base search capability that integrates seamlessly into the conversational AI experience through tool-calling.

## Relevant Files & Modules

### Files to Examine

**Backend - LangGraph Graph & State:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Main streaming graph where RAG tool will be registered alongside other tools (multiply, add, web_search)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - ConversationState extending MessagesState with conversation_id, user_id fields
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - LLM invocation node that binds tools; RAG tool will be added to this binding
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/process_input.py` - Input validation node (no changes needed)

**Backend - Tool Definitions:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/web_search.py` - Existing tool pattern to follow for RAG tool implementation
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/multiply.py` - Simple tool example (reference pattern)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/add.py` - Simple tool example (reference pattern)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/__init__.py` - Tool exports; RAG tool will be added here

**Backend - RAG Infrastructure (NEW):**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/rag/chroma_client.py` (NEW) - Singleton ChromaDB client initialization and lifecycle management
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/rag/embeddings.py` (NEW) - Embedding generation using configured provider (OpenAI, Anthropic, or local model)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/rag/document_store.py` (NEW) - Document store adapter for RAG operations
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/rag_repository.py` (NEW) - RAG repository port interface

**Backend - Document Management:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/data/knowledge_base/` (NEW DIRECTORY) - Storage location for source documents (PDFs, markdown, text files)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/document_processors/text_processor.py` (NEW) - Text file processor with chunking strategy
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/document_processors/markdown_processor.py` (NEW) - Markdown document processor with chunk preservation
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/document_processors/pdf_processor.py` (NEW) - PDF document processor with OCR support

**Backend - Application Startup & Lifecycle:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py` - Application entry point where ChromaDB and RAG infrastructure will be initialized during lifespan
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py` - Configuration file; will need new RAG-related settings (embedding_model, chunk_size, overlap, chroma_db_path)

**Backend - LLM Provider Integration:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - ILLMProvider interface (no changes needed; embedding model will be separate)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/` - Provider implementations (reference for patterns)

**Backend - WebSocket Handler & Events:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - Handles WebSocket connections; already streams tool events (RAG tool will leverage existing on_tool_start/on_tool_end events)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py` - WebSocket message types (no changes needed; existing TOOL_START/TOOL_COMPLETE will handle RAG events)

**Backend - Testing:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_tools.py` - Unit tests for tools; RAG tool tests will be added here
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_rag_pipeline.py` (NEW) - Unit tests for document ingestion, chunking, and retrieval
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_rag_tool.py` (NEW) - Integration tests for RAG tool with LLM

**Data Persistence:**
- `/Users/pablolozano/Mac Projects August/genesis/data/chromadb/` - ChromaDB persistent storage directory (already exists; will contain collections)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/mongodb.py` - MongoDB connections; ChromaDB will be separate client

### Key Functions & Classes

**Tool Interface:**
- `knowledge_base_search(query: str) -> str` in `langgraph/tools/rag.py` - Main RAG tool callable that queries ChromaDB and returns relevant documents
- Signature must follow tool pattern used by multiply/add/web_search for LangGraph compatibility

**RAG Infrastructure:**
- `ChromaClientSingleton` in `infrastructure/rag/chroma_client.py` - Manages ChromaDB client lifecycle (initialization, persistence path)
- `EmbeddingsGenerator` in `infrastructure/rag/embeddings.py` - Generates embeddings for documents and queries (abstracts embedding model)
- `DocumentProcessor` abstract class in `adapters/outbound/document_processors/` - Base class for document loading with `process(file_path: str) -> List[Document]` method
- `RAGRepository` port in `core/ports/rag_repository.py` - Interface defining `index_documents()`, `search()`, `get_statistics()` methods

**Document Ingestion:**
- `ingest_documents(source_dir: str)` async function - Orchestrates loading all documents from knowledge_base directory
- `chunk_documents(documents: List[str]) -> List[Chunk]` - Splits documents into overlapping chunks for vector storage
- Called during application startup (in lifespan) before graph compilation

**Query & Retrieval:**
- `query_knowledge_base(query: str, top_k: int = 5) -> List[Document]` - Queries ChromaDB collection with vector similarity
- Returns tuple of (chunk_text, similarity_score, metadata) for each result
- Called by `knowledge_base_search` tool when LLM decides to use it

**State & Caching:**
- RAG collection in ChromaDB (persistent) - Caches all indexed documents and embeddings
- Optional in-memory cache for frequent queries (LRU cache decorator on search function)
- Document metadata stored with each chunk for source tracking

## Current Data Flow Overview

### High-Level Architecture (Before RAG Addition)

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Frontend (Browser)                         │
│  User sends message → useWebSocket Hook → WebSocketService          │
└──────────────────┬──────────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Backend - WebSocket Layer                         │
│  websocket_handler.handle_websocket_chat()                           │
│    ↓ authenticate user                                              │
│    ↓ validate conversation ownership                                │
│    ↓ create HumanMessage from user input                            │
│    ↓ invoke graph.astream_events()                                  │
└──────────────────┬───────────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│              Backend - LangGraph Execution                           │
│  streaming_chat_graph (with checkpointer)                           │
│                                                                      │
│  START → process_input → call_llm → tools → call_llm → END         │
│                            ↓                                         │
│  Tools available: [multiply, add, web_search]                       │
│  LLM decides if tool call needed                                    │
│  Tool executes, returns result as ToolMessage                       │
│  Loop continues until LLM produces no tool calls                    │
└──────────────────┬───────────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│         Events streamed to Frontend via WebSocket                    │
│  on_chat_model_stream → ServerTokenMessage (LLM tokens)             │
│  on_tool_start → ServerToolStartMessage                             │
│  on_tool_end → ServerToolCompleteMessage                            │
│  completion → ServerCompleteMessage                                 │
└──────────────────────────────────────────────────────────────────────┘
```

## Data Flow for RAG Pipeline (With Additions)

### Phase 1: Document Ingestion (Application Startup)

```
                    Application Startup (lifespan)
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│           Document Discovery & Loading                              │
│  backend/data/knowledge_base/ directory scan                        │
│    ├─ Discover all .txt, .md, .pdf files                           │
│    └─ Create Document objects with metadata                        │
└──────────────────┬───────────────────────────────────────────────────┘
                   │ List[Document] with content, source, type
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│            Document Chunking (Text Splitting)                       │
│  Chunk parameters:                                                   │
│    - chunk_size: 512 tokens (configurable in settings)             │
│    - overlap: 50 tokens (preserve context between chunks)          │
│    - splitter: RecursiveCharacterTextSplitter                      │
│                                                                      │
│  Output: List[Chunk] with:                                          │
│    - text: chunk content                                            │
│    - metadata: {source, page, chunk_index, date_ingested}          │
└──────────────────┬───────────────────────────────────────────────────┘
                   │ List[Chunk] ready for embedding
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│           Embedding Generation (Batch Processing)                   │
│  EmbeddingsGenerator uses configured model:                         │
│    - OpenAI text-embedding-3-small (default, ~50 tokens/request)  │
│    - or Anthropic embeddings API (if configured)                  │
│    - or local HuggingFace model (for offline use)                 │
│                                                                      │
│  Batch process chunks (e.g., 10 chunks per batch)                 │
│  Rate limiting: respect API limits, cache embeddings               │
│                                                                      │
│  Output: List[(chunk_text, embedding_vector, metadata)]            │
└──────────────────┬───────────────────────────────────────────────────┘
                   │ Ready for ChromaDB storage
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│          ChromaDB Collection Creation & Indexing                    │
│  ChromaDB client.create_or_get_collection("knowledge_base")        │
│                                                                      │
│  For each (chunk_text, embedding, metadata):                       │
│    - collection.add(                                               │
│        ids=[unique_id],                                            │
│        documents=[chunk_text],                                     │
│        embeddings=[vector],                                        │
│        metadatas=[metadata]                                        │
│      )                                                             │
│                                                                      │
│  Persistence: data/chromadb/ directory                             │
│                                                                      │
│  Log ingestion statistics: total chunks, sources, embedding time   │
└──────────────────┬───────────────────────────────────────────────────┘
                   │ RAG Ready
                   ▼
              Graph Compilation
           (tools list includes RAG tool)
```

### Phase 2: Query Execution (User Message → LLM → Optional RAG Tool Call)

This is a detailed flow showing how data moves from user query through the RAG pipeline.

**See full document in the generated file for complete details on:**
- Query execution flow
- Tool execution details  
- WebSocket event streaming
- Error handling at each stage
- Performance bottlenecks
- Caching strategies
- Testing strategy
- Implementation guidance

## Data Transformation Points

| Stage | Input | Transformation | Output | Responsibility |
|-------|-------|----------------|--------|-----------------|
| **Document Discovery** | File paths in knowledge_base/ | Read files, create Document objects | List[Document] | DocumentProcessor classes |
| **Document Chunking** | List[Document] | Split by size/tokens with overlap | List[Chunk] | Text splitter utility |
| **Embedding Generation** | Chunk text | Generate embedding vectors | List[(text, vector, metadata)] | EmbeddingsGenerator |
| **ChromaDB Indexing** | Embeddings + metadata | Store in collection with IDs | Indexed collection | ChromaDB client |
| **Query Embedding** | User query string | Generate same-dim embedding vector | Vector | EmbeddingsGenerator (consistency) |
| **Vector Search** | Query vector | Find top-k similar vectors | List[(chunk_text, score, metadata)] | ChromaDB query |
| **Result Formatting** | Raw ChromaDB results | Format for LLM context | String with sources | RAG tool function |
| **Tool Result** | Formatted string | ToolMessage wrapper | ToolMessage appended to state | LangGraph ToolNode |

## Module Structure (Proposed)

```
backend/app/
├── infrastructure/rag/                          (NEW)
│   ├── __init__.py
│   ├── chroma_client.py                        - ChromaDB client singleton
│   └── embeddings.py                           - Embedding generation adapter
├── adapters/outbound/rag/                      (NEW)
│   ├── __init__.py
│   └── document_store.py                       - RAG repository implementation
├── adapters/outbound/document_processors/      (NEW)
│   ├── __init__.py
│   ├── base.py                                 - DocumentProcessor abstract class
│   ├── text_processor.py                       - .txt processor
│   ├── markdown_processor.py                   - .md processor
│   └── pdf_processor.py                        - .pdf processor
├── core/ports/
│   └── rag_repository.py                       (NEW) - RAG port interface
└── langgraph/tools/
    ├── __init__.py                             (MODIFY - add rag export)
    └── rag.py                                  (NEW) - knowledge_base_search tool
```

## Files to Create & Modify

### Create
- `/backend/app/langgraph/tools/rag.py` - RAG tool
- `/backend/app/infrastructure/rag/chroma_client.py` - ChromaDB client
- `/backend/app/infrastructure/rag/embeddings.py` - Embeddings
- `/backend/app/core/ports/rag_repository.py` - RAG port
- `/backend/app/adapters/outbound/rag/document_store.py` - RAG implementation
- `/backend/app/adapters/outbound/document_processors/base.py` - Base processor
- `/backend/app/adapters/outbound/document_processors/text_processor.py` - Text processor
- `/backend/app/adapters/outbound/document_processors/markdown_processor.py` - Markdown processor
- `/backend/app/adapters/outbound/document_processors/pdf_processor.py` - PDF processor

### Modify
- `/backend/app/langgraph/tools/__init__.py` - Export RAG tool
- `/backend/app/langgraph/nodes/call_llm.py` - Add RAG tool to bind_tools
- `/backend/app/langgraph/graphs/streaming_chat_graph.py` - Add RAG tool to tools list
- `/backend/app/main.py` - Initialize RAG in lifespan
- `/backend/app/infrastructure/config/settings.py` - Add RAG configuration

## Key Risks & Considerations

### Critical Data Flow Risks

1. **Embedding Model Drift**: Documents indexed with one model, queries with another = poor results
   - Mitigation: Lock embedding model version, document in README
   
2. **ChromaDB Data Corruption**: Indexed documents become unavailable
   - Mitigation: Regular backups, verify collection integrity on startup
   
3. **Stale Knowledge**: Users get outdated information
   - Mitigation: Implement versioning, track ingestion dates, allow refresh

4. **Token Budget Overflow**: Large RAG results exceed LLM token limits
   - Mitigation: Limit chunk count to top_k=3-5, summarize before LLM

5. **Performance Degradation**: Large knowledge bases slow down searches
   - Mitigation: Test with realistic document count, implement pagination

### Bottlenecks & Optimization

| Operation | Baseline | Bottleneck | Optimization |
|-----------|----------|-----------|---------------|
| Document Ingestion | ~5-10s per doc | Embedding API calls | Batch 10-20 chunks, parallel workers |
| Query Embedding | ~200-500ms | Network latency | In-memory cache, use faster local model |
| Vector Search | ~10-50ms | Index lookup | Pre-load collection into memory |
| Result Formatting | ~50-100ms | String manipulation | Pre-format or lazy format |

## Testing Strategy

### Unit Tests
- Document processors (test chunking, splitting)
- Embeddings (test vector dimensions, consistency)
- RAG tool (mock ChromaDB, verify result format)

### Integration Tests
- RAG pipeline (load docs, verify indexing)
- LangGraph integration (RAG tool in graph)
- WebSocket streaming (tool events to frontend)

### Performance Tests
- Document ingestion latency (100, 1000, 10000 chunks)
- Query latency (<2s end-to-end)
- Concurrent tool calls (10, 50, 100 parallel)

## Summary

This analysis provides a comprehensive data flow blueprint for implementing RAG with ChromaDB in the Genesis architecture. Key takeaways:

1. **Reuse existing patterns**: Follow tool pattern (multiply/add/web_search), repository pattern (IConversationRepository), and WebSocket event infrastructure
2. **Separate concerns**: Document processing, embedding, storage, and search in distinct modules
3. **Leverage checkpointer**: AsyncMongoDBSaver automatically persists RAG tool results
4. **Monitor performance**: Identify bottlenecks in embedding API and vector search
5. **Plan for scale**: Consider batching, caching, and concurrent queries from the start

The implementation can proceed with confidence that the data flow architecture aligns with the existing Genesis patterns and clean architecture principles.
