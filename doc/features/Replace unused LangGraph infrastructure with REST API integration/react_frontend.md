# React Frontend Analysis

## Request Summary

Migrate the chat messaging system from WebSocket-based communication (currently unused LangGraph infrastructure) to REST API calls. This involves replacing the real-time streaming WebSocket pattern with a request-response REST approach. The migration removes dependency on WebSocket infrastructure while maintaining the ability to send messages and display assistant responses.

## Relevant Files & Modules

### Files to Examine

- `frontend/src/contexts/ChatContext.tsx` - Main chat state management context; uses WebSocket hook and manages conversations/messages
- `frontend/src/hooks/useWebSocket.ts` - Custom hook managing WebSocket lifecycle, connection state, and streaming message reception
- `frontend/src/services/websocketService.ts` - WebSocket service class handling connection, message sending, and token streaming
- `frontend/src/pages/Chat.tsx` - Main chat page component rendering sidebar, message list, and input
- `frontend/src/components/chat/MessageList.tsx` - Displays messages with streaming state and auto-scroll
- `frontend/src/components/chat/MessageInput.tsx` - Text input with send functionality and disabled state management
- `frontend/src/components/chat/ConversationSidebar.tsx` - Conversation list sidebar with CRUD operations
- `frontend/src/services/conversationService.ts` - REST API service for conversation and message operations
- `frontend/src/contexts/AuthContext.tsx` - Authentication state and token management
- `frontend/src/services/authService.ts` - Token persistence and auth API calls
- `frontend/src/services/axiosConfig.ts` - Axios interceptor setup for 401 error handling
- `frontend/src/App.tsx` - Root component with routing and provider setup

### Key Components & Hooks

- `ChatProvider` in `frontend/src/contexts/ChatContext.tsx` - Context provider managing chat state
- `useChat()` in `frontend/src/contexts/ChatContext.tsx` - Hook exposing chat state and actions to components
- `useWebSocket()` in `frontend/src/hooks/useWebSocket.ts` - Hook managing WebSocket connection (to be removed)
- `Chat` in `frontend/src/pages/Chat.tsx` - Page component orchestrating chat layout
- `MessageList` in `frontend/src/components/chat/MessageList.tsx` - Message display component
- `MessageInput` in `frontend/src/components/chat/MessageInput.tsx` - Message input form component
- `ConversationSidebar` in `frontend/src/components/chat/ConversationSidebar.tsx` - Sidebar navigation
- `ConversationService` in `frontend/src/services/conversationService.ts` - REST API client

## Current Architecture Overview

### Pages & Routing

The app uses React Router with three main routes:
- `/login` - Login page (`frontend/src/pages/Login.tsx`)
- `/register` - Registration page (`frontend/src/pages/Register.tsx`)
- `/chat` - Protected chat page (`frontend/src/pages/Chat.tsx`)

The chat page is wrapped in `ProtectedRoute` to require authentication. `App.tsx` (lines 1-34) orchestrates the routing structure with provider hierarchy: `AuthProvider` > `Routes` > `ProtectedRoute` > `ChatProvider` > `Chat`.

### State Management

The application uses React Context API with two main contexts:

**AuthContext** (`frontend/src/contexts/AuthContext.tsx`):
- Manages user, token, authentication status
- Provides login, register, logout methods
- Initializes token from localStorage on mount (lines 27-44)
- Handles isLoading and error states implicitly through async operations

**ChatContext** (`frontend/src/contexts/ChatContext.tsx`):
- Manages conversations, currentConversation, messages
- Tracks streaming state: `streamingMessage`, `isStreaming`, `isConnected`, `error`
- Provides methods: loadConversations, createConversation, selectConversation, deleteConversation, sendMessage, updateConversationTitle
- Uses WebSocket hook for real-time communication (line 39)
- Auto-generates conversation titles on first message (lines 153-156)

**Local Component State**:
- `MessageInput` uses local `input` state for textarea value
- `ConversationSidebar` uses local `editingId` and `editValue` for inline conversation renaming

### Data Fetching

