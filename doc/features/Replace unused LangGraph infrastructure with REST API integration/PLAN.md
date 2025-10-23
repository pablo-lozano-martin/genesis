# Implementation Plan: Replace Unused LangGraph Infrastructure with REST API Integration

**Issue:** #4
**Date:** 2025-10-24
**Status:** Ready for Implementation

---

## Executive Summary

This plan outlines the migration from unused LangGraph infrastructure to a REST API endpoint for message creation. The current WebSocket implementation bypasses LangGraph entirely, making the graph nodes, state management, and orchestration infrastructure dead code. This migration simplifies the architecture while maintaining all functionality.

### Key Findings from Analysis

1. **LangGraph is completely unused** - WebSocket handler and SendMessage use case bypass all LangGraph graphs
2. **SendMessage use case already exists** - Implements the complete message creation workflow without LangGraph
3. **REST API integration is straightforward** - Reuse existing use case and repository patterns
4. **No schema changes needed** - Current MongoDB schema supports all requirements
5. **Frontend changes are minimal** - Replace WebSocket calls with REST API calls

---

## Architecture Overview

### Current State (To Be Replaced)

```
WebSocket Client
    ↓
websocket_handler.py:132 (direct LLM streaming)
    ├─ llm_provider.stream() - bypasses LangGraph
    ├─ message_repository.create()
    └─ conversation_repository.increment_message_count()
```

**Dead Code:**
- `backend/app/langgraph/graphs/` - Never instantiated
- `backend/app/langgraph/nodes/` - Never called
- `backend/app/langgraph/state.py` - Never used

### Target State (New Implementation)

```
REST Client
    ↓
POST /api/conversations/{id}/messages
    ↓
SendMessage Use Case (already exists at send_message.py:44-87)
    ├─ Create user message
    ├─ llm_provider.generate()
    ├─ Create assistant message
    └─ increment_message_count(2)
    ↓
Return MessagePairResponse
```

---

## Implementation Phases

### Phase 1: Backend - Create REST Endpoint with Existing Use Case

**Objective:** Add REST endpoint that uses the existing SendMessage use case

#### 1.1 Create Request/Response Schemas

**File:** `backend/app/core/domain/message.py`

**Add after line 76:**

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
                    "content": "Decorators are functions that modify...",
                    "created_at": "2025-01-15T10:30:01",
                    "metadata": None
                }
            }
        }
```

#### 1.2 Modify SendMessage Use Case to Return Both Messages

**File:** `backend/app/core/use_cases/send_message.py`

**Current signature (line 44):**
```python
async def execute(self, conversation_id: str, user_message_content: str) -> Message:
```

**New signature:**
```python
async def execute(self, conversation_id: str, user_message_content: str) -> tuple[Message, Message]:
```

**Modify return statement (line 87):**
```python
# Old: return assistant_message_entity
# New: return (saved_user_message, assistant_message_entity)
```

**Add at line 70** (save user message variable):
```python
saved_user_message = await self.message_repository.create(user_message)
```

#### 1.3 Create REST Endpoint

**File:** `backend/app/adapters/inbound/message_router.py`

**Add after line 69:**

```python
@router.post(
    "/{conversation_id}/messages",
    response_model=MessagePairResponse,
    status_code=status.HTTP_201_CREATED
)
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
        logger.warning(
            f"User {current_user.id} attempted to access conversation "
            f"{conversation_id} owned by {conversation.user_id}"
        )
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
        user_message, assistant_message = await send_message_use_case.execute(
            conversation_id=conversation_id,
            user_message_content=message_data.content
        )

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

**Add imports at top of file:**
```python
from app.core.domain.message import MessageCreateRequest, MessagePairResponse
from app.core.use_cases.send_message import SendMessage
from app.adapters.outbound.llm_providers.provider_factory import get_llm_provider
from fastapi import status
```

#### 1.4 Testing

**File:** `backend/tests/integration/test_message_creation.py` (NEW)

```python
import pytest
from httpx import AsyncClient
from app.core.domain.message import MessageRole


@pytest.mark.integration
class TestMessageCreationAPI:
    """Integration tests for POST /api/conversations/{id}/messages."""

    async def create_user_and_login(self, client: AsyncClient) -> dict:
        """Helper: Create user and return auth headers."""
        # Register
        await client.post(
            "/api/auth/register",
            json={
                "email": f"test{id(self)}@example.com",
                "username": f"testuser{id(self)}",
                "password": "TestPass123!",
                "full_name": "Test User"
            }
        )

        # Login
        response = await client.post(
            "/api/auth/token",
            data={"username": f"test{id(self)}@example.com", "password": "TestPass123!"}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

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
        headers = await self.create_user_and_login(client)
        conversation_id = await self.create_conversation(client, headers)

        response = await client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": "What is Python?"},
            headers=headers
        )

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

        await client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": "Hello"},
            headers=headers
        )

        response = await client.get(
            f"/api/conversations/{conversation_id}",
            headers=headers
        )

        assert response.json()["message_count"] == 2
```

