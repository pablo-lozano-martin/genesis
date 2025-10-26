# React Frontend Analysis: Tool-Calling Support with Transparent UI

## Request Summary

Add React frontend support for displaying tool execution transparently to users. This feature enables users to see what tools the LLM is using during a conversation, including tool names, inputs, outputs, and execution status. The backend implements LangGraph's `ToolNode` with the `tools_condition` conditional edge routing, so the frontend needs to display these tool invocations inline with messages without breaking the streaming experience.

## Relevant Files & Modules

### Files to Examine

**WebSocket Service & Protocol:**
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/websocketService.ts` - WebSocket protocol definition with message types (TOKEN, COMPLETE, ERROR, PING, PONG); needs extension for TOOL_START, TOOL_COMPLETE
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/hooks/useWebSocket.ts` - Custom hook managing WebSocket connection lifecycle, message sending, and streaming state

**State Management:**
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx` - Chat context providing messages, streamingMessage, isStreaming; needs extension for tool execution tracking
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/conversationService.ts` - REST API client for conversations and messages; defines Message interface

**Components:**
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MessageList.tsx` - Renders messages and streaming content; needs modification to display tool cards inline
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MessageInput.tsx` - Message input component; unchanged for tool feature
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/pages/Chat.tsx` - Main chat page orchestrating all components; unchanged core logic

**Pages & Routing:**
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/App.tsx` - Router setup and main app component
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/pages/Login.tsx` - Authentication page (unchanged)
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/pages/Register.tsx` - Registration page (unchanged)

**Authentication:**
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/AuthContext.tsx` - Auth context with user state (unchanged for tool feature)
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/authService.ts` - Auth API client (unchanged)

**Utilities:**
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/lib/titleUtils.ts` - Title generation utility (unchanged)
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/lib/utils.ts` - Shared utilities (may be extended)

### Key Components & Hooks

- **Chat page** in `/Users/pablolozano/Mac Projects August/genesis/frontend/src/pages/Chat.tsx` - Orchestrates chat UI, passes context to MessageList and MessageInput
- **useChat()** hook - Provides conversations, currentConversation, messages, streamingMessage, isStreaming, and methods to send messages
- **useWebSocket()** hook - Manages WebSocket connection, encapsulates onToken, onComplete, onError callbacks
- **MessageList** component - Displays all messages and streaming content; will render tool execution cards
- **ChatContext** - Central state management for chat conversations and messages

## Current Architecture Overview

### Pages & Routing

The frontend has a simple two-page structure:
- **Chat page** (`/chat`) - Main authenticated chat interface after login
- **Auth pages** (`/login`, `/register`) - Pre-authentication flow
- **Routing**: Protected route ensures only authenticated users access Chat page

Chat page orchestrates all chat functionality by consuming `useChat()` hook and passing state to child components.

### State Management

**ChatContext** manages:
- `conversations: Conversation[]` - List of user's conversations
- `currentConversation: Conversation | null` - Currently selected conversation
- `messages: Message[]` - Messages from REST API for current conversation
- `streamingMessage: string | null` - Token accumulation during streaming
- `isStreaming: boolean` - Flag indicating active LLM response generation
- `isConnected: boolean` - WebSocket connection status

**useWebSocket hook** returns:
- `isConnected: boolean` - Connection state
- `error: string | null` - Error messages
- `streamingMessage: StreamingMessage | null` - Streaming response with conversationId, content, isComplete
- `sendMessage(conversationId, content)` - Send user message via WebSocket

### Data Fetching

**REST API (via conversationService)**:
- List conversations
- Create, get, delete, update conversations
- Get messages for a conversation (loaded after conversation selection)

**WebSocket Streaming**:
- Real-time token streaming from LLM
- Automatic reconnection with exponential backoff
- Ping/pong keep-alive mechanism

**Message Flow**:
```
User Input → MessageInput sends to useChat.sendMessage()
           → ChatContext calls useWebSocket.sendMessage()
           → WebSocket sends ClientMessage { type: "message", conversation_id, content }
           → Backend processes via LangGraph
           → Backend streams tokens via "on_chat_model_stream" events
           → WebSocket receives ServerTokenMessage { type: "token", content }
           → useWebSocket updates streamingMessage state
           → ChatContext reflects in streamingMessage state
           → MessageList renders accumulating tokens
           → WebSocket receives ServerCompleteMessage { type: "complete", message_id, conversation_id }
           → ChatContext fetches full message history from REST API
           → MessageList shows completed message
```

