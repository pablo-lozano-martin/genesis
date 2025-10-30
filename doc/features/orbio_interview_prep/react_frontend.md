# React Frontend Analysis

## Request Summary

Analysis of the React frontend implementation for the Orbio onboarding chatbot assignment. This document examines component structure, state management, chat interface mechanics, frontend-backend communication, and key UI/UX decisions.

## Relevant Files & Modules

### Core Application Files
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/main.tsx` - React root entry point with StrictMode
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/App.tsx` - Main app component with routing and context providers
- `/Users/pablolozano/Mac Projects August/genesis/frontend/package.json` - Dependencies and build configuration

### Pages & Routing
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/pages/Chat.tsx` - Main chat page component
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/pages/Login.tsx` - Authentication login page
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/pages/Register.tsx` - User registration page

### Context Providers (State Management)
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/AuthContext.tsx` - Authentication state management
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx` - Chat and conversation state management

### Custom Hooks
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/hooks/useWebSocket.ts` - WebSocket connection and streaming
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/hooks/useSpeechToText.ts` - Browser audio recording and transcription

### Chat Components
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MessageList.tsx` - Chat message display with auto-scroll
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MessageInput.tsx` - Text input with speech-to-text button
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/ConversationSidebar.tsx` - Conversation list with CRUD actions
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MarkdownMessage.tsx` - Markdown rendering with syntax highlighting
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/ToolExecutionCard.tsx` - Tool execution status display

### Auth Components
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/auth/ProtectedRoute.tsx` - Route guard for authenticated pages

### Services (API & Communication)
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/authService.ts` - Authentication API client with token management
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/conversationService.ts` - Conversation CRUD operations
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/websocketService.ts` - WebSocket connection service with reconnection logic
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/transcriptionService.ts` - Audio transcription API client
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/axiosConfig.ts` - Axios HTTP client configuration

### UI Components (Shadcn)
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/ui/badge.tsx` - Badge component for tags and labels
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/ui/card.tsx` - Card container component

### Utilities & Types
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/lib/titleUtils.ts` - Conversation title generation logic
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/lib/utils.ts` - Utility functions (likely clsx/tailwind-merge)
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/types/auth.ts` - TypeScript types for authentication

### Key Dependencies (from package.json)
- **React 19.1.1** - Core UI library (latest version)
- **React Router DOM 7.9.4** - Client-side routing
- **Axios 1.12.2** - HTTP client for REST API
- **React Markdown 10.1.0** - Markdown rendering
- **Lucide React 0.545.0** - Icon library
- **Tailwind CSS 3.4.1** - Utility-first CSS framework
- **Radix UI** - Accessible component primitives
- **Vite 7.1.7** - Build tool and dev server

## Current Architecture Overview

The frontend follows a clean, well-organized React architecture with clear separation of concerns. The application uses Context API for global state, custom hooks for reusable logic, and a service layer for API communication.

### Pages & Routing

The application has a simple three-page routing structure:

1. **`/login`** - Public login page
2. **`/register`** - Public registration page
3. **`/chat`** - Protected chat interface (requires authentication)
4. **`/`** - Redirects to `/chat`

**Routing Pattern:**
- Uses React Router v7 with `<BrowserRouter>`
- Protected routes wrapped with `<ProtectedRoute>` guard component
- Authentication check redirects unauthenticated users to `/login`
- Clean navigation flow with `useNavigate` hook

**Provider Hierarchy:**
```
<BrowserRouter>
  <AuthProvider>              // Global auth state
    <Routes>
      <Route path="/chat">
        <ProtectedRoute>       // Auth guard
          <ChatProvider>       // Chat-specific state
            <Chat />
          </ChatProvider>
        </ProtectedRoute>
      </Route>
    </Routes>
  </AuthProvider>
