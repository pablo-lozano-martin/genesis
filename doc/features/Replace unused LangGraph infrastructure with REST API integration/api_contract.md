# API Contract Analysis: REST Message Creation Endpoint

## Request Summary

Replace WebSocket-based message creation with a REST API endpoint (`POST /api/conversations/{id}/messages`) that accepts message creation requests and returns a single response with the created user message and generated assistant response. This migration removes the dependency on unused LangGraph infrastructure while maintaining the core message creation and LLM response generation business logic.

**Key Objective**: Provide a synchronous REST endpoint for message creation that accepts a user message, invokes the LLM provider, and returns both the saved user message and assistant response in a single JSON response.

## Relevant Files & Modules

### Files to Examine

- `backend/app/adapters/inbound/websocket_schemas.py` (lines 1-77) - WebSocket message protocol schemas defining message types and validation
- `backend/app/adapters/inbound/websocket_router.py` (lines 1-63) - WebSocket route handler with authentication and dependency injection
- `backend/app/adapters/inbound/websocket_handler.py` (lines 1-180) - Core WebSocket connection management and streaming logic
- `backend/app/adapters/inbound/message_router.py` (lines 1-70) - Existing message read-only endpoint for retrieving conversation messages
- `backend/app/adapters/inbound/conversation_router.py` (lines 1-190) - Conversation CRUD endpoints showing REST API patterns
- `backend/app/core/domain/message.py` (lines 1-77) - Message domain model with `Message`, `MessageCreate`, and `MessageResponse` schemas
- `backend/app/core/domain/conversation.py` (lines 1-70) - Conversation domain model and response schemas
- `backend/app/core/use_cases/send_message.py` (lines 1-88) - Business logic for message creation and LLM response generation
- `backend/app/core/ports/message_repository.py` (lines 1-90) - Message repository interface defining data operations
- `backend/app/core/ports/conversation_repository.py` (lines 1-101) - Conversation repository interface with metadata operations
- `backend/app/core/ports/llm_provider.py` (lines 1-61) - LLM provider interface with `generate()` and `stream()` methods
- `backend/app/infrastructure/security/dependencies.py` (lines 1-80) - OAuth2 authentication dependency and `CurrentUser` type alias
- `backend/app/main.py` (lines 1-95) - FastAPI application setup and router registration
- `backend/tests/integration/test_conversation_api.py` (lines 1-216) - Integration test patterns for REST endpoints showing authentication and error handling
- `doc/general/API.md` (lines 1-188) - API reference documentation showing current endpoints and error response format
- `doc/general/ARCHITECTURE.md` (lines 1-195) - Hexagonal architecture overview and data flow patterns

### Key Functions & Endpoints

**WebSocket Current Implementation:**
- `websocket_chat_endpoint()` in `websocket_router.py` (lines 17-63) - WebSocket route handler
- `handle_websocket_chat()` in `websocket_handler.py` (lines 56-180) - Core WebSocket connection handler with streaming logic
- `ConnectionManager` class in `websocket_handler.py` (lines 26-53) - Manages WebSocket connections

**Existing REST Message Endpoints:**
- `get_conversation_messages()` in `message_router.py` (lines 20-69) - GET endpoint returning list of messages

**Domain & Business Logic:**
- `SendMessage.execute()` in `send_message.py` (lines 44-87) - Use case implementing message creation and LLM response generation
- `Message`, `MessageCreate`, `MessageResponse` in `message.py` (lines 18-77) - Domain models for messages
- `Conversation`, `ConversationCreate`, `ConversationResponse` in `conversation.py` (lines 9-70) - Domain models for conversations

**Authentication:**
- `get_current_active_user()` in `dependencies.py` (lines 56-76) - Dependency providing authenticated user
- `CurrentUser` type alias in `dependencies.py` (line 79) - Annotated type for protected routes

**Conversation Operations:**
- `create_conversation()` in `conversation_router.py` (lines 51-75) - POST endpoint returning `ConversationResponse` with HTTP 201
- `get_conversation()` in `conversation_router.py` (lines 78-113) - GET endpoint with ownership validation and HTTP 404
- `update_conversation()` in `conversation_router.py` (lines 116-156) - PATCH endpoint with authorization checks

