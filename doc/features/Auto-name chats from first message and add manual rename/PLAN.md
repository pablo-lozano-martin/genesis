# Implementation Plan: Auto-name Chats from First Message and Add Manual Rename

## Overview

This plan implements two features for conversation management:
1. **Auto-naming**: Automatically generate conversation titles from the first 3-4 words of the first user message (max 50 characters)
2. **Manual rename**: Allow users to manually rename conversations via inline editing in the sidebar

## Requirements Summary

From GitHub Issue #1:
- Title auto-generates from first 3-4 words of first message, max ~50 chars
- Title updates client-side immediately after sending first message
- Title synced to backend via existing PATCH `/api/conversations/{id}` endpoint
- Manual rename functionality with click-to-edit UI in sidebar
- Handle edge cases: short messages (1-2 words), long words, special characters
- Comprehensive testing (unit, integration, E2E)

## Architecture Decision

**Auto-Naming Approach**: **Client-Side** (based on requirements clarification)
- Generate title on frontend immediately after user sends first message
- Call PATCH endpoint to persist title
- Simpler implementation, no backend LLM integration needed
- Consistent with requirement: "Title updates client-side immediately after sending first message"

**Manual Rename Approach**: **Click-to-Edit** in sidebar
- Inline editing pattern (common in modern apps)
- No additional UI chrome needed
- Keyboard accessible (Enter/Escape)

## Files to Modify

### Frontend Files

1. **`/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/conversationService.ts`**
   - Add `updateConversation()` method to call PATCH endpoint
   - Add TypeScript interface `UpdateConversationRequest`

2. **`/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx`**
   - Add `updateConversationTitle()` method
   - Modify `sendMessage()` to detect first message and trigger auto-naming
   - Update conversations and currentConversation state after title update

3. **`/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/ConversationSidebar.tsx`**
   - Add local state for editing mode (`editingId`, `editValue`)
   - Add click-to-edit UI for conversation titles
   - Add keyboard handlers (Enter, Escape)
   - Call `updateConversationTitle` on save

### Files to Create

4. **`/Users/pablolozano/Mac Projects August/genesis/frontend/src/lib/titleUtils.ts`** (new file)
   - Create `generateTitleFromMessage()` utility function
   - Handle word extraction, character limits, edge cases

### Backend Files

**No backend changes required** for basic functionality:
- PATCH `/api/conversations/{id}` endpoint already exists (conversation_router.py:116-156)
- `ConversationUpdate` schema supports title updates (conversation.py:43-46)
- `MongoConversationRepository.update()` method works correctly (mongo_conversation_repository.py:73-95)

### Test Files

5. **`/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_title_generation.py`** (new file)
   - Unit tests for title generation utility

6. **`/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_conversation_api.py`** (extend existing)
   - Add PATCH endpoint integration tests

7. **`/Users/pablolozano/Mac Projects August/genesis/frontend/src/lib/__tests__/titleUtils.test.ts`** (new file, if frontend testing added)
   - Frontend unit tests for title generation

## Implementation Steps

### Phase 1: Frontend - Title Generation Utility

**File**: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/lib/titleUtils.ts`

```typescript
// ABOUTME: Utility functions for generating conversation titles from messages
// ABOUTME: Handles word extraction, character limits, and edge cases

/**
 * Generate a conversation title from a message.
 * Extracts first 3-4 words, max 50 characters.
 *
 * @param content - Message content to generate title from
 * @param maxLength - Maximum title length (default: 50)
 * @returns Generated title
 */
export function generateTitleFromMessage(content: string, maxLength: number = 50): string {
  // Trim and clean the content
  const cleaned = content.trim();

  // Handle empty message
  if (!cleaned) {
    return "New Chat";
  }

  // Split into words
  const words = cleaned.split(/\s+/);

  // Take first 3-4 words
  const wordCount = Math.min(words.length, 4);
  const firstWords = words.slice(0, wordCount).join(' ');

  // If within limit, return as-is
  if (firstWords.length <= maxLength) {
    return firstWords;
  }

  // Try with 3 words
  if (wordCount === 4) {
    const threeWords = words.slice(0, 3).join(' ');
    if (threeWords.length <= maxLength) {
      return threeWords;
    }
  }

  // Truncate at character boundary with ellipsis
  return firstWords.substring(0, maxLength - 3) + '...';
}
```

**Edge Cases Handled**:
- Empty/whitespace-only → "New Chat"
- Short messages (1-2 words) → Use as-is
- Long words → Truncate with ellipsis
- Multi-word within limit → First 3-4 words
- Special characters → Preserved

### Phase 2: Frontend - Conversation Service Update

**File**: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/conversationService.ts`

**Add interface** (after existing Conversation interface around line 16):