### Custom Hooks

**useWebSocket()** - Encapsulates WebSocket lifecycle:
- Lazy connection on demand
- Auto-reconnect with exponential backoff (max 5 attempts)
- Message sending with connection validation
- Streaming state management
- Error handling and propagation

**useChat()** - Provides chat context:
- Conversation CRUD operations
- Message loading and streaming
- Auto-title generation on first message
- WebSocket integration via useWebSocket hook

## Current Message Format

**Frontend Message Interface** (`conversationService.ts`):
```typescript
interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}
```

**WebSocket Protocol** (currently):
- `MessageType.TOKEN` - Token streaming
- `MessageType.COMPLETE` - Response complete
- `MessageType.ERROR` - Error occurred
- `MessageType.PING/PONG` - Keep-alive

## Impact Analysis

### Which Components Will Be Affected

1. **WebSocket Protocol Extension** (websocketService.ts)
   - Add `TOOL_START` and `TOOL_COMPLETE` message types
   - Define `ToolStartMessage` and `ToolCompleteMessage` interfaces
   - Update `ServerMessage` union type

2. **useWebSocket Hook** (hooks/useWebSocket.ts)
   - Add `onToolStart` and `onToolComplete` callbacks to WebSocketConfig
   - Update handler in `handleMessage()` to route tool messages
   - Extend `UseWebSocketReturn` to expose tool execution state

3. **ChatContext** (contexts/ChatContext.tsx)
   - Add `toolExecutions` state to track active and completed tool runs
   - Add `currentToolExecution` to track which tool is executing
   - Extend WebSocket config to pass tool callbacks
   - Update context interface to expose tool state

4. **MessageList Component** (components/chat/MessageList.tsx)
   - Render ToolExecutionCard components between or alongside messages
   - Handle tool execution status visualization (pending, running, completed, error)
   - Display tool inputs, outputs, and execution time

5. **New Component: ToolExecutionCard**
   - Display single tool execution (input, status, output)
   - Show tool name, parameters, result
   - Indicate execution duration and status

6. **Chat Page** (pages/Chat.tsx)
   - Minimal changes - just pass tool state to MessageList

### Data Model Considerations

**Tool Execution State** (to add to ChatContext):
```typescript
interface ToolExecution {
  id: string;  // Unique identifier for this tool execution
  toolName: string;  // Name of the tool being executed
  input: Record<string, any>;  // Tool input parameters
  status: "pending" | "running" | "completed" | "error";
  output?: Record<string, any> | string;  // Tool result
  error?: string;  // Error message if status is error
  startTime: number;  // Timestamp when execution started
  endTime?: number;  // Timestamp when execution completed
}
```

**Message Enhancement** (future - currently messages are plain):
Note: Backend filters intermediate tool messages, only showing final AIMessage. Frontend receives final response with tool calls already executed.

## React Architecture Recommendations

### Proposed Components

**New: ToolExecutionCard Component**
- **Location**: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/ToolExecutionCard.tsx`
- **Purpose**: Display single tool execution with status and results
- **Props**:
  - `toolExecution: ToolExecution`
  - `isStreaming?: boolean` (true while tool is running)
- **Behavior**:
  - Shows tool name as badge/header
  - Displays input parameters (collapsed by default)
  - Shows execution status with spinner/checkmark/error icon
  - Displays output when complete
  - Shows execution duration

**Modified: MessageList Component**
- **Changes**:
  - Add prop `toolExecutions: ToolExecution[]` from ChatContext
  - Render ToolExecutionCard for each active tool execution
  - Insert tool cards between user/assistant message pairs or inline before assistant response
  - Maintain auto-scroll behavior when tool cards appear/update

**Pattern: Inline Tool Display**
- Tool executions should appear between the user message and the final assistant response
- Multiple concurrent tools (if parallel_tool_calls=true) should display side-by-side or stacked
- Tool status transitions (pending → running → complete) should update in-place without repositioning

### Proposed Hooks

**useToolExecution Hook** (optional refactor)
- **Location**: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/hooks/useToolExecution.ts`
- **Purpose**: Extract tool execution logic from ChatContext to separate concern
- **Responsibilities**:
  - Track active tool executions
  - Manage tool execution lifecycle (add, update, complete)
  - Calculate execution duration
  - Handle tool errors