**REST API Calls** (via `ConversationService`):
- `listConversations()` - GET `/api/conversations` with pagination
- `createConversation(data)` - POST `/api/conversations` with optional title
- `getConversation(id)` - GET `/api/conversations/{id}`
- `deleteConversation(id)` - DELETE `/api/conversations/{id}`
- `updateConversation(id, data)` - PATCH `/api/conversations/{id}`
- `getMessages(conversationId, skip, limit)` - GET `/api/conversations/{conversationId}/messages`

All REST calls include Bearer token authorization (lines 35-40 in conversationService.ts).

**WebSocket Communication** (to be replaced):
- Establishes WebSocket connection to `ws://[API_URL]/ws/chat?token=[TOKEN]`
- Sends message: `{ type: "message", conversation_id: string, content: string }`
- Receives streaming tokens: `{ type: "token", content: string }`
- Receives completion: `{ type: "complete", message_id: string, conversation_id: string }`
- Receives errors: `{ type: "error", message: string, code?: string }`
- Implements auto-reconnect with exponential backoff (up to 5 attempts, 1000ms base delay)

### Custom Hooks

**useWebSocket()** (`frontend/src/hooks/useWebSocket.ts`):
- Manages WebSocket connection lifecycle and state
- Provides `isConnected`, `error`, `sendMessage`, `streamingMessage`, `connect`, `disconnect`
- Auto-connects on mount if `autoConnect: true`
- Handles token streaming by accumulating chunks in state (lines 69-81)
- Tracks current conversation ID to properly associate streaming messages (line 50)
- Returns callback-based `sendMessage` function for sending chat messages

## Impact Analysis

### WebSocket Dependencies

The WebSocket infrastructure is deeply integrated into the chat flow:

1. **ChatContext.tsx (lines 39-59)**:
   - Line 39: Initializes `useWebSocket` hook with URL and token
   - Lines 45-59: Effect hook watches `wsStreamingMessage` and updates local state
   - This creates tight coupling between WebSocket reception and UI state updates

2. **MessageInput.tsx (line 75)**:
   - Input is disabled when `!isConnected || isStreaming`
   - Currently depends on WebSocket connection status to enable/disable sending

3. **MessageList.tsx (lines 45-62)**:
   - Renders streaming message UI while `isStreaming` is true
   - Shows animated dots when streaming content but before first token arrives
   - Displays streaming content with visual indicator

4. **Chat.tsx (lines 66-70)**:
   - Displays "Connecting..." banner when `!isConnected`
   - Displays error banner when `error` is set

### State Changes Required

**Removal of WebSocket-specific state**:
- `isConnected` - WebSocket connection status (no longer needed for REST)
- `streamingMessage` - Streaming token accumulator (replaced with loading state)
- `isStreaming` - Streaming in-progress flag (replaced with `isLoading`)

**Addition of REST-specific state**:
- `isLoading` or `isMessageLoading` - Loading state while sending message
- Error handling for individual message sends (in addition to general errors)
- Potentially timestamp tracking for optimistic UI updates

**State transition**:
- From: Real-time streaming updates arriving in chunks via WebSocket
- To: Single response from REST endpoint containing complete assistant message

### Affected Components

1. **ChatContext.tsx** - Major refactor needed
   - Remove `useWebSocket` hook initialization (line 39)
   - Remove streaming message effect (lines 45-59)
   - Create new REST-based `sendMessage` function
   - Replace `isConnected` with `isLoading`

2. **Chat.tsx** - Moderate updates needed
   - Remove "Connecting..." banner (lines 66-70)
   - Update disabled state logic for MessageInput
   - Handle loading states differently

3. **MessageList.tsx** - Moderate updates needed
   - Remove streaming animation when no token yet (lines 54-58)
   - Update streaming message display logic
   - Remove isStreaming dependency, rely on presence of streamingMessage

4. **MessageInput.tsx** - Minor updates needed
   - Update disabled state logic to use `isLoading` instead of `isConnected`

5. **useWebSocket.ts** - Delete entire file
   - No longer needed for REST-based approach

6. **websocketService.ts** - Delete entire file
   - No longer needed for REST-based approach

## React Architecture Recommendations

