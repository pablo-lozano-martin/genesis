# Testing Coverage Analysis: ChromaDB RAG Tool

## Request Summary

Implement a ChromaDB RAG (Retrieval-Augmented Generation) tool that allows the AI to search a shared knowledge base during conversations. This tool integrates with the existing LangGraph tool-calling architecture and enables semantic search across indexed documents.

## Relevant Files & Modules

### Files to Examine

#### Test Files (Existing)
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_tools.py` - Unit tests for simple tools (add, multiply)
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/conftest.py` - Shared pytest fixtures (mock repositories, mock LLM)
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_conversation_api.py` - Integration tests for conversation endpoints
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_auth_api.py` - Integration tests for auth flow
- `/Users/pablolozano/Mac Projects August/genesis/backend/backend/pytest.ini` - Pytest configuration with markers and async mode

#### Tool Implementation Files (Existing)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/__init__.py` - Tool exports
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/add.py` - Simple add tool (reference)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/multiply.py` - Simple multiply tool (reference)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/web_search.py` - External API tool (reference for mocking pattern)

#### LangGraph Integration Files (Existing)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Tool registration and graph building
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - Tool binding in LLM node
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - Conversation state definition
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket chat handler with tool execution events

#### Port/Interface Files (Existing)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - ILLMProvider interface (references bind_tools pattern)

#### Architecture Documentation (Existing)
- `/Users/pablolozano/Mac Projects August/genesis/doc/general/ARCHITECTURE.md` - Full architecture reference with tool-calling section

### Key Test Cases & Functions

#### Existing Unit Test Functions
- `TestAddTool.test_add_positive_numbers()` - Simple tool unit test pattern
- `TestAddTool.test_add_with_zero()` - Edge case handling
- `TestMultiplyTool.test_multiply_negative_numbers()` - Sign handling
- All tests in test_tools.py follow: Direct function invocation -> Assert result pattern

#### Existing Integration Test Functions
- `TestConversationAPI.test_create_conversation()` - Create resource with auth
- `TestConversationAPI.test_list_conversations()` - List with auth verification
- `TestConversationAPI.test_unauthorized_access()` - Auth guard testing
- `TestAuthAPI.test_register_user_success()` - Happy path flow
- `TestAuthAPI.test_login_flow()` - Multi-step integration flow

#### Existing Fixture Functions in conftest.py
- `app()` - FastAPI application instance
- `client()` - AsyncClient for HTTP testing
- `mock_user_repository()` - AsyncMock for user operations
- `mock_conversation_repository()` - AsyncMock for conversation operations
- `mock_message_repository()` - AsyncMock for message operations
- `mock_llm_provider()` - AsyncMock with `generate()` and `stream()` methods
- `sample_user()` - User domain object for testing
- `sample_user_create()` - User creation data
- `sample_conversation()` - Conversation domain object
- `auth_service()` - AuthService instance

## Current Testing Overview

### Unit Tests

**Location**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/`

**Current Coverage**:
- `test_tools.py`: Simple mathematical tools (add, multiply) with basic arithmetic operations
- `test_llm_providers.py`: LLMProviderFactory tests using `@patch` decorator with mock settings
- `test_use_cases.py`: Use case logic with mocked repositories (AsyncMock)
- `test_domain_models.py`: Domain model validation
- `test_dual_database.py`: Database connection handling
- `test_websocket_schemas.py`: Message schema validation

**Testing Pattern**:
- Direct function invocation with assertions
- Mocking via `unittest.mock.AsyncMock` and `patch`
- Minimal dependencies, maximum isolation
- Test classes organize related tests with `Test*` prefix
- Async tests use `@pytest.mark.asyncio` decorator

### Integration Tests

