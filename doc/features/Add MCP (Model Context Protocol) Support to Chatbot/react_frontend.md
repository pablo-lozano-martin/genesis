# React Frontend Analysis: MCP Tool Support UI

## Request Summary

This analysis examines how tools are currently displayed in the React frontend and identifies the necessary changes to add visual indicators for MCP (Model Context Protocol) tools. The feature requires distinguishing MCP tools from native Python tools in the chat UI while leveraging the existing tool execution display infrastructure.

## Relevant Files & Modules

### Files to Examine

**Chat Components:**
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/ToolExecutionCard.tsx` - Component that renders individual tool executions with status and results
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MessageList.tsx` - Displays chat messages and tool executions in chronological order
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/pages/Chat.tsx` - Main chat page container coordinating all chat components

**WebSocket & State Management:**
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/hooks/useWebSocket.ts` - Custom hook managing WebSocket lifecycle and message streaming
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/websocketService.ts` - WebSocket service handling connection and message parsing
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx` - Chat context providing tool execution state to components

**UI Components & Utilities:**
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/ui/badge.tsx` - Badge component using shadcn-ui pattern for tool name display
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/ui/card.tsx` - Card component wrapping tool execution display
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/lib/utils.ts` - Utility functions for className merging

**Type Definitions:**
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/types/auth.ts` - Authentication types (minimal relevance, included for completeness)

### Key Components & Hooks

| Component/Hook | File Path | Purpose | Relevance to MCP |
|---|---|---|---|
| `ToolExecutionCard` | `chat/ToolExecutionCard.tsx` | Renders tool execution with name, input, status, and result | Primary UI component for MCP tool display; needs source indicator |
| `MessageList` | `chat/MessageList.tsx` | Renders chat messages and tool executions in scrollable container | Renders tool executions; uses ToolExecutionCard |
| `useWebSocket` | `hooks/useWebSocket.ts` | Manages WebSocket lifecycle, callbacks for tool events | Receives `onToolStart` and `onToolComplete` callbacks; passes tool metadata |
| `WebSocketService` | `services/websocketService.ts` | Handles WebSocket connection and message parsing | Parses `TOOL_START` and `TOOL_COMPLETE` messages from server |
| `ChatContext` / `useChat` | `contexts/ChatContext.tsx` | Manages tool executions state array and current execution | Stores `toolExecutions[]` and receives tool events from WebSocket |
| `Badge` | `ui/badge.tsx` | Reusable badge component with variants | Used in ToolExecutionCard for tool name display |
| `Chat` (Page) | `pages/Chat.tsx` | Main chat page layout and composition | Passes toolExecutions from context to MessageList |

## Current Architecture Overview

### Pages & Routing

The chat feature is a single-page SPA with routing:
- **Entry:** `Chat.tsx` page component
- **Layout:** Three-column layout (sidebar, message area, input)
- **Sidebar:** `ConversationSidebar` - conversation list and management
- **Main area:** `MessageList` (messages/tools) + `MessageInput` (user input)

### State Management

**Architecture:** Context API with local state
- **ChatContext** (`contexts/ChatContext.tsx`):
  - Provides: conversations, currentConversation, messages, streamingMessage, toolExecutions, etc.
  - Manages: message loading, conversation selection, WebSocket integration
  - Uses: `useWebSocket` hook for real-time events

**Tool Execution State:**
```typescript
interface ToolExecution {
  id: string;                      // Unique ID: `${timestamp}-${toolName}`
  toolName: string;                // Tool name (no source indicator currently)
  toolInput: string;               // JSON string of input parameters
  toolResult?: string;             // String result after completion
  status: "running" | "completed"; // Current execution status
  startTime: string;               // ISO timestamp
  endTime?: string;                // ISO timestamp after completion
}
```

**State stored in ChatContext:**
- `toolExecutions: ToolExecution[]` - All tool executions in current message stream
- `currentToolExecution: ToolExecution | null` - Tool currently executing or last executed

### Data Fetching

**WebSocket-driven streaming:**
1. User sends message via `sendMessage(content)` → `ChatContext.wsSendMessage(conversationId, content)`
2. WebSocket listener (`onToolStart` callback) receives `TOOL_START` event
3. ChatContext handler (`handleToolStart`) creates `ToolExecution` and adds to state
4. ToolExecutionCard re-renders with new execution
5. WebSocket listener receives `TOOL_COMPLETE` event
6. ChatContext handler updates execution with result and status