---

## Current API Contract Overview

### Existing Endpoints & Routes

**Conversation Management:**
- `GET /api/conversations` - List user conversations (paginated)
- `POST /api/conversations` - Create new conversation, returns `ConversationResponse` (HTTP 201)
- `GET /api/conversations/{id}` - Get conversation details, returns `ConversationResponse` (HTTP 200)
- `PATCH /api/conversations/{id}` - Update conversation title, returns `ConversationResponse` (HTTP 200)
- `DELETE /api/conversations/{id}` - Delete conversation, returns HTTP 204

**Message Management:**
- `GET /api/conversations/{id}/messages` - Get all messages in conversation, returns `List[MessageResponse]` (HTTP 200)

**WebSocket:**
- `WS /ws/chat` - Real-time streaming chat using WebSocket protocol with token-by-token streaming

### Request Schemas (Pydantic Models)

**WebSocket Protocol** (`websocket_schemas.py`):
- `ClientMessage` - User message from client: `{type, conversation_id, content}`
- `ServerTokenMessage` - Token streamed from server: `{type: "token", content: str}`
- `ServerCompleteMessage` - Completion message: `{type: "complete", message_id, conversation_id}`
- `ServerErrorMessage` - Error message: `{type: "error", message, code}`

**REST Domain Models** (`message.py`):
- `MessageCreate` (lines 47-53) - Message creation schema: `{conversation_id, role, content, metadata?}`
- `ConversationCreate` (lines 37-40) - Conversation creation: `{title?}`

### Response Schemas (Pydantic Models)

**Message Response** (`message.py`, lines 56-76):
- `MessageResponse` - Public message schema: `{id, conversation_id, role, content, created_at, metadata?}`
  - Example (lines 67-75):
    ```json
    {
      "id": "507f1f77bcf86cd799439013",
      "conversation_id": "507f1f77bcf86cd799439012",
      "role": "user",
      "content": "How do I use Python decorators?",
      "created_at": "2025-01-15T10:30:00",
      "metadata": {"token_count": 8}
    }
    ```

**Conversation Response** (`conversation.py`, lines 49-69):
- `ConversationResponse` - Conversation schema: `{id, user_id, title, created_at, updated_at, message_count}`

### Validation Rules

**Message Validation**:
- Content: `str`, required, minimum length 1 (enforced in `MessageCreate` line 52 and WebSocket `ClientMessage` line 29)
- Conversation ID: `str`, required (line 28 in websocket_schemas, line 28 in message.py)
- Role: `MessageRole` enum (`USER`, `ASSISTANT`, `SYSTEM`) (line 29 in message.py)
- Metadata: optional dictionary (line 32 in message.py)

**Conversation Validation**:
- Title: optional, max 200 characters (line 40 in conversation.py)

**Query Parameters**:
- `skip`: integer, default 0, minimum 0 (message_router.py line 24)
- `limit`: integer, default 100, minimum 1, maximum 500 for messages (message_router.py line 25)

### Authentication & Authorization Patterns

**Dependency Injection** (`dependencies.py`, line 79):
```python
CurrentUser = Annotated[User, Depends(get_current_active_user)]
```

**Protected Endpoints** (all conversation/message endpoints):
- Require `CurrentUser` dependency
- Verify user owns the resource before returning/modifying

**Authorization Checks** (conversation_router.py):
- Lines 44-49: Check conversation ownership before allowing access
- Lines 99-104: Raise HTTP 403 if user doesn't own conversation
- Lines 138-144: Prevent unauthorized updates
- Lines 180-186: Prevent unauthorized deletion

### Error Response Format

**Standard HTTP Errors** (API.md, lines 173-180):
```json
{
  "detail": "Error message description"
}
```

