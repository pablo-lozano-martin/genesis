# LLM Integration Analysis: ChromaDB RAG Tool

## Request Summary

Add a ChromaDB-based Retrieval-Augmented Generation (RAG) tool to the existing tool-calling infrastructure. This tool will enable the LLM to search a shared knowledge base using vector similarity and return relevant documents to augment the model's responses. The tool integrates into the existing LangGraph streaming architecture and must follow the established tool patterns and registration mechanisms.

## Relevant Files & Modules

### Tool Implementation Files
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/add.py` - Simple arithmetic tool (reference implementation)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/multiply.py` - Simple arithmetic tool (reference implementation)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/web_search.py` - External API integration tool (reference for async patterns)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/__init__.py` - Tool module exports and registration

### Graph & LLM Integration Files
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Primary graph with tool registration (uses ToolNode, tools_condition)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Alternative graph without web_search (reference)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - LLM invocation node (tool binding happens here)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - ConversationState schema (MessagesState-based)

### LLM Provider Files
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - ILLMProvider interface (defines bind_tools contract)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/openai_provider.py` - OpenAI implementation with bind_tools
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/anthropic_provider.py` - Anthropic implementation with bind_tools
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/provider_factory.py` - Provider factory pattern

### WebSocket & Streaming Files
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - Tool execution event handling (on_tool_start, on_tool_end)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py` - Tool message types (ServerToolStartMessage, ServerToolCompleteMessage)

### Configuration Files
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py` - Application settings (for ChromaDB configuration)

### Test Files
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_tools.py` - Tool unit tests (reference for testing patterns)

## Current Integration Overview

### Provider Abstraction Pattern

The project uses a hexagonal architecture with provider abstraction:

**ILLMProvider Interface** (port):
```
backend/app/core/ports/llm_provider.py:
  - generate(messages) -> BaseMessage (async)
  - stream(messages) -> AsyncGenerator[str] (async)
  - get_model_name() -> str (async)
  - bind_tools(tools, **kwargs) -> ILLMProvider
```

**Provider Implementations** (adapters):
- OpenAI via `langchain_openai.ChatOpenAI`
- Anthropic via `langchain_anthropic.ChatAnthropic`
- Google Gemini via `langchain_google_genai.ChatGoogleGenerativeAI`
- Ollama via `langchain_community.chat_models.ChatOllama`

All providers implement the same interface and support LangChain's `bind_tools()` method for tool calling.

### Tool Architecture

Tools follow a simple, consistent pattern:

**Tool Definition**:
- Plain Python functions with type hints and docstrings
- Located in `/backend/app/langgraph/tools/`
- Each tool is a separate file with clear responsibility
- Signature: `async def tool_name(param: Type) -> ReturnType`

**Tool Registration**:
1. **Graph Registration** (`streaming_chat_graph.py`):
   - Tools imported into `create_streaming_chat_graph()`
   - Added to tools list: `tools = [multiply, add, web_search]`
   - Passed to `ToolNode(tools)` as graph node
   - Registered via conditional edges with `tools_condition`

2. **LLM Node Registration** (`call_llm.py`):
   - Tools imported into `call_llm()` node function
   - Bound to LLM provider: `llm_provider_with_tools = llm_provider.bind_tools(tools, parallel_tool_calls=False)`
   - Used to invoke LLM: `ai_message = await llm_provider_with_tools.generate(messages)`

3. **Tool Module Exports** (`tools/__init__.py`):
   - Tools exported via `__all__` list for visibility
   - Currently: `["multiply", "add"]` (web_search not exposed due to import issue)

### Graph Flow with Tool Execution

```
START
  ↓
process_input (validates messages in state)
  ↓
call_llm (invokes LLM with bound tools)
  ├─ If tool calls: → tools (ToolNode executes all tool calls) → call_llm (loop)
  └─ If no tool calls: → END
```

**Key Flow Details**:
- LLM invocation uses `llm_provider_with_tools.generate(messages)` which returns AIMessage
- AIMessage may contain `tool_calls` attribute (list of ToolCall objects)
- `tools_condition` from langgraph checks for tool_calls and routes accordingly
- `ToolNode` automatically handles tool execution, converting results to ToolMessages
- Loop continues until LLM stops calling tools

