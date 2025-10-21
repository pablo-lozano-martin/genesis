# React Frontend Analysis

## Request Summary

Implement auto-naming for chats based on the first message content and add manual rename functionality to the conversation sidebar. When a user sends the first message in a conversation, the chat title should automatically update to the first 3-4 words (max 50 characters). Users should also be able to manually rename conversations through an inline editing interface in the sidebar.

## Relevant Files & Modules

### Files to Examine

**Core State Management:**
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx` - Main chat state management with conversations, messages, and WebSocket integration
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/conversationService.ts` - Conversation API service with CRUD operations

**UI Components:**
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/ConversationSidebar.tsx` - Sidebar component displaying conversation list (needs edit functionality)
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MessageInput.tsx` - Message input component where sendMessage is triggered
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MessageList.tsx` - Message display component
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/pages/Chat.tsx` - Main chat page orchestrating all components

**Hooks & Services:**
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/hooks/useWebSocket.ts` - WebSocket hook for real-time messaging
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/websocketService.ts` - WebSocket service implementation

**Utilities:**
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/lib/utils.ts` - Utility functions including className merging

**Backend API Reference:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/conversation_router.py` - Conversation REST endpoints including PATCH `/api/conversations/{id}`

### Key Components & Hooks

**ChatContext (ChatProvider):**
- `conversations: Conversation[]` - Array of all user conversations
- `currentConversation: Conversation | null` - Currently selected conversation
- `messages: Message[]` - Messages in current conversation
- `streamingMessage: string | null` - Content being streamed from assistant
- `isStreaming: boolean` - Whether a message is currently streaming
- `sendMessage(content: string): void` - Send message via WebSocket
- `createConversation(): Promise<void>` - Create new conversation with "New Chat" title
- `selectConversation(id: string): Promise<void>` - Load and display a conversation
- `deleteConversation(id: string): Promise<void>` - Delete a conversation
- `loadConversations(): Promise<void>` - Refresh conversation list

**ConversationService:**
- `listConversations(skip, limit): Promise<Conversation[]>` - Fetch user conversations
- `createConversation(data): Promise<Conversation>` - Create new conversation
- `getConversation(id): Promise<Conversation>` - Get single conversation
- `deleteConversation(id): Promise<void>` - Delete conversation
- `getMessages(conversationId, skip, limit): Promise<Message[]>` - Fetch messages

**ConversationSidebar Component:**
- Props: `conversations`, `currentConversation`, `onSelect`, `onCreate`, `onDelete`
- Displays conversation list with title, message count, and delete button
- Minimal styling using Tailwind CSS

## Current Architecture Overview

### State Management Pattern

The application uses **React Context API** for global state management:

1. **ChatContext** provides centralized state for:
   - All conversations (fetched from REST API)
   - Current conversation and its messages
   - WebSocket connection status and streaming state

2. **State Flow:**
   - Initial load: `useEffect` in ChatProvider calls `loadConversations()`
   - Conversation creation: Creates with hardcoded "New Chat" title
   - Message sending: Goes through WebSocket, triggers streaming state
   - Message completion: Reloads messages from REST API after streaming completes

3. **State Update Mechanism:**
   - Uses `useState` for local state
   - Updates are synchronous for optimistic UI (e.g., adding user message immediately)
   - Server confirmations come through WebSocket completion events or REST API refreshes

### Data Fetching Architecture

The application uses a **hybrid REST + WebSocket approach**:

1. **REST API (via axios):**
   - Used for CRUD operations on conversations
   - Used for fetching message history
   - Auth headers injected via `getAuthHeaders()` method
   - No centralized axios instance with interceptors in conversationService

2. **WebSocket:**
   - Used exclusively for sending messages and receiving streaming responses
   - Connects to `/ws/chat` with token in query string
   - Handles token-by-token streaming, completion events, and errors
   - Auto-reconnect logic with exponential backoff

### Component Hierarchy

```
<Chat> (page)
├── <ConversationSidebar>
│   └── Conversation list items (inline JSX)
└── Main chat area
    ├── <MessageList>
    │   └── Message items (inline JSX)
    └── <MessageInput>
```

### Current sendMessage Flow

1. User types message in `MessageInput` and hits Enter or Send button
2. `MessageInput.handleSend()` calls `onSend(input.trim())`
3. This calls `ChatContext.sendMessage()` which:
   - Checks if `currentConversation` exists and `isConnected` is true
   - Optimistically adds user message to local `messages` state with temp ID
   - Sets `isStreaming` to true
   - Calls `wsSendMessage(conversationId, content)` to send via WebSocket