</BrowserRouter>
```

This hierarchy ensures:
- Authentication state available app-wide
- Chat state scoped to authenticated chat page only
- No unnecessary state initialization on public pages

### State Management

The application uses **React Context API** for state management with two primary contexts:

#### 1. AuthContext (`contexts/AuthContext.tsx`)

**Purpose:** Global authentication state and user management

**State:**
- `user: User | null` - Current user data
- `token: string | null` - JWT authentication token
- `isAuthenticated: boolean` - Auth status flag
- `isLoading: boolean` - Auth initialization loading state

**Methods:**
- `login(data: LoginRequest)` - Authenticate user, fetch user data, set token
- `register(data: RegisterRequest)` - Register and auto-login
- `logout()` - Clear token and user state

**Key Features:**
- Token persistence via `localStorage`
- Auto-initialization on app load (checks stored token and validates with `/api/auth/me`)
- Service layer delegation (`authService`) for API calls
- Custom hook `useAuth()` for consuming context with safety checks

**Pattern:** Singleton service pattern - `authService` is a singleton instance managing token storage and API communication.

#### 2. ChatContext (`contexts/ChatContext.tsx`)

**Purpose:** Chat-specific state including conversations, messages, streaming, and tool execution

**State:**
- `conversations: Conversation[]` - List of all user conversations
- `currentConversation: Conversation | null` - Active conversation
- `messages: Message[]` - Messages in current conversation
- `streamingMessage: string | null` - Partial AI response being streamed
- `isStreaming: boolean` - Stream active indicator
- `isConnected: boolean` - WebSocket connection status
- `error: string | null` - Error message display
- `toolExecutions: ToolExecution[]` - Active tool calls
- `currentToolExecution: ToolExecution | null` - Currently executing tool

**Methods:**
- `loadConversations()` - Fetch all conversations via REST
- `createConversation()` - Create new conversation
- `selectConversation(id)` - Switch to conversation and load messages
- `deleteConversation(id)` - Delete conversation
- `sendMessage(content)` - Send user message via WebSocket
- `updateConversationTitle(id, title)` - Rename conversation

**Key Features:**
- **Integrates `useWebSocket` hook** for real-time communication
- **Tool execution tracking** with start/complete events
- **Auto-naming conversations** from first user message
- **Streaming state management** with cleanup after completion
- **Ref-based tool execution tracking** (`currentToolExecutionRef`) to avoid stale closure issues

**WebSocket Integration:**
- Connects to `ws://localhost:8000/ws/onboarding` with auth token
- Handles `TOKEN`, `COMPLETE`, `ERROR`, `TOOL_START`, `TOOL_COMPLETE` message types
- Auto-reconnection logic in underlying service

**Pattern:** The ChatContext acts as a coordinator between WebSocket streams, REST API calls, and UI state updates.

### Data Fetching

The application uses a **hybrid REST + WebSocket** approach:

#### REST API (via Axios)
Used for CRUD operations and data persistence:
- **Authentication:** Login, register, get current user
- **Conversations:** List, create, read, update, delete
- **Messages:** Fetch message history
- **Transcription:** Upload audio for speech-to-text

**Service Pattern:**
- Each domain has a dedicated service class (`AuthService`, `ConversationService`, `TranscriptionService`)
- Services encapsulate API base URL, headers, and error handling
- Token automatically injected via `authService.getToken()` in headers

**Example:**
```typescript
// conversationService.ts
async listConversations(skip = 0, limit = 100): Promise<Conversation[]> {
  const response = await axios.get(`${API_URL}/api/conversations`, {
    headers: this.getAuthHeaders(),
    params: { skip, limit },
  });
  return response.data;
}
```

#### WebSocket (via WebSocketService)
Used for real-time chat with streaming responses:
- **Message sending:** User messages sent as JSON over WebSocket
- **Streaming responses:** AI responses streamed token-by-token
- **Tool execution events:** Real-time tool start/complete notifications
- **Connection management:** Auto-reconnection with exponential backoff

**WebSocket Message Flow:**
1. User types message and clicks send
2. `ChatContext.sendMessage()` calls `wsSendMessage(conversationId, content)`
3. WebSocket sends JSON: `{ type: "message", conversation_id, content }`
4. Backend processes and streams tokens back
5. Each token triggers `onToken` callback, updating `streamingMessage` state
6. When complete, `onComplete` callback reloads messages from REST API

**Key Design Decision:** Streaming happens via WebSocket, but final message persistence is handled by the backend. After streaming completes, the frontend fetches the full conversation history via REST to ensure consistency.

### Custom Hooks

The application uses custom hooks to encapsulate complex stateful logic:

#### 1. `useWebSocket` (`hooks/useWebSocket.ts`)

**Purpose:** Manage WebSocket connection lifecycle and streaming

