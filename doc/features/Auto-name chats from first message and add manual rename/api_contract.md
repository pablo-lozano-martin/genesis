# API Contract Analysis

## Request Summary

Add automatic conversation naming based on the first user message and support manual conversation renaming. This involves analyzing the existing PATCH endpoint for conversation updates and determining the best approach for implementing auto-naming (client-side vs server-side).

## Relevant Files & Modules

### Backend API Routes & Handlers

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/conversation_router.py` - REST API endpoints for conversation CRUD operations, including PATCH /api/conversations/{id} for updates
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket handler that processes chat messages and could trigger auto-naming
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_router.py` - WebSocket route definition for /ws/chat endpoint
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_router.py` - Message retrieval endpoints with authorization checks

### Domain Models & Schemas

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/conversation.py` - Conversation domain model and DTOs (Conversation, ConversationCreate, ConversationUpdate, ConversationResponse)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py` - WebSocket message protocol schemas (ClientMessage, ServerTokenMessage, ServerCompleteMessage, ServerErrorMessage)

### Repository Layer

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/conversation_repository.py` - IConversationRepository interface defining data operations contract
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_conversation_repository.py` - MongoDB implementation of conversation repository with update() method
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_models.py` - Beanie ODM ConversationDocument model

### Frontend Services & Components

- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/conversationService.ts` - TypeScript API client for conversation operations (currently lacks updateConversation method)
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx` - React context managing conversation and message state
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/ConversationSidebar.tsx` - UI component displaying conversation list with titles

### Tests

- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_conversation_api.py` - Integration tests for conversation API (missing update/patch tests)
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_domain_models.py` - Unit tests for Pydantic models including ConversationCreate and ConversationUpdate

### Key Functions & Endpoints

- **PATCH /api/conversations/{conversation_id}** in `conversation_router.py:116-156` - Updates conversation metadata (currently supports title updates)
- **update_conversation()** in `conversation_router.py:117-156` - Endpoint handler with ownership validation
- **MongoConversationRepository.update()** in `mongo_conversation_repository.py:73-95` - Repository method that updates conversation and sets updated_at timestamp
- **handle_websocket_chat()** in `websocket_handler.py:56-179` - WebSocket handler that processes user messages (potential trigger point for auto-naming)

## Current API Contract Overview

### Endpoints & Routes

#### Existing Conversation Endpoints

1. **GET /api/conversations** (Lines 19-48 in conversation_router.py)
   - Lists all conversations for authenticated user
   - Query params: `skip` (default: 0), `limit` (default: 100, max: 100)
   - Response: `List[ConversationResponse]`
   - Authorization: Requires valid JWT token

2. **POST /api/conversations** (Lines 51-75 in conversation_router.py)
   - Creates new conversation
   - Request body: `ConversationCreate` (optional title, defaults to "New Conversation")
   - Response: `ConversationResponse` with 201 status
   - Authorization: Requires valid JWT token

3. **GET /api/conversations/{conversation_id}** (Lines 78-113 in conversation_router.py)
   - Retrieves specific conversation
   - Response: `ConversationResponse`
   - Authorization: Requires ownership validation
   - Errors: 404 if not found, 403 if access denied

4. **PATCH /api/conversations/{conversation_id}** (Lines 116-156 in conversation_router.py)
   - Updates conversation details (currently title only)
   - Request body: `ConversationUpdate`
   - Response: `ConversationResponse`
   - Authorization: Requires ownership validation
   - Errors: 404 if not found, 403 if access denied

5. **DELETE /api/conversations/{conversation_id}** (Lines 159-189 in conversation_router.py)
   - Deletes conversation and all messages
   - Response: 204 No Content
   - Authorization: Requires ownership validation
   - Errors: 404 if not found, 403 if access denied

#### WebSocket Endpoint

**WS /ws/chat** (Lines 17-62 in websocket_router.py)
- Handles real-time chat streaming
- Authentication via token (query param or Authorization header)
- Protocol: Client sends ClientMessage, server streams ServerTokenMessage, completes with ServerCompleteMessage
- Error handling: ServerErrorMessage with error codes (INVALID_FORMAT, ACCESS_DENIED, LLM_ERROR, INTERNAL_ERROR)

### Request Schemas

#### ConversationCreate (Lines 37-40 in conversation.py)
```python
class ConversationCreate(BaseModel):
    title: Optional[str] = Field(default="New Conversation", max_length=200)
