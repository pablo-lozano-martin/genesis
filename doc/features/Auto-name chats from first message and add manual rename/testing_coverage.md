# Testing Coverage Analysis

## Request Summary

This feature adds two key capabilities to the chat application:
1. **Auto-naming**: Automatically generate conversation titles from the first user message (extract first 3 words, max 50 characters)
2. **Manual rename**: Allow users to manually rename conversations via the sidebar

The implementation requires changes across multiple layers: domain models, API endpoints, frontend services, and UI components.

## Relevant Files & Modules

### Files to Examine

#### Backend Domain & Schemas
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/conversation.py` - Conversation domain model with ConversationUpdate schema (already supports title updates)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/message.py` - Message domain model for accessing first message content

#### Backend API Layer
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/conversation_router.py` - PATCH endpoint at line 116-156 (already implemented, needs integration testing)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket handler where auto-naming logic should trigger after first message

#### Backend Repository Layer
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_conversation_repository.py` - MongoDB conversation repository with update method (lines 73-95)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/conversation_repository.py` - Repository port interface defining update contract

#### Backend Use Cases
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/use_cases/send_message.py` - SendMessage use case where auto-naming should occur after first user message

#### Frontend Services
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/conversationService.ts` - ConversationService needs updateConversation method to call PATCH endpoint
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/hooks/useWebSocket.ts` - WebSocket hook for streaming messages

#### Frontend State Management
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx` - Chat context managing conversation and message state, needs updateConversation method

#### Frontend UI Components
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/ConversationSidebar.tsx` - Sidebar displaying conversation titles, needs inline edit functionality

#### Test Files
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_conversation_api.py` - Integration tests for conversation API (needs PATCH endpoint tests)
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_use_cases.py` - Unit tests for use cases (needs auto-naming logic tests)
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_domain_models.py` - Domain model validation tests (ConversationUpdate validation)
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/conftest.py` - Shared test fixtures

### Key Test Cases & Functions

#### Existing Test Patterns
- `test_create_conversation()` in `test_conversation_api.py` (line 37-51) - Pattern for conversation creation
- `test_get_conversation()` in `test_conversation_api.py` (line 77-97) - Pattern for fetching conversations
- `test_delete_conversation()` in `test_conversation_api.py` (line 100-124) - Pattern for deletion with cleanup verification
- `create_user_and_login()` helper in `test_conversation_api.py` (line 12-34) - Authentication setup for integration tests
- `test_register_user_success()` in `test_auth_api.py` (line 22-36) - Pattern for successful API operations
- `test_conversation_creation_valid()` in `test_domain_models.py` (line 75-86) - Pattern for domain model validation

#### Test Infrastructure
- `@pytest.mark.integration` decorator for integration tests
- `@pytest.mark.unit` decorator for unit tests
- `@pytest.mark.asyncio` decorator for async test functions
- `pytest.random_id` fixture for test isolation (defined in `test_auth_api.py` line 103-108)
- Mock repositories using `AsyncMock` from `unittest.mock`
- `client: AsyncClient` fixture from conftest.py for HTTP testing

## Current Testing Overview

### Unit Tests

**Location**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/`

**Existing Coverage**:
- `test_domain_models.py` - Validates Pydantic schemas for User, Conversation, and Message models
  - Tests valid conversation creation, default values, validation errors
  - ConversationUpdate schema exists but no explicit validation tests
- `test_use_cases.py` - Tests RegisterUser and AuthenticateUser with mocked dependencies
  - Pattern: Mock repository methods, call use case execute(), assert outcomes
  - No tests for conversation or message use cases yet
- `test_llm_providers.py` - Tests LLM provider implementations

**Missing Coverage**:
- No unit tests for conversation-related use cases
- No tests for title generation utility function
- No tests for auto-naming business logic
- No validation tests for ConversationUpdate edge cases

### Integration Tests

**Location**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/`