**Features:**
- Auto-connect on mount with `autoConnect` option
- Connection state tracking (`isConnected`, `error`)
- Streaming message accumulation (token-by-token)
- Ref-based service instance management (prevents recreating WebSocket on re-render)
- Cleanup on unmount

**API:**
```typescript
const {
  isConnected,
  error,
  sendMessage,
  streamingMessage,
  connect,
  disconnect
} = useWebSocket({
  url: "ws://localhost:8000/ws/onboarding",
  token: authToken,
  autoConnect: true,
  onToolStart: (toolName, toolInput) => {},
  onToolComplete: (toolName, toolResult) => {}
});
```

**Pattern:** This hook delegates to `WebSocketService` class but provides a React-friendly interface with state and lifecycle management.

#### 2. `useSpeechToText` (`hooks/useSpeechToText.ts`)

**Purpose:** Browser audio recording with speech-to-text transcription

**Features:**
- Uses **MediaRecorder API** for browser audio capture
- Records audio as `audio/webm` with opus codec
- Manages recording state (`isRecording`, `isTranscribing`, `error`)
- Automatic transcription via backend API on stop
- Callback pattern for transcript completion

**API:**
```typescript
const {
  isRecording,
  isTranscribing,
  error,
  transcript,
  startRecording,
  stopRecording,
  resetTranscript
} = useSpeechToText({
  onTranscriptComplete: (text) => setInput(text)
});
```

**Flow:**
1. User clicks mic button → `startRecording()`
2. Request microphone permissions via `navigator.mediaDevices.getUserMedia()`
3. Create MediaRecorder, start recording chunks
4. User clicks stop → `stopRecording()`
5. `onstop` event assembles audio blob
6. Upload blob to `/api/transcribe` endpoint
7. Receive transcription result, invoke `onTranscriptComplete` callback
8. Callback sets transcript in message input textarea

**Pattern:** This hook encapsulates browser API complexity and async operations, exposing only simple boolean states and callbacks to components.

## Impact Analysis

### Component Responsibilities

The chat page components have clear, focused responsibilities:

#### `Chat.tsx` (Page Container)
- **Layout orchestration** - Assembles header, sidebar, and message components
- **Context consumption** - Pulls state from `useAuth()` and `useChat()`
- **Prop delegation** - Passes callbacks and state down to child components
- **Conditional rendering** - Shows connection status, errors, empty states

**No business logic** - All state management happens in contexts/hooks.

#### `ConversationSidebar.tsx`
- **Conversation list display** - Maps over `conversations` array
- **Inline editing** - Local state for edit mode with keyboard handlers (Enter/Escape)
- **Event bubbling control** - Uses `stopPropagation()` to prevent select when clicking edit/delete
- **CRUD actions** - Delegates to context methods (`onSelect`, `onCreate`, `onDelete`, `onRename`)

**Pattern:** Controlled component - all data flows from parent via props, events bubble up via callbacks.

#### `MessageList.tsx`
- **Message rendering** - Maps over `messages` with role-based styling
- **Streaming display** - Shows partial `streamingMessage` during streaming
- **Tool execution cards** - Displays `toolExecutions` array inline
- **Auto-scroll** - Uses ref and `useEffect` to scroll on message updates
- **Loading state** - Animated dots while waiting for first token

**Key UI Decision:** User messages align right (blue), assistant messages align left (gray). Streaming message shows with a pulsing dot indicator.

#### `MessageInput.tsx`
- **Text input** - Controlled textarea with Enter-to-send (Shift+Enter for newline)
- **Speech-to-text** - Integrates `useSpeechToText` hook with mic button
- **Send button** - Disabled when empty or disconnected
- **Visual feedback** - Mic button pulses red during recording, shows spinner during transcription

**Pattern:** Presentation component that coordinates two input methods (typing + voice).

#### `MarkdownMessage.tsx`
- **Markdown rendering** - Uses `react-markdown` with GFM support
- **Syntax highlighting** - Code blocks highlighted via `rehype-highlight`
- **Custom component overrides** - Tailwind-styled markdown elements
- **Security** - Links open in new tab with `rel="noopener noreferrer"`

**Pattern:** Pure rendering component with no state, delegates to libraries for markdown processing.