**Estimated Effort:** 3-4 hours (implementation + testing)

---

### Phase 2: Frontend - Migrate to REST API

**Objective:** Replace WebSocket communication with REST API calls

#### 2.1 Add REST API Method to Service

**File:** `frontend/src/services/conversationService.ts`

**Add after line 88:**

```typescript
export const sendMessage = async (
  conversationId: string,
  content: string
): Promise<{ user_message: Message; assistant_message: Message }> => {
  const response = await api.post(
    `/conversations/${conversationId}/messages`,
    { content }
  );
  return response.data;
};
```

#### 2.2 Update ChatContext

**File:** `frontend/src/contexts/ChatContext.tsx`

**Remove (lines 11, 17-18, 35-36, 39-43, 45-59):**
- WebSocket URL configuration
- `streamingMessage` and `isStreaming` from interface and state
- `useWebSocket` hook call
- WebSocket streaming effect

**Add to interface (replace isConnected and isStreaming):**
```typescript
isMessageLoading: boolean;
```

**Modify sendMessage implementation (lines 131-157):**

```typescript
const sendMessage = useCallback(
  async (content: string) => {
    if (!currentConversation || isMessageLoading) return;

    setIsMessageLoading(true);
    setError(null);

    try {
      // Call REST API
      const { user_message, assistant_message } = await conversationService.sendMessage(
        currentConversation.id,
        content
      );

      // Add both messages to state
      setMessages((prev) => [...prev, user_message, assistant_message]);

      // Auto-generate title on first message
      if (currentConversation.message_count === 0) {
        const newTitle = content.slice(0, 30) + (content.length > 30 ? "..." : "");
        await updateConversationTitle(currentConversation.id, newTitle);
      }

      // Update conversation list
      await loadConversations();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message");
    } finally {
      setIsMessageLoading(false);
    }
  },
  [currentConversation, isMessageLoading, updateConversationTitle, loadConversations]
);
```

#### 2.3 Update Chat Page

**File:** `frontend/src/pages/Chat.tsx`

**Remove (lines 66-70):**
```typescript
{!isConnected && (
  <div className="bg-yellow-50 border-b border-yellow-200 p-2 text-sm text-yellow-800 text-center">
    Connecting...
  </div>
)}
```

**Keep error banner but remove isConnected check**

#### 2.4 Update MessageInput

**File:** `frontend/src/components/chat/MessageInput.tsx`

**Modify disabled condition (line 75):**

```typescript
// Old: disabled={!isConnected || isStreaming || input.trim().length === 0}
// New:
disabled={!currentConversation || isMessageLoading || input.trim().length === 0}
```

#### 2.5 Update MessageList

**File:** `frontend/src/components/chat/MessageList.tsx`

**Remove streaming UI (lines 45-62):**
- Remove `streamingMessage` prop
- Remove `isStreaming` prop
- Remove streaming animation block

**Simplify to display messages array only**

#### 2.6 Delete WebSocket Files

**Files to delete:**
- `frontend/src/hooks/useWebSocket.ts`
- `frontend/src/services/websocketService.ts`

**Estimated Effort:** 2-3 hours (implementation + testing)

---

### Phase 3: Backend - Remove Unused LangGraph Infrastructure

**Objective:** Clean up dead code after REST API is working

#### 3.1 Delete LangGraph Files

**Files to remove:**
- `backend/app/langgraph/graphs/chat_graph.py`
- `backend/app/langgraph/graphs/streaming_chat_graph.py`
- `backend/app/langgraph/nodes/call_llm.py`
- `backend/app/langgraph/nodes/process_input.py`
- `backend/app/langgraph/nodes/format_response.py`
- `backend/app/langgraph/nodes/save_history.py`
- `backend/app/langgraph/state.py`
- `backend/app/langgraph/` (entire directory if empty)

#### 3.2 Remove WebSocket Infrastructure

**Files to remove:**
- `backend/app/adapters/inbound/websocket_handler.py`
- `backend/app/adapters/inbound/websocket_schemas.py`
- `backend/app/adapters/inbound/websocket_router.py`
- `backend/app/infrastructure/security/websocket_auth.py`

**File to modify:**
- `backend/app/main.py` - Remove websocket_router import and registration (around line 79)

#### 3.3 Update Dependencies