**Existing Coverage**:
- `test_conversation_api.py` - Tests conversation CRUD endpoints
  - GET /api/conversations (list)
  - POST /api/conversations (create)
  - GET /api/conversations/{id} (retrieve)
  - DELETE /api/conversations/{id} (delete)
  - **Missing**: PATCH /api/conversations/{id} (update)
- `test_auth_api.py` - Tests authentication flow
  - Provides pattern for multi-step integration tests
  - Uses `create_user_and_login()` helper for auth setup

**Missing Coverage**:
- No integration tests for PATCH /api/conversations/{id} endpoint
- No tests for auto-naming after first message via WebSocket
- No tests for manual rename flow end-to-end
- No tests for authorization (user can only update their own conversations)
- No tests for edge cases (empty title, very long title, special characters)

### End-to-End Tests

**Status**: No E2E test infrastructure detected in the project

**Missing Coverage**:
- No Playwright, Cypress, or similar E2E framework found
- No `frontend/package.json` scripts for E2E tests
- No E2E test directories found

**Frontend Testing**: No frontend test files found (no `.test.ts`, `.test.tsx`, `.spec.ts` files in frontend/src)

### Test Utilities & Fixtures

**Location**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/conftest.py`

**Available Fixtures**:
- `app()` - FastAPI application instance
- `client()` - AsyncClient for HTTP API testing
- `mock_user_repository()` - AsyncMock for user repository
- `mock_conversation_repository()` - AsyncMock for conversation repository
- `mock_message_repository()` - AsyncMock for message repository
- `mock_llm_provider()` - AsyncMock for LLM provider with stream support
- `sample_user()` - Pre-configured User domain model
- `sample_conversation()` - Pre-configured Conversation domain model
- `sample_message()` - Pre-configured Message domain model
- `auth_service()` - AuthService instance

## Coverage Analysis

### Well-Tested Components
- **Authentication flow**: Comprehensive integration tests for register, login, token validation
- **Domain model validation**: Good coverage of Pydantic schema validation for basic cases
- **Conversation CRUD (partial)**: Create, Read, Delete operations tested at integration level

### Undertested Components
- **Conversation updates**: PATCH endpoint implemented but not integration tested
- **Use cases**: Only auth use cases tested; conversation and message use cases untested
- **WebSocket handlers**: No tests for WebSocket message handling, streaming, or error cases
- **Repository update operations**: Update method exists but not tested in isolation

### Untested Components
- **Title generation logic**: No utility function exists yet, will need comprehensive unit tests
- **Auto-naming workflow**: Integration of title generation with WebSocket message handling
- **Frontend services**: No test coverage for ConversationService or WebSocket hooks
- **Frontend components**: No test coverage for ChatContext or ConversationSidebar
- **Multi-tab synchronization**: No tests for WebSocket-based real-time updates
- **Edge cases**: Long messages, special characters, Unicode, empty messages, very long titles

## Testing Recommendations

### Proposed Unit Tests

#### 1. Title Generation Utility Tests
**New File**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_title_generation.py`

Test cases:
- `test_generate_title_from_short_message()` - "Hello world" → "Hello world"
- `test_generate_title_from_long_message()` - Extract first 3 words, ensure max 50 chars
- `test_generate_title_from_single_word()` - Single long word handling, truncate to 50 chars
- `test_generate_title_with_special_characters()` - "Hello! How are you?" → "Hello! How are"
- `test_generate_title_with_unicode()` - Handle emoji, non-ASCII characters correctly
- `test_generate_title_with_extra_whitespace()` - Normalize multiple spaces
- `test_generate_title_from_empty_string()` - Should raise ValueError or return default
- `test_generate_title_with_newlines()` - "Hello\nworld\ntest" → "Hello world test"
- `test_generate_title_max_50_characters()` - Verify hard limit enforcement
- `test_generate_title_preserves_case()` - Don't alter original casing