#### `ToolExecutionCard.tsx`
- **Tool status display** - Shows tool name, input, status (running/completed), result
- **Visual differentiation** - MCP tools have purple accent, local tools have blue
- **Loading state** - Spinner icon during execution, checkmark when complete

**Pattern:** Pure presentation component receiving `ToolExecution` object as prop.

### Data Flow Through Component Tree

**Authentication Flow:**
```
App (AuthProvider)
  → ProtectedRoute (useAuth)
    → Chat (useAuth, ChatProvider)
      → Header (user.username, logout)
```

**Chat Flow:**
```
Chat (ChatProvider)
  → ConversationSidebar
    ← conversations, currentConversation, callbacks
    → User clicks conversation
    → selectConversation(id) called
    → ChatContext loads messages via REST

  → MessageList
    ← messages, streamingMessage, isStreaming
    ← toolExecutions (from ChatContext)

  → MessageInput
    ← disabled (isConnected && isStreaming)
    → User types/speaks message
    → sendMessage(content) called
    → ChatContext sends via WebSocket
    → Backend streams response
    → streamingMessage updates (token-by-token)
    → On complete, messages reloaded
```

**Key Pattern:** Unidirectional data flow - state lives in contexts, flows down via props, events bubble up via callbacks. No prop drilling beyond one level.

## React Architecture Recommendations

### Strengths of Current Implementation

1. **Clean separation of concerns**
   - Contexts for state, hooks for logic, services for API, components for UI
   - Each layer has clear boundaries and single responsibility

2. **Excellent custom hook abstraction**
   - `useWebSocket` and `useSpeechToText` encapsulate complex logic cleanly
   - Reusable, testable, and maintainable

3. **Service layer pattern**
   - Singleton services (`authService`, `conversationService`) prevent multiple instances
   - Clear API boundaries between frontend and backend

4. **Type safety**
   - Comprehensive TypeScript types for all data structures
   - Proper typing of context interfaces and hook return values

5. **Modern React patterns**
   - Functional components with hooks throughout
   - Context API for state management (appropriate scale for this app)
   - Ref-based workarounds for closure issues (`currentToolExecutionRef`)

### Areas for Potential Improvement

While the current architecture is solid, there are some patterns that could be refined:

#### 1. **WebSocket Cleanup Timing**

**Current Pattern:**
```typescript
// ChatContext.tsx
useEffect(() => {
  if (wsStreamingMessage?.isComplete) {
    setTimeout(() => {
      setStreamingMessage(null);
      setToolExecutions([]);
      // ...
    }, 100);
  }
}, [wsStreamingMessage]);
```

**Observation:** The 100ms delay is a "magic number" used to ensure UI visibility before cleanup. This works but is brittle.

**Recommendation:** Consider using a flag-based approach where the UI explicitly acknowledges message display before triggering cleanup, or use CSS transitions with `transitionend` events for smoother UX.

#### 2. **Message Reload After Streaming**

**Current Pattern:** After WebSocket streaming completes, the frontend reloads all messages via REST API:

```typescript
if (wsStreamingMessage.isComplete) {
  setTimeout(() => {
    // ...
    if (currentConversation) {
      loadMessages(currentConversation.id);
    }
  }, 100);
}
```

**Observation:** This ensures consistency but causes a network round-trip after every message. The frontend could optimize by appending the streamed message directly to state rather than refetching.

**Recommendation:** Consider having the WebSocket `COMPLETE` message include the full persisted message object (with ID, timestamps) so the frontend can append it directly without a REST API call. This reduces latency and improves perceived performance.

#### 3. **Error Handling Granularity**

**Current Pattern:** Errors are caught and logged but not always surfaced to the user:

```typescript
const loadConversations = async () => {
  try {
    const convs = await conversationService.listConversations();
    setConversations(convs);
  } catch (err) {
    console.error("Failed to load conversations:", err);
  }
};
```

**Observation:** Failed operations silently fail with only console logs. Users may not realize something went wrong.

**Recommendation:** Add error state to context (`conversationsError`, `messagesError`) and display user-friendly error messages in the UI. Consider retry mechanisms for transient failures.

#### 4. **Optimistic Updates**

**Current Pattern:** When creating a conversation, the frontend waits for the server response:

```typescript
const createConversation = async () => {
  const newConv = await conversationService.createConversation({ title: "New Chat" });
  setConversations((prev) => [newConv, ...prev]);
  setCurrentConversation(newConv);
};
```

