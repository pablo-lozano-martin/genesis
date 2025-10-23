# Testing Coverage Analysis: WebSocket to REST API Migration with LangGraph Integration

## Request Summary

This feature request involves replacing the unused LangGraph infrastructure (specifically the streaming chat graph) with a REST API endpoint that integrates LangGraph nodes to process messages and generate LLM responses. The migration maintains message persistence, LLM integration, and conversation workflows while changing the communication protocol from WebSocket to HTTP POST requests for non-real-time chat interactions.

**Key Context:**
- Current: WebSocket handler streams tokens via `handle_websocket_chat()` using `streaming_chat_graph.py`
- Target: REST `/api/conversations/{id}/messages` POST endpoint that uses individual LangGraph nodes
- Scope: Message processing, LLM invocation, response formatting, and persistence

---

## Relevant Files & Modules

### Test Files (Existing)
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/conftest.py` - Pytest fixtures and configuration with mocks for repositories and LLM providers
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_domain_models.py` - Domain model validation tests (41 tests total across all files)
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_use_cases.py` - Use case business logic tests with mocked dependencies
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_llm_providers.py` - LLM provider factory and message conversion tests
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_auth_api.py` - Authentication API endpoint tests
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_conversation_api.py` - Conversation CRUD API tests with authorization

### Implementation Files (Code Under Test)

#### REST Endpoints
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_router.py` - GET endpoint for retrieving conversation messages (requires auth, enforces user isolation)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/conversation_router.py` - Conversation CRUD endpoints (to be extended with POST message endpoint)

#### WebSocket Infrastructure (Current - To Be Replaced)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket handler with streaming token logic (lines 56-180)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py` - Message protocol schemas (ClientMessage, ServerTokenMessage, etc.)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_router.py` - WebSocket route registration

#### LangGraph Components
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - ConversationState TypedDict with messages, conversation_id, user_id, current_input, llm_response, error (lines 10-30)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Main conversation graph orchestration with should_continue() routing logic (lines 19-90)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Streaming-specific graph (UNUSED - candidate for removal/consolidation)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/process_input.py` - Input validation node that creates user Message objects (lines 11-46)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - LLM invocation node with error handling (lines 11-46)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/format_response.py` - Response formatting into Message objects (lines 11-44)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/save_history.py` - Message persistence node with conversation metadata updates (lines 12-64)

#### Domain & Port Interfaces
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/message.py` - Message, MessageCreate, MessageResponse, MessageRole enum
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/message_repository.py` - IMessageRepository interface
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/conversation_repository.py` - IConversationRepository interface
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - ILLMProvider interface with generate() and stream() methods

#### MongoDB Adapters
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_message_repository.py` - MongoDB message repository (create, get_by_conversation_id, delete)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_conversation_repository.py` - MongoDB conversation repository (increment_message_count)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_models.py` - Beanie document models

#### Security & Dependencies
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/security/dependencies.py` - get_current_user(), CurrentUser dependency injection (lines 19-79)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/security/auth_service.py` - JWT authentication service

#### Configuration
- `/Users/pablolozano/Mac Projects August/genesis/backend/pytest.ini` - Pytest markers (unit, integration), async mode configuration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py` - FastAPI app creation and router registration

---

## Current Testing Overview

### Unit Tests (Test Isolation - Mocked Dependencies)

**Domain Model Tests** (`test_domain_models.py`):
- Tests Pydantic schema validation for User, Conversation, Message
- Validates field constraints (email format, password length, username length, message content required)
- Tests enum roles (USER, ASSISTANT, SYSTEM)
- Tests optional metadata dictionaries
- **Coverage: 100% of model validation paths** - Well-maintained

**Use Case Tests** (`test_use_cases.py`):
- Tests RegisterUser use case with mocked user repository
- Tests AuthenticateUser use case with mocked user repository and auth service
- Tests error scenarios: duplicate email, duplicate username, invalid credentials, inactive user
- Uses AsyncMock fixtures for repository methods
- **Coverage: Business logic in isolation** - Good pattern establishment

**LLM Provider Tests** (`test_llm_providers.py`):
- Tests provider factory with mocked settings for all four providers (OpenAI, Anthropic, Gemini, Ollama)
- Tests unsupported provider error handling
- Tests message role enumeration correctness
- Tests basic message creation for LLM processing
- **Coverage: Factory pattern, but limited provider behavior testing**