#### 2. ConversationUpdate Schema Validation Tests
**Extend**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_domain_models.py`

Add to `TestConversationModel` class:
- `test_conversation_update_valid_title()` - Valid title update
- `test_conversation_update_empty_title()` - Empty string should fail validation
- `test_conversation_update_title_too_long()` - Exceeding 200 char max should fail
- `test_conversation_update_title_none()` - None should be allowed (no update)
- `test_conversation_update_whitespace_only()` - Should fail or normalize

#### 3. Auto-Naming Use Case Tests
**New File**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_conversation_use_cases.py`

Test cases:
- `test_auto_name_after_first_message()` - Mock message repository to return 0 messages, verify title update called
- `test_no_auto_name_after_second_message()` - Mock repository returning 1+ messages, verify no title update
- `test_auto_name_with_generated_title()` - Verify title generation function called with message content
- `test_auto_name_updates_conversation()` - Verify conversation repository update() called with generated title
- `test_auto_name_failure_doesnt_block_message()` - If title generation fails, message should still be saved

### Proposed Integration Tests

#### 1. PATCH Conversation Endpoint Tests
**Extend**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_conversation_api.py`

Add to `TestConversationAPI` class:
- `test_update_conversation_title()` - PATCH with valid title, verify 200 response and updated title
- `test_update_conversation_empty_title()` - PATCH with empty title, verify 422 validation error
- `test_update_conversation_title_too_long()` - PATCH with 201+ char title, verify 422 error
- `test_update_conversation_not_found()` - PATCH non-existent conversation, verify 404
- `test_update_conversation_unauthorized()` - User A cannot update User B's conversation, verify 403
- `test_update_conversation_no_changes()` - PATCH with empty body or no fields, verify no error
- `test_update_conversation_special_characters()` - Title with emoji, Unicode, special chars
- `test_update_conversation_updates_timestamp()` - Verify updated_at timestamp changes

#### 2. Auto-Naming Integration Tests
**Extend**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_conversation_api.py`

New test class or extend existing:
- `test_auto_name_on_first_message()` - Create conversation, send first message via API/WebSocket, verify title updated
- `test_no_auto_name_on_subsequent_messages()` - Send multiple messages, verify title only updated after first
- `test_auto_name_preserves_manual_rename()` - If user manually renamed, auto-naming should not override (edge case consideration)
- `test_auto_name_with_long_first_message()` - First message > 200 chars, verify title truncated properly

#### 3. WebSocket Message Flow Tests
**New File**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_websocket_chat.py`

Test cases:
- `test_websocket_send_message_and_receive_stream()` - Send message, verify streaming response
- `test_websocket_first_message_updates_title()` - Connect, send first message, verify conversation title auto-updated
- `test_websocket_authentication_required()` - Connect without token, verify connection rejected
- `test_websocket_invalid_conversation_id()` - Send message to non-existent conversation, verify error response
- `test_websocket_unauthorized_conversation_access()` - User A cannot send to User B's conversation
- `test_websocket_ping_pong()` - Send PING, verify PONG response (already implemented in handler)
- `test_websocket_error_handling()` - Trigger LLM error, verify error message sent to client

**Note**: WebSocket testing requires different patterns than HTTP testing. Consider using:
- `TestClient` from Starlette for WebSocket connections in integration tests
- Mock LLM provider to avoid external API calls
- Async context managers for WebSocket connection lifecycle

### Proposed End-to-End Tests

**Recommendation**: Implement E2E tests using Playwright (modern, TypeScript-first, better for React apps)

#### Setup Required
1. Install Playwright: `npm install -D @playwright/test` in frontend directory
2. Create `/Users/pablolozano/Mac Projects August/genesis/frontend/e2e/` directory
3. Add `playwright.config.ts` to frontend root
4. Update `frontend/package.json` with test scripts

#### E2E Test Files

**New File**: `/Users/pablolozano/Mac Projects August/genesis/frontend/e2e/conversation-naming.spec.ts`

Test scenarios:
- `test_auto_name_flow()`:
  1. Login as test user
  2. Create new conversation (initially "New Chat")
  3. Send first message "Hello how are you today"
  4. Verify sidebar updates to "Hello how are"
  5. Verify title persists after page refresh

- `test_manual_rename_flow()`:
  1. Login, create conversation, send message
  2. Click conversation title in sidebar to edit
  3. Type new title "My Custom Title"
  4. Press Enter or click outside to save
  5. Verify title updated in sidebar
  6. Verify title persisted after refresh

- `test_rename_edge_cases()`:
  1. Test empty title (should fail or revert)
  2. Test very long title (should truncate or show error)
  3. Test special characters in title
  4. Test canceling edit (ESC key)

- `test_multi_tab_synchronization()`:
  1. Open conversation in two browser tabs
  2. Rename in tab 1
  3. Verify tab 2 updates in real-time (via WebSocket or polling)

- `test_auto_name_with_edge_cases()`:
  1. First message is single emoji → Title should be emoji
  2. First message is very long → Title truncated to 50 chars
  3. First message has newlines → Title normalized

**New File**: `/Users/pablolozano/Mac Projects August/genesis/frontend/e2e/conversation-crud.spec.ts`

Test scenarios for conversation management:
- `test_create_conversation()` - Click "New Chat", verify new conversation in sidebar
- `test_delete_conversation()` - Delete conversation, verify removed from sidebar
- `test_switch_conversations()` - Create multiple, switch between them, verify messages load correctly

### Test Data & Fixtures

#### Backend Test Fixtures

**Extend**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/conftest.py`