```
- All fields optional with defaults
- Title limited to 200 characters
- No minimum length validation

#### ConversationUpdate (Lines 43-46 in conversation.py)
```python
class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
```
- Title is optional (allows partial updates)
- Max length: 200 characters
- Uses `exclude_unset=True` in repository layer (line 88 in mongo_conversation_repository.py)
- No minimum length validation
- No additional fields defined

#### ClientMessage (Lines 20-29 in websocket_schemas.py)
```python
class ClientMessage(BaseModel):
    type: MessageType = Field(default=MessageType.MESSAGE)
    conversation_id: str = Field(..., description="Conversation UUID")
    content: str = Field(..., min_length=1, description="User message content")
```
- Validates user messages sent via WebSocket
- Requires non-empty content

### Response Schemas

#### ConversationResponse (Lines 49-69 in conversation.py)
```python
class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
```
- All fields required in response
- Used consistently across all conversation endpoints
- Includes metadata for UI display (message count, timestamps)

#### Frontend TypeScript Interface (Lines 9-16 in conversationService.ts)
```typescript
export interface Conversation {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}
```
- Matches backend ConversationResponse schema exactly

### Validation Rules

#### Pydantic Model Validation

1. **Title Field Validation**
   - Max length: 200 characters (enforced by Pydantic Field)
   - Optional in both Create and Update schemas
   - No min length constraint
   - No pattern/regex validation

2. **Message Count Validation** (Line 22 in conversation.py)
   - Must be >= 0 (enforced by `ge=0`)
   - Automatically incremented via `increment_message_count()` method

3. **User ID Validation**
   - Required field (string type)
   - No format validation (should be MongoDB ObjectId string)

#### HTTP-Level Validation

1. **Authorization Checks**
   - All endpoints require `CurrentUser` dependency
   - Ownership validation: `conversation.user_id != current_user.id` → 403 Forbidden
   - Missing conversation: 404 Not Found

2. **WebSocket Message Validation**
   - Invalid JSON format → ServerErrorMessage with code "INVALID_FORMAT"
   - Invalid conversation access → ServerErrorMessage with code "ACCESS_DENIED"
   - LLM streaming errors → ServerErrorMessage with code "LLM_ERROR"

## Impact Analysis

### Affected Components

#### For Manual Rename Feature

1. **Frontend Service Layer** (conversationService.ts)
   - **Missing method**: `updateConversation(id: string, data: UpdateConversationRequest)`
   - Current implementation has no update method despite backend PATCH endpoint existing
   - Need to add TypeScript interface for update request

2. **Frontend Context Layer** (ChatContext.tsx)
   - **Missing method**: `renameConversation(id: string, newTitle: string)`
   - Context exposes createConversation and deleteConversation but not update
   - Should update local state after successful rename

3. **UI Component** (ConversationSidebar.tsx)
   - Currently displays read-only title (line 44)
   - Need UI affordance for rename (e.g., inline edit, modal, or context menu)
   - Should handle rename action and optimistic updates

4. **Backend Endpoint** (conversation_router.py:116-156)
   - **Already exists and functional**: PATCH /api/conversations/{conversation_id}
   - Validates ownership correctly
   - Returns updated ConversationResponse
   - **No changes needed** - the API contract is complete

#### For Auto-Naming Feature

1. **WebSocket Handler** (websocket_handler.py)
   - Line 125: After saving user message, could check if message_count == 0
   - Line 148: After incrementing message count, conversation object is not retrieved
   - Need to call conversation_repository.update() to set auto-generated title

2. **Conversation Repository** (mongo_conversation_repository.py)
   - update() method already exists (lines 73-95)
   - Accepts ConversationUpdate and performs partial updates
   - **No changes needed** - repository contract is sufficient

3. **Domain Schema** (conversation.py)
   - ConversationUpdate schema supports title updates
   - **No changes needed** - existing contract is adequate

4. **LLM Integration** (Not examined in detail)
   - Need to determine how to generate title from first message
   - Likely requires new use case or service method
   - Could use same LLM provider or separate title generation logic

### Data Flow Changes

#### Current Update Flow (Manual Rename)
```
Frontend Component
  → (NOT IMPLEMENTED) conversationService.updateConversation()
  → PATCH /api/conversations/{id}
  → conversation_router.update_conversation()
  → Authorization checks (ownership)
  → MongoConversationRepository.update()
  → ConversationDocument.save()
  → ConversationResponse returned