### Proposed Components

No new components required. Existing components are suitable for REST API integration.

### Proposed Hooks

**Option A: Create `useMessageSending` hook (Recommended)**
```
Path: frontend/src/hooks/useMessageSending.ts

Purpose: Encapsulate message sending logic with loading state
- Manages isLoading state for individual message sends
- Handles error state for message-specific errors
- Returns { sendMessage, isLoading, error } interface
- Simplifies ChatContext by moving implementation detail into hook
- Reusable if multiple components need message-sending capability
```

**Option B: Inline REST calls directly in ChatContext**
```
Simpler but less reusable; appropriate if message sending is chat-context-specific
Less modular but acceptable given current architecture
```

Recommendation: Option A provides better separation of concerns and reusability.

### State Management Changes

**In ChatContext.tsx:**

Remove:
- `streamingMessage: string | null` (line 35)
- `isStreaming: boolean` (line 36)
- `isConnected: boolean` (line 19)
- WebSocket-related interface properties (lines 19, 17-18)
- `useWebSocket` hook call (line 39-43)
- WebSocket streaming effect (lines 45-59)

Add:
- `isMessageLoading: boolean` - True while waiting for message response
- `messageError: string | null` - Error from message send operations
- REST endpoint URL configuration: `const MESSAGE_API_URL = "${API_URL}/api/conversations/{conversationId}/messages"`

Modify:
- `sendMessage(content: string)` implementation (lines 131-157)
  - Add optimistic user message to UI immediately
  - Call REST API to send message and get response
  - Add assistant message to UI with response content
  - Handle errors gracefully with user feedback

**Update ChatContextType interface:**
```typescript
interface ChatContextType {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  messages: Message[];
  isMessageLoading: boolean;        // NEW: replaces isStreaming and isConnected
  error: string | null;             // Keep for conversation-level errors
  messageError: string | null;      // NEW: message send-specific errors
  loadConversations: () => Promise<void>;
  createConversation: () => Promise<void>;
  selectConversation: (id: string) => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;  // Change to async
  updateConversationTitle: (id: string, title: string) => Promise<void>;
}
```

### Data Flow Diagram

**Current WebSocket Flow:**
```
User types → MessageInput.onSend
  → ChatContext.sendMessage
  → WebSocket.sendMessage
  → Streaming tokens arrive via ws.onmessage
  → useWebSocket.handleMessage
  → setStreamingMessage
  → ChatContext updates state
  → MessageList re-renders with partial response
```

**Proposed REST Flow:**
```
User types → MessageInput.onSend
  → ChatContext.sendMessage
  → Add user message to UI (optimistic)
  → Set isMessageLoading = true
  → REST POST /api/conversations/{id}/messages with content
  → Await response with complete assistant message
  → Add assistant message to UI
  → Set isMessageLoading = false
  → Handle errors and update messageError if needed
```

## Implementation Guidance

### Phase 1: Create Message Sending Infrastructure

1. **Create `frontend/src/hooks/useMessageSending.ts`**
   - Accept conversationId and currentConversation as parameters
   - Manage isLoading and error states for message sends
   - Implement sendMessage function using axios POST to `/api/conversations/{conversationId}/messages`
   - Return { sendMessage, isLoading, error }

2. **Update `frontend/src/services/conversationService.ts`**
   - Add `sendMessage(conversationId: string, content: string): Promise<Message>` method
   - Makes POST request to `/api/conversations/{conversationId}/messages`
   - Sends request body: `{ content: string }`
   - Returns Message object from response

### Phase 2: Update ChatContext

1. **Remove WebSocket integration from `ChatContext.tsx`** (lines 39-59)
   - Delete useWebSocket import and hook call
   - Delete streamingMessage and isStreaming state
   - Update ChatContextType interface

2. **Implement REST-based sendMessage**
   - Add useMessageSending hook (or inline axios calls)
   - Rewrite sendMessage to be async
   - Add user message to messages array immediately (optimistic update)
   - Call conversationService.sendMessage()
   - Add assistant message to messages array on response
   - Handle errors and update error state
   - Keep auto-title generation logic (lines 153-156)