**Message flow:**
```
Browser WebSocket
  ↓
ClientMessage {"type":"message", "conversation_id":"...", "content":"..."}
  ↓
Server (WebSocket handler)
  ↓
Emits: ServerToolStartMessage {"type":"tool_start", "tool_name":"...", "tool_input":"..."}
  ↓
Frontend WebSocket onmessage()
  ↓
useWebSocket onToolStart callback
  ↓
ChatContext handleToolStart
  ↓
ToolExecution added to state
  ↓
MessageList renders ToolExecutionCard
```

### Custom Hooks

**`useWebSocket(options: UseWebSocketOptions)`** - Manages WebSocket connection

```typescript
interface UseWebSocketOptions {
  url: string;                                      // WebSocket URL
  token: string;                                    // Auth token
  autoConnect?: boolean;                            // Auto-connect on mount
  onToolStart?: (toolName: string, toolInput: string) => void;    // Tool execution start
  onToolComplete?: (toolName: string, toolResult: string) => void; // Tool execution end
}
```

**Returns:**
- `isConnected: boolean` - WebSocket connection state
- `error: string | null` - Last error message
- `sendMessage(conversationId, content)` - Send user message
- `streamingMessage: StreamingMessage | null` - Current streaming LLM response

**Implementation details:**
- Creates `WebSocketService` instance internally
- Manages streaming message state (accumulates tokens)
- Handles connection lifecycle (connect/disconnect)
- Calls `onToolStart` and `onToolComplete` with tool metadata from server

## Impact Analysis

### Frontend Components Affected by MCP Support

**Direct Impact (primary changes needed):**

1. **`ToolExecutionCard.tsx`** - Tool display component
   - Current: Shows tool name, input, status icon, and result
   - Needed: Add MCP source indicator (badge, icon, or styling)
   - Data dependency: Will receive tool execution with new `source` field
   - Rendering: Add conditional rendering for MCP-specific UI

2. **`websocketService.ts`** - Message parsing
   - Current: Parses `TOOL_START` and `TOOL_COMPLETE` messages
   - Needed: Extract source information from WebSocket messages (if provided)
   - Data dependency: Backend must send tool source in event messages
   - No structural changes: Passes existing callbacks to config

3. **`useWebSocket.ts` hook** - WebSocket integration
   - Current: Callbacks receive (toolName, toolInput) / (toolName, toolResult)
   - Needed: Extend callbacks to include source information
   - Change type: Signature update: `onToolStart?: (toolName, toolInput, source?) => void`

4. **`ChatContext.tsx`** - State management
   - Current: `ToolExecution` interface has no source field
   - Needed: Add `source?: 'native' | 'mcp'` to ToolExecution interface
   - Change scope: Update `handleToolStart` to capture and store source
   - Storage: Add source to state alongside toolName, toolInput, etc.

**Indirect Impact (no changes, but dependent):**

5. **`MessageList.tsx`** - Container for tool executions
   - Current: Maps over `toolExecutions` and renders `ToolExecutionCard`
   - Impact: Automatically displays updated ToolExecutionCard (no changes needed)

6. **`Chat.tsx` page** - Main layout
   - Current: Passes toolExecutions from context to MessageList
   - Impact: Receives updated state from ChatContext (no changes needed)

7. **UI Components (`Badge`, `Card`)** - Reusable components
   - Current: Used for styling tool execution display
   - Impact: May add new variant classes for MCP styling (optional enhancement)

### State Data Flow

```
Server WebSocket Message (TOOL_START with source)
  ↓
websocketService.handleMessage()
  ↓
config.onToolStart(toolName, toolInput, source)  [NEW: include source]
  ↓
useWebSocket returns callback reference
  ↓
ChatContext.handleToolStart(toolName, toolInput, source)  [NEW: capture source]
  ↓
Creates ToolExecution with source field  [NEW: store source]
  ↓
setToolExecutions([...prev, execution])
  ↓
MessageList receives toolExecutions via context
  ↓
MessageList renders ToolExecutionCard for each execution
  ↓
ToolExecutionCard displays source indicator  [NEW: render MCP badge/icon]
```

### API Contract Dependencies

**Backend must provide:**
1. Tool source information in `ServerToolStartMessage` and `ServerToolCompleteMessage`
2. Source field values: `'native'` or `'mcp'` (or similar enum)
3. Consistent source in both TOOL_START and TOOL_COMPLETE events