**Observation:** This introduces latency before the user sees the new conversation.

**Recommendation:** Consider optimistic updates - immediately add a temporary conversation to the UI, then replace it with the server response. This improves perceived performance.

#### 5. **Auto-Naming Logic Location**

**Current Pattern:** Auto-naming happens in `ChatContext.sendMessage()`:

```typescript
// ChatContext.tsx
if (isFirstMessage && currentConversation.title === "New Chat") {
  const autoTitle = generateTitleFromMessage(content);
  updateConversationTitle(currentConversation.id, autoTitle);
}
```

**Observation:** This works but couples message sending with title management. If auto-naming logic changes (e.g., use AI to generate titles), multiple places might need updates.

**Recommendation:** Consider moving this logic into a dedicated `useAutoNaming` hook or into the backend. The backend could auto-name on first message, reducing frontend complexity.

#### 6. **LocalStorage Sync**

**Current Pattern:** `authService` directly uses `localStorage` for token persistence:

```typescript
setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}
```

**Observation:** This works but doesn't handle edge cases like storage quota exceeded, multiple tabs, or security concerns (XSS).

**Recommendation:** Consider:
- **Security:** Evaluate if `httpOnly` cookies are more secure for token storage (prevents XSS attacks)
- **Multi-tab sync:** Listen to `storage` events to sync auth state across tabs
- **Error handling:** Wrap localStorage calls in try-catch for quota/permission errors

### Proposed Components

No new components needed. The current component structure is clean and well-organized.

**Possible Future Addition:** If tool execution UI grows more complex, consider extracting a `ToolExecutionList` component that manages its own state (expand/collapse individual executions, filtering, etc.).

### Proposed Hooks

The existing hooks are excellent. Potential future additions:

#### 1. `useOptimisticConversation`
Manages optimistic conversation creation with rollback on failure.

**API:**
```typescript
const { createConversation } = useOptimisticConversation({
  onSuccess: (conversation) => {},
  onError: (error) => {}
});
```

#### 2. `useAutoNaming`
Encapsulates conversation auto-naming logic, making it reusable and testable.

**API:**
```typescript
const { shouldAutoName, generateAndUpdateTitle } = useAutoNaming({
  conversation,
  messages,
  onUpdate: updateConversationTitle
});
```

### State Management Changes

The current Context API approach is appropriate for this application scale. No migration to Redux, Zustand, or other state libraries is necessary.

**Recommendation:** Continue with Context API. It provides:
- Simple mental model
- Built-in React integration
- Sufficient performance for this app size
- No additional dependencies

**When to consider alternatives:**
- If the app grows to 10+ contexts with complex interdependencies
- If performance profiling shows unnecessary re-renders
- If you need dev tools for time-travel debugging

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         App.tsx                             │
│                                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │ AuthProvider (AuthContext)                          │   │
│  │   - user, token, isAuthenticated                   │   │
│  │   - login(), register(), logout()                  │   │
│  │   - Uses: authService (localStorage + REST)       │   │
│  │                                                     │   │
│  │  ┌──────────────────────────────────────────────┐ │   │
│  │  │ ProtectedRoute                                │ │   │
│  │  │   - Checks isAuthenticated                   │ │   │
│  │  │   - Redirects to /login if not authed       │ │   │
│  │  │                                              │ │   │
│  │  │  ┌────────────────────────────────────────┐ │ │   │
│  │  │  │ ChatProvider (ChatContext)             │ │ │   │
│  │  │  │   - conversations, messages, streaming │ │ │   │
│  │  │  │   - Uses: useWebSocket hook            │ │ │   │
│  │  │  │           conversationService (REST)   │ │ │   │
│  │  │  │                                        │ │ │   │
│  │  │  │  ┌──────────────────────────────────┐ │ │ │   │
│  │  │  │  │ Chat.tsx (Page)                  │ │ │ │   │
│  │  │  │  │                                  │ │ │ │   │
│  │  │  │  │  ┌────────────────────────────┐ │ │ │ │   │
│  │  │  │  │  │ ConversationSidebar        │ │ │ │ │   │
│  │  │  │  │  │   - conversations list     │ │ │ │ │   │
│  │  │  │  │  │   - CRUD callbacks         │ │ │ │ │   │
│  │  │  │  │  └────────────────────────────┘ │ │ │ │   │
│  │  │  │  │                                  │ │ │ │   │
│  │  │  │  │  ┌────────────────────────────┐ │ │ │ │   │
│  │  │  │  │  │ MessageList                │ │ │ │ │   │
│  │  │  │  │  │   - messages               │ │ │ │ │   │
│  │  │  │  │  │   - streamingMessage       │ │ │ │ │   │
│  │  │  │  │  │   - toolExecutions         │ │ │ │ │   │
│  │  │  │  │  │   ├─ MarkdownMessage       │ │ │ │ │   │
│  │  │  │  │  │   └─ ToolExecutionCard     │ │ │ │ │   │
│  │  │  │  │  └────────────────────────────┘ │ │ │ │   │
│  │  │  │  │                                  │ │ │ │   │
│  │  │  │  │  ┌────────────────────────────┐ │ │ │ │   │
│  │  │  │  │  │ MessageInput               │ │ │ │ │   │
│  │  │  │  │  │   - Uses: useSpeechToText  │ │ │ │ │   │
│  │  │  │  │  │   - sendMessage callback   │ │ │ │ │   │
│  │  │  │  │  └────────────────────────────┘ │ │ │ │   │
│  │  │  │  └──────────────────────────────────┘ │ │ │   │
│  │  │  └────────────────────────────────────────┘ │ │   │
│  │  └──────────────────────────────────────────────┘ │   │
│  └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘

External Services:
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ authService      │     │conversationService│     │websocketService │
│ (REST + localStorage)   │ (REST)           │     │ (WebSocket)      │
└──────────────────┘     └──────────────────┘     └──────────────────┘
        │                        │                        │
        ▼                        ▼                        ▼
    /api/auth/*            /api/conversations/*    ws://*/ws/onboarding
```

**Data Flow:**
1. **Auth:** `AuthContext` → `authService` → REST API → localStorage
2. **Conversations:** `ChatContext` → `conversationService` → REST API
3. **Messages:** `ChatContext` → `useWebSocket` → `websocketService` → WebSocket
4. **Speech:** `MessageInput` → `useSpeechToText` → `transcriptionService` → REST API

**Key Pattern:** Contexts coordinate between services and UI, hooks encapsulate service interactions.

## Implementation Guidance

For anyone working with this codebase, follow these patterns:

### Adding a New Message Type

1. **Define type in `websocketService.ts`:**
   ```typescript
   export interface ServerNewMessageType {
     type: typeof MessageType.NEW_TYPE;
     field: string;
   }
   ```

2. **Add to `ServerMessage` union type**

3. **Handle in `websocketService.handleMessage()`**

4. **Add callback to `WebSocketConfig` interface**

5. **Wire callback through `useWebSocket` hook**

6. **Handle in `ChatContext` when initializing `useWebSocket`**

7. **Update UI components to consume new state**

### Adding a New REST Endpoint

1. **Add method to appropriate service class**
   ```typescript
   // conversationService.ts
   async newMethod(param: string): Promise<Result> {
     const response = await axios.post(`${API_URL}/api/endpoint`, { param }, {
       headers: this.getAuthHeaders(),
     });
     return response.data;
   }
   ```

2. **Add method to context that calls service**
   ```typescript
   // ChatContext.tsx
   const performAction = async (param: string) => {
     try {
       const result = await conversationService.newMethod(param);
       // Update state
     } catch (err) {
       console.error("Failed:", err);
     }
   };
   ```

3. **Expose method in context interface and provider value**

4. **Call from components via `useChat()` or `useAuth()`**

### Adding a New Component

1. **Create component file in appropriate directory:**
   - Pages: `src/pages/`
   - Chat-specific: `src/components/chat/`
   - Auth-specific: `src/components/auth/`
   - Reusable UI: `src/components/ui/`

2. **Use functional component with TypeScript:**
   ```typescript
   // ABOUTME: Brief description of what component does
   // ABOUTME: Key features or behavior

   interface ComponentProps {
     data: DataType;
     onAction: (param: string) => void;
   }

   export const Component: React.FC<ComponentProps> = ({ data, onAction }) => {
     // Component logic
     return <div>...</div>;
   };
   ```

3. **Import contexts via hooks:**
   ```typescript
   const { user } = useAuth();
   const { messages, sendMessage } = useChat();
   ```

4. **Follow existing styling patterns:**
   - Use Tailwind utility classes
   - Match spacing, colors, and sizing of existing components
   - Use Lucide icons for consistency

### Testing New Features

**Unit Testing:**
- Test hooks in isolation with `@testing-library/react-hooks`
- Test components with `@testing-library/react`
- Mock contexts with custom render helpers

**Integration Testing:**
- Test user flows (login → create conversation → send message)
- Use MSW (Mock Service Worker) for API mocking
- Test WebSocket interactions with mock WebSocket server

**E2E Testing:**
- Use Playwright or Cypress for full user journeys
- Test speech-to-text with fixture audio files
- Test streaming with controlled WebSocket responses

## Risks and Considerations

### 1. **WebSocket Reconnection Edge Cases**

**Risk:** If the WebSocket disconnects mid-stream, partial messages may be lost or duplicated.

**Current Mitigation:**
- Auto-reconnection with exponential backoff
- Error state displayed to user
- Send button disabled when disconnected

**Recommendation:** Add idempotency tokens to messages and implement server-side deduplication. Consider adding a "retry" mechanism for failed messages.

### 2. **Token Expiration Handling**

**Risk:** JWT tokens expire, but the frontend doesn't proactively refresh them.

**Current Behavior:**
- Token stored in localStorage
- No expiration check or refresh logic
- Failed API calls remove token and log out user

**Recommendation:**
- Implement token refresh flow (short-lived access token + long-lived refresh token)
- Add axios interceptor to automatically refresh on 401 responses
- Warn user before token expiration with "session ending soon" message

### 3. **Browser Compatibility**

**Risk:** MediaRecorder API and WebSocket may not work on older browsers.

**Current Mitigation:** None explicit.

**Recommendation:**
- Add feature detection for MediaRecorder before showing mic button
- Provide fallback message: "Speech-to-text requires a modern browser"
- Test on Safari (MediaRecorder support is limited)

### 4. **Memory Leaks in Long Sessions**

**Risk:** Long chat sessions accumulate messages and tool executions in memory.

**Current Mitigation:**
- Tool executions cleared after each message completes
- Messages loaded from server on conversation switch

**Recommendation:**
- Implement message pagination (only load recent 50 messages)
- Add "load more" button for message history
- Consider virtual scrolling for very long conversations

### 5. **State Synchronization Across Tabs**

**Risk:** User opens app in multiple tabs, auth state or messages become out of sync.

**Current Behavior:**
- Each tab maintains independent state
- Auth token shared via localStorage but no sync events

**Recommendation:**
- Listen to `storage` events to sync auth state across tabs
- Show warning if user logs out in one tab while another is active
- Consider using BroadcastChannel API for real-time state sync

### 6. **Accessibility**

**Risk:** Screen reader users may struggle with streaming messages and keyboard navigation.

**Current Mitigation:**
- Semantic HTML in most places
- ARIA labels on mic button (`aria-label`, `aria-pressed`)

**Recommendation:**
- Add ARIA live regions for streaming messages (`aria-live="polite"`)
- Ensure keyboard navigation works for conversation list (arrow keys)
- Add focus management when creating new conversations
- Test with screen readers (NVDA, JAWS, VoiceOver)

### 7. **Large File Uploads (Audio)**

**Risk:** Large audio recordings may fail to upload or cause UI freezes.

**Current Mitigation:**
- Audio recorded as webm/opus (compressed format)

**Recommendation:**
- Add file size checks before upload (warn if > 10MB)
- Show upload progress indicator
- Implement chunked upload for large files
- Add audio recording time limit (e.g., 5 minutes max)

## Testing Strategy

### Unit Tests

**Contexts:**
- Test `AuthContext` state transitions (login, logout, register)
- Test `ChatContext` message accumulation and streaming logic
- Mock service layer responses

**Hooks:**
- Test `useWebSocket` connection lifecycle
- Test `useSpeechToText` state transitions
- Mock browser APIs (MediaRecorder, WebSocket)

**Services:**
- Test `authService` token management
- Test `conversationService` API calls with mocked axios
- Test `websocketService` message handling

**Utilities:**
- Test `generateTitleFromMessage` with various inputs (empty, long, short)

**Example:**
```typescript
describe('useAuth', () => {
  it('initializes as loading', () => {
    const { result } = renderHook(() => useAuth());
    expect(result.current.isLoading).toBe(true);
  });

  it('authenticates user on login', async () => {
    mockAuthService.login.mockResolvedValue({ access_token: 'token' });
    const { result } = renderHook(() => useAuth());

    await act(() => result.current.login({ username: 'test', password: 'pass' }));

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user).toBeDefined();
  });
});
```

### Integration Tests

**User Flows:**
- Login → Create conversation → Send message → See streamed response
- Register → Auto-login → Navigate to chat
- Speech-to-text → Transcription appears in input → Send message

**WebSocket Integration:**
- Test message streaming with mock WebSocket server
- Test reconnection behavior
- Test tool execution notifications

**Example:**
```typescript
describe('Chat flow', () => {
  it('sends message and displays streamed response', async () => {
    render(<App />);

    // Login
    await userEvent.type(screen.getByPlaceholderText('Username'), 'testuser');
    await userEvent.type(screen.getByPlaceholderText('Password'), 'password');
    await userEvent.click(screen.getByText('Login'));

    // Create conversation
    await userEvent.click(screen.getByText('New Chat'));

    // Send message
    await userEvent.type(screen.getByPlaceholderText('Type a message...'), 'Hello');
    await userEvent.click(screen.getByText('Send'));

    // Verify message appears
    expect(await screen.findByText('Hello')).toBeInTheDocument();

    // Verify streaming response (mocked via MSW)
    expect(await screen.findByText(/AI response/i)).toBeInTheDocument();
  });
});
```

### E2E Tests

**Critical Paths:**
- Full onboarding flow (register → chat → onboarding questions)
- Speech-to-text input with fixture audio
- Multi-turn conversations with tool executions
- Conversation management (create, rename, delete)

**Browser Testing:**
- Test on Chrome, Firefox, Safari, Edge
- Test on mobile browsers (iOS Safari, Chrome Mobile)
- Test with slow network connections

**Example (Playwright):**
```typescript
test('user can complete onboarding conversation', async ({ page }) => {
  await page.goto('http://localhost:5173');

  // Register
  await page.click('text=Register');
  await page.fill('[placeholder="Username"]', 'newuser');
  await page.fill('[placeholder="Email"]', 'user@example.com');
  await page.fill('[placeholder="Password"]', 'securepass');
  await page.click('button:has-text("Register")');

  // Wait for redirect to chat
  await page.waitForURL('**/chat');

  // Create conversation
  await page.click('button:has-text("New Chat")');

  // Answer onboarding questions
  await page.fill('[placeholder="Type a message..."]', 'I want to learn about...');
  await page.click('button:has-text("Send")');

  // Wait for AI response
  await page.waitForSelector('text=/learning goals/i');

  // Continue conversation
  await page.fill('[placeholder="Type a message..."]', 'My goals are...');
  await page.click('button:has-text("Send")');

  // Verify tool execution appears
  await page.waitForSelector('[data-testid="tool-execution"]');
});
```

## Summary

The React frontend for the Orbio assignment demonstrates **excellent architectural decisions** and modern React best practices:

**Key Strengths:**
- Clean separation of concerns with contexts, hooks, services, and components
- Custom hooks (`useWebSocket`, `useSpeechToText`) encapsulate complex logic elegantly
- Service layer provides clear API boundaries
- Type-safe TypeScript throughout
- Real-time streaming with WebSocket handled cleanly
- Speech-to-text integration via MediaRecorder API

**Key Considerations:**
- Token refresh mechanism should be added for production use
- Optimistic updates would improve perceived performance
- Error handling could be more user-facing
- Accessibility improvements needed (ARIA live regions, keyboard nav)
- Consider backend-driven auto-naming for conversations

**Architecture Verdict:** The current implementation is **production-ready for the assignment scope** and demonstrates strong React architectural knowledge. The codebase is maintainable, testable, and follows modern patterns. Future enhancements should focus on polish (error handling, accessibility) rather than architectural changes.

**For the main agent:** All critical files are documented above with full paths. The component hierarchy is clear, state management is well-scoped, and data flow follows unidirectional patterns. The implementation requires no major refactoring - only incremental improvements for production hardening.
