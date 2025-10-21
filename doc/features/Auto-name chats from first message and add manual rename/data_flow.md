# Data Flow Analysis

## Request Summary

Implement two conversation title update mechanisms:
1. **Auto-naming**: Automatically generate a descriptive title when the first user message is sent
2. **Manual rename**: Allow users to manually rename conversations from the sidebar

## Relevant Files & Modules

### Frontend Files

#### React Context & State Management
- `/frontend/src/contexts/ChatContext.tsx` - Main chat state provider managing conversations, messages, and WebSocket integration
- `/frontend/src/hooks/useWebSocket.ts` - WebSocket hook managing connection state and streaming message handling

#### Services
- `/frontend/src/services/conversationService.ts` - REST API service for conversation CRUD operations
- `/frontend/src/services/websocketService.ts` - WebSocket service for real-time chat communication

#### UI Components
- `/frontend/src/components/chat/ConversationSidebar.tsx` - Sidebar displaying conversation list with title display
- `/frontend/src/components/chat/MessageInput.tsx` - Message input component
- `/frontend/src/components/chat/MessageList.tsx` - Message display component
- `/frontend/src/pages/Chat.tsx` - Main chat page component

### Backend Files

#### Domain Models
- `/backend/app/core/domain/conversation.py` - Conversation domain model with ConversationUpdate schema (lines 43-46)
- `/backend/app/core/domain/message.py` - Message domain model with MessageRole enum

#### Repository Ports
- `/backend/app/core/ports/conversation_repository.py` - IConversationRepository interface defining update() method (lines 62-73)
- `/backend/app/core/ports/message_repository.py` - IMessageRepository interface for message operations
- `/backend/app/core/ports/llm_provider.py` - ILLMProvider interface for LLM operations

#### Repository Implementations
- `/backend/app/adapters/outbound/repositories/mongo_conversation_repository.py` - MongoDB conversation repository with update() method (lines 73-95) and increment_message_count() (lines 114-133)
- `/backend/app/adapters/outbound/repositories/mongo_message_repository.py` - MongoDB message repository
- `/backend/app/adapters/outbound/repositories/mongo_models.py` - Beanie ODM document models (ConversationDocument lines 35-53, MessageDocument lines 56-74)

#### API Endpoints
- `/backend/app/adapters/inbound/conversation_router.py` - REST API endpoints including PATCH /{conversation_id} (lines 116-156) for title updates
- `/backend/app/adapters/inbound/message_router.py` - Message history API endpoint
- `/backend/app/adapters/inbound/websocket_handler.py` - WebSocket handler for streaming chat (lines 56-179)
- `/backend/app/adapters/inbound/websocket_schemas.py` - WebSocket message protocol schemas

#### Use Cases
- `/backend/app/core/use_cases/create_conversation.py` - Conversation creation use case
- `/backend/app/core/use_cases/send_message.py` - Message sending use case (if exists)

### Key Functions & Classes

#### Frontend
- `createConversation()` in ChatContext.tsx (lines 68-77) - Creates conversation with "New Chat" title
- `loadConversations()` in ChatContext.tsx (lines 59-66) - Refreshes conversation list
- `sendMessage()` in ChatContext.tsx (lines 111-127) - Sends message via WebSocket and adds optimistic message
- `ConversationService.createConversation()` (lines 46-50) - POST /api/conversations
- `ConversationService.getConversation()` (lines 53-57) - GET /api/conversations/{id}
- No existing `updateConversation()` method in ConversationService - needs to be added

#### Backend
- `handle_websocket_chat()` in websocket_handler.py (lines 56-179) - Main WebSocket message handler
  - Saves user message (line 125)
  - Streams LLM response (lines 132-136)
  - Saves assistant message (line 145)
  - Increments message_count by 2 (line 148)
  - Sends completion message (lines 150-154)
- `MongoConversationRepository.update()` (lines 73-95) - Updates conversation fields including title
- `MongoConversationRepository.increment_message_count()` (lines 114-133) - Increments message count and updates updated_at timestamp
- `PATCH /api/conversations/{conversation_id}` endpoint (lines 116-156) - Conversation update API with ownership validation

## Current Data Flow Overview

### Data Entry Points

**Conversation Creation Flow:**
1. User clicks "New Chat" button in ConversationSidebar
2. ChatContext.createConversation() calls conversationService.createConversation()
3. POST /api/conversations with `{ title: "New Chat" }`
4. conversation_router creates conversation via MongoConversationRepository
5. Conversation saved to MongoDB with default title "New Chat"
6. Response returned to frontend, conversation added to state