**Current schema** (from `websocketService.ts`):
```typescript
interface ServerToolStartMessage {
  type: 'tool_start';
  tool_name: string;
  tool_input: string;
  timestamp: string;
}
```

**Proposed addition:**
```typescript
interface ServerToolStartMessage {
  type: 'tool_start';
  tool_name: string;
  tool_input: string;
  timestamp: string;
  source?: 'native' | 'mcp';  // NEW: identify tool origin
}
```

## React Architecture Recommendations

### 1. Extend ToolExecution Interface

**Location:** `contexts/ChatContext.tsx`

**Current:**
```typescript
export interface ToolExecution {
  id: string;
  toolName: string;
  toolInput: string;
  toolResult?: string;
  status: "running" | "completed";
  startTime: string;
  endTime?: string;
}
```

**Proposed:**
```typescript
export interface ToolExecution {
  id: string;
  toolName: string;
  toolInput: string;
  toolResult?: string;
  status: "running" | "completed";
  startTime: string;
  endTime?: string;
  source?: "native" | "mcp";  // NEW: identify tool origin (default: "native" for backward compat)
}
```

**Rationale:**
- Backward compatible (optional field)
- Enables conditional rendering in ToolExecutionCard
- Minimal change to existing state shape

### 2. Update WebSocket Callback Signatures

**Location:** `hooks/useWebSocket.ts`

**Current:**
```typescript
export interface UseWebSocketOptions {
  onToolStart?: (toolName: string, toolInput: string) => void;
  onToolComplete?: (toolName: string, toolResult: string) => void;
}
```

**Proposed:**
```typescript
export interface UseWebSocketOptions {
  onToolStart?: (toolName: string, toolInput: string, source?: string) => void;
  onToolComplete?: (toolName: string, toolResult: string, source?: string) => void;
}
```

**Rationale:**
- Allows ChatContext to receive source metadata
- Optional parameter maintains backward compatibility
- Follows existing callback pattern

### 3. Update WebSocketService Message Handling

**Location:** `services/websocketService.ts`

**Changes needed:**
1. Update `ServerToolStartMessage` and `ServerToolCompleteMessage` interfaces to include optional `source` field
2. Pass source to callbacks in `handleMessage()`:

**Current code (lines 155-161):**
```typescript
case MessageType.TOOL_START:
  this.config.onToolStart?.(message.tool_name, message.tool_input);
  break;
```

**Proposed:**
```typescript
case MessageType.TOOL_START:
  this.config.onToolStart?.(message.tool_name, message.tool_input, message.source);
  break;
```

Similarly for TOOL_COMPLETE (lines 159-161).

### 4. Update ChatContext Tool Handlers

**Location:** `contexts/ChatContext.tsx`

**Current `handleToolStart` (lines 53-64):**
```typescript
const handleToolStart = useCallback((toolName: string, toolInput: string) => {
  const execution: ToolExecution = {
    id: `${Date.now()}-${toolName}`,
    toolName,
    toolInput,
    status: "running",
    startTime: new Date().toISOString(),
  };
  currentToolExecutionRef.current = execution;
  setCurrentToolExecution(execution);
  setToolExecutions((prev) => [...prev, execution]);
}, []);
```

**Proposed:**
```typescript
const handleToolStart = useCallback((toolName: string, toolInput: string, source?: string) => {
  const execution: ToolExecution = {
    id: `${Date.now()}-${toolName}`,
    toolName,
    toolInput,
    status: "running",
    startTime: new Date().toISOString(),
    source: source || "native",  // Default to native for backward compatibility
  };
  currentToolExecutionRef.current = execution;
  setCurrentToolExecution(execution);
  setToolExecutions((prev) => [...prev, execution]);
}, []);
```

**Current `handleToolComplete` (lines 66-76):**
```typescript
const handleToolComplete = useCallback((_toolName: string, toolResult: string) => {
  setToolExecutions((prev) =>
    prev.map((exec) =>
      exec.id === currentToolExecutionRef.current?.id
        ? { ...exec, toolResult, status: "completed", endTime: new Date().toISOString() }
        : exec
    )
  );
  currentToolExecutionRef.current = null;
  setCurrentToolExecution(null);
}, []);
```

**Proposed:**
```typescript
const handleToolComplete = useCallback((_toolName: string, toolResult: string, source?: string) => {
  setToolExecutions((prev) =>
    prev.map((exec) =>
      exec.id === currentToolExecutionRef.current?.id
        ? { ...exec, toolResult, status: "completed", endTime: new Date().toISOString() }
        : exec
    )
  );
  currentToolExecutionRef.current = null;
  setCurrentToolExecution(null);
}, []);
```