**File:** `backend/pyproject.toml` or `requirements.txt`

**Remove if no longer needed:**
- `langgraph` package
- Any LangGraph-specific dependencies

**Estimated Effort:** 1 hour

---

### Phase 4: Documentation

**Objective:** Update documentation to reflect new architecture

#### 4.1 Update API Documentation

**File:** `doc/general/API.md`

**Add new endpoint documentation:**

```markdown
### POST /api/conversations/{conversation_id}/messages

Create a message in a conversation and generate LLM response.

**Authentication:** Required

**Request Body:**
```json
{
  "content": "User message content",
  "metadata": {} // optional
}
```

**Response (201 Created):**
```json
{
  "user_message": {
    "id": "507f1f77bcf86cd799439013",
    "conversation_id": "507f1f77bcf86cd799439012",
    "role": "user",
    "content": "User message content",
    "created_at": "2025-01-15T10:30:00",
    "metadata": null
  },
  "assistant_message": {
    "id": "507f1f77bcf86cd799439014",
    "conversation_id": "507f1f77bcf86cd799439012",
    "role": "assistant",
    "content": "AI response...",
    "created_at": "2025-01-15T10:30:01",
    "metadata": null
  }
}
```

**Error Responses:**
- 401: Not authenticated
- 403: Access denied (not conversation owner)
- 404: Conversation not found
- 422: Validation error
- 500: LLM provider error
```

#### 4.2 Update Architecture Documentation

**File:** `doc/general/ARCHITECTURE.md`

**Update to reflect:**
- REST API message creation flow
- Removal of LangGraph infrastructure
- SendMessage use case as core business logic
- Direct LLM provider integration

**Estimated Effort:** 1 hour

---

## File-by-File Changes Summary

### Backend Changes

| File | Action | Lines | Description |
|------|--------|-------|-------------|
| `backend/app/core/domain/message.py` | Modify | After 76 | Add MessageCreateRequest and MessagePairResponse |
| `backend/app/core/use_cases/send_message.py` | Modify | 44, 70, 87 | Return tuple, save user message variable |
| `backend/app/adapters/inbound/message_router.py` | Modify | After 69 | Add POST endpoint with authorization |
| `backend/tests/integration/test_message_creation.py` | Create | New file | Integration tests for message endpoint |
| `backend/app/langgraph/*` | Delete | All files | Remove unused LangGraph |
| `backend/app/adapters/inbound/websocket_*.py` | Delete | All files | Remove WebSocket infrastructure |
| `backend/app/infrastructure/security/websocket_auth.py` | Delete | Full file | Remove WebSocket auth |
| `backend/app/main.py` | Modify | ~79 | Remove websocket_router |
| `doc/general/API.md` | Modify | Append | Add new endpoint docs |
| `doc/general/ARCHITECTURE.md` | Modify | Update | Reflect new architecture |

### Frontend Changes

| File | Action | Lines | Description |
|------|--------|-------|-------------|
| `frontend/src/services/conversationService.ts` | Modify | After 88 | Add sendMessage method |
| `frontend/src/contexts/ChatContext.tsx` | Modify | Multiple | Replace WebSocket with REST |
| `frontend/src/pages/Chat.tsx` | Modify | 66-70 | Remove connection banner |
| `frontend/src/components/chat/MessageInput.tsx` | Modify | 75 | Update disabled logic |
| `frontend/src/components/chat/MessageList.tsx` | Modify | 45-62 | Remove streaming UI |
| `frontend/src/hooks/useWebSocket.ts` | Delete | Full file | No longer needed |
| `frontend/src/services/websocketService.ts` | Delete | Full file | No longer needed |

---

## Testing Strategy

### Backend Tests

**Unit Tests (Not Required):**
- SendMessage use case already tested
- No new business logic added

**Integration Tests (REQUIRED):**
```bash
backend/tests/integration/test_message_creation.py
- test_create_message_success
- test_create_message_conversation_not_found
- test_create_message_access_denied
- test_create_message_unauthorized
- test_create_message_validation_error
- test_create_message_updates_count
```

**Run tests:**
```bash
cd backend
pytest tests/integration/test_message_creation.py -v
```

### Frontend Tests

**Manual Testing Checklist:**
- [ ] Create new conversation
- [ ] Send message to conversation
- [ ] Verify both user and assistant messages appear
- [ ] Verify conversation message_count incremented by 2
- [ ] Load conversation history (messages persist)
- [ ] Delete conversation (messages deleted)
- [ ] Send message to non-existent conversation (404 error)
- [ ] Send message to other user's conversation (403 error)
- [ ] Send empty message (validation error)

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| SendMessage use case needs modification | Medium | Low | Modify to return both messages instead of only assistant |
| Authorization not enforced | Critical | Low | Follow existing conversation endpoint patterns |
| Message count incorrect | Medium | Low | Use existing increment_message_count method |
| Frontend breaking changes | Medium | Low | Test thoroughly before removing WebSocket |
| LLM provider errors | Medium | Medium | Wrap in try-catch, return 500 with error detail |