Add new fixtures:
```python
@pytest.fixture
def sample_first_message(sample_conversation: Conversation) -> Message:
    """Create a sample first message for auto-naming tests."""
    return Message(
        id="first-message-id",
        conversation_id=sample_conversation.id,
        role=MessageRole.USER,
        content="Hello how are you doing today?"
    )

@pytest.fixture
def sample_conversation_with_messages(sample_conversation: Conversation) -> Conversation:
    """Create a conversation with message_count > 0 for testing non-first messages."""
    sample_conversation.message_count = 5
    return sample_conversation

@pytest.fixture
async def authenticated_client(client: AsyncClient) -> tuple[AsyncClient, dict]:
    """Create an authenticated client with auth headers."""
    # Register and login, return (client, headers)
    # Reusable pattern from test_conversation_api.py create_user_and_login()
```

#### Frontend Test Fixtures (for E2E)

**New File**: `/Users/pablolozano/Mac Projects August/genesis/frontend/e2e/fixtures.ts`

```typescript
// Test user credentials
export const TEST_USER = {
  email: 'test@example.com',
  username: 'testuser',
  password: 'testpass123'
}

// Helper to login and get authenticated page
export async function loginAsTestUser(page: Page) {
  await page.goto('/login')
  await page.fill('[name="username"]', TEST_USER.username)
  await page.fill('[name="password"]', TEST_USER.password)
  await page.click('button[type="submit"]')
  await page.waitForURL('/chat')
}

// Helper to create conversation via UI
export async function createConversation(page: Page) {
  await page.click('button:has-text("New Chat")')
  await page.waitForSelector('.conversation-item') // Wait for sidebar update
}
```

#### Mock Data for WebSocket Tests

**Pattern**: Use `AsyncMock` for WebSocket connections in integration tests

```python
@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing."""
    mock = AsyncMock()
    mock.accept = AsyncMock()
    mock.send_text = AsyncMock()
    mock.receive_text = AsyncMock()
    return mock
```

## Implementation Guidance

### Step-by-Step Testing Approach