```

#### Proposed Auto-Naming Flow (Option 1: Server-Side)
```
WebSocket receives first message
  → handle_websocket_chat() detects message_count == 0
  → Generate title from user message content
  → conversation_repository.update() with generated title
  → Continue normal message processing
  → Frontend polls/refreshes conversation list to see new title
```

#### Proposed Auto-Naming Flow (Option 2: Client-Side)
```
Frontend sends first message via WebSocket
  → Receives ServerCompleteMessage
  → ChatContext detects first message in conversation
  → Calls conversationService.updateConversation() with generated title
  → PATCH /api/conversations/{id}
  → Updates local state with new title
```

## API Contract Recommendations

### For Manual Rename Feature

#### No Backend Changes Required

The existing PATCH endpoint fully supports manual renaming. The backend contract is complete and follows RESTful principles:

- ✓ Proper HTTP method (PATCH for partial updates)
- ✓ Idempotent operation
- ✓ Ownership validation
- ✓ Appropriate status codes (200 OK, 404 Not Found, 403 Forbidden)
- ✓ Proper schema validation (max 200 chars)

#### Frontend Implementation Needed

1. **Add Update Method to conversationService.ts**
```typescript
export interface UpdateConversationRequest {
  title?: string;
}

async updateConversation(id: string, data: UpdateConversationRequest): Promise<Conversation> {
  const response = await axios.patch(`${API_URL}/api/conversations/${id}`, data, {
    headers: this.getAuthHeaders(),
  });
  return response.data;
}
```

2. **Add Rename Method to ChatContext.tsx**
```typescript
const renameConversation = async (id: string, newTitle: string) => {
  try {
    const updated = await conversationService.updateConversation(id, { title: newTitle });
    setConversations(prev => prev.map(c => c.id === id ? updated : c));
    if (currentConversation?.id === id) {
      setCurrentConversation(updated);
    }
  } catch (err) {
    console.error("Failed to rename conversation:", err);
  }
};
```

3. **UI Component Enhancement**
- Add inline edit capability or rename button to ConversationSidebar
- Implement optimistic UI updates for better UX
- Handle validation errors (e.g., title too long)

### For Auto-Naming Feature

#### Recommended Approach: Server-Side Auto-Naming

**Rationale:**
- Keeps business logic on server (separation of concerns)
- Frontend doesn't need LLM integration for title generation
- Single source of truth for when auto-naming occurs
- No race conditions between multiple clients
- Better for future features (e.g., background title regeneration)

#### Proposed Backend Changes

1. **New Use Case: GenerateConversationTitle**

Create `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/use_cases/generate_conversation_title.py`:

```python
class GenerateConversationTitle:
    """
    Use case to generate a concise conversation title from first message.

    This should be called automatically after the first user message.
    """

    async def execute(self, user_message_content: str) -> str:
        # Truncate long messages
        # Extract key phrases or use LLM to generate title
        # Return concise title (max 200 chars)
        pass