4. WebSocket streams response tokens back
5. On completion, ChatContext reloads messages via `loadMessages(conversationId)`
6. `loadMessages` calls `conversationService.getMessages()` to fetch all messages from REST API

**Critical Insight:** There is currently NO logic to detect if this is the first user message in a conversation. The auto-naming must be injected into this flow.

## Impact Analysis

### Components Requiring Changes

1. **ChatContext.tsx** (Primary Impact):
   - Add `updateConversationTitle()` method
   - Modify `sendMessage()` to detect first message and trigger auto-naming
   - Update local `conversations` state after title change
   - Update `currentConversation` state if it's the active one

2. **conversationService.ts** (New Method Required):
   - Add `updateConversation(id, data)` method to call PATCH endpoint
   - Must send `{ title: string }` in request body
   - Returns updated `Conversation` object

3. **ConversationSidebar.tsx** (UI Enhancement):
   - Add inline editing capability to conversation title
   - Could use contentEditable, input field, or edit icon approach
   - Must handle click-to-edit interaction
   - Must call update method when user finishes editing
   - Must handle escape/blur to cancel edit

4. **No Changes Required:**
   - MessageInput, MessageList, Chat page, useWebSocket (no changes needed)

### State Synchronization Challenges

1. **Optimistic Updates:**
   - Should update local state immediately for responsive UI
   - Must handle rollback if server update fails

2. **Race Conditions:**
   - Auto-naming happens after first message is sent
   - User might send second message before auto-naming completes
   - Solution: Check message count before auto-naming

3. **Multi-tab Synchronization:**
   - Current architecture has NO WebSocket broadcast for conversation updates
   - Changes in one tab won't reflect in another tab
   - Would require either polling, WebSocket events, or accepting inconsistency
   - **Recommendation:** Accept single-tab consistency for now, document limitation

## React Architecture Recommendations

### Proposed Service Method

Add to `conversationService.ts`:

```typescript
async updateConversation(
  id: string,
  data: { title?: string }
): Promise<Conversation> {
  const response = await axios.patch(
    `${API_URL}/api/conversations/${id}`,
    data,
    { headers: this.getAuthHeaders() }
  );
  return response.data;
}
```

**Why:** Follows existing service pattern. Single responsibility. Type-safe with existing `Conversation` interface.

### Proposed ChatContext Method

Add to `ChatContext`:

```typescript
const updateConversationTitle = async (id: string, title: string) => {
  try {
    const updated = await conversationService.updateConversation(id, { title });

    // Update conversations list
    setConversations(prev =>
      prev.map(c => c.id === id ? updated : c)
    );

    // Update current conversation if it's the one being renamed
    if (currentConversation?.id === id) {
      setCurrentConversation(updated);
    }
  } catch (err) {
    console.error("Failed to update conversation title:", err);
    // Could show toast notification here
  }
};
```

**Why:** Centralizes title update logic. Maintains state consistency. Follows error handling pattern used in other methods.

### Auto-Naming Logic Integration

**Location:** Inject into `ChatContext.sendMessage()` method after WebSocket send.

**Detection Logic:**
```typescript
const sendMessage = (content: string) => {
  if (!currentConversation || !isConnected) return;

  // Detect if this is the first user message
  const isFirstMessage = messages.filter(m => m.role === 'user').length === 0;

  // Add message optimistically
  setMessages(prev => [
    ...prev,
    {
      id: `temp-${Date.now()}`,
      conversation_id: currentConversation.id,
      role: "user",
      content,
      created_at: new Date().toISOString(),
    },
  ]);

  setIsStreaming(true);
  wsSendMessage(currentConversation.id, content);

  // Auto-name if first message
  if (isFirstMessage && currentConversation.title === 'New Chat') {
    const autoTitle = generateTitleFromMessage(content);
    updateConversationTitle(currentConversation.id, autoTitle);
  }
};
```

**Why First Message Detection:**
- Checks `messages` array filtered by `role === 'user'`
- Only counts real user messages, not system or assistant messages
- Also checks if current title is still "New Chat" (prevents overwriting manual renames)

### Title Generation Utility

**Location:** Create new utility function in `ChatContext.tsx` or `lib/utils.ts`

```typescript
function generateTitleFromMessage(content: string, maxLength: number = 50): string {
  // Trim and clean the content
  const cleaned = content.trim();

  // Split into words
  const words = cleaned.split(/\s+/);

  // Take first 3-4 words
  const firstWords = words.slice(0, 4).join(' ');

  // Truncate to max length
  if (firstWords.length <= maxLength) {
    return firstWords;
  }

  // Truncate and add ellipsis if needed
  return firstWords.substring(0, maxLength - 3) + '...';
}
```