#### Phase 1: Unit Tests (Foundational)
1. **Create title generation utility** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/core/utils/title_generator.py`)
   - Implement `generate_title(message: str) -> str` function
   - Write comprehensive unit tests in `test_title_generation.py`
   - Run: `cd backend && pytest tests/unit/test_title_generation.py -v`

2. **Add ConversationUpdate validation tests**
   - Extend `test_domain_models.py` with ConversationUpdate edge cases
   - Run: `cd backend && pytest tests/unit/test_domain_models.py::TestConversationModel -v`

3. **Test auto-naming business logic**
   - Create `test_conversation_use_cases.py` with mocked repositories
   - Test decision logic: auto-name only if message_count == 0
   - Run: `cd backend && pytest tests/unit/test_conversation_use_cases.py -v`

#### Phase 2: Integration Tests (API Layer)
1. **Test PATCH endpoint**
   - Extend `test_conversation_api.py` with update tests
   - Test happy path, validation errors, authorization
   - Run: `cd backend && pytest tests/integration/test_conversation_api.py::TestConversationAPI::test_update_conversation_title -v`

2. **Test auto-naming integration**
   - Add tests verifying title updates after first message
   - Mock LLM provider to avoid external API calls
   - Run: `cd backend && pytest tests/integration/test_conversation_api.py -v -k auto_name`

3. **Test WebSocket flow** (if implementing WebSocket tests)
   - Create `test_websocket_chat.py`
   - Use Starlette TestClient for WebSocket connections
   - Run: `cd backend && pytest tests/integration/test_websocket_chat.py -v`

#### Phase 3: Frontend Integration (if adding frontend tests)
1. **Add ConversationService tests** (if setting up frontend testing)
   - Use Vitest (already in package.json as vite)
   - Mock axios calls with `vi.mock('axios')`
   - Test `updateConversation()` method

2. **Add ChatContext tests**
   - Test context state updates when conversation renamed
   - Mock ConversationService
   - Verify state propagation to components

#### Phase 4: End-to-End Tests (User Flows)
1. **Setup Playwright** (if implementing E2E tests)
   - Install: `cd frontend && npm install -D @playwright/test`
   - Create `playwright.config.ts`
   - Add test scripts to `package.json`

2. **Implement auto-naming E2E test**
   - Test complete user flow: login → create → send → verify title
   - Run: `cd frontend && npx playwright test conversation-naming.spec.ts`

3. **Implement manual rename E2E test**
   - Test inline edit flow in sidebar
   - Run: `cd frontend && npx playwright test conversation-naming.spec.ts::test_manual_rename_flow`

### Running Tests

**Backend Unit Tests**:
```bash
cd /Users/pablolozano/Mac\ Projects\ August/genesis/backend
pytest tests/unit/ -v
```

**Backend Integration Tests**:
```bash
cd /Users/pablolozano/Mac\ Projects\ August/genesis/backend
pytest tests/integration/ -v -m integration
```

**All Backend Tests**:
```bash
cd /Users/pablolozano/Mac\ Projects\ August/genesis/backend
pytest -v
```

**Frontend Tests** (once configured):
```bash
cd /Users/pablolozano/Mac\ Projects\ August/genesis/frontend
npm test                    # Unit tests with Vitest
npx playwright test        # E2E tests with Playwright
```

**Test Coverage Report** (recommended to add):
```bash
cd /Users/pablolozano/Mac\ Projects\ August/genesis/backend
pytest --cov=app --cov-report=html tests/
open htmlcov/index.html
```

## Risks and Considerations

### Technical Risks

1. **Race Condition**: Auto-naming after first message might race with manual rename
   - **Mitigation**: Check message_count before updating title; if user manually renamed (message_count > 0 but title != "New Chat"), skip auto-naming
   - **Test**: Create test case where user rapidly renames during first message streaming

2. **WebSocket Testing Complexity**: Testing WebSocket flows is more complex than HTTP
   - **Mitigation**: Use Starlette's TestClient for WebSocket testing in integration tests
   - **Test**: May need to mock WebSocket connections or use real connections with test database

3. **Frontend State Synchronization**: Renamed conversation must update in sidebar immediately
   - **Mitigation**: Update ChatContext state after successful PATCH request
   - **Test**: E2E test verifying sidebar updates without page refresh

4. **Title Truncation Edge Cases**: Unicode characters, emoji, RTL text may have unexpected behavior
   - **Mitigation**: Use Unicode-aware string operations, test with diverse character sets
   - **Test**: Unit tests with emoji (2-4 bytes), Chinese characters, Arabic text

5. **Database Transaction Consistency**: Auto-naming updates conversation while saving message
   - **Mitigation**: Ensure title update doesn't block message persistence; use separate transaction or make it non-critical
   - **Test**: Simulate title update failure, verify message still saved

### Testing Technical Debt

1. **No E2E Test Infrastructure**: Project lacks E2E testing framework
   - **Impact**: Cannot test full user flows, multi-tab synchronization, real browser behavior
   - **Recommendation**: Prioritize adding Playwright for E2E tests (relatively quick setup)

2. **No Frontend Unit Tests**: No test coverage for frontend services or components
   - **Impact**: Risk of regressions in ChatContext, ConversationService, WebSocket hooks
   - **Recommendation**: Add Vitest for frontend unit tests (minimal config with Vite)

3. **Limited WebSocket Test Coverage**: No tests for WebSocket handler
   - **Impact**: WebSocket bugs may not be caught until manual testing
   - **Recommendation**: Add integration tests using Starlette TestClient for WebSocket

4. **Mock LLM Provider in Tests**: Integration tests should mock LLM to avoid external API calls and costs
   - **Current State**: `mock_llm_provider` fixture exists in conftest.py
   - **Recommendation**: Ensure all integration tests use mock, never real LLM API

### Edge Cases Requiring Special Attention

1. **Empty First Message**: User sends empty message (should fail validation)
   - **Test**: Unit test for title generation with empty string
   - **Test**: Integration test for POST message with empty content

2. **Very Long First Message**: Message > 1000 characters
   - **Test**: Verify title truncated to 50 chars without breaking Unicode
   - **Test**: Verify no database field overflow (title max_length=200)

3. **First Message is Only Whitespace**: "   \n\t  "
   - **Test**: Verify validation catches this or normalizes to empty

4. **Special Characters in Title**: Title with `/`, `\`, `"`, `'`, `<`, `>`
   - **Test**: Verify no XSS vulnerability in frontend display
   - **Test**: Verify proper escaping in MongoDB storage