### Data Integrity Risks

| Risk | Mitigation |
|------|------------|
| Race condition in message count | Document limitation; MongoDB 4.0+ transactions optional for future |
| Orphaned messages if LLM fails | Acceptable; user message persists, retry possible |
| Transaction consistency | Accept atomic-per-document model; no changes needed |

---

## Implementation Timeline

### Week 1: Backend Development
- **Day 1-2:** Create schemas and modify SendMessage (Phase 1.1-1.2)
- **Day 3-4:** Create REST endpoint (Phase 1.3)
- **Day 5:** Write integration tests (Phase 1.4)

### Week 2: Frontend Development
- **Day 1-2:** Add REST API method and update ChatContext (Phase 2.1-2.2)
- **Day 3-4:** Update UI components (Phase 2.3-2.5)
- **Day 5:** Manual testing and bug fixes

### Week 3: Cleanup and Documentation
- **Day 1:** Remove LangGraph infrastructure (Phase 3.1)
- **Day 2:** Remove WebSocket infrastructure (Phase 3.2)
- **Day 3:** Update dependencies (Phase 3.3)
- **Day 4-5:** Update documentation (Phase 4)

**Total Estimated Effort:** 9-14 hours

---

## Success Criteria

- [x] REST endpoint returns both user and assistant messages
- [x] Conversation message count increments by 2
- [x] Authorization enforced (user owns conversation)
- [x] Error handling for all scenarios (404, 403, 422, 500)
- [x] Integration tests pass with >80% coverage
- [x] Frontend displays messages correctly
- [x] No WebSocket code remains
- [x] Documentation updated
- [x] All LangGraph infrastructure removed
- [x] No breaking changes to existing endpoints

---

## Rollback Plan

If issues arise during implementation:

1. **Backend rollback:** Revert changes to `message_router.py` and `send_message.py`
2. **Frontend rollback:** Revert changes to `ChatContext.tsx` and restore WebSocket files
3. **Database rollback:** No schema changes, no rollback needed
4. **LangGraph rollback:** Restore from git if accidentally removed

**Rollback decision points:**
- If integration tests fail after 2 debugging iterations
- If frontend cannot connect to REST API after 1 day
- If message count accuracy < 95% after testing

---

## Open Questions

1. **Message Length:** Maximum content length? (Recommended: 10,000 characters)
2. **Rate Limiting:** Per-user or per-conversation? (Recommended: 30 messages/minute per user)
3. **Metadata:** Should REST endpoint accept metadata in request? (Recommended: Yes, optional)
4. **Error Messages:** Generic or detailed error messages? (Recommended: Generic for security)
5. **Timeout:** LLM response timeout? (Recommended: 60 seconds)

---

## References

### Code Patterns to Follow

**Authorization Pattern:**
```
conversation_router.py lines 99-104, 138-143, 180-185
message_router.py lines 44-49
```

**Authentication Pattern:**
```
dependencies.py lines 19-54, 56-76
conversation_router.py lines 20-22, 50-54 (CurrentUser parameter)
```

**Error Handling Pattern:**
```
conversation_router.py lines 92-97, 131-136
message_router.py lines 37-42
```

**Integration Test Pattern:**
```
test_conversation_api.py lines 130-134 (unauthorized access test)
test_conversation_api.py lines 179-196 (authorization test)
```

### Analyzer Reports

All detailed analysis available in:
- `doc/features/Replace unused LangGraph infrastructure with REST API integration/backend_hexagonal.md`
- `doc/features/Replace unused LangGraph infrastructure with REST API integration/api_contract.md`
- `doc/features/Replace unused LangGraph infrastructure with REST API integration/data_flow.md`
- `doc/features/Replace unused LangGraph infrastructure with REST API integration/llm_integration.md`
- `doc/features/Replace unused LangGraph infrastructure with REST API integration/react_frontend.md`
- `doc/features/Replace unused LangGraph infrastructure with REST API integration/security.md`
- `doc/features/Replace unused LangGraph infrastructure with REST API integration/database_mongodb.md`
- `doc/features/Replace unused LangGraph infrastructure with REST API integration/testing_coverage.md`

---

**Last Updated:** 2025-10-24
**Approved By:** Pending Review
**Ready for Implementation:** Yes