**Message Sending Flow:**
1. User types message and submits via MessageInput
2. ChatContext.sendMessage() adds optimistic user message to UI
3. Message sent via WebSocket: `{ type: "message", conversation_id, content }`
4. websocket_handler.handle_websocket_chat() receives message

### Transformation Layers

**Backend Message Processing (websocket_handler.py):**
1. Validates conversation ownership (lines 108-117)
2. Creates Message domain model from client data (lines 119-123)
3. Saves user message via message_repository.create() (line 125)
4. Retrieves all conversation messages (line 128)
5. Streams LLM response token-by-token (lines 132-136)
6. Assembles full response and creates assistant Message (lines 137-143)
7. Saves assistant message (line 145)
8. Updates conversation metadata via increment_message_count() (line 148)

**Data Transformation Points:**
- Client JSON → ClientMessage schema (line 97)
- ClientMessage → Message domain model (lines 119-123)
- Message domain → MessageDocument (in message_repository)
- ConversationDocument → Conversation domain → ConversationResponse

### Persistence Layer

**MongoDB Collections:**
- `conversations` collection via ConversationDocument
  - Fields: user_id, title, created_at, updated_at, message_count
  - Indexes: user_id, (user_id, updated_at)
- `messages` collection via MessageDocument
  - Fields: conversation_id, role, content, created_at, metadata
  - Indexes: conversation_id, (conversation_id, created_at)

**Update Operations:**
- `MongoConversationRepository.update()` - Updates title and sets updated_at
- `MongoConversationRepository.increment_message_count()` - Atomic increment with updated_at

### Data Exit Points

**WebSocket Streaming:**
- ServerTokenMessage sent for each LLM token
- ServerCompleteMessage sent when response complete (includes message_id, conversation_id)

**REST API Responses:**
- ConversationResponse returned from PATCH /api/conversations/{id}
- Message[] returned from GET /api/conversations/{id}/messages

**Frontend State Updates:**
- ChatContext.loadMessages() called after stream completion (line 52)
- Conversations list in state updated via setConversations()

## Impact Analysis

### Components Affected by Auto-Naming

**Backend:**
1. **websocket_handler.py** - After saving first user message, detect if message_count == 0, trigger auto-naming
2. **LLM Provider** - Need method to generate short title from message content
3. **conversation_repository** - Update method already exists, will be used to set generated title

**Frontend:**
1. **ChatContext.tsx** - After receiving ServerCompleteMessage, reload conversation list to get updated title
2. **ConversationSidebar.tsx** - No changes needed, displays title from conversation object

### Components Affected by Manual Rename

**Backend:**
1. **conversation_router.py** - PATCH endpoint already exists and functional

**Frontend:**
1. **conversationService.ts** - Add updateConversation() method calling PATCH /api/conversations/{id}
2. **ConversationSidebar.tsx** - Add edit UI (inline edit or modal) with rename capability
3. **ChatContext.tsx** - Add updateConversation() function calling service and updating state

### Message Count Tracking

**Current Implementation:**
- `message_count` field exists on Conversation domain model (conversation.py line 22)
- Incremented by 2 after each exchange in websocket_handler.py (line 148)
- Displayed in ConversationSidebar (line 46)

**Detection Strategy for First Message:**
- Check if conversation.message_count == 0 before incrementing
- This indicates the current message is the first user message
- After incrementing, message_count will be 2 (user + assistant)

## Data Flow Recommendations

### Proposed DTOs

**Frontend:**
```typescript
// Add to conversationService.ts
interface UpdateConversationRequest {
  title?: string;
}
```

**Backend:**
- ConversationUpdate already exists (conversation.py lines 43-46)
- No new DTOs needed for basic functionality

### Proposed Transformations

#### Auto-Naming Title Generation

**New Port Interface:**
```python
# backend/app/core/ports/llm_provider.py
# Add to ILLMProvider interface:

@abstractmethod
async def generate_title(self, user_message: str) -> str:
    """
    Generate a concise conversation title from the first user message.

    Args:
        user_message: First message content from user

    Returns:
        Short title (max 50 characters) summarizing the message
    """
    pass
```

**Implementation in LLM Providers:**
- Each provider (OpenAI, Anthropic, etc.) implements generate_title()
- Use simple prompt: "Generate a short title (max 5 words) for this question: {message}"
- Returns plain text title without quotes or extra formatting