```

2. **Modify WebSocket Handler**

In `websocket_handler.py`, after line 126 (after saving user message):

```python
# Check if this is the first message (before incrementing count)
if conversation.message_count == 0:
    # Generate title from first user message
    generated_title = await generate_conversation_title(client_message.content)

    # Update conversation with generated title
    await conversation_repository.update(
        conversation_id,
        ConversationUpdate(title=generated_title)
    )
    logger.info(f"Auto-named conversation {conversation_id}: {generated_title}")
```

3. **No Schema Changes Needed**
- ConversationUpdate already supports optional title
- No new API endpoints required
- No new response fields needed

#### Alternative Approach: Client-Side Auto-Naming

If server-side is not desired, the client could:
1. Detect first message sent (message_count == 0 before sending)
2. After receiving ServerCompleteMessage, extract key words from user message
3. Call PATCH /api/conversations/{id} with generated title

**Drawbacks:**
- Requires client-side title generation logic
- Multiple clients could cause race conditions
- Less control over quality of generated titles
- Extra API call adds latency

#### WebSocket Protocol Consideration

**Option: Add Title to ServerCompleteMessage**

If auto-naming is server-side, consider extending ServerCompleteMessage to include updated conversation metadata:

```python
class ServerCompleteMessage(BaseModel):
    type: MessageType = Field(default=MessageType.COMPLETE)
    message_id: str
    conversation_id: str
    conversation_title: Optional[str] = None  # NEW: Include if title was auto-generated