**Note:** The `handleToolComplete` doesn't need to update source (already set in `handleToolStart`), but keeping the signature consistent is important for clarity.

### 5. Enhance ToolExecutionCard Component

**Location:** `components/chat/ToolExecutionCard.tsx`

**Current implementation (lines 14-37):**
- Shows tool name in badge
- Shows running/completed status with icons
- Shows tool result after completion

**Proposed additions:**

```typescript
export const ToolExecutionCard: React.FC<ToolExecutionCardProps> = ({ execution }) => {
  const isMcpTool = execution.source === "mcp";

  return (
    <Card className={`my-1.5 border-l-2 ${isMcpTool ? "border-l-purple-500 bg-purple-50/50" : "border-l-blue-500 bg-blue-50/50"}`}>
      <div className="px-3 py-2">
        <div className="flex items-center gap-2">
          {execution.status === "running" && (
            <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-600" />
          )}
          {execution.status === "completed" && (
            <Check className="h-3.5 w-3.5 text-green-600" />
          )}
          <Badge variant="outline" className={`font-mono text-xs ${isMcpTool ? "border-purple-300" : ""}`}>
            {execution.toolName}
          </Badge>
          {isMcpTool && (
            <Badge variant="secondary" className="text-xs">
              MCP
            </Badge>
          )}
          {execution.toolResult && (
            <span className="text-xs text-gray-600 font-mono">
              → {execution.toolResult}
            </span>
          )}
        </div>
      </div>
    </Card>
  );
};
```

**Design decisions:**
1. **Color scheme:** Use purple for MCP tools, blue for native (visual distinction)
2. **Badge:** Add "MCP" badge next to tool name for clear identification
3. **Border:** Different left border color for quick visual scanning
4. **Backward compatibility:** Default to native styling if source not provided

### 6. Optional: Create Dedicated MCP Badge Component

**Location:** `components/ui/mcp-badge.tsx` (optional new component)

**Purpose:** Reusable MCP source indicator

```typescript
import React from "react";
import { Badge } from "@/components/ui/badge";

interface MCPBadgeProps {
  showLabel?: boolean;
  className?: string;
}

export const MCPBadge: React.FC<MCPBadgeProps> = ({
  showLabel = false,
  className = ""
}) => {
  return (
    <Badge
      variant="secondary"
      className={`text-xs bg-purple-100 text-purple-700 ${className}`}
    >
      {showLabel ? "MCP Tool" : "MCP"}
    </Badge>
  );
};
```

**Usage in ToolExecutionCard:**
```typescript
{isMcpTool && <MCPBadge showLabel={false} />}
```

**Benefits:**
- Reusable across components
- Consistent MCP styling
- Easy to update appearance globally

## Implementation Guidance

### Step 1: Update Type Definitions

1. Modify `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx`:
   - Add `source?: "native" | "mcp"` field to `ToolExecution` interface
   - Update `handleToolStart` callback signature to include source parameter
   - Set source in execution object with default fallback to "native"

2. Modify `/Users/pablolozano/Mac Projects August/genesis/frontend/src/hooks/useWebSocket.ts`:
   - Update `UseWebSocketOptions` interface callbacks to accept source parameter
   - Pass source through to config callbacks

### Step 2: Update WebSocket Service

1. Modify `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/websocketService.ts`:
   - Add `source?: string` field to `ServerToolStartMessage` and `ServerToolCompleteMessage` interfaces
   - Update message handling to pass source to callbacks (lines 156, 160)

### Step 3: Update Component Display

1. Modify `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/ToolExecutionCard.tsx`:
   - Extract `isMcpTool` from `execution.source`
   - Apply conditional styling (border color, background)
   - Add MCP badge when `isMcpTool` is true
   - Maintain existing functionality for native tools

### Step 4: Backend Coordination

Ensure backend WebSocket handler sends source information:

1. Update `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py`:
   - Add optional `source` field to `ServerToolStartMessage` and `ServerToolCompleteMessage`
   - Set source to "mcp" for MCP tools, "native" for Python tools

2. Update `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py`:
   - When creating `ServerToolStartMessage`, include source information
   - When creating `ServerToolCompleteMessage`, include source information
   - Determine source from tool definition (check if tool is MCP-backed)

### Step 5: Testing