#### Backend WebSocket Flow Enhancement

**Modified websocket_handler.py flow:**
```python
# After line 126 (saved_user_message created)
# Check if this is the first message:
if conversation.message_count == 0:
    # Generate title from first user message
    generated_title = await llm_provider.generate_title(client_message.content)

    # Update conversation with generated title
    update_data = ConversationUpdate(title=generated_title)
    await conversation_repository.update(conversation_id, update_data)

# Continue with normal flow (LLM streaming, etc.)
```

**Key Considerations:**
- Title generation should happen BEFORE streaming response to avoid race conditions
- Keep it simple: single LLM call with short timeout
- Fallback to "New Chat" if generation fails
- Title generation should not block main message flow

### Repository Changes

**No repository changes needed:**
- `update()` method already exists and handles title updates
- `increment_message_count()` already exists
- Both methods properly update `updated_at` timestamp

### Data Flow Diagram

#### Auto-Naming Flow
```
1. User sends first message via WebSocket
   ↓
2. websocket_handler receives message
   ↓
3. Check conversation.message_count == 0
   ↓
4. Generate title via llm_provider.generate_title()
   ↓
5. Update conversation via repository.update()
   ↓
6. Continue normal flow: stream LLM response
   ↓
7. Increment message_count by 2
   ↓
8. Send ServerCompleteMessage to client
   ↓
9. Frontend calls loadConversations() to refresh list
   ↓
10. Updated title displayed in sidebar
```

#### Manual Rename Flow
```
1. User clicks edit/rename in ConversationSidebar
   ↓
2. UI shows inline input or modal with current title
   ↓
3. User enters new title and submits
   ↓
4. ChatContext.updateConversation() called
   ↓
5. conversationService.updateConversation() called
   ↓
6. PATCH /api/conversations/{id} with { title: "new title" }
   ↓
7. conversation_router validates ownership
   ↓
8. MongoConversationRepository.update() persists change
   ↓
9. Updated ConversationResponse returned
   ↓
10. ChatContext updates conversation in state
   ↓
11. Sidebar re-renders with new title
```

## Implementation Guidance

### Step 1: Backend - Add Title Generation Port

1. Add `generate_title()` method to ILLMProvider port interface
2. Implement in each LLM provider adapter (OpenAI, Anthropic, Gemini, Ollama)
3. Use simple prompt strategy with max 5-word constraint
4. Handle errors gracefully with fallback to original title

### Step 2: Backend - Auto-Naming in WebSocket Handler

1. In `websocket_handler.py`, after saving user message:
   - Check if `conversation.message_count == 0`
   - If true, call `llm_provider.generate_title(client_message.content)`
   - Create `ConversationUpdate` with generated title
   - Call `conversation_repository.update(conversation_id, update_data)`
2. Ensure this happens BEFORE LLM response streaming
3. Add error handling to prevent title generation from blocking chat
4. Log title generation for debugging

### Step 3: Frontend - Add Update Service Method

1. Add `updateConversation()` method to ConversationService:
   ```typescript
   async updateConversation(id: string, data: UpdateConversationRequest): Promise<Conversation> {
     const response = await axios.patch(`${API_URL}/api/conversations/${id}`, data, {
       headers: this.getAuthHeaders(),
     });
     return response.data;
   }
   ```

### Step 4: Frontend - Add Update Context Method

1. Add `updateConversation()` to ChatContext:
   ```typescript
   const updateConversation = async (id: string, title: string) => {
     try {
       const updated = await conversationService.updateConversation(id, { title });
       setConversations((prev) =>
         prev.map((c) => (c.id === id ? updated : c))
       );
       if (currentConversation?.id === id) {
         setCurrentConversation(updated);
       }
     } catch (err) {
       console.error("Failed to update conversation:", err);
     }
   };
   ```

### Step 5: Frontend - Add Rename UI to Sidebar

1. Add state for editing mode per conversation
2. Add edit button next to conversation title
3. On edit click, show inline input with current title
4. On blur or enter, call `updateConversation()`
5. On escape, cancel edit
6. Show loading state during update

### Step 6: Frontend - Auto-Refresh After First Message

1. In ChatContext, the existing flow already refreshes messages after streaming
2. Add call to `loadConversations()` after first message to get updated title:
   ```typescript
   if (wsStreamingMessage.isComplete) {
     setTimeout(() => {
       setStreamingMessage(null);
       if (currentConversation) {
         loadMessages(currentConversation.id);
         loadConversations(); // Refresh to get auto-generated title
       }
     }, 100);
   }
   ```