3. **Update context value provider**
   - Replace isConnected with isMessageLoading
   - Remove streamingMessage
   - Remove isStreaming
   - Add messageError if using separated error handling

### Phase 3: Update UI Components

1. **Update `Chat.tsx`** (lines 66-70)
   - Remove "Connecting..." banner logic
   - Keep error banner for conversation-level errors
   - Add error banner for message-level errors if messageError provided

2. **Update `MessageInput.tsx`** (line 75)
   - Change disabled condition from `!isConnected || isStreaming`
   - To: `!currentConversation || isMessageLoading`
   - Remove isConnected dependency entirely

3. **Update `MessageList.tsx`** (lines 45-62)
   - Remove streaming animation UI (lines 54-58 bounce dots)
   - Remove streamingMessage parameter from props
   - Remove isStreaming parameter from props
   - Component becomes simpler: just display messages array

### Phase 4: Cleanup

1. **Delete `frontend/src/hooks/useWebSocket.ts`** - No longer used
2. **Delete `frontend/src/services/websocketService.ts`** - No longer used
3. **Remove WebSocket URL configuration from ChatContext.tsx** (line 11)
4. **Remove axios from MessageInput if using optimistic updates** - Actually, keep axios already in use

### Code References by File

**ChatContext.tsx changes:**
- Remove: Lines 11 (WS_URL), 17-18 (streamingMessage/isStreaming from type), 35-36 (state), 39-43 (useWebSocket hook), 45-59 (effect)
- Modify: Lines 131-157 (sendMessage implementation), 164-180 (provider value)

**Chat.tsx changes:**
- Remove: Lines 66-70 (connecting banner)
- Modify: Line 75 (disabled logic for MessageInput)

**MessageInput.tsx changes:**
- Modify: Line 75 (disabled condition)

**MessageList.tsx changes:**
- Remove: Line 9 (streamingMessage prop), 10 (isStreaming prop), 45-62 (streaming UI block)
- Modify: Lines 22 (empty state condition)

**conversationService.ts changes:**
- Add: New sendMessage method after line 88

### Implementation Order

1. First create `useMessageSending` hook or add REST method to service
2. Update `conversationService.sendMessage()`
3. Rewrite `ChatContext.sendMessage()` to use REST
4. Update `ChatContextType` interface
5. Update `Chat.tsx` to remove connection banner
6. Update `MessageInput.tsx` disabled logic
7. Update `MessageList.tsx` to remove streaming UI
8. Delete WebSocket files after confirming all references removed

## Risks and Considerations

### Architectural Concerns

1. **Loss of Streaming UX**: WebSocket streaming provided real-time token display creating perceived responsiveness. REST approach will show complete response only after API returns. Mitigate by:
   - Using optimistic UI updates for user messages
   - Keeping component loading states clear
   - Ensuring API response times are acceptable

2. **No Real-Time Updates**: If multiple devices open same conversation, they won't see each other's messages. Current WebSocket also doesn't implement multi-device sync, so this is acceptable but worth noting for future enhancements.

3. **Prop Drilling**: ChatContext currently passes many props. REST migration doesn't worsen this but consider extracting message input handling to custom hook if sendMessage logic grows complex.

4. **Error Handling Asymmetry**: Currently error state is context-wide. Consider whether message-specific errors need separate handling to avoid confusing conversation-level errors with message send errors.

### State Management Risks

1. **Race Conditions**: If user sends multiple messages quickly while responses are pending, ensure:
   - Message queue ordering by timestamp (already in DB)
   - isMessageLoading blocks sending until response received
   - Each message send is independent operation

2. **Optimistic Updates**: If user message added to UI before server confirmation:
   - Must have temporary ID (already using `temp-${Date.now()}` in ChatContext line 141)
   - Should update with server ID when response received
   - If message fails, remove from UI or mark as failed

3. **Stale State**: After message send completes, ensure:
   - loadMessages() called to refresh message list with server IDs
   - Or assistant message response includes both user and assistant messages
   - Current implementation calls loadMessages after streaming completes (line 54), replicate this

### Component Coupling