```typescript
export interface UpdateConversationRequest {
  title?: string;
}
```

**Add method** (after `deleteConversation()` around line 67):

```typescript
async updateConversation(
  id: string,
  data: UpdateConversationRequest
): Promise<Conversation> {
  const response = await axios.patch(
    `${API_URL}/api/conversations/${id}`,
    data,
    { headers: this.getAuthHeaders() }
  );
  return response.data;
}
```

**Why**: Follows existing service pattern. Type-safe. Reuses auth headers.

### Phase 3: Frontend - Chat Context Enhancement

**File**: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx`

**Step 3.1: Add import** (around line 6):

```typescript
import { generateTitleFromMessage } from "../lib/titleUtils";
```

**Step 3.2: Add method to interface** (around line 24):

```typescript
interface ChatContextType {
  // ... existing fields
  updateConversationTitle: (id: string, title: string) => Promise<void>;
}
```

**Step 3.3: Add implementation** (after `deleteConversation()` around line 109):

```typescript
const updateConversationTitle = async (id: string, title: string) => {
  try {
    const updated = await conversationService.updateConversation(id, { title });

    // Update conversations list
    setConversations((prev) =>
      prev.map((c) => (c.id === id ? updated : c))
    );

    // Update current conversation if it's the one being renamed
    if (currentConversation?.id === id) {
      setCurrentConversation(updated);
    }
  } catch (err) {
    console.error("Failed to update conversation title:", err);
  }
};
```

**Step 3.4: Modify `sendMessage()` for auto-naming** (around line 111-127):

Replace the `sendMessage` function with:

```typescript
const sendMessage = (content: string) => {
  if (!currentConversation || !isConnected) return;

  // Detect if this is the first user message
  const userMessages = messages.filter((m) => m.role === "user");
  const isFirstMessage = userMessages.length === 0;

  // Add message optimistically
  setMessages((prev) => [
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

  // Auto-name if first message and title is still default
  if (isFirstMessage && currentConversation.title === "New Chat") {
    const autoTitle = generateTitleFromMessage(content);
    updateConversationTitle(currentConversation.id, autoTitle);
  }
};
```

**Step 3.5: Add to context provider value** (around line 149):

```typescript
return (
  <ChatContext.Provider
    value={{
      // ... existing values
      updateConversationTitle,
    }}
  >
    {children}
  </ChatContext.Provider>
);
```

**Why**:
- First message detection checks user role messages only
- Also checks if title is still "New Chat" (prevents overwriting manual renames)
- Auto-naming happens immediately after send (client-side as required)
- State updates are optimistic for responsive UI

### Phase 4: Frontend - Conversation Sidebar Manual Rename

**File**: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/ConversationSidebar.tsx`

**Step 4.1: Add state** (after component props, around line 21):

```typescript
export const ConversationSidebar: React.FC<ConversationSidebarProps> = ({
  conversations,
  currentConversation,
  onSelect,
  onCreate,
  onDelete,
}) => {
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [editValue, setEditValue] = React.useState("");

  const startEdit = (id: string, currentTitle: string) => {
    setEditingId(id);
    setEditValue(currentTitle);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditValue("");
  };

  const saveEdit = async (id: string) => {
    if (!editValue.trim()) {
      cancelEdit();
      return;
    }

    // This will be passed from Chat.tsx which has access to ChatContext
    // For now, we'll add it as a prop
    if (onRename) {
      await onRename(id, editValue.trim());
    }
    cancelEdit();
  };

  const handleKeyDown = (e: React.KeyboardEvent, id: string) => {
    if (e.key === "Enter") {
      e.preventDefault();
      saveEdit(id);
    } else if (e.key === "Escape") {
      e.preventDefault();
      cancelEdit();
    }
  };

  return (
    // ... rest of component
  );
};
```

**Step 4.2: Update props interface** (around line 7):

```typescript
interface ConversationSidebarProps {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onDelete: (id: string) => void;
  onRename?: (id: string, newTitle: string) => Promise<void>;
}
```

**Step 4.3: Replace title display** (around line 44, inside the map):

Replace:
```typescript
<div className="text-sm font-medium truncate">{conv.title}</div>
```

With:
```typescript
{editingId === conv.id ? (
  <input
    type="text"
    value={editValue}
    onChange={(e) => setEditValue(e.target.value)}
    onBlur={() => saveEdit(conv.id)}
    onKeyDown={(e) => handleKeyDown(e, conv.id)}
    autoFocus
    className="text-sm font-medium w-full px-1 py-0.5 border border-blue-500 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
    onClick={(e) => e.stopPropagation()}
  />
) : (
  <div
    className="text-sm font-medium truncate cursor-text"
    onClick={(e) => {
      e.stopPropagation();
      startEdit(conv.id, conv.title);
    }}
  >
    {conv.title}
  </div>
)}
```

**Step 4.4: Update Chat.tsx to pass onRename** (in `/Users/pablolozano/Mac Projects August/genesis/frontend/src/pages/Chat.tsx`):

Find the ConversationSidebar usage and add:

```typescript
<ConversationSidebar
  conversations={conversations}
  currentConversation={currentConversation}
  onSelect={selectConversation}
  onCreate={createConversation}
  onDelete={deleteConversation}
  onRename={updateConversationTitle}
/>
```

**Why**:
- Click-to-edit pattern is intuitive and common
- No additional UI chrome needed
- Keyboard accessible (Enter/Escape)
- stopPropagation prevents selecting conversation when editing
- Blur saves automatically for good UX

### Phase 5: Backend - Integration Tests for PATCH Endpoint

**File**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_conversation_api.py`

**Add tests** (at end of `TestConversationAPI` class):

```python
@pytest.mark.asyncio
async def test_update_conversation_title(self, client: AsyncClient):
    """Test PATCH /api/conversations/{id} with valid title."""
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
        json={"title": "Updated Title"},
        headers=headers
    )

    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "Updated Title"
    assert update_resp.json()["id"] == conversation_id

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

    # Title with 201 characters
    long_title = "x" * 201
    update_resp = await client.patch(
        f"/api/conversations/{conversation_id}",
        json={"title": long_title},
        headers=headers
    )

    assert update_resp.status_code == 422

@pytest.mark.asyncio
async def test_update_conversation_unauthorized(self, client: AsyncClient):
    """Test updating another user's conversation returns 403."""
    # User A creates conversation
    headers_a = await self.create_user_and_login(client)
    create_resp = await client.post(
        "/api/conversations",
        json={"title": "User A Conversation"},
        headers=headers_a
    )
    conversation_id = create_resp.json()["id"]

    # User B tries to update
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
```

### Phase 6: Frontend - Unit Tests for Title Generation

**File**: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/lib/__tests__/titleUtils.test.ts` (new file)

**Note**: This requires frontend testing setup (Vitest). If not configured, these tests can be written later.

```typescript
import { describe, it, expect } from 'vitest';
import { generateTitleFromMessage } from '../titleUtils';

describe('generateTitleFromMessage', () => {
  it('should take first 4 words', () => {
    expect(generateTitleFromMessage('Hello world this is a test'))
      .toBe('Hello world this is');
  });

  it('should handle short messages', () => {
    expect(generateTitleFromMessage('Hi')).toBe('Hi');
    expect(generateTitleFromMessage('Hello world')).toBe('Hello world');
  });

  it('should truncate at 50 chars with ellipsis', () => {
    const long = 'This is a very long message with many words that exceeds fifty characters easily';
    const result = generateTitleFromMessage(long);
    expect(result.length).toBeLessThanOrEqual(50);
    expect(result).toContain('...');
  });

  it('should handle single very long word', () => {
    const longWord = 'Supercalifragilisticexpialidocious and more words here';
    const result = generateTitleFromMessage(longWord);
    expect(result.length).toBeLessThanOrEqual(50);
  });

  it('should trim whitespace', () => {
    expect(generateTitleFromMessage('  Hello world  ')).toBe('Hello world');
  });

  it('should handle empty string', () => {
    expect(generateTitleFromMessage('')).toBe('New Chat');
    expect(generateTitleFromMessage('   ')).toBe('New Chat');
  });

  it('should handle special characters', () => {
    expect(generateTitleFromMessage('How to use `Array.map()`?'))
      .toBe('How to use `Array.map()`?');
  });

  it('should handle newlines as word separators', () => {
    expect(generateTitleFromMessage('Hello\nworld\ntest\nfoo'))
      .toBe('Hello world test foo');
  });
});
```

## Testing Strategy

### Unit Tests (Priority 1)

**Backend**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/`
- No backend unit tests needed (title generation is frontend-only)

**Frontend**: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/lib/__tests__/`
- `titleUtils.test.ts` - 10+ test cases for edge cases
- Run: `npm test` (requires Vitest setup)

### Integration Tests (Priority 2)

**Backend**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_conversation_api.py`
- 4 new tests for PATCH endpoint
- Tests: success, too long, unauthorized, not found
- Run: `cd backend && pytest tests/integration/test_conversation_api.py -v`

### End-to-End Tests (Priority 3 - Optional)

**Frontend**: `/Users/pablolozano/Mac Projects August/genesis/frontend/e2e/conversation-naming.spec.ts`

Requires Playwright setup:
```bash
cd frontend
npm install -D @playwright/test
npx playwright install
```

Test scenarios:
1. Auto-name flow: Create chat → Send "Hello how are you" → Verify title becomes "Hello how are"
2. Manual rename flow: Click title → Edit → Verify update
3. Edge cases: Very long message, short message, special characters

## Edge Cases Handling

### Title Generation

| Input | Output | Handling |
|-------|--------|----------|
| "Hi" | "Hi" | Use as-is if < 50 chars |
| "" or "   " | "New Chat" | Fallback to default |
| "Supercalifragilisticexpialidocious test" | "Supercalifragilistic..." | Truncate at 47 chars + "..." |
| "Hello\nworld\ntest" | "Hello world test" | Normalize whitespace |
| "How to use `Array.map()`?" | "How to use `Array.map()`?" | Preserve special chars |
| 201-char message | First 3-4 words, max 50 | Extract words, then truncate |

### Auto-Naming Detection

- Only trigger if `messages.filter(m => m.role === 'user').length === 0`
- Only trigger if `currentConversation.title === "New Chat"`
- This prevents overwriting manual renames

### Manual Rename

- Empty title → Cancel edit, revert to current
- Title > 200 chars → Server returns 422, log error
- Network failure → Error logged, UI shows stale title
- Escape key → Cancel edit
- Enter key → Save edit
- Blur → Save edit

## Risk Mitigation

### Race Conditions

**Risk**: User sends two messages rapidly, both trigger auto-naming.

**Mitigation**:
- Check both conditions: `message_count === 0` AND `title === "New Chat"`
- First message will pass check, second will fail (message_count > 0 after first)

### Stale UI State

**Risk**: Title updates in one tab, not reflected in other tabs.

**Mitigation**:
- Accept single-tab consistency for initial implementation
- Document as known limitation
- Future: Add WebSocket broadcast or polling

### API Failures

**Risk**: Title update fails, UI shows wrong title.

**Mitigation**:
- Current pattern: Log error, no rollback
- UI will show correct title after next `loadConversations()` call
- Better: Implement optimistic update with rollback (future enhancement)

## Definition of Done Checklist

### Implementation
- [ ] `titleUtils.ts` created with `generateTitleFromMessage()`
- [ ] `conversationService.ts` has `updateConversation()` method
- [ ] `ChatContext.tsx` has `updateConversationTitle()` method
- [ ] `ChatContext.tsx` `sendMessage()` triggers auto-naming on first message
- [ ] `ConversationSidebar.tsx` has click-to-edit UI
- [ ] `Chat.tsx` passes `onRename` prop to sidebar

### Testing
- [ ] Frontend unit tests for title generation (10+ cases)
- [ ] Backend integration tests for PATCH endpoint (4+ cases)
- [ ] Manual testing checklist completed (see GitHub issue)
- [ ] Test coverage >80% for new code

### Quality
- [ ] No TypeScript errors (`npm run build` passes)
- [ ] No Python lint errors (`ruff check` passes)
- [ ] All files start with ABOUTME comments
- [ ] No temporal naming or comments
- [ ] Code matches surrounding style

### Documentation
- [ ] PLAN.md (this file) reviewed and approved
- [ ] Code comments explain non-obvious logic
- [ ] GitHub issue updated with progress

## Files Summary

### To Modify (6 files)
1. `frontend/src/services/conversationService.ts` - Add updateConversation()
2. `frontend/src/contexts/ChatContext.tsx` - Add updateConversationTitle() and auto-naming
3. `frontend/src/components/chat/ConversationSidebar.tsx` - Add inline edit UI
4. `frontend/src/pages/Chat.tsx` - Pass onRename prop
5. `backend/tests/integration/test_conversation_api.py` - Add PATCH tests
6. `frontend/src/lib/__tests__/titleUtils.test.ts` - Frontend unit tests (if Vitest configured)

### To Create (1 file)
1. `frontend/src/lib/titleUtils.ts` - Title generation utility

### No Changes Required
- Backend API routes (already implemented)
- Backend domain models (already support title updates)
- Backend repositories (already have update() method)
- Database schema (title field exists)

## Estimated Effort

- **Phase 1-4 (Frontend Implementation)**: 4-6 hours
- **Phase 5 (Backend Integration Tests)**: 2-3 hours
- **Phase 6 (Frontend Unit Tests)**: 1-2 hours (if Vitest configured)
- **Manual Testing & Bug Fixes**: 2-3 hours
- **Total**: 9-14 hours

## Next Steps for Pablo

1. **Review this PLAN.md** - Approve or request changes
2. **Start Implementation** - Use `/start-working-on-issue 1` command
3. **Follow phases in order** - Frontend first (no backend changes needed)
4. **Test thoroughly** - Use manual testing checklist from GitHub issue
5. **Create PR** - After all tests pass and manual testing complete