1. **Unit tests** for ToolExecutionCard:
   - Test rendering with `source: "native"`
   - Test rendering with `source: "mcp"`
   - Verify conditional styling applied correctly
   - Verify MCP badge appears only for MCP tools

2. **Integration tests**:
   - Mock WebSocket messages with source field
   - Verify state updates include source
   - Test full flow from message to display

3. **Manual testing**:
   - Test with native tool execution
   - Test with MCP tool execution
   - Verify visual distinction is clear
   - Test backward compatibility (missing source field)

## Risks and Considerations

### Risk 1: Backward Compatibility

**Issue:** Existing code doesn't expect source field in ToolExecution

**Mitigation:**
- Make source field optional with default value of "native"
- Set default in ChatContext when source is undefined
- WebSocket service passes source when available, undefined otherwise
- Graceful degradation: component works fine without source

### Risk 2: Source Information from Backend

**Issue:** Backend may not initially send source in WebSocket messages

**Mitigation:**
- Implement frontend gracefully (optional source parameter)
- Backend can send source incrementally
- Frontend displays native tool styling if source not provided
- Add clear logging when source is missing (for debugging)

### Risk 3: Multiple Tool Executions

**Issue:** Current tool execution tracking uses `currentToolExecutionRef` which only tracks one tool at a time

**Consideration:** If LangGraph supports parallel tool calls in future:
- Each tool would need its own tracking ID
- Backend would need to include tool call ID in messages
- Current implementation assumes `parallel_tool_calls=False`
- **No change needed for MCP support** - MCP doesn't change parallelism model

### Risk 4: Tool Source Discovery Complexity

**Issue:** How to determine if tool is MCP-backed in backend?

**Options:**
1. **Store source in tool adapter:** MCPToolAdapter includes source metadata
2. **Track in configuration:** MCP tools registered separately from native tools
3. **Check at runtime:** Determine source during tool execution

**Recommended:** Option 1 or 2 - source is known at tool binding time in backend

### Risk 5: Styling Consistency

**Issue:** MCP styling should be consistent across all MCP-related UI