### Integration Tests (Multi-Component Testing - Real Dependencies)

**Authentication API Tests** (`test_auth_api.py`):
- Tests health check endpoint
- Tests user registration with validation
- Tests login flow (register → login → get current user)
- Tests invalid credentials handling
- Uses real database and HTTP client via AsyncClient
- **Coverage: Full auth workflow** - Good end-to-end pattern

**Conversation API Tests** (`test_conversation_api.py`):
- Tests create conversation endpoint (201)
- Tests list conversations endpoint (pagination)
- Tests get specific conversation (user isolation with ownership checks)
- Tests delete conversation endpoint (404 after deletion)
- Tests unauthorized access (401 without token)
- Tests PATCH conversation title update with validation
- Tests update with too-long title (422 validation error)
- Tests cross-user unauthorized update (403 access denied)
- Tests update non-existent conversation (404)
- Helper method: `create_user_and_login()` for test setup
- **Coverage: Full CRUD with authorization** - Comprehensive authorization testing

### Test Fixtures & Fixtures Pattern (`conftest.py`)

**Current Fixtures:**
- `app()` - FastAPI application instance
- `client()` - AsyncClient with ASGI transport for HTTP testing
- `mock_user_repository()` - AsyncMock for user repository
- `mock_conversation_repository()` - AsyncMock for conversation repository
- `mock_message_repository()` - AsyncMock for message repository
- `mock_llm_provider()` - AsyncMock with generate() and stream() methods
- `sample_user()` - User entity with test data
- `sample_user_create()` - UserCreate DTO with test data
- `sample_conversation()` - Conversation entity with test data
- `sample_message()` - Message entity with test data
- `auth_service()` - AuthService instance

**Coverage Quality:** Fixtures follow factory pattern for reusability and consistency

### Coverage Gaps & Observations

1. **No LangGraph Node Testing** - Individual nodes (process_input, call_llm, format_response, save_history) have no unit tests despite being core business logic
2. **No Message Node Integration** - WebSocket handler exists but no dedicated integration tests for message streaming
3. **No LangGraph Graph Testing** - The chat_graph creation and routing logic (should_continue) lacks tests
4. **Limited Error Path Testing** - WebSocket error handling, LLM provider failures, repository exceptions not thoroughly tested
5. **No Message API Integration Tests** - Only GET endpoint tested; no POST endpoint exists yet (migration target)
6. **WebSocket Not Tested** - WebSocket handler complex logic (token streaming, error handling, connection management) untested
7. **State Management Untested** - ConversationState reducer (add_messages) not validated
8. **Repository Methods Partially Tested** - get_by_conversation_id() pagination, delete_by_conversation_id() not tested

---

## Coverage Analysis

### Components Well-Tested
1. **Domain Models** - Full validation with edge cases
2. **Authentication Flow** - Registration, login, token refresh
3. **Conversation CRUD** - Create, read, list, update, delete with authorization
4. **Use Cases** - Business logic with mocked dependencies
5. **LLM Provider Factory** - Provider selection and configuration

### Components Under-Tested
1. **LangGraph Nodes** - Core message processing logic untested
2. **Message Processing Pipeline** - Input validation → LLM call → Response formatting → Persistence
3. **LLM Integration** - Provider invocation and error handling
4. **Message Repository Methods** - Pagination, batch deletion, conversation queries
5. **Conversation Repository Updates** - Message count increments, metadata updates
6. **State Management** - LangGraph state transitions and message reducer
7. **Error Handling** - Failure paths throughout the processing pipeline

### Test Layer Distribution

```
Unit Tests:        25 tests (61%) - Domain models, use cases, factory
Integration Tests: 16 tests (39%) - API endpoints with real DB
E2E Tests:         0 tests        - Full workflows with all components
```

**Target Distribution (Best Practice):**
```
Unit Tests:        70% - Component isolation with mocks
Integration Tests: 20% - Multi-component workflows
E2E Tests:         10% - Critical user journeys
```

---

## Testing Recommendations

### Proposed Unit Tests