- **Returns**: Tool state and mutation functions
- **Benefit**: Cleaner separation between message state and tool execution state

**Modified: useWebSocket Hook**
- **Changes**:
  - Add `onToolStart` callback handling
  - Add `onToolComplete` callback handling
  - Update `WebSocketConfig` interface to include these callbacks
  - Parse TOOL_START and TOOL_COMPLETE message types

**Benefit**: Encapsulates WebSocket protocol details, keeps ChatContext focused on state management

### State Management Changes

**ChatContext Extension**:
```typescript
interface ChatContextType {
  // Existing fields
  conversations: Conversation[];
  currentConversation: Conversation | null;
  messages: Message[];
  streamingMessage: string | null;
  isStreaming: boolean;
  isConnected: boolean;
  error: string | null;

  // New fields for tool execution tracking
  toolExecutions: ToolExecution[];  // All tool executions in current response
  currentToolExecution: ToolExecution | null;  // Currently executing tool

  // Existing methods
  loadConversations: () => Promise<void>;
  createConversation: () => Promise<void>;
  selectConversation: (id: string) => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  sendMessage: (content: string) => void;
  updateConversationTitle: (id: string, title: string) => Promise<void>;
}
```

**State Initialization**:
```typescript
const [toolExecutions, setToolExecutions] = useState<ToolExecution[]>([]);
const [currentToolExecution, setCurrentToolExecution] = useState<ToolExecution | null>(null);
```

**WebSocket Callback Handlers** (in ChatProvider):
```typescript
onToolStart: (toolName: string, input: Record<string, any>) => {
  // Create new ToolExecution with pending status
  // Add to toolExecutions array
  // Set as currentToolExecution
  // Update state
}

onToolComplete: (toolName: string, output: Record<string, any> | string) => {
  // Update currentToolExecution status to completed
  // Set output
  // Set endTime for duration calculation
  // Keep in toolExecutions for display
}

onToolError: (toolName: string, error: string) => {
  // Update currentToolExecution status to error
  // Set error message
  // Keep in toolExecutions for display
}
```

**Cleanup Logic**:
When a response completes:
- Keep toolExecutions visible briefly (optional fade-out animation)
- OR clear toolExecutions when ServerCompleteMessage arrives
- Decision depends on UX: show tool summary or clean up immediately

### Data Flow Diagram

```
WebSocket Backend → LangGraph Tool Execution Flow

Backend Flow:
1. User sends message via WebSocket
2. LangGraph call_llm node invokes LLM with tools bound
3. LLM returns ToolCall in AIMessage
4. tools_condition routes to ToolNode
5. ToolNode executes tool (multiply, etc.)
6. Result captured as ToolMessage
7. Routed back to call_llm for another iteration
8. Final AIMessage without tool calls sent to completion

Frontend Flow:
1. WebSocket receives on_chat_model_stream event → TokenMessage
2. Accumulate tokens in streamingMessage
3. WebSocket receives tool_start event → ToolStartMessage
   - Create ToolExecution with pending status
   - Add to toolExecutions array
   - Trigger MessageList re-render
4. Tool executes on backend (no WebSocket event during execution)
5. WebSocket receives tool_complete event → ToolCompleteMessage
   - Update ToolExecution with output
   - Set status to completed
   - Trigger MessageList re-render
6. WebSocket receives final on_chat_model_stream events
   - Continue accumulating response tokens
7. WebSocket receives ServerCompleteMessage
   - Set isStreaming to false
   - Clear or fade out toolExecutions
   - Load full message history via REST API

Visual Result:
┌─────────────────────────────┐
│ User: Calculate 3 * 4       │
└─────────────────────────────┘

Tool Execution:
┌─ Tool: multiply ────────────┐
│ Input: a=3, b=4             │
│ Status: ✓ Completed         │
│ Output: 12                  │
└─────────────────────────────┘

┌─────────────────────────────┐
│ Assistant: The answer is... │
│ (streaming...)              │
└─────────────────────────────┘
```