**Mitigation:**
- Use TailwindCSS utility classes for consistency
- Consider creating reusable MCP badge component
- Document color scheme in style guide
- Purple is good choice (distinct from blue for native, doesn't conflict with existing palette)

## Testing Strategy

### Unit Tests for ToolExecutionCard

**File:** `frontend/src/components/chat/__tests__/ToolExecutionCard.test.tsx`

```typescript
describe('ToolExecutionCard', () => {
  describe('Native Tool Rendering', () => {
    it('should render with blue border for native tools', () => {
      const execution: ToolExecution = {
        id: 'test-1',
        toolName: 'add',
        toolInput: '{"a": 1, "b": 2}',
        status: 'completed',
        toolResult: '3',
        startTime: new Date().toISOString(),
        source: 'native'
      };

      const { container } = render(<ToolExecutionCard execution={execution} />);
      const card = container.querySelector('[class*="border-l-blue-500"]');
      expect(card).toBeInTheDocument();
    });

    it('should not show MCP badge for native tools', () => {
      const execution: ToolExecution = {
        // ... native tool setup
        source: 'native'
      };

      const { queryByText } = render(<ToolExecutionCard execution={execution} />);
      expect(queryByText('MCP')).not.toBeInTheDocument();
    });
  });

  describe('MCP Tool Rendering', () => {
    it('should render with purple border for MCP tools', () => {
      const execution: ToolExecution = {
        id: 'test-1',
        toolName: 'search_knowledge',
        toolInput: '{"query": "test"}',
        status: 'completed',
        toolResult: 'result from MCP',
        startTime: new Date().toISOString(),
        source: 'mcp'
      };

      const { container } = render(<ToolExecutionCard execution={execution} />);
      const card = container.querySelector('[class*="border-l-purple-500"]');
      expect(card).toBeInTheDocument();
    });

    it('should show MCP badge for MCP tools', () => {
      const execution: ToolExecution = {
        // ... MCP tool setup
        source: 'mcp'
      };

      const { getByText } = render(<ToolExecutionCard execution={execution} />);
      expect(getByText('MCP')).toBeInTheDocument();
    });
  });

  describe('Backward Compatibility', () => {
    it('should render as native tool when source is not provided', () => {
      const execution: ToolExecution = {
        id: 'test-1',
        toolName: 'multiply',
        toolInput: '{"a": 3, "b": 4}',
        status: 'completed',
        toolResult: '12',
        startTime: new Date().toISOString(),
        // source intentionally omitted
      };

      const { container } = render(<ToolExecutionCard execution={execution} />);
      const card = container.querySelector('[class*="border-l-blue-500"]');
      expect(card).toBeInTheDocument();
    });
  });
});
```

### Integration Tests for WebSocket Flow

**File:** `frontend/src/__tests__/mcp-tool-flow.test.tsx`

```typescript
describe('MCP Tool Execution Flow', () => {
  it('should display MCP tool execution with correct styling', async () => {
    const { getByText, container } = render(
      <ChatProvider>
        <MessageList messages={[]} streamingMessage={null} isStreaming={false} />
      </ChatProvider>
    );

    // Simulate WebSocket TOOL_START event with MCP source
    const toolExecution: ToolExecution = {
      id: '1234-search',
      toolName: 'search_knowledge_base',
      toolInput: '{"query": "test query"}',
      status: 'running',
      startTime: new Date().toISOString(),
      source: 'mcp'
    };

    // Would need to mock ChatContext to inject execution
    // Verify MCP badge appears
    expect(getByText('MCP')).toBeInTheDocument();
    expect(getByText('search_knowledge_base')).toBeInTheDocument();
  });
});
```

### Manual Test Cases

1. **Native Tool Execution**
   - Send message that triggers native tool
   - Verify tool execution card shows blue border
   - Verify no MCP badge is shown
   - Verify tool name and result display correctly

2. **MCP Tool Execution**
   - Send message that triggers MCP tool
   - Verify tool execution card shows purple border
   - Verify MCP badge is shown
   - Verify tool name and result display correctly

3. **Mixed Tool Execution**
   - Send message triggering both native and MCP tools
   - Verify both display with correct styling
   - Verify MCP tools distinct from native tools
   - Verify order maintained (chronological)

4. **Backward Compatibility**
   - Test with WebSocket messages missing source field
   - Verify tools render as native (default styling)
   - Verify no errors or undefined behavior

## Key Implementation Decisions

### 1. Source Field as Optional

**Decision:** Make `source` optional with default "native"

**Rationale:**
- Backward compatible with existing code
- Graceful degradation if backend doesn't send source immediately
- Minimal changes to existing components
- Clear upgrade path

### 2. Color Scheme (Blue vs Purple)

**Decision:** Native = blue (existing), MCP = purple (new)

**Rationale:**
- Purple is distinct from existing blue
- Good contrast with white/light backgrounds
- Doesn't conflict with other UI elements
- Consistent with modern design patterns
- Easy to remember and recognize

### 3. Badge Over Icon

**Decision:** Use "MCP" text badge instead of icon

**Rationale:**
- More readable than icon alone
- Consistent with existing tool name badge
- Clear to users unfamiliar with MCP
- Easy to extend with more information later
- Less cognitive load than symbol

### 4. State Capture at TOOL_START

**Decision:** Store source when tool starts, not when it completes

**Rationale:**
- Source is determined by LLM's tool selection
- Known at tool invocation time
- Simplifies state management
- Tool complete just updates result, doesn't change source
- Aligns with tool lifecycle

## Summary

The React frontend is well-structured for adding MCP tool support:

**Existing strengths:**
1. Clear separation of concerns (service, hook, context, component)
2. Callback-based event handling from WebSocket
3. Simple state management for tool executions
4. Reusable component patterns (Badge, Card)
5. Type-safe development with TypeScript

**Required changes are minimal:**
1. Add optional `source` field to `ToolExecution` interface
2. Update WebSocket callbacks to accept and pass source parameter
3. Update service message interfaces to include source
4. Enhance ToolExecutionCard with conditional styling and MCP badge
5. Coordinate with backend to send source in WebSocket events

**No architectural refactoring needed:**
- Existing data flow remains unchanged
- WebSocket streaming model supports new metadata
- State management scales to include source
- Component composition flexible enough for styling variations
- Backward compatibility maintained throughout

**Implementation complexity:** Low to Medium
- Straightforward type definition changes
- Simple conditional rendering in one component
- No new hooks or contexts required
- Limited surface area (single component primarily affected)

**Timeline estimate:** 2-3 hours for implementation + testing
- Type definition updates: 15 minutes
- WebSocket service changes: 15 minutes
- ToolExecutionCard enhancement: 30 minutes
- ChatContext updates: 15 minutes
- Testing: 60 minutes