**Location**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/`

**Current Coverage**:
- `test_conversation_api.py`: Full conversation lifecycle (create, read, update, delete, list)
- `test_auth_api.py`: User registration, login, token generation flows

**Testing Pattern**:
- HTTP requests via `AsyncClient` against running FastAPI app
- Real authentication flows (password hashing, token generation)
- Resource ownership verification (403 Forbidden for other users)
- Validation error handling (422 Unprocessable Entity)
- Database state verification after operations
- Session-scoped random ID for test isolation

### End-to-End Tests

**Current Status**: No dedicated e2e test files found for WebSocket/streaming chat

**Missing Opportunities**:
- WebSocket chat flow with tool execution
- Streaming token reception
- Tool execution in message context
- Full conversation lifecycle through WebSocket

### Test Utilities & Fixtures

**Fixture Scope**:
- Session-scoped: `setup_test_ids()` - Provides `pytest.random_id` for test isolation
- Function-scoped: Most fixtures (default scope)
- Async fixtures: `app()` and `client()` use async generators

**Mock Pattern**:
- AsyncMock for repository methods
- patch() decorator for settings/configuration
- Simple return_value assignment for mock results
- Mock LLM provider has `.generate()` and `.stream()` methods

**Test Isolation**:
- `pytest.random_id` appended to emails/usernames to prevent collision across test runs
- Each test class has isolated fixtures via function scope
- Integration tests create fresh resources per test

## Coverage Analysis

### Well-Tested Components

1. **Simple Tool Functions** (test_tools.py)
   - Pattern established for basic tool testing
   - Covers happy path and edge cases
   - Clear naming: `test_add_positive_numbers()`, `test_add_with_zero()`

2. **Authentication & Authorization** (test_auth_api.py, test_conversation_api.py)
   - User creation with validation
   - Login flow with token generation
   - Unauthorized access prevention (401, 403)
   - Conversation ownership checks

3. **API Endpoints** (test_*_api.py)
   - CRUD operations
   - Validation error responses (422)
   - Resource not found (404)
   - Success response structures

### Undertested Components

1. **Tool Execution in LangGraph Context**
   - No tests for tool binding via `bind_tools()`
   - No tests for `tools_condition` edge routing
   - No tests for ToolNode execution
   - No tests for tool result handling in conversation

2. **LangGraph Streaming & Checkpointing**
   - No tests for `graph.astream_events()` token streaming
   - No tests for message checkpointing
   - No tests for state persistence across invocations
   - No tests for conversation thread_id to conversation.id mapping

3. **External Service Integration**
   - `web_search` tool exists but not tested
   - No tests for mocking external APIs (DuckDuckGo in web_search.py)
   - No pattern established for tool error handling

4. **WebSocket Chat Flow**
   - No e2e tests for real-time message streaming
   - No tests for tool execution event messages (TOOL_START, TOOL_COMPLETE)
   - No tests for connection handling/disconnection
   - No tests for concurrent message handling

### Gaps for RAG Tool Implementation

1. **Vector Database (ChromaDB) Integration**
   - Need mocking pattern for ChromaDB operations
   - Need tests for semantic search execution
   - Need tests for document retrieval ranking
   - Need tests for empty search results

2. **Tool Function Definition**
   - Need unit tests for RAG search function
   - Need tests for query validation
   - Need tests for result formatting
   - Need tests for error conditions (DB offline, corrupted index)

3. **Knowledge Base Management**
   - Tests for document indexing
   - Tests for index updates/deletes
   - Tests for index persistence
   - Tests for concurrent index access

4. **LangGraph Integration**
   - Tests for RAG tool binding in call_llm node
   - Tests for tool selection (when does LLM choose RAG vs other tools)
   - Tests for result integration into LLM context
   - Tests for RAG + other tools in same conversation

## Testing Recommendations

### Proposed Unit Tests

**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_rag_tool.py`

**Test Cases**:

1. **Basic Search Operations**
   ```
   test_search_knowledge_base_found()
   - Query: "python programming"
   - Assert: Returns list of relevant documents with scores
   - Assert: Results are sorted by relevance (descending score)
   ```

2. **Empty Search Results**
   ```
   test_search_knowledge_base_no_results()
   - Query: "xyz nonsense query that matches nothing"
   - Assert: Returns empty list (no exception)
   - Assert: Graceful degradation
   ```

3. **Query Validation**
   ```
   test_search_empty_query()
   - Query: ""
   - Assert: Raises ValueError with clear message
   ```

   ```
   test_search_very_long_query()
   - Query: "x" * 10000
   - Assert: Either truncates or raises with max length error
   ```

4. **Special Characters & Encoding**
   ```
   test_search_unicode_query()
   - Query: "日本語 中文 العربية"
   - Assert: Handles multi-language queries correctly
   ```