```

**Benefits:**
- Frontend immediately knows about title change
- No need to refetch conversation list
- Better UX (instant title update in sidebar)

**Drawbacks:**
- Breaks existing WebSocket contract (requires frontend update)
- Adds complexity to message protocol
- Consider versioning if this is a breaking change

### Validation Enhancements

#### Recommended: Add Minimum Title Length

Current schema allows empty string title. Consider adding validation:

```python
class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
```

#### Recommended: Sanitize Generated Titles

For auto-generated titles, ensure:
- No leading/trailing whitespace
- No special characters that break UI
- Fallback to "New Conversation" if generation fails
- Truncate at word boundaries if too long

## Implementation Guidance

### Step-by-Step Approach for Manual Rename

1. **Frontend Service Layer** (Low Risk)
   - Add `updateConversation()` method to conversationService.ts
   - Add TypeScript interface `UpdateConversationRequest`
   - Test API call manually or with integration tests

2. **Frontend Context Layer** (Low Risk)
   - Add `renameConversation()` to ChatContext
   - Update local state optimistically
   - Handle errors gracefully

3. **UI Component** (Medium Risk)
   - Add rename UI (button, inline edit, or modal)
   - Implement validation on frontend (max 200 chars)
   - Show loading state during API call
   - Handle errors and revert optimistic updates

4. **Integration Testing** (Required)
   - Test successful rename
   - Test rename of other user's conversation (should fail with 403)
   - Test rename of non-existent conversation (should fail with 404)
   - Test title too long (should fail with 422)

### Step-by-Step Approach for Auto-Naming

1. **Create Title Generation Use Case** (High Risk)
   - Implement logic to extract title from message
   - Consider using LLM for better quality
   - Add fallback logic if generation fails
   - Add unit tests for title generation

2. **Modify WebSocket Handler** (High Risk)
   - Add check for message_count == 0
   - Call title generation use case
   - Update conversation via repository
   - Add error handling (don't fail message processing if title generation fails)
   - Add logging for debugging

3. **Frontend Changes** (Low Risk)
   - Option A: Poll conversation list after sending first message
   - Option B: Listen for updated title in WebSocket message
   - Update UI to show generated title

4. **Testing Strategy** (Critical)
   - Test first message triggers auto-naming
   - Test subsequent messages don't trigger auto-naming
   - Test title generation failure doesn't break chat
   - Test concurrent first messages from multiple sessions
   - Test manually renamed conversations aren't auto-renamed

### Testing Approach

#### Unit Tests

1. **Test ConversationUpdate Schema Validation** (extend test_domain_models.py)
   - Valid title update
   - Empty title (should this be allowed?)
   - Title exceeding 200 chars
   - Title with special characters

2. **Test Title Generation Logic**
   - Short messages (< 50 chars)
   - Long messages (> 200 chars)
   - Messages with code blocks
   - Messages in different languages

#### Integration Tests

1. **Test PATCH Endpoint** (add to test_conversation_api.py)
   - Successful title update
   - Update non-existent conversation
   - Update other user's conversation
   - Invalid title (too long)
   - Empty request body

2. **Test Auto-Naming Flow** (new test file: test_auto_naming.py)
   - Send first message, verify title changes
   - Send second message, verify title doesn't change
   - Create conversation with custom title, send message, verify title doesn't change

#### End-to-End Tests

1. **Manual Rename E2E**
   - User creates conversation
   - User renames conversation
   - Title updates in sidebar immediately
   - Title persists after page reload

2. **Auto-Naming E2E**
   - User creates new conversation
   - User sends first message
   - Title automatically updates
   - Manual rename still works after auto-naming

## Risks and Considerations

### API Contract Risks

1. **Breaking Changes**
   - If modifying ConversationUpdate schema, ensure backward compatibility
   - If extending WebSocket protocol, version the API or make fields optional
   - Frontend and backend must be deployed in sync if protocol changes

2. **Validation Inconsistencies**
   - Frontend should validate title length before API call (better UX)
   - Backend must enforce validation as source of truth
   - Consider using shared validation schemas (e.g., via OpenAPI spec)

3. **Rate Limiting**
   - Rapid rename requests could abuse the API
   - Consider rate limiting PATCH requests per user
   - WebSocket auto-naming happens once per conversation (low risk)

### Data Consistency Risks

1. **Race Conditions**
   - Multiple clients could rename same conversation simultaneously
   - Auto-naming and manual rename could conflict
   - MongoDB document updates are atomic, so last-write-wins
   - Consider adding version field or optimistic locking if this is a concern

2. **Cache Invalidation**
   - If conversation list is cached on frontend, ensure it updates after rename
   - WebSocket doesn't notify other sessions about title changes
   - Consider adding WebSocket broadcast for conversation updates

3. **Stale UI State**
   - User A renames conversation
   - User B has same conversation open in another tab
   - User B sees stale title until refresh
   - Consider implementing real-time sync via WebSocket or polling

### Implementation Risks

1. **Auto-Naming Quality**
   - LLM-generated titles may be inconsistent or inappropriate
   - Short user messages may not provide enough context
   - Non-English messages may produce poor titles
   - Need fallback logic and content moderation

2. **Performance Impact**
   - Title generation adds latency to first message
   - LLM API calls add cost
   - Consider async/background processing if latency is high
   - Cache or reuse titles for similar messages

3. **User Experience**
   - Auto-generated titles may not match user expectations
   - Users may be confused if title changes automatically
   - Consider adding UI indicator ("Auto-named") or allow opt-out

### Security Considerations

1. **Title Content**
   - User-provided titles could contain XSS payloads
   - Auto-generated titles should be sanitized
   - Frontend should escape HTML in title display (React does this by default)

2. **Authorization**
   - Existing ownership checks are sufficient
   - No new authorization concerns for rename feature
   - Ensure auto-naming doesn't leak conversation data to other users

3. **Input Validation**
   - Title length limited to 200 chars (prevents DoS)
   - No regex or pattern validation (consider allowing emoji, unicode)
   - Consider sanitizing special characters in auto-generated titles

## Testing Strategy

### Unit Tests

**File: backend/tests/unit/test_conversation_update.py** (new file)

```python
def test_conversation_update_title():
    """Test updating conversation title with valid data."""
    update_data = ConversationUpdate(title="Updated Title")
    assert update_data.title == "Updated Title"