### Streaming & WebSocket Integration

Tool execution is streamed to WebSocket clients via `graph.astream_events()`:

**Event Types**:
- `on_chat_model_stream` - LLM tokens (ServerTokenMessage)
- `on_chat_model_end` - LLM finish, extract tool_calls from AIMessage
- `on_tool_start` - Tool begins (ServerToolStartMessage with tool_name, tool_input)
- `on_tool_end` - Tool finishes (ServerToolCompleteMessage with tool_name, tool_result)

**Event Handling** (`websocket_handler.py`):
- Caches `current_tool_call` when AIMessage contains tool_calls
- Emits TOOL_START event when tool executes
- Emits TOOL_COMPLETE event when tool finishes
- Resets cached tool_call for next iteration

### Message State Management

- Uses LangGraph's native `MessagesState` (converted to `ConversationState`)
- Messages are `BaseMessage` types from LangChain: HumanMessage, AIMessage, ToolMessage
- HumanMessage created in WebSocket handler before graph invocation
- AIMessage generated by LLM with optional `tool_calls` and `tool_call_id`
- ToolMessage generated by ToolNode with tool execution results

## Impact Analysis

### Components Affected by ChromaDB RAG Tool

1. **Tool Implementation** (NEW):
   - Create `/backend/app/langgraph/tools/rag_search.py`
   - Implement async function with ChromaDB client integration
   - Handle vector embedding and similarity search

2. **Tool Registration** (MODIFY):
   - Update `/backend/app/langgraph/graphs/streaming_chat_graph.py` - add to tools list
   - Update `/backend/app/langgraph/nodes/call_llm.py` - add to tools list
   - Update `/backend/app/langgraph/tools/__init__.py` - export new tool

3. **Configuration** (MODIFY):
   - Add ChromaDB connection settings to `/backend/app/infrastructure/config/settings.py`
   - May need collection name, embedding model, persistence path

4. **Dependencies** (ADD):
   - Add `chromadb` package to requirements
   - May need embedding model (e.g., `langchain-openai` embeddings, `sentence-transformers`)

5. **No Changes Required**:
   - LLM provider abstraction - fully compatible with bind_tools pattern
   - WebSocket streaming - ToolNode handles events automatically
   - State management - tool results become ToolMessages naturally

## LLM Integration Recommendations

### 1. Tool Function Signature

**REQUIRED Pattern** (matches LangChain tool calling):
```python
# File: backend/app/langgraph/tools/rag_search.py

async def rag_search(query: str) -> str:
    """
    Search the shared knowledge base for relevant documents.

    Uses vector similarity to find documents matching the query.
    The LLM can use this to augment its responses with retrieved context.

    Args:
        query: The search query string to find relevant documents

    Returns:
        A string containing the top matching documents formatted for LLM consumption
    """
    # Implementation
    pass
```