5. **Document Ranking & Filtering**
   ```
   test_search_results_sorted_by_score()
   - Assert: First result always has highest score
   - Assert: Scores decrease monotonically
   ```

   ```
   test_search_with_min_score_threshold()
   - Query with score_threshold parameter
   - Assert: Filters out low-relevance results
   ```

6. **Error Conditions**
   ```
   test_search_database_connection_error()
   - Mock ChromaDB to raise connection error
   - Assert: Tool raises ChromaDBError with context
   - Assert: Error message helps debugging
   ```

   ```
   test_search_corrupted_index()
   - Mock ChromaDB returning invalid embeddings
   - Assert: Tool handles gracefully
   ```

### Proposed Integration Tests

**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_rag_adapter.py`

**Test Cases**:

1. **ChromaDB Adapter Initialization**
   ```
   test_chromadb_adapter_connect()
   - Verify connection to actual ChromaDB instance
   - Assert: Collection exists/created
   - Assert: Metadata preserved
   ```

2. **Document Indexing**
   ```
   test_index_document()
   - Insert document: {"id": "doc1", "content": "...", "metadata": {...}}
   - Assert: Document retrievable via search
   - Assert: Metadata searchable
   ```

   ```
   test_update_document()
   - Index document, then update content
   - Assert: Old content no longer found
   - Assert: New content searchable
   ```

   ```
   test_delete_document()
   - Index document, then delete
   - Assert: Search no longer returns it
   ```

3. **Batch Operations**
   ```
   test_batch_index_documents()
   - Index 100 documents
   - Assert: All retrievable
   - Assert: Performance acceptable (< 5 seconds for 100 docs)
   ```

4. **Search Quality**
   ```
   test_semantic_search_accuracy()
   - Index documents about "cats"
   - Query: "feline animals"
   - Assert: Cat documents rank highest
   - Assert: Irrelevant documents rank lower
   ```

5. **Metadata Filtering**
   ```
   test_search_with_metadata_filter()
   - Index documents with category metadata
   - Search with where={"category": "python"}
   - Assert: Only Python docs returned
   ```

### Proposed End-to-End Tests

**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/e2e/test_rag_chat_flow.py`

**Note**: This requires WebSocket e2e testing framework setup (currently missing)

**Test Cases**:

1. **Simple RAG Query in Chat**
   ```
   test_rag_tool_executed_in_conversation()
   - Create conversation via REST API
   - Send message: "What do we know about authentication?"
   - Listen for WebSocket events:
     - TOOL_START with tool="rag_search"
     - TOOL_COMPLETE with search results
     - AI response incorporating search results
   - Assert: All three events received in order
   - Assert: AI response references search results
   ```

2. **RAG + Other Tools**
   ```
   test_rag_with_add_tool()
   - Message: "Search docs and add 5+3"
   - Assert: Both tools executed
   - Assert: Results combined in final response
   ```

3. **Knowledge Base Scoping**
   ```
   test_rag_searches_correct_knowledge_base()
   - Create two conversations
   - Add different knowledge bases to each
   - Query in first conversation
   - Assert: Results only from first knowledge base
   ```

4. **Error Handling in Chat**
   ```
   test_rag_search_fails_gracefully()
   - Mock ChromaDB to fail
   - Send message requiring RAG
   - Assert: UI receives error message
   - Assert: Chat doesn't crash, user can retry
   - Assert: Error is user-friendly (not stack trace)
   ```

5. **Empty Knowledge Base**
   ```
   test_rag_search_empty_knowledge_base()
   - No documents indexed
   - Send message requiring RAG
   - Assert: Tool returns empty results
   - Assert: LLM responds about no results found
   - Assert: Conversation continues normally
   ```

### Test Data & Fixtures

**New Fixtures Needed** (add to `/Users/pablolozano/Mac Projects August/genesis/backend/tests/conftest.py`):

1. **Mock ChromaDB Collection**
   ```python
   @pytest.fixture
   def mock_chromadb_collection():
       """Mock ChromaDB collection for unit tests."""
       mock = AsyncMock()
       mock.query = AsyncMock(return_value={
           "ids": [["doc1", "doc2"]],
           "distances": [[0.1, 0.3]],  # Lower is more relevant
           "documents": [["Content 1", "Content 2"]],
           "metadatas": [[{"source": "file1.txt"}, {"source": "file2.txt"}]]
       })
       return mock
   ```