def test_conversation_update_title_too_long():
    """Test validation error for title exceeding 200 chars."""
    with pytest.raises(ValidationError):
        ConversationUpdate(title="x" * 201)

def test_conversation_update_empty_title():
    """Test updating with empty title (currently allowed)."""
    update_data = ConversationUpdate(title="")
    assert update_data.title == ""

def test_conversation_update_partial():
    """Test partial update with exclude_unset."""
    update_data = ConversationUpdate()
    assert update_data.model_dump(exclude_unset=True) == {}
```

**File: backend/tests/unit/test_title_generation.py** (new file for auto-naming)

```python
def test_generate_title_from_short_message():
    """Test title generation from message under 50 chars."""
    title = generate_title("What is Python?")
    assert len(title) <= 200
    assert len(title) > 0

def test_generate_title_from_long_message():
    """Test title generation from message over 200 chars."""
    long_message = "x" * 500
    title = generate_title(long_message)
    assert len(title) <= 200

def test_generate_title_fallback():
    """Test fallback when generation fails."""
    title = generate_title("")  # Edge case
    assert title == "New Conversation"
```

### Integration Tests

**File: backend/tests/integration/test_conversation_api.py** (extend existing)

```python
@pytest.mark.asyncio
async def test_update_conversation_title(self, client: AsyncClient):
    """Test PATCH /api/conversations/{id} endpoint."""
    headers = await self.create_user_and_login(client)

    # Create conversation
    create_resp = await client.post(
        "/api/conversations",
        json={"title": "Original Title"},
        headers=headers
    )
    conversation_id = create_resp.json()["id"]

    # Update title
    update_resp = await client.patch(
        f"/api/conversations/{conversation_id}",
        json={"title": "New Title"},
        headers=headers
    )

    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "New Title"

@pytest.mark.asyncio
async def test_update_conversation_unauthorized(self, client: AsyncClient):
    """Test updating another user's conversation returns 403."""
    # Create user A and conversation
    headers_a = await self.create_user_and_login(client)
    create_resp = await client.post(
        "/api/conversations",
        json={"title": "User A Conversation"},
        headers=headers_a
    )
    conversation_id = create_resp.json()["id"]

    # Try to update as user B
    headers_b = await self.create_user_and_login(client)
    update_resp = await client.patch(
        f"/api/conversations/{conversation_id}",
        json={"title": "Hacked"},
        headers=headers_b
    )

    assert update_resp.status_code == 403

@pytest.mark.asyncio
async def test_update_conversation_not_found(self, client: AsyncClient):
    """Test updating non-existent conversation returns 404."""
    headers = await self.create_user_and_login(client)

    update_resp = await client.patch(
        "/api/conversations/000000000000000000000000",
        json={"title": "New Title"},
        headers=headers
    )

    assert update_resp.status_code == 404

@pytest.mark.asyncio
async def test_update_conversation_title_too_long(self, client: AsyncClient):
    """Test validation error for title over 200 chars."""
    headers = await self.create_user_and_login(client)

    create_resp = await client.post(
        "/api/conversations",
        json={"title": "Original"},
        headers=headers
    )
    conversation_id = create_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/conversations/{conversation_id}",
        json={"title": "x" * 201},
        headers=headers
    )

    assert update_resp.status_code == 422  # Validation error
```

### End-to-End Tests

**File: frontend/e2e/conversation-rename.spec.ts** (Playwright/Cypress)

```typescript
test('user can manually rename conversation', async () => {
  // Login
  await login('testuser', 'password');

  // Create conversation
  await click('New Chat');

  // Rename conversation
  await click('conversation-options');
  await click('rename');
  await fill('title-input', 'My Custom Title');
  await click('save');

  // Verify title updated
  await expect('conversation-title').toHaveText('My Custom Title');

  // Reload page
  await reload();

  // Verify title persisted
  await expect('conversation-title').toHaveText('My Custom Title');
});