**HTTP Status Codes**:
- `200` OK - Success
- `201` Created - Resource created
- `204` No Content - Success, no body
- `400` Bad Request - Invalid data
- `401` Unauthorized - Auth required/failed
- `403` Forbidden - Access denied
- `404` Not Found - Resource not found
- `422` Unprocessable Entity - Validation error (Pydantic validation failures)

**WebSocket Error Messages** (websocket_handler.py, lines 100-104, 112-116, 158-162):
```json
{
  "type": "error",
  "message": "Error description",
  "code": "ERROR_CODE"
}
```

Error codes: `INVALID_FORMAT`, `ACCESS_DENIED`, `LLM_ERROR`, `INTERNAL_ERROR`

---

## Impact Analysis

### API Components Affected by REST Message Creation Endpoint

**Direct Changes Required:**

1. **Request Schema** (NEW):
   - Create `MessageCreateRequest` DTO in `message.py` or separate REST schema file
   - Accept `content` and optional `metadata`
   - Omit `role` (always "user" for REST endpoint)
   - Omit `conversation_id` (from URL path)
   - Validation: content required, min 1 character, max TBD

2. **Response Schema** (NEW):
   - Create composite response containing both user message and assistant response
   - Option A: Wrapper DTO `MessagePairResponse` with `{user_message: MessageResponse, assistant_message: MessageResponse}`
   - Option B: Extended response with additional field
   - Must include generated message IDs from database

3. **Endpoint Implementation** (NEW):
   - Add `POST /api/conversations/{conversation_id}/messages` to `message_router.py`
   - HTTP 201 Created status
   - Full request/response cycle in single endpoint

4. **Business Logic** (REUSE):
   - Use existing `SendMessage` use case (send_message.py, lines 44-87)
   - Leverages current repositories and LLM provider interfaces
   - No changes to use case implementation required