2. **Sample Documents**
   ```python
   @pytest.fixture
   def sample_documents():
       """Sample documents for RAG testing."""
       return [
           {
               "id": "auth-doc-1",
               "content": "JWT tokens provide stateless authentication...",
               "source": "docs/auth.md",
               "category": "security"
           },
           {
               "id": "db-doc-1",
               "content": "MongoDB uses BSON format for documents...",
               "source": "docs/database.md",
               "category": "database"
           }
       ]
   ```

3. **Real ChromaDB for Integration Tests**
   ```python
   @pytest.fixture(scope="function")
   async def chromadb_instance():
       """Real ChromaDB instance for integration tests (ephemeral)."""
       import chromadb
       client = chromadb.EphemeralClient()
       collection = client.get_or_create_collection(
           name="test_knowledge_base",
           metadata={"hnsw:space": "cosine"}
       )
       yield collection
       # Cleanup happens automatically with ephemeral client
   ```

4. **RAG Tool Instance**
   ```python
   @pytest.fixture
   def rag_tool(mock_chromadb_collection):
       """RAG tool instance with mocked ChromaDB."""
       from app.langgraph.tools.rag_search import RAGSearchTool
       return RAGSearchTool(collection=mock_chromadb_collection)
   ```

### Test Marker Organization

Add new markers to `/Users/pablolozano/Mac Projects August/genesis/backend/pytest.ini`:

```ini
[pytest]
markers =
    unit: Unit tests (isolated, no external deps)
    integration: Integration tests (real db, mocked externals)
    e2e: End-to-end tests (full system flow)
    rag: RAG tool specific tests
    slow: Slow running tests (> 5 seconds)
    chromadb: Tests requiring ChromaDB
```

Usage in tests:
```python
@pytest.mark.unit
@pytest.mark.rag
class TestRAGTool:
    ...

@pytest.mark.integration
@pytest.mark.chromadb
class TestRAGAdapter:
    ...
```

## Implementation Guidance

### Phase 1: Unit Test Foundation

1. **Create tool function** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/rag_search.py`):
   - Simple synchronous function: `def rag_search(query: str) -> str`
   - Returns formatted search results or empty string
   - Raises specific exceptions for error cases

2. **Create unit tests** (`/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_rag_tool.py`):
   - Mock ChromaDB collection
   - Test all happy path cases
   - Test all error conditions
   - Test boundary conditions (empty query, very long query)

3. **Fixtures in conftest.py**:
   - Add `mock_chromadb_collection` fixture
   - Add `sample_documents` fixture
   - Add `rag_tool` fixture with mocked collection

### Phase 2: Integration Test Foundation

1. **Create adapter** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/vector_stores/chromadb_adapter.py`):
   - Implements IVectorStore port (must create)
   - Manages actual ChromaDB operations
   - Handles connection pooling/lifecycle