5. **Concurrent Updates**: User renames while auto-naming is in progress
   - **Test**: Integration test with race condition simulation
   - **Mitigation**: Use optimistic locking or last-write-wins strategy

6. **Multiple Tabs Open**: User has same conversation open in two tabs
   - **Test**: E2E test verifying WebSocket updates propagate to all tabs
   - **Consideration**: May need WebSocket broadcast or polling mechanism

7. **Offline/Online Transitions**: User renames while offline
   - **Test**: E2E test with network throttling/disconnection
   - **Consideration**: May need retry logic or queue for failed updates

## Testing Strategy

### Test Pyramid Balance

**Recommended Distribution**:
- **60% Unit Tests**: Fast, isolated, comprehensive edge case coverage
  - Title generation utility (10 test cases)
  - Domain model validation (5 test cases)
  - Use case business logic (5 test cases)

- **30% Integration Tests**: API contracts, database interactions, WebSocket flows
  - PATCH endpoint tests (8 test cases)
  - Auto-naming integration (4 test cases)
  - WebSocket message flow (6 test cases)

- **10% End-to-End Tests**: Critical user flows only
  - Auto-name flow (1 test)
  - Manual rename flow (1 test)
  - Edge case flows (2 tests)

**Rationale**:
- Unit tests are fast and catch most bugs early
- Integration tests verify layer boundaries and real dependencies
- E2E tests are slow and brittle; reserve for critical user journeys

### CI Integration

**Current State**: No CI/CD configuration detected in project root

**Recommendations**:
1. Add `.github/workflows/backend-tests.yml` for backend pytest runs
2. Add `.github/workflows/frontend-tests.yml` for frontend tests (when implemented)
3. Require tests to pass before merging PRs
4. Generate and upload coverage reports to Codecov or similar