### Step 7: Testing Strategy

**Backend Tests:**
- Unit test LLM provider generate_title() methods
- Integration test websocket flow with message_count == 0
- Test PATCH endpoint for manual rename
- Test error handling when title generation fails

**Frontend Tests:**
- Test conversationService.updateConversation()
- Test ChatContext.updateConversation()
- Test sidebar rename UI interactions
- Test auto-refresh after first message

## Risks and Considerations

### Race Conditions

**Risk:** WebSocket message processing vs. REST API conversation updates
- WebSocket handler updates message_count while UI might be updating title
- Multiple rapid messages could trigger multiple title generations

**Mitigation:**
- Only generate title when message_count == 0 (strict check)
- Title generation happens synchronously before message_count increment
- Use MongoDB atomic operations (already in place)

### Stale Data in Conversation List

**Risk:** Sidebar shows old title after auto-naming or manual rename
- Frontend state not synchronized with backend changes
- Multiple tabs/windows showing different titles

**Mitigation:**
- Call loadConversations() after WebSocket completion
- Update local state immediately on manual rename (optimistic update)
- Consider WebSocket broadcast for multi-tab sync (future enhancement)

### LLM Title Generation Failures

**Risk:** Title generation fails, conversation stuck without proper title
- LLM API timeout or error
- Generated title exceeds character limit
- Empty or invalid response

**Mitigation:**
- Wrap title generation in try-catch
- Set short timeout (2-3 seconds max)
- Validate generated title length and content
- Fallback to "New Chat" or truncated first message on failure
- Log errors for monitoring

### Performance Bottlenecks

**Risk:** Extra LLM call adds latency to first message
- User experiences delay before seeing assistant response
- Title generation blocks message processing

**Mitigation:**
- Generate title before streaming (acceptable delay)
- Consider async title generation after response (alternative approach)
- Cache title generation prompts and settings
- Monitor P95/P99 latency metrics

### Updated_at Timestamp Behavior

**Risk:** Auto-naming updates updated_at, affecting conversation sort order
- Conversations jump to top of list unexpectedly
- Users lose context of when conversation was truly "updated"

**Current Behavior:**
- Both update() and increment_message_count() set updated_at = datetime.utcnow()
- This is actually CORRECT - any activity should update the timestamp

**Consideration:**
- Current behavior is acceptable for chat applications
- Latest active conversations should appear first
- No changes needed

### Data Consistency

**Current Guarantees:**
- MongoDB document updates are atomic
- message_count incremented after both messages saved
- updated_at timestamp set on all updates

**Edge Cases:**
- User deletes conversation while title being generated → handled by ownership check
- Concurrent manual rename and auto-naming → auto-naming happens first, manual rename wins
- WebSocket disconnect during title generation → no issue, title already saved

### Frontend State Management

**Risk:** Optimistic updates not rolled back on failure
- Manual rename fails but UI shows new title
- Conversation list out of sync with backend

**Mitigation:**
- Implement optimistic update with rollback on error
- Show loading/error states in UI
- Reload conversation on error to ensure consistency

## Summary

The data flow for conversation title updates is well-structured and aligns with the hexagonal architecture:

**Auto-Naming:**
- Cleanly integrates into existing WebSocket message flow
- Uses existing repository update() method
- Requires new generate_title() port method on ILLMProvider
- Frontend requires minimal changes (just refresh conversations list)

**Manual Rename:**
- Backend already fully implemented (PATCH endpoint, repository method)
- Frontend needs service method and UI components
- Simple REST API flow with optimistic updates

**Key Data Flow Boundaries:**
- WebSocket for real-time messaging (inbound)
- REST API for conversation metadata (inbound)
- LLM Provider for title generation (outbound)
- MongoDB for persistence (outbound)

**Transformation Points:**
- Client JSON → Pydantic schemas (validation)
- Schemas → Domain models (business logic)
- Domain models → MongoDB documents (persistence)
- Documents → Domain models → Response schemas (API output)

**Integration Points:**
- Title generation happens in WebSocket handler before message streaming
- Conversation list refresh happens after WebSocket completion
- Manual rename updates both local state and backend atomically

All proposed changes respect layer boundaries and maintain the clean separation of concerns established by the hexagonal architecture.