1. **MessageInput depends on ChatContext**: Currently tight coupling via disabled state. REST migration doesn't change this but is acceptable pattern.

2. **MessageList displays streamingMessage**: After migration, simply won't render streaming placeholder. Simpler logic.

3. **isConnected dependency**: Several components check isConnected. REST removes connection concept - verify all usages replaced.

### Testing Considerations

1. **No WebSocket mocking needed**: Simplifies testing by removing WebSocket setup
2. **Mock REST endpoints**: Test message sending with axios mocks
3. **Error scenarios**: Test network errors, 401 unauthorized, invalid message content
4. **Race condition tests**: Verify message ordering with rapid sends
5. **UI state tests**: Verify loading states, error messages, optimistic updates

## Testing Strategy

### Unit Tests

**ChatContext.tsx**
- Test sendMessage adds user message to UI immediately
- Test sendMessage calls conversationService.sendMessage
- Test sendMessage updates isMessageLoading state
- Test error handling when sendMessage fails
- Test auto-title generation on first message
- Test conversation selection loads messages
- Test conversation deletion removes from list

**conversationService.ts**
- Test sendMessage makes POST request with correct headers
- Test sendMessage includes content in request body
- Test sendMessage returns Message from response
- Test error handling for failed requests
- Test authorization header included

**MessageInput.tsx**
- Test disabled when isMessageLoading true
- Test disabled when currentConversation null
- Test onSend called with trimmed content
- Test input cleared after send

**MessageList.tsx**
- Test messages rendered with correct role styling
- Test auto-scroll on message list updates
- Test empty state displays when no messages

### Integration Tests

- Test full message send flow: user input → ChatContext → REST API → message in list
- Test error display when message send fails
- Test conversation switching clears messages
- Test conversation creation and immediate message send
- Test auto-title generation with first message

### E2E Tests

- Test user can send message and see response
- Test conversation list updates after creating conversation
- Test conversation deletion removes from sidebar
- Test error toast/banner displays on message send failure
- Test input remains focused after message send (UX consideration)

## UI/UX Considerations

### Loading States

**Current state with WebSocket:**
- Shows animated dots while waiting for first token
- Shows growing message while tokens arrive
- Natural perception of work happening in real-time

**New state with REST:**
- Need clear loading indicator while awaiting response
- Consider:
  - Disable input while loading (already implemented via isMessageLoading)
  - Show "Assistant is thinking..." or spinner in message area
  - Or show assistant message placeholder that updates when response arrives

### No Streaming Text Display

REST approach requires full message before display. UI implications:
- Users won't see partial responses mid-computation
- Perception of responsiveness depends on API latency
- Consider showing spinner/skeleton in message area during wait

### Error Recovery

WebSocket can auto-reconnect on network failure. REST approach:
- Each message send is independent
- If send fails, user can retry
- Consider "Retry" button on failed message state

### Message Ordering

Ensure messages displayed in correct order:
- User messages: Sent at user's device timestamp
- Assistant messages: Return with server timestamp
- Current implementation uses created_at from server, which is correct

### Optimistic vs Pessimistic Updates

Current implementation:
- Adds user message immediately (optimistic)
- Loads full message list after streaming completes (pessimistic confirmation)

Proposed implementation should maintain this pattern:
- Add user message immediately
- Wait for REST response with assistant message
- Add assistant message to UI

This provides fast perceived response while ensuring correctness.

## Summary

This migration simplifies the frontend architecture by removing WebSocket complexity while maintaining message send/receive functionality. The trade-off is loss of streaming token display, which is acceptable given the requirement to replace LangGraph infrastructure.

Key architectural benefits:
- Eliminates connection management complexity
- Removes streaming state management overhead
- Simplifies component logic in Chat, MessageList, MessageInput
- Aligns with existing REST API usage patterns
- Reduces frontend dependencies

Implementation complexity:
- Straightforward migration path with clear file changes
- No changes to routing or authentication
- Minimal impact on other features
- Testing simplified by removing WebSocket mocking needs

The proposed approach maintains current UX as closely as possible while supporting the shift to REST-only API communication.