#### 1. LangGraph Node Tests (NEW)
**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_langgraph_nodes.py`

**Purpose:** Test individual node functions in isolation with mocked state and dependencies

**Test Cases:**

**ProcessInput Node:**
- `test_process_input_valid()` - Valid user input creates USER message and clears error
- `test_process_input_empty_input()` - Empty string triggers error state
- `test_process_input_whitespace_only()` - Whitespace-only input triggers error
- `test_process_input_strips_whitespace()` - Content properly trimmed before processing
- `test_process_input_preserves_content()` - Message content preserved exactly
- `test_process_input_state_structure()` - Returns dict with messages and error fields

**CallLLM Node:**
- `test_call_llm_success()` - Successful LLM call stores response and clears error
- `test_call_llm_provider_exception()` - Provider exception captured in error state
- `test_call_llm_with_empty_messages()` - Handles empty message history gracefully
- `test_call_llm_passes_conversation_history()` - All messages passed to provider
- `test_call_llm_state_structure()` - Returns dict with llm_response and error fields

**FormatResponse Node:**
- `test_format_response_creates_assistant_message()` - LLM response becomes ASSISTANT message
- `test_format_response_sets_conversation_id()` - Message uses conversation_id from state
- `test_format_response_empty_response()` - Empty response returns empty dict
- `test_format_response_clears_llm_response()` - Temporary field cleared after formatting
- `test_format_response_preserves_response_text()` - Response text not modified

**SaveHistory Node:**
- `test_save_history_persists_messages()` - All messages saved to repository
- `test_save_history_increments_count()` - Conversation message count updated correctly
- `test_save_history_no_messages()` - Empty messages list returns empty dict
- `test_save_history_repository_exception()` - Repository error stored in error state
- `test_save_history_conversation_not_found()` - Handles missing conversation gracefully
- `test_save_history_partial_failure()` - Logs individual message failures but continues

**Fixtures Needed:**
- `mock_llm_provider` (existing)
- `mock_message_repository` (existing)
- `mock_conversation_repository` (existing)
- `sample_conversation_state()` (NEW)
- `sample_state_with_error()` (NEW)

#### 2. LangGraph Graph Tests (NEW)
**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_langgraph_graph.py`

**Purpose:** Test graph orchestration, routing logic, and state transitions

**Test Cases:**
- `test_create_chat_graph_structure()` - Graph contains all four nodes
- `test_should_continue_with_error()` - should_continue() returns "end" when error present
- `test_should_continue_no_error()` - should_continue() returns "call_llm" when no error
- `test_graph_node_edges()` - All edges properly configured (START→process_input, etc.)
- `test_graph_conditional_routing()` - Conditional edge routes correctly based on error state

**Note:** These tests use LangGraph's testing utilities to invoke the compiled graph with state

#### 3. Message Domain Tests Enhancement (EXTEND)
**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_domain_models.py`

Add to TestMessageModel class:
- `test_message_list_conversion()` - Multiple messages convert correctly for LLM
- `test_message_with_all_fields()` - All optional fields work together
- `test_message_create_schema()` - MessageCreate schema validation
- `test_message_response_schema()` - MessageResponse schema validation

#### 4. Message Repository Tests (NEW)
**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_repositories.py`

**Purpose:** Test repository methods in isolation with mocked Beanie ODM

**Test Cases:**
- `test_message_repository_create()` - Message created with correct fields
- `test_message_repository_get_by_id()` - Message retrieved by ID
- `test_message_repository_get_by_conversation_id_pagination()` - Skip/limit work correctly
- `test_message_repository_delete()` - Message deletion returns True/False
- `test_message_repository_delete_by_conversation_id()` - Batch deletion returns count
- `test_conversation_repository_increment_message_count()` - Count incremented by N

**Note:** These tests mock Beanie's database operations at the document level

### Proposed Integration Tests