5. **Error Handling**:
   - HTTP 401 - Authentication required (missing/invalid token)
   - HTTP 403 - Access denied (user doesn't own conversation)
   - HTTP 404 - Conversation not found
   - HTTP 422 - Validation error (Pydantic validation)
   - HTTP 500 - LLM provider error

**Indirect Impact:**

- **No changes** to WebSocket infrastructure (remains available for other use cases)
- **No changes** to conversation CRUD endpoints
- **No changes** to message read endpoint
- **No changes** to domain models or repositories
- **No changes** to authentication/authorization mechanisms

---

## API Contract Recommendations

### Proposed Endpoint

```
POST /api/conversations/{conversation_id}/messages
```

**Purpose**: Create a message in a conversation and generate LLM response

**Authentication**: Required (Bearer token)

**Authorization**: User must own the conversation

**HTTP Status Code**: `201 Created`

### Proposed Request Schema

**File**: `backend/app/core/domain/message.py` (add after existing schemas)

```python
class MessageCreateRequest(BaseModel):
    """
    REST API request schema for creating a message.

    Used in POST /api/conversations/{id}/messages endpoint.
    The conversation_id comes from the URL path.
    The role is always 'user' for REST API (no user choice).
    """

    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Message content from user"
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Optional metadata associated with the message"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "content": "How do I use Python decorators?",
                "metadata": None
            }
        }
```

**Rationale**:
- Omits `conversation_id` (from URL path parameter)
- Omits `role` (always `MessageRole.USER` for REST API)
- Includes content with reasonable length constraint (10000 chars)
- Optional metadata for extensibility
- Pydantic validation enforces constraints

### Proposed Response Schema

**Option A - Composite Response (RECOMMENDED)**

**File**: `backend/app/core/domain/message.py` (add after existing schemas)

```python
class MessagePairResponse(BaseModel):
    """
    Response containing both user and assistant messages.

    Returned by POST /api/conversations/{id}/messages endpoint.
    Both messages have been persisted to database.
    """

    user_message: MessageResponse
    assistant_message: MessageResponse

    class Config:
        json_schema_extra = {
            "example": {
                "user_message": {
                    "id": "507f1f77bcf86cd799439013",
                    "conversation_id": "507f1f77bcf86cd799439012",
                    "role": "user",
                    "content": "How do I use Python decorators?",
                    "created_at": "2025-01-15T10:30:00",
                    "metadata": None
                },
                "assistant_message": {
                    "id": "507f1f77bcf86cd799439014",
                    "conversation_id": "507f1f77bcf86cd799439012",
                    "role": "assistant",
                    "content": "Decorators are functions that modify other functions or classes...",
                    "created_at": "2025-01-15T10:30:01",
                    "metadata": None
                }
            }
        }
```

**Rationale**:
- Clear separation of user and assistant messages
- Matches WebSocket behavior (both messages saved together)
- Allows clients to display both messages immediately
- Extensible for future metadata
- Explicit structure prevents confusion about message order

### Proposed Endpoint Handler

**File**: `backend/app/adapters/inbound/message_router.py` (add to existing router)

**Location**: After existing `get_conversation_messages()` endpoint (after line 69)

**Implementation Pattern** (reference: conversation_router.py create_conversation, lines 51-75):

```python
@router.post("/{conversation_id}/messages", response_model=MessagePairResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    conversation_id: str,
    message_data: MessageCreateRequest,
    current_user: CurrentUser
):
    """
    Create a message in a conversation and generate LLM response.

    This endpoint:
    1. Validates user owns the conversation
    2. Saves the user's message
    3. Calls the LLM provider with conversation history
    4. Saves the assistant's response
    5. Updates conversation message count

    Returns both messages (user and assistant) in the response.

    Args:
        conversation_id: ID of the conversation
        message_data: Request body with message content
        current_user: Authenticated user from dependency

    Returns:
        MessagePairResponse with user and assistant messages

    Raises:
        HTTPException:
            - 404 if conversation not found
            - 403 if user doesn't own conversation
            - 422 if validation fails
            - 500 if LLM provider fails
    """
    logger.info(f"Creating message in conversation {conversation_id} for user {current_user.id}")

    # Verify conversation exists and user owns it
    conversation = await conversation_repository.get_by_id(conversation_id)

    if not conversation:
        logger.warning(f"Conversation {conversation_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    if conversation.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted to access conversation {conversation_id} owned by {conversation.user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Use existing SendMessage use case
    llm_provider = get_llm_provider()
    send_message_use_case = SendMessage(
        message_repository=message_repository,
        conversation_repository=conversation_repository,
        llm_provider=llm_provider
    )

    try:
        assistant_message = await send_message_use_case.execute(
            conversation_id=conversation_id,
            user_message_content=message_data.content
        )

        # Retrieve the user message (last-1 in conversation)
        messages = await message_repository.get_by_conversation_id(
            conversation_id=conversation_id,
            limit=2
        )
        # Messages are ordered by creation time, assistant is last
        user_message = messages[-2] if len(messages) >= 2 else messages[0]

        logger.info(f"Created message pair in conversation {conversation_id}")

        return MessagePairResponse(
            user_message=MessageResponse(
                id=user_message.id,
                conversation_id=user_message.conversation_id,
                role=user_message.role,
                content=user_message.content,
                created_at=user_message.created_at,
                metadata=user_message.metadata
            ),
            assistant_message=MessageResponse(
                id=assistant_message.id,
                conversation_id=assistant_message.conversation_id,
                role=assistant_message.role,
                content=assistant_message.content,
                created_at=assistant_message.created_at,
                metadata=assistant_message.metadata
            )
        )

    except ValueError as e:
        logger.error(f"Validation error creating message: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating message in conversation {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate response"
        )
```

### Validation Changes

**Input Validation**:
- Use Pydantic `MessageCreateRequest` model with field constraints
- Content: required, min 1 char, max 10000 chars (prevents abuse/spam)
- Metadata: optional dict (allow flexibility)
- Conversation ID: from path parameter (FastAPI automatic validation)

**Business Logic Validation** (SendMessage.execute() already handles):
- Empty message check (send_message.py, line 58)
- Conversation existence check (send_message.py, lines 61-63)
- Message content strip/trim (send_message.py, line 68)

**Authorization Validation** (endpoint implementation):
- User owns conversation (raise 403 if not)
- Conversation exists (raise 404 if not)

### Error Handling Strategy

| Scenario | HTTP Status | Detail | Code |
|----------|-------------|--------|------|
| Missing auth token | 401 | "Not authenticated" | (Framework default) |
| Invalid/expired token | 401 | "Could not validate credentials" | (Framework default) |
| Conversation not found | 404 | "Conversation not found" | (custom) |
| User doesn't own conversation | 403 | "Access denied" | (custom) |
| Invalid request body | 422 | Pydantic validation errors | (Framework default) |
| Empty message content | 422 | "Message content cannot be empty" | (use case validation) |
| LLM provider error | 500 | "Failed to generate response" | (custom) |

### Data Flow Diagram

```
REST Client
    ↓
POST /api/conversations/{id}/messages
    ↓
FastAPI Route Handler (message_router.py)
    ├─ Extract path param: conversation_id
    ├─ Extract body: MessageCreateRequest
    ├─ Verify auth: CurrentUser dependency → validates JWT
    ├─ Check authorization: user owns conversation?
    │   ├─ NO → raise HTTP 403
    │   └─ YES → continue
    │
    ├─ Instantiate SendMessage Use Case
    │   ├─ message_repository (MongoDB adapter)
    │   ├─ conversation_repository (MongoDB adapter)
    │   └─ llm_provider (OpenAI/Anthropic/etc adapter)
    │
    ├─ Execute use case
    │   ├─ Save user message (MessageCreate with role=USER)
    │   ├─ Get conversation history from repository
    │   ├─ Call LLM provider with conversation history
    │   ├─ Save assistant response (MessageCreate with role=ASSISTANT)
    │   ├─ Increment conversation message_count by 2
    │   └─ Return assistant_message entity
    │
    ├─ Retrieve user message from repository
    ├─ Build MessagePairResponse
    │   ├─ user_message: MessageResponse
    │   └─ assistant_message: MessageResponse
    │
    └─ Return HTTP 201 with JSON response body

Database (MongoDB)
    └─ Two documents created/updated in messages collection
```

---

## Implementation Guidance

### Step-by-Step Approach

**Phase 1: Schema Definition** (1 endpoint)
1. Add `MessageCreateRequest` to `backend/app/core/domain/message.py`
   - Content: required string, min 1, max 10000
   - Metadata: optional dict
2. Add `MessagePairResponse` to `backend/app/core/domain/message.py`
   - Contains two `MessageResponse` objects (user and assistant)
3. Import SendMessage use case (already exists in send_message.py)

**Phase 2: Endpoint Implementation** (1 endpoint)
1. Add import to `message_router.py`:
   - `from app.core.use_cases.send_message import SendMessage`
   - `from app.core.domain.message import MessageCreateRequest, MessagePairResponse`
   - `from app.adapters.outbound.llm_providers.provider_factory import get_llm_provider`
2. Add POST endpoint handler to `message_router.py`:
   - Route: `/{conversation_id}/messages`
   - Method: POST
   - Status code: 201 Created
   - Response model: MessagePairResponse
   - Dependencies: CurrentUser
   - Logic: Follow conversation_router.py patterns for auth checks
3. Use existing `SendMessage.execute()` (no changes needed)

**Phase 3: Testing** (comprehensive coverage)
1. Unit tests for schemas:
   - Valid MessageCreateRequest payloads
   - Invalid payloads (empty content, too long content, wrong types)
2. Integration tests:
   - Successful message creation (201 with both messages)
   - Missing conversation (404)
   - Unauthorized access to another user's conversation (403)
   - Unauthorized request without token (401)
   - Invalid request body (422)
   - LLM provider error handling (500)
3. End-to-end test:
   - Create conversation
   - Create message
   - Verify both user and assistant messages saved
   - Verify conversation message_count incremented by 2
   - Retrieve messages via GET endpoint

### Following RESTful Principles

✓ **Correct HTTP Method**: POST (creates new resource - messages)
✓ **Correct Status Code**: 201 Created (new resource created)
✓ **Resource in URL**: `/conversations/{id}/messages` (messages nested under conversation)
✓ **Idempotency**: Not idempotent (multiple calls create multiple message pairs) - acceptable for chat UX
✓ **Self-Describing**: Response contains all data (message IDs, timestamps, content)
✓ **Status Codes**: Standard error codes (401, 403, 404, 422, 500)
✓ **Content Negotiation**: JSON request/response (via Pydantic)

### Following FastAPI Best Practices

✓ **Dependency Injection**: `CurrentUser` for auth (dependencies.py line 79)
✓ **Type Annotations**: All parameters typed with Pydantic models
✓ **Response Models**: `MessagePairResponse` for automatic validation/serialization
✓ **Status Codes**: Explicit `status_code=status.HTTP_201_CREATED`
✓ **Error Handling**: HTTPException with appropriate status codes
✓ **Logging**: Consistent logging pattern (message_router.py, conversation_router.py)
✓ **Documentation**: Docstring explains endpoint behavior, parameters, exceptions

---

## Risks and Considerations

### Backward Compatibility

**Risk**: None - new endpoint doesn't change existing API surface
- ✓ Existing WebSocket remains available
- ✓ Existing message GET endpoint unchanged
- ✓ Existing conversation CRUD unchanged
- ✓ No schema changes to existing responses

### Breaking Changes

**None identified** - purely additive change

### LLM Provider Error Handling

**Current State** (websocket_handler.py, lines 156-162):
- Catches exceptions from `llm_provider.stream()`
- Sends error message to client
- Connection remains open for retry

**Proposed REST Behavior**:
- Catch exceptions from `llm_provider.generate()` (SendMessage.execute)
- Return HTTP 500 with error detail
- Client receives synchronous error response
- Transient failures (timeouts, rate limits) require client retry logic

**Recommendation**:
- Implement timeout handling in LLM provider calls
- Consider exponential backoff for client retries
- Document expected error scenarios in API docs

### Message Retrieval Timing

**Current Implementation Concern** (step 1: retrieve user message):
The user message is saved by `SendMessage.execute()` but then retrieved by querying the repository. There's potential for race conditions if:
- Multiple messages are added concurrently
- Message ordering relies purely on timestamps with low resolution

**Better Approach**:
Modify `SendMessage.execute()` to return both messages (already returns assistant_message):
```python
async def execute(...) -> Tuple[Message, Message]:
    # ... existing code saves user_message ...
    saved_user_message = await self.message_repository.create(user_message)
    # ... existing code generates and saves assistant_message ...
    return saved_user_message, assistant_message_entity
```

This ensures you have exact message objects without additional database query.

### Streaming Removal Trade-offs

**Loss**:
- Token-by-token streaming feedback to user
- Real-time response visibility during generation
- WebSocket persistent connection benefits

**Gain**:
- Simpler client implementation (single request/response)
- Easier error handling (single response)
- Standard HTTP caching/proxying support
- Simpler testing and debugging
- Better for non-real-time use cases

**Recommendation**:
- Document that REST endpoint waits for full LLM response
- Mention WebSocket for streaming use cases
- Set reasonable timeout on LLM calls (to prevent hanging requests)

### Conversation Message Count Accuracy

**Current Implementation** (websocket_handler.py line 148, send_message.py line 85):
- Increments by 2 (user message + assistant message)
- Race condition possible if concurrent messages to same conversation

**Mitigation**:
- SendMessage.execute() already handles increment (line 85 in send_message.py)
- Works correctly whether called via WebSocket or REST
- Atomic operation in MongoDB (increment operation)

### Database Load

**Comparison**:
- WebSocket: Streaming only returns tokens, doesn't query DB repeatedly for streaming
- REST: Full request/response cycle, database queries for validation and persistence
- Impact: Negligible for typical chat workloads

---

## Testing Strategy

### Unit Tests

**File**: `backend/tests/unit/test_message_api_schemas.py` (new)

```python
import pytest
from app.core.domain.message import MessageCreateRequest, MessagePairResponse, MessageResponse

class TestMessageCreateRequest:
    """Test request validation schema."""

    def test_valid_message_request(self):
        """Valid request passes validation."""
        request = MessageCreateRequest(content="Hello")
        assert request.content == "Hello"
        assert request.metadata is None

    def test_content_required(self):
        """Content is required."""
        with pytest.raises(ValueError):
            MessageCreateRequest()

    def test_content_minimum_length(self):
        """Content cannot be empty."""
        with pytest.raises(ValueError):
            MessageCreateRequest(content="")

    def test_content_maximum_length(self):
        """Content cannot exceed 10000 characters."""
        with pytest.raises(ValueError):
            MessageCreateRequest(content="x" * 10001)

    def test_metadata_optional(self):
        """Metadata is optional."""
        request = MessageCreateRequest(content="Hello", metadata={"key": "value"})
        assert request.metadata == {"key": "value"}

class TestMessagePairResponse:
    """Test response composition schema."""

    def test_valid_message_pair(self):
        """Valid message pair response."""
        from datetime import datetime
        user_msg = MessageResponse(
            id="1", conversation_id="c1", role="user",
            content="Hello", created_at=datetime.now()
        )
        asst_msg = MessageResponse(
            id="2", conversation_id="c1", role="assistant",
            content="Hi", created_at=datetime.now()
        )
        pair = MessagePairResponse(user_message=user_msg, assistant_message=asst_msg)
        assert pair.user_message == user_msg
        assert pair.assistant_message == asst_msg
```

### Integration Tests

**File**: `backend/tests/integration/test_message_create_api.py` (new)

```python
import pytest
from httpx import AsyncClient

@pytest.mark.integration
class TestMessageCreateAPI:
    """Integration tests for POST /api/conversations/{id}/messages."""

    async def create_conversation(self, client: AsyncClient, headers: dict) -> str:
        """Helper: Create conversation and return ID."""
        response = await client.post(
            "/api/conversations",
            json={"title": "Test"},
            headers=headers
        )
        return response.json()["id"]

    @pytest.mark.asyncio
    async def test_create_message_success(self, client: AsyncClient):
        """Test successful message creation with both messages."""
        # Setup: Create user and conversation
        headers = await self.create_user_and_login(client)
        conversation_id = await self.create_conversation(client, headers)

        # Execute: Create message
        response = await client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": "What is Python?"},
            headers=headers
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert "user_message" in data
        assert "assistant_message" in data
        assert data["user_message"]["content"] == "What is Python?"
        assert data["user_message"]["role"] == "user"
        assert data["assistant_message"]["role"] == "assistant"
        assert len(data["assistant_message"]["content"]) > 0

    @pytest.mark.asyncio
    async def test_create_message_conversation_not_found(self, client: AsyncClient):
        """Test 404 when conversation doesn't exist."""
        headers = await self.create_user_and_login(client)

        response = await client.post(
            "/api/conversations/000000000000000000000000/messages",
            json={"content": "Hello"},
            headers=headers
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_message_access_denied(self, client: AsyncClient):
        """Test 403 when user doesn't own conversation."""
        # User A creates conversation
        headers_a = await self.create_user_and_login(client)
        conversation_id = await self.create_conversation(client, headers_a)

        # User B tries to add message
        headers_b = await self.create_user_and_login(client)
        response = await client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": "Hacked"},
            headers=headers_b
        )

        assert response.status_code == 403
        assert "denied" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_message_unauthorized(self, client: AsyncClient):
        """Test 401 when not authenticated."""
        response = await client.post(
            "/api/conversations/any-id/messages",
            json={"content": "Hello"}
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_message_validation_error(self, client: AsyncClient):
        """Test 422 when content validation fails."""
        headers = await self.create_user_and_login(client)
        conversation_id = await self.create_conversation(client, headers)

        # Empty content
        response = await client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": ""},
            headers=headers
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_message_updates_count(self, client: AsyncClient):
        """Test that message_count is updated after creation."""
        headers = await self.create_user_and_login(client)
        conversation_id = await self.create_conversation(client, headers)

        # Create message
        await client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": "Hello"},
            headers=headers
        )

        # Check conversation message count incremented by 2
        response = await client.get(
            f"/api/conversations/{conversation_id}",
            headers=headers
        )

        assert response.json()["message_count"] == 2
```

### Test Coverage Goals

- **Request Schema Validation**: 4-6 tests (empty, min/max length, valid cases)
- **Response Schema**: 2-3 tests (structure, composition)
- **Happy Path**: 1 test (successful creation returns both messages)
- **Not Found**: 1 test (conversation doesn't exist → 404)
- **Authorization**: 2 tests (unauthorized request, user doesn't own conversation)
- **Validation Errors**: 1-2 tests (invalid content)
- **Integration with Repositories**: 1 test (messages persisted correctly)
- **Integration with LLM**: 1 test (response generated and saved)

**Total**: ~15-20 tests providing comprehensive coverage

---

## Summary of Key Implementation Decisions

### 1. Response Structure: MessagePairResponse

**Decision**: Return both user and assistant messages in single response
- **Rationale**: Matches WebSocket behavior (both messages saved together), clearer API contract, easier client handling
- **Alternative Rejected**: Return only assistant message (incomplete - user message also needed)
- **Alternative Rejected**: Return full conversation state (heavyweight, not RESTful)

### 2. Synchronous vs Streaming

**Decision**: Synchronous REST endpoint (full LLM response returned in single HTTP response)
- **Rationale**: Standard HTTP, simpler for clients, easier error handling, suitable for non-real-time use cases
- **Trade-off**: Loss of token-by-token streaming feedback (WebSocket still available)
- **Timeout Consideration**: LLM calls may take 5-30+ seconds - document in API

### 3. Business Logic Reuse

**Decision**: Use existing `SendMessage` use case without modification
- **Rationale**: Hexagonal architecture already separates domain from infrastructure
- **Implementation**: Instantiate use case in endpoint handler with required dependencies
- **Benefits**: No duplication, consistent business logic, easy to test

### 4. Error Handling

**Decision**: Standard HTTP error responses (401, 403, 404, 422, 500)
- **Rationale**: RESTful conventions, client familiarity, framework support
- **Distinction from WebSocket**: WebSocket uses streaming error messages within connection; REST uses HTTP status codes
- **Documentation**: Errors documented in API.md with status codes and detail field

### 5. Request/Response Payload Location

**Decision**:
- Request body: `MessageCreateRequest` with content and optional metadata
- URL path parameter: `conversation_id`
- No role field (always USER for REST endpoint)

**Rationale**:
- RESTful convention (resource ID in path, data in body)
- Role determined by endpoint (REST endpoint = user message)
- Metadata optional for extensibility (logging, feature flags, etc)

### 6. Authorization Pattern

**Decision**: Reuse existing `CurrentUser` dependency for authentication, implement conversation ownership check in endpoint
- **Rationale**: Consistent with existing endpoints (conversation_router.py), leverages FastAPI dependency injection
- **Error Handling**: 401 for missing auth, 403 for ownership violation

---

## References to Existing API Patterns

All implementation decisions reference existing patterns in the codebase:

| Pattern | Location | Line Numbers |
|---------|----------|--------------|
| POST endpoint with HTTP 201 | conversation_router.py | 51-75 |
| Response model mapping | conversation_router.py | 68-75 |
| Ownership validation | conversation_router.py | 99-104 |
| Error responses (404, 403) | conversation_router.py | 94-104, 138-144 |
| CurrentUser dependency | message_router.py | 20 |
| Logging pattern | message_router.py | 33, 57 |
| Query parameter validation | message_router.py | 24-25 |
| Repository instantiation | message_router.py | 16-17 |
| Use case pattern | send_message.py | 26-87 |
| Business logic with multiple repos | send_message.py | 44-87 |
| Pydantic schema patterns | message.py, conversation.py | 18-77 |