**Edge Cases Handled:**
- Empty/whitespace-only messages: Won't trigger (content.trim() is already validated)
- Very long single words: Truncate at 50 chars with ellipsis
- Special characters: Preserved as-is (no sanitization needed for display)
- Multi-line messages: Split by any whitespace, works correctly

**Why This Approach:**
- Simple and predictable
- No complex NLP or AI needed
- Fast and synchronous
- Works well for 95% of use cases

### Manual Rename UI Pattern

**Recommended Approach:** Click-to-edit with inline input

**Implementation in ConversationSidebar.tsx:**

1. **State Management:**
   - Add local state: `editingId: string | null` and `editValue: string`
   - Track which conversation is being edited

2. **UI Pattern:**
   ```
   [Conversation Title] -> Click -> [Input Field] -> Enter/Blur -> Save
                                                  -> Escape -> Cancel
   ```

3. **Component Structure:**
   ```tsx
   {editingId === conv.id ? (
     <input
       value={editValue}
       onChange={(e) => setEditValue(e.target.value)}
       onBlur={handleSaveEdit}
       onKeyDown={handleKeyDown}
       autoFocus
       className="..."
     />
   ) : (
     <div
       onClick={() => startEdit(conv.id, conv.title)}
       className="cursor-text ..."
     >
       {conv.title}
     </div>
   )}
   ```

4. **Alternative Pattern:** Edit icon button
   - Less discoverable but clearer intent
   - Add pencil icon from `lucide-react` (already installed)
   - Click icon -> show input or modal

**Why Click-to-Edit:**
- Common pattern (similar to Notion, Linear, Trello)
- No additional UI chrome needed
- Direct manipulation feels natural
- Works well with keyboard navigation

**Props Addition:**
```tsx
interface ConversationSidebarProps {
  // ... existing props
  onRename?: (id: string, newTitle: string) => void;
}
```

### Error Handling Pattern

Follow existing pattern in ChatContext:

```typescript
try {
  await updateConversationTitle(id, title);
} catch (err) {
  console.error("Failed to update conversation title:", err);
  // Optional: Show user-facing error notification
  // Could use a toast library or error state
}
```

**Current Error Handling:**
- All methods use try/catch with console.error
- No user-facing error notifications currently
- Errors fail silently (bad UX but consistent with current pattern)

**Recommendation:**
- Match existing pattern for consistency
- Document that error handling should be improved across the board
- Could add toast notifications in future enhancement

## Implementation Guidance

### Step 1: Add Backend Integration

1. Add `updateConversation()` method to `conversationService.ts`
2. Test with existing PATCH endpoint (already implemented in backend)
3. Verify auth headers are included correctly

### Step 2: Extend ChatContext

1. Add `updateConversationTitle()` method
2. Add to context type and provider value
3. Test by calling from Chat page temporarily

### Step 3: Implement Auto-Naming

1. Create `generateTitleFromMessage()` utility function
2. Modify `sendMessage()` in ChatContext to detect first message
3. Call `updateConversationTitle()` with generated title
4. Test with new conversations

### Step 4: Add Manual Rename UI

1. Add local state to ConversationSidebar for editing
2. Implement click-to-edit interaction
3. Wire up `onRename` prop to `updateConversationTitle`
4. Handle keyboard events (Enter, Escape)
5. Style input to match title display

### Step 5: Refinement

1. Test edge cases (empty title, special characters, long titles)
2. Add loading states if needed
3. Handle concurrent edits gracefully
4. Verify state updates are reflected immediately

## Risks and Considerations

### Race Condition: Double Auto-Naming

**Risk:** If user sends two messages rapidly, both might trigger auto-naming.

**Mitigation:**
- Check `messages.filter(m => m.role === 'user').length === 0`
- Also check `currentConversation.title === 'New Chat'`
- Both conditions must be true

### State Staleness

**Risk:** `messages` state might be stale when `sendMessage` is called.

**Current Reality:**
- Not an issue because messages are updated optimistically in same function
- First message will always see empty array before optimistic update

### Backend Title Validation

**Risk:** Backend might reject title (too long, invalid characters).

**Backend Constraint:** `max_length=200` (from ConversationUpdate schema)

**Frontend Protection:**
- Generate max 50 chars, well within limit
- No special validation needed

### Multi-Tab Consistency

**Risk:** Title changes in one tab won't reflect in other tabs.

**Current Limitation:**
- No WebSocket broadcast for conversation updates
- Other tabs will show stale titles until they refresh conversations

**Recommendation:**
- Accept this limitation for initial implementation
- Document as known issue
- Could add polling or WebSocket events in future

### Optimistic Update Rollback

**Risk:** Local state shows new title, but server update fails.