**Critical Patterns**:
- Function must be async-compatible (can be sync, but async for I/O ops)
- Parameter type hints are required (LLM tool binding uses them for schema)
- Return type must be serializable to string (LLM needs to understand the output)
- Docstring is critical (becomes the tool description in LLM's tool manifest)
- Function name becomes the tool name (lowercase, no spaces)

### 2. Tool Registration Pattern

**In streaming_chat_graph.py** (line 43):
```python
from app.langgraph.tools.rag_search import rag_search

def create_streaming_chat_graph(checkpointer: AsyncMongoDBSaver):
    # ...
    tools = [multiply, add, web_search, rag_search]  # ADD HERE
    graph_builder.add_node("tools", ToolNode(tools))
    # ...
```

**In call_llm.py** (line 36):
```python
from app.langgraph.tools.rag_search import rag_search

async def call_llm(state: ConversationState, config: RunnableConfig) -> dict:
    # ...
    tools = [multiply, add, web_search, rag_search]  # ADD HERE
    llm_provider_with_tools = llm_provider.bind_tools(tools, parallel_tool_calls=False)
    # ...
```

**In tools/__init__.py**:
```python
from .rag_search import rag_search

__all__ = ["multiply", "add", "rag_search"]  # ADD HERE
```

**Registration Order**: Tools appear in this order in both locations. The order determines tool priority in LLM's tool manifest, but functionally all tools are equivalent.

### 3. ChromaDB Integration Pattern

**Recommended Architecture**:
```
Tool Function (rag_search)
  ↓
ChromaDB Client Singleton/Service
  ↓
Vector Store (ChromaDB collection)
  ↓
Vector Embeddings (external API or local model)
```

**Implementation Considerations**:
1. **Embedding Model**:
   - Can use OpenAI embeddings via `langchain_openai.OpenAIEmbeddings`
   - Or use open-source model via `langchain_community.embeddings.HuggingFaceEmbeddings`
   - Should be configured, not hardcoded

2. **ChromaDB Client**:
   - Create singleton or service class to manage connection
   - Can be persistent (file-based) or ephemeral (in-memory)
   - Connection should be initialized at application startup

3. **Collection Management**:
   - Each knowledge base could be a separate collection
   - Pre-populate with documents during initialization
   - Handle embedding at document ingestion time

4. **Error Handling**:
   - Tool should gracefully handle ChromaDB unavailability
   - Return meaningful error messages that the LLM can understand
   - Log errors for debugging

### 4. Configuration Management

**Add to settings.py**:
```python
# ChromaDB Settings
chromadb_collection_name: str = "shared_knowledge_base"
chromadb_persist_directory: Optional[str] = None  # None = ephemeral
chromadb_embedding_model: str = "openai"  # or "huggingface"
chromadb_similarity_threshold: float = 0.5
chromadb_top_k_results: int = 3
```

**Environment Variables**:
```
CHROMADB_COLLECTION_NAME=shared_knowledge_base
CHROMADB_PERSIST_DIRECTORY=/path/to/data
CHROMADB_EMBEDDING_MODEL=openai
CHROMADB_SIMILARITY_THRESHOLD=0.5
CHROMADB_TOP_K_RESULTS=3
```

### 5. Tool Function Implementation Guidance

**Basic Structure**:
```python
# backend/app/langgraph/tools/rag_search.py
# ABOUTME: RAG vector search tool for querying shared knowledge base
# ABOUTME: Uses ChromaDB for semantic search with vector embeddings

from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger
import chromadb

logger = get_logger(__name__)

# ChromaDB client (singleton pattern - initialize once)
_chroma_client = None

def get_chroma_client():
    """Get or initialize ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        # Initialize with persistence if configured
        if settings.chromadb_persist_directory:
            _chroma_client = chromadb.PersistentClient(
                path=settings.chromadb_persist_directory
            )
        else:
            _chroma_client = chromadb.EphemeralClient()
    return _chroma_client

async def rag_search(query: str) -> str:
    """
    Search the shared knowledge base for relevant documents.

    Args:
        query: The search query string

    Returns:
        Formatted string of top matching documents
    """
    try:
        client = get_chroma_client()
        collection = client.get_collection(
            name=settings.chromadb_collection_name
        )

        # Query by text similarity (ChromaDB handles embedding)
        results = collection.query(
            query_texts=[query],
            n_results=settings.chromadb_top_k_results
        )

        # Format results for LLM consumption
        if not results or not results["documents"]:
            return "No relevant documents found in knowledge base."

        formatted = "\n\n".join([
            f"Document {i+1}: {doc}"
            for i, doc in enumerate(results["documents"][0])
        ])

        logger.info(f"RAG search found {len(results['documents'][0])} documents")
        return formatted

    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        return f"Knowledge base search failed: {str(e)}"
```

### 6. LangGraph Tool Binding Details

**How bind_tools Works**:
1. Tool function is introspected (name, docstring, parameter types)
2. JSON schema is generated from function signature
3. Provider API is called with tool definitions
4. LLM includes tools in its prompt/system message
5. LLM can generate tool_calls in response
6. ToolNode routes execution to matching function

**Example Tool Binding Chain**:
```
rag_search function
  ↓ (inspection)
Tool Schema: {
  "type": "function",
  "function": {
    "name": "rag_search",
    "description": "Search the shared knowledge base for relevant documents...",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "The search query string"
        }
      },
      "required": ["query"]
    }
  }
}
  ↓ (provider.bind_tools)
OpenAI/Anthropic API call
  ↓
LLM generates response with tool_calls
  ↓
ToolNode executes rag_search(query=...)
  ↓
ToolMessage added to message history
```

### 7. Streaming and Frontend Integration

**Tool Events Flow**:
```
LLM Response: AIMessage with tool_calls=[{"name": "rag_search", "args": {"query": "..."}}]
  ↓
on_chat_model_end event (cache tool_call)
  ↓
on_tool_start event (emit ServerToolStartMessage to WebSocket)
  ↓
ToolNode executes rag_search()
  ↓
on_tool_end event (emit ServerToolCompleteMessage with result)
  ↓
Tool result becomes ToolMessage
  ↓
call_llm node invoked again with updated message history
```

**WebSocket Message Format** (already defined, no changes needed):
```python
# ServerToolStartMessage
{
  "type": "tool_start",
  "tool_name": "rag_search",
  "tool_input": "{\"query\": \"machine learning basics\"}",
  "timestamp": "2024-10-26T..."
}

# ServerToolCompleteMessage
{
  "type": "tool_complete",
  "tool_name": "rag_search",
  "tool_result": "Document 1: ...\n\nDocument 2: ...",
  "timestamp": "2024-10-26T..."
}
```

## Implementation Guidance

### Step-by-Step Integration

1. **Create Tool Implementation**
   - Create `/backend/app/langgraph/tools/rag_search.py`
   - Implement `rag_search(query: str) -> str` function
   - Add ChromaDB client initialization logic
   - Follow docstring and type hint patterns from `add.py` and `web_search.py`

2. **Update Tool Registration in Graph**
   - Import `rag_search` in `streaming_chat_graph.py`
   - Add to `tools` list before `ToolNode` creation
   - Verify order matches other graph files

3. **Update Tool Registration in LLM Node**
   - Import `rag_search` in `call_llm.py`
   - Add to `tools` list before `bind_tools()` call
   - Same order as streaming_chat_graph.py

4. **Export Tool from Module**
   - Add import and export in `tools/__init__.py`
   - Add to `__all__` list

5. **Configure ChromaDB Settings**
   - Add configuration variables to `settings.py`
   - Define environment variable names
   - Provide sensible defaults

6. **Initialize ChromaDB**
   - Create service/factory for ChromaDB client
   - Initialize at application startup (in main app initialization)
   - Handle persistence vs ephemeral configuration

7. **Add Tests**
   - Unit test: Tool function with mock ChromaDB
   - Integration test: Tool in graph with real ChromaDB
   - WebSocket test: Tool events flow to frontend
   - Test error cases: ChromaDB unavailable, no results, etc.

8. **Document Knowledge Base**
   - Add guide for populating knowledge base
   - Document expected document format
   - Explain embedding and search configuration

### Testing Strategy

**Unit Tests** (test_rag_search.py):
```python
# Test tool function directly
# Mock ChromaDB client
# Verify query handling and result formatting
# Test error cases
```

**Integration Tests** (test_rag_search_in_graph.py):
```python
# Create graph with rag_search tool
# Invoke graph with query that triggers rag_search
# Verify tool execution in message history
# Check tool result is included in final response
```

**WebSocket Tests** (test_rag_search_events.py):
```python
# Stream graph execution
# Verify on_tool_start event
# Verify on_tool_end event
# Verify ServerToolStartMessage sent to client
# Verify ServerToolCompleteMessage sent with results
```

**Error Handling Tests**:
```python
# ChromaDB unavailable
# No matching documents
# Invalid query
# Malformed search results
```

## Provider-Specific Considerations

### OpenAI (Primary Provider)
- `bind_tools()` generates proper function schemas
- Tool calling is reliable and stable
- Supports `parallel_tool_calls=False` configuration
- Token counting includes tool definitions

### Anthropic (Claude)
- `bind_tools()` generates proper function schemas
- Tool calling follows Claude's tool_use format
- Same `parallel_tool_calls=False` pattern
- Well-documented tool calling behavior

### Google Gemini
- Supports tool binding via LangChain
- May have different schema generation
- Verify tool calling behavior with real API

### Ollama
- Local model, tool support depends on model capabilities
- May not support advanced tool calling
- Test with actual models before deployment

**Abstraction Benefit**: The ILLMProvider interface means the RAG tool works with all providers automatically. No provider-specific code needed in the tool itself.

## Risk & Considerations

### Performance
1. **Vector Search Latency**: ChromaDB similarity search adds latency
   - Consider caching frequently used queries
   - Monitor search time and set timeout expectations
   - Large knowledge bases may need optimization (indexing, batching)

2. **Token Count**: Retrieved documents consume tokens
   - Limit number of results (currently `top_k_results=3`)
   - Consider document length and token limits
   - May affect overall response latency

3. **Embedding Costs**: If using OpenAI embeddings
   - Embedding every user query costs tokens
   - Consider caching or batch processing
   - Monitor monthly costs

### Knowledge Base
1. **Document Format**: Ensure consistent formatting
   - Clear document structure
   - Proper metadata and tagging
   - Regular updates and maintenance

2. **Embedding Quality**: Different embedding models give different results
   - Open-source models may be less accurate than OpenAI
   - Trade-off between cost and accuracy
   - Test with real queries

3. **Staleness**: Knowledge base may become outdated
   - Implement update mechanism
   - Monitor relevance over time
   - Archive old documents appropriately

### Error Handling
1. **ChromaDB Unavailability**: Tool should fail gracefully
   - Return meaningful error message LLM can understand
   - Don't crash the entire chat
   - Log details for debugging

2. **Empty Results**: Handle searches with no matches
   - Return helpful message ("No relevant documents found")
   - Let LLM respond based on training data
   - Consider alternative search strategies

### Rate Limiting
1. **If using external embeddings**: May hit rate limits
   - Implement retry logic with exponential backoff
   - Queue requests if necessary
   - Monitor API usage

2. **ChromaDB local access**: Generally unlimited
   - Ensure file system I/O doesn't bottleneck
   - Test with expected query volume

## Data Flow Diagram

```
User Message (WebSocket)
  ↓
process_input Node (validation)
  ↓
call_llm Node
  ├─ Bind tools to LLM: rag_search + other tools
  ├─ Invoke LLM: llm_provider_with_tools.generate(messages)
  └─ Return: AIMessage [possibly with tool_calls]
  ↓
tools_condition (check for tool_calls)
  ├─ YES: Route to ToolNode
  └─ NO: Route to END
  ↓
ToolNode (if tool called)
  ├─ Extract tool_calls from AIMessage
  ├─ For rag_search call:
  │  ├─ Parse query argument
  │  ├─ ChromaDB.query(query) → retrieve documents
  │  ├─ Format documents as string
  │  └─ Return as ToolMessage
  └─ Return: message state with ToolMessage
  ↓
Loop back to call_llm with updated message history
  ├─ Messages now include: HumanMessage + AIMessage + ToolMessage
  ├─ LLM can respond based on retrieved documents
  └─ Generate final AIMessage (no more tool_calls)
  ↓
END
```

## Summary

The ChromaDB RAG tool integrates seamlessly into the existing LangGraph tool-calling infrastructure by:

1. **Following Tool Patterns**: Simple async function with type hints and docstring
2. **Leveraging Provider Abstraction**: Works with all ILLMProvider implementations via bind_tools
3. **Using LangGraph ToolNode**: Automatically handles execution and message routing
4. **Supporting Streaming**: Tool execution events are streamed to WebSocket clients
5. **Maintaining State**: Tool results become ToolMessages in conversation history

The implementation requires minimal changes to existing code (only imports and tool list updates in two places) and benefits from the established infrastructure for tool management, streaming, and provider abstraction.