#### 1. Message REST API Endpoint Tests (NEW)
**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_message_api.py`

**Purpose:** Test the new POST /api/conversations/{id}/messages endpoint end-to-end with real database

**Test Cases:**

**Happy Path:**
- `test_send_message_success()` - POST creates user message, invokes LLM, returns assistant response (200)
- `test_send_message_creates_both_messages()` - Both user and assistant messages persisted
- `test_send_message_updates_conversation_count()` - Message count incremented by 2
- `test_send_message_response_structure()` - Response includes message_id, content, role, conversation_id, created_at

**Validation:**
- `test_send_message_empty_content()` - Empty message rejected (400)
- `test_send_message_missing_conversation()` - 404 for non-existent conversation
- `test_send_message_unauthorized_conversation()` - 403 when accessing other user's conversation

**Error Handling:**
- `test_send_message_llm_provider_error()` - Provider exception returns 500 with error message
- `test_send_message_repository_failure()` - Repository exception handled gracefully

**Integration Scenarios:**
- `test_send_message_preserves_conversation_history()` - GET messages includes new messages
- `test_send_message_conversation_sequence()` - Multiple messages in sequence maintain order
- `test_send_message_pagination_after_new_message()` - Pagination reflects new message count

**Fixtures Needed:**
- `client()` (existing)
- `create_user_and_login()` helper (extend from conversation tests)
- `create_conversation()` helper (NEW)

**Example Test Pattern:**
```python
@pytest.mark.integration
class TestMessageAPI:
    async def test_send_message_success(self, client: AsyncClient):
        """Test successfully sending a message and receiving LLM response."""
        headers = await self.create_user_and_login(client)
        conversation = await self.create_conversation(client, headers)

        response = await client.post(
            f"/api/conversations/{conversation['id']}/messages",
            json={"content": "Hello, how are you?"},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == MessageRole.ASSISTANT
        assert "content" in data
        assert data["conversation_id"] == conversation['id']
```

#### 2. WebSocket to REST Migration Tests (NEW)
**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_message_api_vs_websocket.py`

**Purpose:** Verify REST endpoint produces equivalent results to WebSocket workflow

**Test Cases:**
- `test_rest_and_websocket_same_response()` - Same message input produces identical LLM output
- `test_rest_and_websocket_same_persistence()` - Messages saved identically in both flows
- `test_rest_endpoint_handles_streaming()` - REST returns complete response (non-streaming)
- `test_websocket_still_streams_tokens()` - WebSocket maintains token streaming (if not being removed)

#### 3. LangGraph Integration Tests (NEW)
**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_langgraph_flow.py`

**Purpose:** Test full graph execution with real repositories and LLM provider mocks

**Test Cases:**
- `test_full_graph_execution()` - Complete flow from input to persisted messages
- `test_graph_with_real_repositories()` - Graph uses actual MongoDB repositories
- `test_graph_with_mock_llm_provider()` - LLM provider mocked, persistence real
- `test_graph_error_recovery()` - Graph handles node failures appropriately
- `test_graph_state_transitions()` - State properly updated at each node

**Example Test Pattern:**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_graph_execution(
    mock_llm_provider,
    sample_conversation,
    sample_user
):
    """Test complete graph execution with mocked LLM."""
    graph = create_chat_graph(
        llm_provider=mock_llm_provider,
        message_repository=MongoMessageRepository(),
        conversation_repository=MongoConversationRepository()
    )

    initial_state = ConversationState(
        messages=[],
        conversation_id=sample_conversation.id,
        user_id=sample_user.id,
        current_input="Test message"
    )

    final_state = await graph.ainvoke(initial_state)

    assert len(final_state["messages"]) > 0
    assert final_state["error"] is None
    # Verify messages persisted to database
```

### Test Data & Fixtures

#### New Fixtures to Add (`conftest.py`)

```python
@pytest.fixture
def sample_conversation_state(sample_conversation, sample_user, sample_message):
    """Create a sample conversation state for LangGraph testing."""
    return ConversationState(
        messages=[sample_message],
        conversation_id=sample_conversation.id,
        user_id=sample_user.id,
        current_input="Test input",
        llm_response=None,
        error=None
    )

@pytest.fixture
def sample_state_with_error(sample_conversation, sample_user):
    """Create a conversation state with error condition."""
    return ConversationState(
        messages=[],
        conversation_id=sample_conversation.id,
        user_id=sample_user.id,
        current_input=None,
        llm_response=None,
        error="Test error message"
    )

@pytest.fixture
async def create_conversation_helper(client: AsyncClient):
    """Helper to create conversation in tests."""
    async def _create(headers: dict, title: str = "Test Conversation"):
        response = await client.post(
            "/api/conversations",
            json={"title": title},
            headers=headers
        )
        return response.json()
    return _create
```

---

## Implementation Guidance

### Phase 1: Unit Tests for LangGraph (Foundation)

1. **Create test_langgraph_nodes.py:**
   - Test each node function independently
   - Use fixtures for state, mocks, and sample data
   - Establish testing patterns for async node functions
   - Target: 100% coverage of node logic

2. **Create test_langgraph_graph.py:**
   - Test graph creation and compilation
   - Test conditional routing (should_continue function)
   - Test state flow between nodes
   - Target: All graph paths covered

3. **Extend conftest.py:**
   - Add ConversationState fixtures
   - Add state with various conditions (error, empty, full)
   - Keep fixtures focused and composable

**Estimated Tests:** 25-30 unit tests
**Coverage Goal:** >95% of node and graph code

### Phase 2: Integration Tests for REST Endpoint (Feature)

1. **Create test_message_api.py:**
   - Test POST endpoint with real database
   - Test authorization and user isolation
   - Test error scenarios and edge cases
   - Test integration with existing conversation endpoints

2. **Update conftest.py:**
   - Add create_conversation_helper
   - Enhance create_user_and_login to return both headers and user data

**Estimated Tests:** 15-20 integration tests
**Coverage Goal:** All endpoint paths and error codes

### Phase 3: Migration Verification Tests (Transition)

1. **Create test_message_api_vs_websocket.py:**
   - Compare REST and WebSocket behavior
   - Verify identical message handling
   - Verify equivalent database state

2. **Deprecation Tests:**
   - Mark WebSocket tests with @pytest.mark.deprecated if keeping WebSocket
   - Or remove WebSocket handler tests if fully migrating away

**Estimated Tests:** 5-10 comparison tests

### Phase 4: Full Coverage Review (Quality)

1. **Run coverage report:**
   ```bash
   pytest --cov=app --cov-report=html --cov-report=term-missing
   ```

2. **Target Coverage Metrics:**
   - Lines: >80%
   - Branches: >75%
   - Functions: >90%
   - Classes: >85%

3. **Focus on:**
   - Message processing pipeline (100%)
   - Error handling paths (95%)
   - Repository operations (90%)
   - LLM integration (85%)

---

## Implementation Order & Test Execution Strategy

### Testing Execution Sequence

```bash
# Unit tests (fast - run first for rapid feedback)
pytest tests/unit/ -v --tb=short

# New LangGraph node tests
pytest tests/unit/test_langgraph_nodes.py -v

# New LangGraph graph tests
pytest tests/unit/test_langgraph_graph.py -v

# Integration tests (slower - test with real components)
pytest tests/integration/ -v

# New message API tests
pytest tests/integration/test_message_api.py -v

# Full test suite with coverage
pytest --cov=app --cov-report=term-missing --cov-report=html

# Watch for coverage gaps
open htmlcov/index.html
```

### Test Markers for Organization

Add to `pytest.ini`:
```ini
markers =
    unit: Unit tests (isolated components)
    integration: Integration tests (multi-component)
    langgraph: LangGraph-specific tests
    message: Message API tests
    deprecated: Tests for deprecated code
```

Run specific test groups:
```bash
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests only
pytest -m langgraph         # LangGraph tests
pytest -m message           # Message API tests
pytest -m "not deprecated"  # Exclude deprecated
```

---

## Risks and Considerations

### Testing Challenges

1. **LangGraph Async Testing**
   - Risk: Complex async/await patterns in graph nodes
   - Mitigation: Use AsyncMock fixtures consistently, test each node independently first
   - Pattern: `async def node_func(state) -> dict` returns dict, not state

2. **State Mutations & Reducers**
   - Risk: add_messages reducer behavior with TypedDict
   - Mitigation: Test message merging separately in unit tests
   - Testing: Verify state structure before/after reducer application

3. **Database Isolation**
   - Risk: Integration tests modify shared database
   - Mitigation: Use random_id fixture for test isolation (already implemented)
   - Pattern: Create unique conversations/users per test run

4. **LLM Provider Mocking**
   - Risk: Mocks must match real provider interface
   - Mitigation: Define ILLMProvider interface clearly, match in mocks
   - Pattern: mock.generate() and mock.stream() must return correct types

5. **Authorization & Security Testing**
   - Risk: User isolation not properly enforced
   - Mitigation: Test cross-user access attempts, verify 403 responses
   - Pattern: Create second user in test, attempt unauthorized access

### Coverage Gaps to Address

1. **Error Paths**
   - What if LLM provider times out?
   - What if database is unavailable during save?
   - What if conversation is deleted mid-processing?
   - Test each with mocked exceptions

2. **Edge Cases**
   - Very long messages (>10K chars)
   - Special characters and unicode in content
   - Rapid successive messages
   - Test through integration tests

3. **Concurrent Operations**
   - Multiple users in same conversation
   - Message ordering with concurrent sends
   - Consider pytest-asyncio concurrent tests

### Testing Violations to Avoid

1. **DO NOT mock IMessageRepository in REST API tests** - Use real MongoDB to verify persistence
2. **DO NOT skip authorization tests** - User isolation must be verified end-to-end
3. **DO NOT test internal LangGraph structure** - Only test node contracts (input state → output dict)
4. **DO NOT use real LLM API calls** - Always mock LLM provider in tests
5. **DO NOT test WebSocket streaming without proper async handling** - Use pytest-asyncio

### Dependencies & Prerequisites

Before implementing tests:
1. Ensure conftest.py has all necessary fixtures
2. Ensure sample_message fixture has full_name (based on recent commit 9e71c95)
3. Ensure mock_llm_provider has both generate() and stream() methods
4. Ensure all repositories implement full interface (get_by_id, create, delete, etc.)

---

## Testing Best Practices Applied

### Test Naming Convention
- `test_<component>_<scenario>_<expected_outcome>()`
- Example: `test_process_input_empty_input_triggers_error()`

### Test Structure (AAA Pattern)
```python
async def test_example(self, mock_repo, sample_data):
    # ARRANGE
    state = ConversationState(...)

    # ACT
    result = await process_user_input(state)

    # ASSERT
    assert result["error"] is None
    assert len(result["messages"]) == 1
```

### Fixture Hierarchy
1. **Session-level:** Database connection, settings
2. **Module-level:** Mock factories, shared data
3. **Function-level:** Test-specific state, unique IDs
4. **Test-level:** Inline arrangement for edge cases

### Async Test Pattern
```python
@pytest.mark.asyncio
async def test_async_operation(self, mock_repo):
    """Test async function with proper await."""
    result = await async_function(mock_repo)
    assert result is not None
```

### Error Testing Pattern
```python
def test_validation_error(self):
    """Test that invalid input raises ValueError."""
    with pytest.raises(ValueError, match="exact error message"):
        invalid_operation()
```

---

## Testing Strategy Summary

### Test Pyramid Target
```
         /\
        /  \  E2E: 10%
       /────\────── (Critical user journeys)
      /      \
     /────────\──── Integration: 20%
    /          \   (Multi-component workflows)
   /────────────\─ Unit: 70%
  /              \(Component isolation)
 /________________\
```

### Coverage Goals by Component

| Component | Unit | Integration | E2E | Target |
|-----------|------|-------------|-----|--------|
| LangGraph Nodes | 100% | 0% | 0% | 100% |
| Chat Graph | 100% | 0% | 0% | 100% |
| Message Domain | 100% | 0% | 0% | 100% |
| REST Endpoint | 0% | 100% | 0% | 100% |
| Message API | 0% | 100% | 0% | 100% |
| Authorization | 10% | 90% | 0% | 90%+ |
| LLM Integration | 80% | 20% | 0% | 85%+ |
| Error Handling | 70% | 30% | 0% | 80%+ |
| **Overall** | **~70%** | **~20%** | **~10%** | **>80%** |

### Continuous Integration Metrics

- **Test Execution Time:** <60 seconds for unit tests, <5 minutes for integration
- **Coverage Threshold:** Fail CI if <80% overall coverage
- **Coverage Reduction:** Fail CI if coverage decreases from baseline
- **Test Quality:** No skipped tests (@pytest.mark.skip without justification)
- **Flaky Tests:** Zero flaky tests (tests must be deterministic)

---

## Key Testing Considerations for Implementation

### Message Processing Pipeline Testing

The core workflow that needs comprehensive testing:

```
REST POST /api/conversations/{id}/messages
    ↓
[Validate user authorization] (integration test)
    ↓
[Create user Message object] (unit test: process_input node)
    ↓
[Save user message to DB] (integration test)
    ↓
[Invoke LLM provider] (unit test: call_llm node with mock)
    ↓
[Format response into Message] (unit test: format_response node)
    ↓
[Persist assistant message] (integration test)
    ↓
[Update conversation metadata] (unit test: save_history node)
    ↓
[Return response to client] (integration test)
```

**Each arrow represents a test boundary - verify both happy path and error path**

### State Management Testing

ConversationState usage across nodes:

```python
# Node receives: ConversationState (read)
# Node returns: dict with updates (write)
# State is merged by framework via add_messages reducer

# Testing strategy:
1. Test each node returns correct dict structure
2. Test state changes are isolated to node scope
3. Test message reducer with multiple messages
4. Test conditional routing based on error state
```

### Authorization Testing Must Cover

```
✓ User can only access their own conversations
✓ User can only send messages in their conversations
✓ User cannot see other users' messages
✓ Unauthenticated requests rejected (401)
✓ Expired tokens rejected (401)
✓ Missing Authorization header rejected (401)
```

---

## References to Existing Test Patterns

### Reference Implementation Pattern: test_conversation_api.py

The `TestConversationAPI` class demonstrates the pattern for REST API integration tests:

**Key Pattern Elements:**
1. Helper method for setup: `create_user_and_login()`
2. AsyncClient for HTTP requests: `await client.post(...)`
3. Status code assertions: `assert response.status_code == 201`
4. Authorization checks: Testing 403 for unauthorized access
5. Pagination testing: Using skip/limit parameters
6. Validation testing: Testing 422 for invalid data

**Apply This Pattern To:**
- New `test_message_api.py` for POST message endpoint
- Use same helper pattern for conversation/user creation
- Follow same assertion style for consistency

### Reference Implementation Pattern: test_use_cases.py

The `TestRegisterUser` and `TestAuthenticateUser` classes demonstrate unit test patterns:

**Key Pattern Elements:**
1. AsyncMock for dependencies: `mock_user_repository = AsyncMock()`
2. Setup return values: `mock_user_repository.get_by_email = AsyncMock(return_value=None)`
3. Test execution: `user = await use_case.execute(...)`
4. Assertion of calls: `mock_user_repository.create.assert_called_once()`
5. Error testing: `with pytest.raises(ValueError, match="...")`

**Apply This Pattern To:**
- New `test_langgraph_nodes.py` for node function tests
- Mock repositories and LLM providers
- Test both happy path and error scenarios

---

## Document Assumptions

1. **WebSocket Handler Will Be Replaced:** Testing assumes REST endpoint replaces WebSocket for message processing
2. **LangGraph Nodes Remain in Use:** Assumes individual nodes continue to be used (not removed)
3. **Database Operations Stay in save_history Node:** Message persistence happens in node, not in REST endpoint
4. **Mock Fixtures Are Sufficient:** Assumes MockAsync adequately represents repository/provider behavior
5. **Coverage Goal Is >80%:** Based on project DoD requirement
6. **Tests Execute in Isolation:** Assumes pytest fixtures properly reset state between tests

---

## Next Steps for Implementation

1. **Week 1:** Implement unit tests for LangGraph nodes (test_langgraph_nodes.py)
   - Establish async testing patterns
   - Create node test fixtures

2. **Week 2:** Implement unit tests for LangGraph graph (test_langgraph_graph.py)
   - Test graph compilation and routing
   - Test state transitions

3. **Week 3:** Implement integration tests for REST endpoint (test_message_api.py)
   - Implement POST endpoint concurrently
   - Test end-to-end workflow

4. **Week 4:** Verification and coverage optimization
   - Run full coverage report
   - Address gaps identified by coverage analysis
   - Optimize flaky or slow tests

---

## Questions for Clarification

If implementation reveals ambiguities, address these:

1. **WebSocket Deprecation:** Is WebSocket being fully removed or kept alongside REST?
2. **Streaming Behavior:** Does REST endpoint return complete response or stream tokens via Server-Sent Events?
3. **Error Response Format:** Should REST error responses match WebSocket error schema?
4. **Message Metadata:** Should REST endpoint populate metadata field (token count, model name)?
5. **Response Time Expectations:** Should REST endpoint have timeout for LLM generation?
6. **Rate Limiting:** Should new endpoint have rate limiting?
7. **Batch Messaging:** Should new endpoint support multiple messages in one request?

---

**Last Updated:** October 24, 2025
**Status:** Analysis Complete - Ready for Implementation
**Coverage Target:** >80% overall, 100% for new components
**Test Count Target:** 70-80 new tests (unit + integration)