**Current Pattern:**
- No rollback mechanism in existing ChatContext methods
- Updates happen async, errors logged only

**Recommendation:**
- Follow existing pattern (no rollback)
- Rely on next `loadConversations()` to restore correct state
- Document that proper error handling is broader technical debt

### Title Truncation UX

**Risk:** Generated titles might cut off mid-word awkwardly.

**Solution:**
- Word boundary truncation already implemented
- Ellipsis added only when needed
- First 3-4 words usually complete thoughts

## Testing Strategy

### Unit Tests for Title Generation

**Test Cases:**
```typescript
describe('generateTitleFromMessage', () => {
  it('should take first 4 words', () => {
    expect(generateTitleFromMessage('Hello world this is a test'))
      .toBe('Hello world this is');
  });

  it('should handle short messages', () => {
    expect(generateTitleFromMessage('Hi'))
      .toBe('Hi');
  });

  it('should truncate at 50 chars', () => {
    const long = 'This is a very long message with many words that exceeds fifty characters easily';
    const result = generateTitleFromMessage(long);
    expect(result.length).toBeLessThanOrEqual(50);
    expect(result).toContain('...');
  });

  it('should trim whitespace', () => {
    expect(generateTitleFromMessage('  Hello world  '))
      .toBe('Hello world');
  });
});
```

### Integration Tests for Auto-Naming

**Test Scenarios:**
1. Create new conversation
2. Send first message
3. Verify conversation title updates
4. Verify title reflects first words of message
5. Verify subsequent messages don't change title

**Testing Challenges:**
- Requires mocking WebSocket
- Requires mocking REST API responses
- Need to test async state updates

**Recommendation:**
- Use React Testing Library
- Mock conversationService methods
- Test ChatContext in isolation

### Manual Testing Checklist

**Auto-Naming:**
- [ ] Create new conversation (title is "New Chat")
- [ ] Send first message: "Hello, how are you today?"
- [ ] Verify title changes to "Hello, how are you"
- [ ] Send second message
- [ ] Verify title doesn't change
- [ ] Test with very short message ("Hi")
- [ ] Test with very long message (>50 chars)
- [ ] Test with multi-line message

**Manual Rename:**
- [ ] Click conversation title in sidebar
- [ ] Verify input field appears
- [ ] Type new title
- [ ] Press Enter
- [ ] Verify title updates in sidebar
- [ ] Verify title persists after page reload
- [ ] Test with empty title (should it be allowed?)
- [ ] Test with very long title
- [ ] Test pressing Escape to cancel
- [ ] Test clicking outside to save (blur)

**Edge Cases:**
- [ ] Rename conversation, then send another message (title shouldn't revert)
- [ ] Send first message while disconnected (error handling)
- [ ] Delete conversation being edited
- [ ] Switch to different conversation while editing

### E2E Test Scenarios

**Full User Journey:**
1. User logs in
2. Creates new conversation
3. Sends message: "What is the weather like?"
4. Sees title update to "What is the weather"
5. Clicks title in sidebar
6. Renames to "Weather Chat"
7. Sends another message
8. Title remains "Weather Chat"
9. Refreshes page
10. Title still shows "Weather Chat"

## Summary

### Key Architecture Points

1. **State Management:** Use existing ChatContext pattern with new `updateConversationTitle()` method
2. **API Integration:** Add simple `updateConversation()` method to conversationService
3. **Auto-Naming:** Inject detection logic into existing `sendMessage()` flow
4. **Title Generation:** Simple word-based truncation, no AI needed
5. **Manual Rename:** Click-to-edit pattern in ConversationSidebar
6. **Error Handling:** Follow existing console.error pattern

### Implementation Complexity

- **Low Complexity:** Title generation utility, service method
- **Medium Complexity:** Auto-naming detection, manual rename UI
- **Low Risk:** Well-isolated changes, no breaking modifications

### Files to Modify

1. `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/conversationService.ts` - Add updateConversation method
2. `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx` - Add updateConversationTitle and auto-naming logic
3. `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/ConversationSidebar.tsx` - Add inline editing UI

### Files to Create

- Optionally: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/lib/titleUtils.ts` - Title generation utility (or add to existing utils.ts)

### Dependencies

- No new npm packages needed
- Existing dependencies sufficient (React, axios, lucide-react for icons if needed)

### Performance Considerations

- Title updates are async but don't block UI
- Auto-naming happens after message send (parallel operation)
- No performance impact on message sending itself

### Accessibility Considerations

- Click-to-edit must be keyboard accessible
- Input field should have proper focus management
- Consider aria-label for edit affordance
- Escape key must work to cancel edit