**Example CI Steps** (GitHub Actions):
```yaml
- name: Run Backend Tests
  run: |
    cd backend
    pytest -v --cov=app --cov-report=xml

- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./backend/coverage.xml
```

### Coverage Goals

**Targets**:
- **Backend Unit Tests**: 90%+ coverage of new code (title generation, use case logic)
- **Backend Integration Tests**: 100% coverage of new API endpoints (PATCH /conversations/{id})
- **Frontend E2E Tests**: 100% coverage of critical user flows (auto-name, manual rename)

**Measurement**:
- Use `pytest --cov` for backend coverage
- Use `vitest --coverage` for frontend coverage (when implemented)
- Exclude generated code, migrations, configuration files

### Test Quality Checklist

Before merging feature implementation, verify:
- [ ] All unit tests pass and cover edge cases (empty, long, special chars, Unicode)
- [ ] All integration tests pass and verify authorization (user can only update own conversations)
- [ ] PATCH endpoint tested for 200 success, 404 not found, 403 forbidden, 422 validation
- [ ] Auto-naming tested for first message only (not subsequent messages)
- [ ] Title generation tested for max 50 chars, first 3 words, proper truncation
- [ ] ConversationUpdate schema validated for empty, too long, None values
- [ ] WebSocket tests verify PING/PONG, error handling, streaming (if implemented)
- [ ] E2E tests verify auto-name flow, manual rename flow (if implemented)
- [ ] No test warnings or errors in output (pristine test output required per CLAUDE.md)
- [ ] Test isolation: each test can run independently, no shared state between tests
- [ ] Teardown: tests clean up created data (conversations, messages, users)

### Test Maintenance

**Best Practices**:
1. **Use descriptive test names**: `test_update_conversation_title_too_long()` not `test_update_fail()`
2. **One assertion per test**: Test one behavior per test function for clarity
3. **AAA Pattern**: Arrange (setup), Act (execute), Assert (verify) structure
4. **DRY Fixtures**: Extract common setup to conftest.py fixtures
5. **Mock External Dependencies**: Always mock LLM, never call real APIs in tests
6. **Test Data Builders**: Use factory pattern for complex test data creation
7. **Avoid Test Interdependence**: Each test should be runnable in isolation
8. **Clean Up After Tests**: Use pytest fixtures with yield for teardown

**Anti-Patterns to Avoid**:
- ❌ Testing implementation details instead of behavior
- ❌ Overly complex test setup obscuring what's being tested
- ❌ Using sleep() for timing; use proper async/await and mocks
- ❌ Sharing mutable state between tests
- ❌ Testing multiple scenarios in one test function
- ❌ Ignoring test failures or flaky tests

## Summary

Pablo, this feature requires comprehensive testing across all layers of the application:

**Unit Tests** (Priority 1):
- Title generation utility with 10+ edge cases
- ConversationUpdate schema validation
- Auto-naming business logic with mocked dependencies

**Integration Tests** (Priority 2):
- PATCH /api/conversations/{id} endpoint with full CRUD verification
- Auto-naming integration after first message
- Authorization and error handling

**E2E Tests** (Priority 3, recommended):
- Full user flow: create → send → verify auto-name
- Manual rename flow via sidebar
- Multi-tab synchronization (if WebSocket broadcasts implemented)

**Key Testing Considerations**:
- Title truncation: max 50 chars, first 3 words
- Auto-naming timing: only after first message (message_count == 0)
- Authorization: users can only update their own conversations
- Edge cases: empty, long, Unicode, special characters
- WebSocket complexity: requires different testing patterns than HTTP

**Test Infrastructure Gaps**:
- No E2E framework (recommend Playwright)
- No frontend unit tests (recommend Vitest)
- Limited WebSocket test coverage (recommend Starlette TestClient)

The testing strategy prioritizes unit tests for fast feedback, integration tests for API contracts, and selective E2E tests for critical user flows. All tests must produce pristine output with no warnings or errors, following the strict testing requirements in CLAUDE.md.