test('conversation auto-names from first message', async () => {
  // Login and create conversation
  await login('testuser', 'password');
  await click('New Chat');

  // Verify default title
  await expect('conversation-title').toHaveText('New Chat');

  // Send first message
  await fill('message-input', 'What is Python programming?');
  await click('send');

  // Wait for response
  await waitFor('assistant-message');

  // Verify title auto-updated
  await expect('conversation-title').not.toHaveText('New Chat');
  await expect('conversation-title').toContain('Python');
});
```

### API Contract Testing

**File: backend/tests/contract/test_conversation_api_contract.py** (new file)

```python
@pytest.mark.asyncio
async def test_patch_conversation_follows_http_semantics(client: AsyncClient):
    """Test PATCH endpoint is idempotent and allows partial updates."""
    headers = await create_user_and_login(client)

    # Create conversation
    create_resp = await client.post(
        "/api/conversations",
        json={"title": "Original"},
        headers=headers
    )
    conversation_id = create_resp.json()["id"]
    original_updated_at = create_resp.json()["updated_at"]

    # First PATCH
    resp1 = await client.patch(
        f"/api/conversations/{conversation_id}",
        json={"title": "Updated"},
        headers=headers
    )

    # Second PATCH with same data (idempotency test)
    resp2 = await client.patch(
        f"/api/conversations/{conversation_id}",
        json={"title": "Updated"},
        headers=headers
    )

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["title"] == resp2.json()["title"]

    # Verify updated_at changed
    assert resp1.json()["updated_at"] > original_updated_at

@pytest.mark.asyncio
async def test_patch_conversation_partial_update(client: AsyncClient):
    """Test PATCH allows partial updates (only title, no other fields)."""
    headers = await create_user_and_login(client)

    create_resp = await client.post(
        "/api/conversations",
        json={"title": "Original"},
        headers=headers
    )
    conversation_id = create_resp.json()["id"]
    original_message_count = create_resp.json()["message_count"]

    # Update only title
    update_resp = await client.patch(
        f"/api/conversations/{conversation_id}",
        json={"title": "New Title"},
        headers=headers
    )

    # Verify other fields unchanged
    assert update_resp.json()["message_count"] == original_message_count
    assert update_resp.json()["user_id"] == create_resp.json()["user_id"]
```

## Summary

### Key Findings

1. **Backend API contract is complete** for manual rename feature
   - PATCH /api/conversations/{id} endpoint exists and follows RESTful principles
   - Proper validation, authorization, and error handling in place
   - No backend changes needed for manual rename

2. **Frontend implementation is missing**
   - conversationService.ts lacks updateConversation() method
   - ChatContext doesn't expose rename functionality
   - UI component needs rename affordance

3. **Auto-naming requires new business logic**
   - WebSocket handler is ideal trigger point (after first message)
   - Need title generation use case/service
   - Existing ConversationUpdate schema supports title updates
   - Consider extending WebSocket protocol to notify client of title change

4. **Testing gaps identified**
   - No integration tests for PATCH endpoint
   - No unit tests for ConversationUpdate validation edge cases
   - Need E2E tests for rename flow

### Recommended Implementation Order

1. **Phase 1: Manual Rename (Frontend Only)**
   - Low risk, no backend changes
   - Immediate user value
   - Estimated effort: 4-8 hours

2. **Phase 2: Auto-Naming (Backend + Frontend)**
   - Higher complexity due to title generation logic
   - Requires careful testing for edge cases
   - Estimated effort: 16-24 hours

3. **Phase 3: Testing & Polish**
   - Comprehensive test coverage
   - UX refinements based on user feedback
   - Estimated effort: 8-16 hours

### Dependencies & Blockers

- No external dependencies required
- No database migrations needed (title field already exists)
- Frontend and backend can be developed in parallel for manual rename
- Auto-naming requires title generation algorithm decision (simple extraction vs LLM)