2. **Create port** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/vector_store.py`):
   - Abstract interface for vector database operations
   - Methods: `search()`, `add()`, `delete()`, `update()`
   - Used by both real ChromaDB and mock implementations

3. **Create integration tests** (`/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_rag_adapter.py`):
   - Ephemeral ChromaDB instance per test
   - Real document indexing
   - Real semantic search
   - Metadata filtering

### Phase 3: LangGraph Integration

1. **Register RAG tool** in `streaming_chat_graph.py`:
   - Import `rag_search` function
   - Add to tools list
   - Tool automatically converted to LangChain schema

2. **Tool tests in LangGraph context**:
   - Create `test_rag_in_call_llm_node()` in new `tests/unit/test_langgraph_tools.py`
   - Mock LLM to select RAG tool
   - Verify tool execution path
   - Verify result integration

3. **Streaming integration**:
   - Test TOOL_START and TOOL_COMPLETE events
   - Verify WebSocket message formats
   - Test timeout handling

### Phase 4: End-to-End Tests (Post MVP)

1. **WebSocket e2e tests** (requires test infrastructure):
   - Real conversation with RAG tool usage
   - Real streaming responses
   - Tool execution events
   - Error scenarios

## Risks and Considerations

### Testing Risks

1. **ChromaDB Mocking Complexity**
   - Risk: Mock doesn't match real ChromaDB behavior
   - Mitigation: Unit tests use mocks, integration tests use real ephemeral instance
   - Mitigation: Document mock interface assumptions

2. **Async/Await Complexity**
   - Risk: Subtle timing issues in concurrent tool execution
   - Mitigation: Use `@pytest.mark.asyncio` consistently
   - Mitigation: Test with multiple concurrent requests

3. **Search Quality Verification**
   - Risk: Hard to assert "correct" results without golden dataset
   - Mitigation: Use known documents with predictable similarities
   - Mitigation: Test ranking order, not absolute relevance

### Implementation Risks

1. **Vector Embedding Consistency**
   - Risk: Different embedding models give different results
   - Mitigation: Fix embedding model in config
   - Mitigation: Document expected model version
   - Mitigation: Test with same model version in all environments

2. **Knowledge Base Scope**
   - Risk: Mixing documents from multiple knowledge bases
   - Mitigation: Add collection per conversation or per knowledge base
   - Mitigation: Test metadata filtering
   - Mitigation: Verify isolation in integration tests

3. **Performance Under Load**
   - Risk: Slow search with large knowledge bases
   - Mitigation: Add benchmark tests
   - Mitigation: Index optimization in integration tests
   - Mitigation: Monitor search latency in e2e tests

### Coverage Gaps to Address

1. **No E2E WebSocket Testing Infrastructure**
   - Current: Only HTTP integration tests
   - Needed: WebSocket client for e2e tests
   - Consider: Pytest plugin for WebSocket (pytest-asyncio-ws)

2. **No Tool Execution Tests in Graph Context**
   - Current: Tools tested in isolation
   - Needed: Tests for `bind_tools()` and `tools_condition`
   - Needed: Tests for ToolMessage creation/handling

3. **No Streaming Tests**
   - Current: No tests for `graph.astream_events()`
   - Needed: Event stream capture/assertion
   - Needed: Token streaming verification

## Testing Strategy

### Test Pyramid for RAG Tool

```
        E2E Tests (5% - full chat flows)
       /                              \
      Integration Tests (25%)
     /    (real chromadb, mocked llm)    \
Unit Tests (70%)
(mocked chromadb, isolated tool function)
```

### Coverage Goals

- **Unit Tests**: 95%+ code coverage (lines and branches)
- **Integration Tests**: 80%+ coverage of adapter code
- **E2E Tests**: All critical user workflows
- **Overall Target**: 85%+ combined coverage

### Continuous Integration Approach

1. **Unit Tests**: Run on every commit (fast, no deps)
2. **Integration Tests**: Run on PR (needs ephemeral DB)
3. **E2E Tests**: Run on main branch (slow, full system)
4. **Performance Tests**: Run nightly (benchmark search latency)

### Testing Best Practices Applied

1. **Arrange-Act-Assert Pattern**
   ```python
   def test_example():
       # Arrange: Setup test data and mocks
       mock_collection = setup_mock_chromadb()

       # Act: Execute the function under test
       results = rag_search("query", mock_collection)

       # Assert: Verify behavior
       assert len(results) == expected_count
   ```

2. **Isolation Between Tests**
   - Function-scoped fixtures (reset after each test)
   - Ephemeral ChromaDB (no persistent state)
   - Random IDs for conversations (avoid collisions)

3. **Clear Test Naming**
   - `test_<function>_<condition>_<expected_outcome>()`
   - Example: `test_rag_search_empty_query_raises_value_error()`

4. **Comprehensive Assertions**
   - Assert return type and structure
   - Assert return values
   - Assert side effects (logging, state changes)
   - Assert error messages for exceptions

5. **Reusable Fixtures**
   - Fixtures in conftest.py for shared setup
   - Scoped appropriately (function, class, module, session)
   - Documented with docstrings

### Tools & Dependencies

**Testing Framework**:
- pytest: Already in use, familiar to team
- pytest-asyncio: Already in use, handles async tests
- pytest-cov: For coverage measurement

**Mocking**:
- unittest.mock (AsyncMock, patch): Already in use
- Consider: pytest-mock plugin (simplifies some patterns)

**ChromaDB Testing**:
- chromadb[test]: Includes ephemeral client for testing
- No external services needed in tests

## Code References: Test Implementation Patterns

### Unit Test Pattern (From existing test_tools.py)

```python
class TestToolName:
    """Tests for tool name."""

    def test_tool_happy_path(self):
        """Test tool with normal inputs."""
        result = tool_function(arg1, arg2)
        assert result == expected_value

    def test_tool_edge_case(self):
        """Test tool with edge case inputs."""
        result = tool_function(edge_input)
        assert result == expected_edge_output