## Implementation Guidance

### Phase 1: WebSocket Protocol Extension

1. **Update websocketService.ts**:
   - Add `TOOL_START` and `TOOL_COMPLETE` to `MessageType` enum
   - Define `ToolStartMessage` interface:
     ```typescript
     interface ToolStartMessage {
       type: typeof MessageType.TOOL_START;
       tool_name: string;
       tool_input: Record<string, any>;
     }
     ```
   - Define `ToolCompleteMessage` interface:
     ```typescript
     interface ToolCompleteMessage {
       type: typeof MessageType.TOOL_COMPLETE;
       tool_name: string;
       tool_output: Record<string, any> | string;
     }
     ```
   - Update `ServerMessage` union to include new types
   - Add handler cases in `handleMessage()` switch statement

2. **Coordinate with Backend**:
   - Confirm backend websocket_schemas.py defines matching message types
   - Backend handler.py needs to emit TOOL_START when tools_condition routes to ToolNode
   - Backend needs to emit TOOL_COMPLETE after tool execution completes

### Phase 2: Hook and Context Updates

1. **Update useWebSocket Hook**:
   - Add `onToolStart` and `onToolComplete` callbacks to `WebSocketConfig` interface
   - Pass callbacks to WebSocketService constructor
   - Update WebSocketService.handleMessage() to invoke callbacks
   - Update hook to return tool state (optional, or handle in ChatContext)

2. **Extend ChatContext**:
   - Add `toolExecutions` and `currentToolExecution` state
   - Create unique ID for each tool execution (e.g., `${Date.now()}-${toolName}`)
   - Implement handlers for tool lifecycle (start, complete, error)
   - Add callbacks to useWebSocket config
   - Expose tool state in ChatContextType

### Phase 3: UI Components

1. **Create ToolExecutionCard Component**:
   - Accept `toolExecution: ToolExecution` prop
   - Display tool name as badge (Shadcn Badge component)
   - Show status icon (Shadcn Check/X/Loader icons)
   - Make input/output collapsible (Shadcn Accordion or custom toggle)
   - Include execution duration calculation
   - Style with TailwindCSS for consistency

2. **Update MessageList Component**:
   - Accept `toolExecutions` prop from ChatContext
   - Render ToolExecutionCard for each execution
   - Position tool cards between user and assistant message pairs
   - Handle tool card updates without breaking scroll behavior
   - Consider: fade-out animation when response completes

3. **Update Chat Page**:
   - Pass `toolExecutions` from useChat() to MessageList
   - No other changes needed at this level

### Phase 4: Testing

1. **Unit Tests**:
   - ToolExecutionCard rendering with different statuses
   - Tool state management in ChatContext
   - Message type handling in websocketService

2. **Integration Tests**:
   - WebSocket message flow with tool execution
   - Tool card appearance/updates during message streaming
   - Tool state cleanup after response complete

3. **Manual Testing**:
   - User sends message that triggers tool call
   - Tool card appears while tool executes
   - Tool output displays when complete
   - Final assistant response appears after tools complete

## Risks and Considerations

### Prop Drilling Risk
**Risk**: Passing `toolExecutions` through multiple component layers
**Mitigation**: Tool state lives in ChatContext, passed only to MessageList. If future refactoring adds more tool-related props, consider extracting ToolExecutionContext.

### Scroll Behavior with Dynamic Content
**Risk**: Tool execution cards appearing/updating may cause jank or scroll position loss
**Mitigation**: Use `ref.scrollIntoView()` existing pattern in MessageList. Consider: batch updates, debounce re-renders, or CSS transitions for smooth appearance.

### Concurrent Tool Execution
**Risk**: Backend may support parallel_tool_calls=True, but frontend only tracks `currentToolExecution`
**Design Decision**: Store `toolExecutions` as array, render all concurrently executing tools. This handles future parallel execution without code changes.

### Tool Output Size
**Risk**: Large tool outputs (complex JSON) may cause performance issues
**Mitigation**: Truncate output display, make full output available in collapsible section. Implement with Accordion for expandable details.

### State Cleanup Timing
**Risk**: Tool executions need to be cleared between messages to avoid visual clutter
**Design Decision**: Clear `toolExecutions` and `currentToolExecution` when ServerCompleteMessage arrives. Consider optional fade-out animation before clearing.

### Backend Message Filtering
**Note**: Backend WebSocket handler filters intermediate tool messages (ToolMessage types) and only streams final AIMessage. This means:
- Frontend receives tokens from final LLM response only
- Tool execution visibility depends on backend emitting explicit TOOL_START/TOOL_COMPLETE events
- Coordinator responsibility with backend: ensure events are properly sent during astream_events() iteration

### Message History Persistence
**Note**: Tool information is NOT stored in Message.content (only final response). If future requirement demands tool history in database:
- Extend Message model with optional `tools_used` field
- Modify backend to save tool execution records separately
- Update frontend Message interface and MessageList rendering

## Testing Strategy

### Unit Tests

**websocketService.ts**:
- Test TOOL_START message parsing
- Test TOOL_COMPLETE message parsing
- Verify callback invocation for tool messages

**ToolExecutionCard Component**:
- Render with pending status (spinner)
- Render with completed status (checkmark + output)
- Render with error status (X + error message)
- Expand/collapse input/output sections
- Calculate and display execution duration

**ChatContext Tool Logic**:
- Add tool execution to state on TOOL_START
- Update tool execution on TOOL_COMPLETE
- Clear executions on message complete
- Handle rapid tool start/complete sequences

### Integration Tests

**WebSocket + ChatContext Flow**:
- Send user message
- Receive TOOL_START event
- Verify `toolExecutions` state updated
- Verify `currentToolExecution` set
- Receive TOOL_COMPLETE event
- Verify tool output reflected in state
- Verify state cleared on ServerCompleteMessage

**MessageList + ToolExecutionCard**:
- Render MessageList with tool executions
- Verify ToolExecutionCard appears for each execution
- Verify cards update on execution complete
- Verify scroll positioning maintained

### End-to-End Tests

**Full Message with Tool Execution**:
1. User sends message (e.g., "multiply 3 and 4")
2. Tool card appears with pending status
3. Tool executes and output displays
4. Final assistant response appears
5. All content visible and properly formatted

**Multiple Sequential Messages**:
1. First message with tool execution completes
2. Tool card clears
3. Second message sent
4. No tool state leakage from previous message

**Error Scenarios**:
1. Tool execution fails - error displayed in ToolExecutionCard
2. WebSocket receives error message - handled gracefully
3. Tool state not cleared - no orphaned executions visible

## Summary of Key Decisions

1. **Tool executions stored in ChatContext, not in Message model** - Keeps message history clean, tool info is execution metadata
2. **ToolExecutionCard as separate component** - Reusable, testable, independent of message rendering
3. **Array-based tool tracking** - Supports future parallel execution without refactoring
4. **Tool state cleared on message complete** - Clean UX, no visual clutter between messages
5. **Inline tool display between user and final response** - Users see what tools were invoked in conversation flow
6. **WebSocket protocol extended, not modified** - Backward compatible, additive changes only

## Assumptions & Open Questions

**Assumption 1**: Backend will emit TOOL_START and TOOL_COMPLETE events during astream_events() iteration
- **Confirm with backend**: How are tool execution events emitted? Are they part of astream_events() v2 protocol?

**Assumption 2**: Tool input/output are JSON-serializable
- **Confirm with backend**: What format are tool_input and tool_output in ServerTokenMessage events?

**Assumption 3**: Only one conversation active at a time
- **Current behavior**: Chat page shows one conversation, tool state scoped to currentConversation
- **Future consideration**: If multi-chat needed, tool state scoping may need adjustment

**Assumption 4**: Tool execution display should be transient (not persisted in message history)
- **Design decision**: Tool cards fade/clear after response complete
- **Alternative**: Store tool history in database for future reference

**Assumption 5**: No tool parameter validation needed on frontend
- **Backend responsibility**: Validate tool parameters before execution
- **Frontend responsibility**: Display what backend sends, assume valid

## Dependencies & Prerequisites

- Shadcn UI components installed: Badge, Check, X, Loader, Accordion (or custom CSS)
- TailwindCSS already configured
- Backend implements tool execution event emission in websocket_handler.py
- Backend websocket_schemas.py defines matching message types
- LangGraph ToolNode and tools_condition already integrated in chat_graph.py