```

**Application to RAG Tool**:
- Direct function call: `rag_search(query, collection_mock)`
- Assert result structure: `assert "documents" in results`
- Assert ranking: `assert results[0]["score"] >= results[1]["score"]`

### Fixture Pattern (From existing conftest.py)

```python
@pytest.fixture
def mock_repository():
    """Create a mock repository for testing."""
    return AsyncMock()

@pytest.fixture
def sample_entity():
    """Create a sample entity for testing."""
    return Entity(id="test-id", field="value")
```

**Application to RAG Tool**:
```python
@pytest.fixture
def mock_chromadb_collection():
    """Create a mock ChromaDB collection."""
    mock = AsyncMock()
    mock.query = AsyncMock(return_value={
        "ids": [["doc1"]],
        "documents": [["Content"]],
        "distances": [[0.1]]
    })
    return mock
```

### Integration Test Pattern (From existing test_conversation_api.py)

```python
@pytest.mark.integration
class TestAPIFeature:
    """Integration tests for API."""

    async def setup_helper(self, client: AsyncClient):
        """Helper to setup prerequisites."""
        # Create resources via API
        # Return auth headers or IDs
        pass

    @pytest.mark.asyncio
    async def test_feature_success(self, client: AsyncClient):
        """Test successful feature execution."""
        # Use setup helper
        # Make API call
        # Assert response and state
        pass
```

**Application to RAG Tool**:
```python
@pytest.mark.integration
@pytest.mark.chromadb
class TestRAGAdapter:
    """Integration tests for ChromaDB adapter."""

    @pytest.mark.asyncio
    async def test_index_and_search(self, chromadb_instance):
        """Test indexing documents and searching."""
        # Index documents
        await adapter.add_documents(documents)

        # Search
        results = await adapter.search("query")

        # Assert results
        assert len(results) > 0
        assert results[0]["id"] in document_ids
```

### Error Handling Pattern (From existing test_use_cases.py)

```python
def test_function_raises_error(self):
    """Test that function raises specific error."""
    use_case = UseCase(mock_dependency)

    with pytest.raises(ValueError, match="error message pattern"):
        await use_case.execute(invalid_input)
```

**Application to RAG Tool**:
```python
def test_rag_search_empty_query_raises_error(self):
    """Test that empty query raises ValueError."""
    with pytest.raises(ValueError, match="Query cannot be empty"):
        rag_search("", mock_collection)
```

### Async Mock Pattern (From existing conftest.py)

```python
@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider for testing."""
    mock = AsyncMock()
    mock.generate = AsyncMock(return_value="Test response")
    mock.stream = AsyncMock()
    return mock
```

**Application to RAG Tool**:
```python
def mock_chromadb_return_search_results():
    """Return realistic ChromaDB search results."""
    return {
        "ids": [["doc1", "doc2", "doc3"]],
        "distances": [[0.05, 0.15, 0.25]],  # Lower = more relevant
        "documents": [["Content 1", "Content 2", "Content 3"]],
        "metadatas": [[
            {"source": "file1.txt"},
            {"source": "file2.txt"},
            {"source": "file3.txt"}
        ]]
    }
```

## Summary

The Genesis project has a solid testing foundation with clear patterns for unit and integration tests. The RAG tool implementation should follow these existing patterns:

1. **Simple tool function** in `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/rag_search.py`
2. **Unit tests** with mocked ChromaDB collection
3. **Integration tests** with ephemeral ChromaDB instance
4. **Adapter layer** following IVectorStore port pattern
5. **LangGraph integration** via tool registration (no new test infrastructure needed)
6. **E2E tests** deferred until WebSocket testing infrastructure is established

The test pyramid focuses on unit testing (70%) with mocked ChromaDB, integration testing (25%) with ephemeral instances, and future e2e testing (5%) once WebSocket infrastructure is ready.
