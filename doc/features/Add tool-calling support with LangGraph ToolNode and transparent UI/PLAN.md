# Implementation Plan: Add Tool-Calling Support with LangGraph ToolNode and Transparent UI

## Executive Summary

This plan outlines the implementation of tool-calling support using LangGraph's ToolNode with transparent UI feedback. The feature enables the AI to invoke tools (functions) during conversations, with real-time visibility into tool execution for users.

**Key Components:**
- Backend: Tool definitions (add, multiply), LangGraph ToolNode integration, WebSocket event streaming
- Frontend: Tool execution UI cards, WebSocket protocol extensions, state management
- Architecture: Maintains hexagonal boundaries, leverages existing bind_tools() infrastructure

**Complexity:** Medium - Most infrastructure exists; primary work is WebSocket event handling and UI components

---

## Phase 1: Backend - Tool Definitions

### 1.1 Create `add` Tool

**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/add.py`

**Implementation:**
```python
def add(a: int, b: int) -> int:
    """
    Simple addition tool.

    Args:
        a: First number.
        b: Second number.
    """
    return a + b
```

**Rationale:**
- Mirrors existing multiply.py pattern
- Simple POC for tool-calling validation
- Enables multi-tool execution testing

### 1.2 Update Tool Exports

**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/__init__.py`

**Change:**
```python
from .multiply import multiply
from .add import add

__all__ = ["multiply", "add"]
```

**Rationale:**
- Makes both tools easily importable
- Follows existing export pattern

---

## Phase 2: Backend - WebSocket Protocol Extensions

### 2.1 Extend Message Type Enum

**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py`

**Location:** Line 9-17 (MessageType enum)

**Change:**
```python
class MessageType(str, Enum):
    MESSAGE = "message"
    TOKEN = "token"
    COMPLETE = "complete"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"
    TOOL_START = "tool_start"      # NEW
    TOOL_COMPLETE = "tool_complete"  # NEW
```

**Rationale:**
- Adds tool lifecycle events to protocol
- Maintains backward compatibility (old clients ignore unknown types)

### 2.2 Create Tool Message Schemas

**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py`

**Location:** After ServerErrorMessage (after line 64)

**Add:**
```python
class ServerToolStartMessage(BaseModel):
    """
    Server message indicating tool execution has started.

    Sent when the LLM decides to call a tool and before the tool executes.
    """
    type: Literal[MessageType.TOOL_START] = MessageType.TOOL_START
    tool_name: str
    tool_input: str  # JSON string of input args
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ServerToolCompleteMessage(BaseModel):
    """
    Server message indicating tool execution has completed.

    Sent when the tool finishes execution with results.
    """
    type: Literal[MessageType.TOOL_COMPLETE] = MessageType.TOOL_COMPLETE
    tool_name: str
    tool_result: str  # String representation of result
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
```

**Imports needed:**
```python
from datetime import datetime
from typing import Literal
```

**Rationale:**
- Pydantic validation for type safety
- Timestamp for debugging/logging
- tool_input as JSON string for flexibility
- tool_result as string (tools return simple values for POC)

### 2.3 Update ServerMessage Union Type

**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py`

**Location:** After PongMessage definition

**Change:**
```python
ServerMessage = (
    ServerTokenMessage
    | ServerCompleteMessage
    | ServerErrorMessage
    | PongMessage
    | ServerToolStartMessage      # NEW
    | ServerToolCompleteMessage   # NEW
)
```

**Rationale:**
- Allows type-safe message handling
- Enables pattern matching on message types

---

## Phase 3: Backend - WebSocket Event Streaming for Tools

### 3.1 Extend Event Loop in WebSocket Handler

**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py`

**Location:** Line 145-152 (astream_events loop)

**Current Code:**
```python
async for event in graph.astream_events(input_data, config, version="v2"):
    # Stream tokens from LLM to client
    if event["event"] == "on_chat_model_stream":
        chunk = event["data"]["chunk"]
        if hasattr(chunk, 'content') and chunk.content:
            token_msg = ServerTokenMessage(content=chunk.content)
            await manager.send_message(websocket, token_msg.model_dump())
```

**Replace with:**
```python
# Track current tool call context (needed because tool events don't contain tool names)
current_tool_call = None

async for event in graph.astream_events(input_data, config, version="v2"):
    event_type = event["event"]

    # Stream LLM tokens
    if event_type == "on_chat_model_stream":
        chunk = event["data"]["chunk"]
        if hasattr(chunk, 'content') and chunk.content:
            token_msg = ServerTokenMessage(content=chunk.content)
            await manager.send_message(websocket, token_msg.model_dump())

    # Cache tool call information before tool execution
    elif event_type == "on_chat_model_end":
        # Check if AIMessage contains tool_calls
        output = event["data"].get("output")
        if output and hasattr(output, 'tool_calls') and output.tool_calls:
            # Store first tool call (parallel_tool_calls=False in our config)
            current_tool_call = output.tool_calls[0]

    # Emit TOOL_START when tool begins execution
    elif event_type == "on_tool_start":
        if current_tool_call:
            import json
            tool_start_msg = ServerToolStartMessage(
                tool_name=current_tool_call.get("name", "unknown"),
                tool_input=json.dumps(current_tool_call.get("args", {}))
            )
            await manager.send_message(websocket, tool_start_msg.model_dump())

    # Emit TOOL_COMPLETE when tool finishes
    elif event_type == "on_tool_end":
        if current_tool_call:
            tool_result = event["data"].get("output", "")
            tool_complete_msg = ServerToolCompleteMessage(
                tool_name=current_tool_call.get("name", "unknown"),
                tool_result=str(tool_result)
            )
            await manager.send_message(websocket, tool_complete_msg.model_dump())
            current_tool_call = None  # Reset for next iteration
```

**Imports needed:**
```python
# Add at top of file after existing imports:
import json
```

**Rationale:**
- `on_chat_model_end` captures tool_calls from AIMessage before tool execution
- `on_tool_start` emits when ToolNode begins executing
- `on_tool_end` emits when ToolNode completes
- Tool name tracking needed because tool events don't contain tool metadata directly
- `parallel_tool_calls=False` ensures single tool execution (simplifies tracking)

**Critical Insight from Data Flow Analysis:**
LangGraph's astream_events() emits events in this order:
1. `on_chat_model_stream` (reasoning tokens)
2. `on_chat_model_end` (AIMessage with tool_calls)
3. `on_tool_start` (ToolNode begins)
4. `on_tool_end` (ToolNode completes, ToolMessage created)
5. `on_chat_model_stream` (LLM generates final response with tool result context)
6. `on_chat_model_end` (final AIMessage)

---

## Phase 4: Backend - Update Graph Tool Registration

### 4.1 Add `add` Tool to Graph

**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py`

**Location:** Line 41 (tools list)

**Current:**
```python
tools = [multiply]
```

**Change to:**
```python
tools = [add, multiply]
```

**Imports needed:**
```python
from app.langgraph.tools.add import add
```

**Rationale:**
- Registers both POC tools with ToolNode
- Enables multi-tool testing scenarios

### 4.2 Update call_llm Node Tool List

**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py`

**Location:** Line 34 (tools list)

**Current:**
```python
tools = [multiply]
```

**Change to:**
```python
tools = [add, multiply]
```

**Imports needed:**
```python
from app.langgraph.tools.add import add
```

**Rationale:**
- Ensures tools are bound to LLM provider
- Matches graph-level tool registration

**Note from Hexagonal Analysis:**
Current approach hardcodes tools in two locations (graph and node). For this POC, acceptable. Future enhancement: centralized tool registry pattern.

---

## Phase 5: Frontend - TypeScript Type Extensions

### 5.1 Extend MessageType Enum

**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/websocketService.ts`

**Location:** Line 4-11 (MessageType constant)

**Current:**
```typescript
export const MessageType = {
  MESSAGE: "message",
  TOKEN: "token",
  COMPLETE: "complete",
  ERROR: "error",
  PING: "ping",
  PONG: "pong",
} as const;
```

**Change to:**
```typescript
export const MessageType = {
  MESSAGE: "message",
  TOKEN: "token",
  COMPLETE: "complete",
  ERROR: "error",
  PING: "ping",
  PONG: "pong",
  TOOL_START: "tool_start",      // NEW
  TOOL_COMPLETE: "tool_complete", // NEW
} as const;
```

### 5.2 Add Tool Message Interfaces

**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/websocketService.ts`

**Location:** After ServerPongMessage (after line 40)

**Add:**
```typescript
export interface ServerToolStartMessage {
  type: typeof MessageType.TOOL_START;
  tool_name: string;
  tool_input: string;
  timestamp: string;
}

export interface ServerToolCompleteMessage {
  type: typeof MessageType.TOOL_COMPLETE;
  tool_name: string;
  tool_result: string;
  timestamp: string;
}
```

### 5.3 Update ServerMessage Union Type

**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/websocketService.ts`

**Location:** Line 42 (ServerMessage type)

**Current:**
```typescript
export type ServerMessage = ServerTokenMessage | ServerCompleteMessage | ServerErrorMessage | ServerPongMessage;
```

**Change to:**
```typescript
export type ServerMessage =
  | ServerTokenMessage
  | ServerCompleteMessage
  | ServerErrorMessage
  | ServerPongMessage
  | ServerToolStartMessage      // NEW
  | ServerToolCompleteMessage;  // NEW
```

**Rationale:**
- Type-safe message handling in TypeScript
- Mirrors backend schema exactly
- Enables autocomplete and compile-time validation

---

## Phase 6: Frontend - WebSocket Service Event Handling

### 6.1 Extend WebSocketConfig Interface

**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/websocketService.ts`

**Location:** Line 44-52 (WebSocketConfig interface)

**Current:**
```typescript
export interface WebSocketConfig {
  url: string;
  token: string;
  onToken?: (token: string) => void;
  onComplete?: (messageId: string, conversationId: string) => void;
  onError?: (error: string, code?: string) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}
```

**Change to:**
```typescript
export interface WebSocketConfig {
  url: string;
  token: string;
  onToken?: (token: string) => void;
  onComplete?: (messageId: string, conversationId: string) => void;
  onError?: (error: string, code?: string) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onToolStart?: (toolName: string, toolInput: string) => void;      // NEW
  onToolComplete?: (toolName: string, toolResult: string) => void;  // NEW
}
```

### 6.2 Update handleMessage Method

**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/websocketService.ts`

**Location:** Line 111-137 (handleMessage method)

**Add to switch statement (after PONG case, before default):**
```typescript
case MessageType.TOOL_START:
  this.config.onToolStart?.(message.tool_name, message.tool_input);
  break;

case MessageType.TOOL_COMPLETE:
  this.config.onToolComplete?.(message.tool_name, message.tool_result);
  break;
```

**Rationale:**
- Routes tool events to callbacks
- Optional callbacks preserve backward compatibility
- Clean separation of concerns

---

## Phase 7: Frontend - State Management for Tool Executions

### 7.1 Create ToolExecution Interface

**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx`

**Location:** After imports, before ChatContextType interface (around line 10)

**Add:**
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

**Rationale:**
- Tracks tool lifecycle state
- id for React key stability
- status for UI rendering logic
- Timestamps for debugging/logging

### 7.2 Extend ChatContextType Interface

**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx`

**Location:** Line 13-27 (ChatContextType interface)

**Add after `error` field:**
```typescript
toolExecutions: ToolExecution[];
currentToolExecution: ToolExecution | null;
```

**Rationale:**
- toolExecutions: Array of all tools executed during current message
- currentToolExecution: Currently executing tool (null if none)

### 7.3 Add Tool State Variables

**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx`

**Location:** After streamingMessage state (around line 36)

**Add:**
```typescript
const [toolExecutions, setToolExecutions] = useState<ToolExecution[]>([]);
const [currentToolExecution, setCurrentToolExecution] = useState<ToolExecution | null>(null);
```

### 7.4 Add Tool Event Handlers to useWebSocket

**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx`

**Location:** Line 39-43 (useWebSocket call)

**Current:**
```typescript
const { isConnected, error, sendMessage: wsSendMessage, streamingMessage: wsStreamingMessage } = useWebSocket({
  url: `${WS_URL}/ws/chat`,
  token,
  autoConnect: true,
});
```

**Change to:**
```typescript
const { isConnected, error, sendMessage: wsSendMessage, streamingMessage: wsStreamingMessage } = useWebSocket({
  url: `${WS_URL}/ws/chat`,
  token,
  autoConnect: true,
  onToolStart: (toolName: string, toolInput: string) => {
    const execution: ToolExecution = {
      id: `${Date.now()}-${toolName}`,
      toolName,
      toolInput,
      status: "running",
      startTime: new Date().toISOString(),
    };
    setCurrentToolExecution(execution);
    setToolExecutions((prev) => [...prev, execution]);
  },
  onToolComplete: (toolName: string, toolResult: string) => {
    setToolExecutions((prev) =>
      prev.map((exec) =>
        exec.id === currentToolExecution?.id
          ? { ...exec, toolResult, status: "completed", endTime: new Date().toISOString() }
          : exec
      )
    );
    setCurrentToolExecution(null);
  },
});
```

**Rationale:**
- onToolStart creates new execution, marks as running
- onToolComplete updates execution with result, marks as completed
- Array tracking supports multiple tool calls per message

### 7.5 Clear Tool Executions on Message Complete

**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx`

**Location:** Line 45-59 (useEffect for wsStreamingMessage)

**Current:**
```typescript
useEffect(() => {
  if (wsStreamingMessage) {
    setStreamingMessage(wsStreamingMessage.content);
    setIsStreaming(!wsStreamingMessage.isComplete);

    if (wsStreamingMessage.isComplete) {
      setTimeout(() => {
        setStreamingMessage(null);
        if (currentConversation) {
          loadMessages(currentConversation.id);
        }
      }, 100);
    }
  }
}, [wsStreamingMessage]);
```

**Change to:**
```typescript
useEffect(() => {
  if (wsStreamingMessage) {
    setStreamingMessage(wsStreamingMessage.content);
    setIsStreaming(!wsStreamingMessage.isComplete);

    if (wsStreamingMessage.isComplete) {
      setTimeout(() => {
        setStreamingMessage(null);
        setToolExecutions([]);        // NEW: Clear tool executions
        setCurrentToolExecution(null); // NEW: Reset current tool
        if (currentConversation) {
          loadMessages(currentConversation.id);
        }
      }, 100);
    }
  }
}, [wsStreamingMessage]);
```

**Rationale:**
- Tool executions are ephemeral UI state (not persisted)
- Clear on message complete to reset for next message
- Matches current pattern for streamingMessage cleanup

### 7.6 Provide Tool State in Context

**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx`

**Location:** Context value object (around line 145)

**Add to value object:**
```typescript
toolExecutions,
currentToolExecution,
```

**Rationale:**
- Makes tool state available to all chat components
- Follows existing pattern for state exposure

---

## Phase 8: Frontend - Tool Execution UI Component

### 8.1 Create ToolExecutionCard Component

**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/ToolExecutionCard.tsx` (NEW FILE)

**Implementation:**
```typescript
// ABOUTME: Component displaying tool execution with name, input, status, and result
// ABOUTME: Shows completed tool calls inline with chat messages for transparency

import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ToolExecution } from "../../contexts/ChatContext";

interface ToolExecutionCardProps {
  execution: ToolExecution;
}

export const ToolExecutionCard: React.FC<ToolExecutionCardProps> = ({ execution }) => {
  return (
    <Card className="my-2 border-l-4 border-l-blue-500 bg-blue-50">
      <CardContent className="p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="font-mono text-xs">
              {execution.toolName}
            </Badge>
            {execution.status === "running" && (
              <Badge variant="secondary" className="text-xs">
                Running...
              </Badge>
            )}
            {execution.status === "completed" && (
              <Badge variant="default" className="text-xs bg-green-600">
                Completed
              </Badge>
            )}
          </div>
        </div>

        {execution.toolResult && (
          <div className="mt-2 text-sm">
            <span className="font-semibold">Result:</span>{" "}
            <span className="font-mono">{execution.toolResult}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
```

**Rationale:**
- Uses Shadcn UI components (Card, Badge) for consistency
- Blue border-l-4 for visual distinction from messages
- Shows tool name, status badge, and result
- Compact design (final result only, no intermediate states per requirements)
- Status badge changes color (secondary → green) when completed

**Shadcn UI Dependencies:**
- Card: Already used in MessageList
- Badge: Check if installed, if not: `npx shadcn-ui@latest add badge`

### 8.2 Integrate ToolExecutionCard in MessageList

**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MessageList.tsx`

**Location:** After displaying user messages, before assistant streaming message

**Context:** MessageList currently renders:
1. Historical messages from API
2. Streaming message (if active)

**Required Change Pattern:**
```typescript
// Import at top
import { ToolExecutionCard } from "./ToolExecutionCard";
import { useChat } from "../../contexts/ChatContext";

// Inside component
const { toolExecutions } = useChat();

// In JSX, after historical messages and before streaming message:
{/* Tool executions during streaming */}
{toolExecutions.length > 0 && (
  <div className="tool-executions">
    {toolExecutions.map((execution) => (
      <ToolExecutionCard key={execution.id} execution={execution} />
    ))}
  </div>
)}
```

**Exact Integration Point:**
Need to examine MessageList.tsx to find the exact location. Likely after mapping over `messages` array and before rendering `streamingMessage`.

**Rationale:**
- Shows tool cards inline during message streaming
- Appears between user message and final AI response
- Each tool execution gets its own card
- Supports multiple tool calls in sequence

---

## Phase 9: Testing - Backend Unit Tests

### 9.1 Create Tool Unit Tests

**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_tools.py` (NEW FILE)

**Implementation:**
```python
"""Unit tests for tool functions."""
import pytest
from app.langgraph.tools.add import add
from app.langgraph.tools.multiply import multiply


class TestAddTool:
    """Tests for add tool."""

    def test_add_positive_numbers(self):
        """Test adding two positive integers."""
        result = add(5, 3)
        assert result == 8

    def test_add_negative_numbers(self):
        """Test adding two negative integers."""
        result = add(-5, -3)
        assert result == -8

    def test_add_mixed_signs(self):
        """Test adding positive and negative."""
        result = add(10, -3)
        assert result == 7

    def test_add_with_zero(self):
        """Test adding with zero."""
        result = add(0, 5)
        assert result == 5


class TestMultiplyTool:
    """Tests for multiply tool."""

    def test_multiply_positive_numbers(self):
        """Test multiplying two positive integers."""
        result = multiply(6, 7)
        assert result == 42

    def test_multiply_with_zero(self):
        """Test multiplying with zero."""
        result = multiply(5, 0)
        assert result == 0

    def test_multiply_negative_numbers(self):
        """Test multiplying two negative integers."""
        result = multiply(-3, -4)
        assert result == 12

    def test_multiply_mixed_signs(self):
        """Test multiplying positive and negative."""
        result = multiply(-5, 3)
        assert result == -15
```

**Rationale:**
- Simple pure function testing
- Edge cases: negatives, zero, mixed signs
- Establishes baseline test coverage

### 9.2 Create Provider bind_tools Tests

**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_provider_bind_tools.py` (NEW FILE)

**Implementation:**
```python
"""Unit tests for bind_tools across all LLM providers."""
import pytest
from unittest.mock import MagicMock, patch
from app.adapters.outbound.llm_providers.openai_provider import OpenAIProvider
from app.adapters.outbound.llm_providers.anthropic_provider import AnthropicProvider
from app.adapters.outbound.llm_providers.gemini_provider import GeminiProvider
from app.adapters.outbound.llm_providers.ollama_provider import OllamaProvider
from app.langgraph.tools.add import add
from app.langgraph.tools.multiply import multiply


@pytest.fixture
def mock_settings_openai():
    """Mock settings for OpenAI provider."""
    with patch("app.adapters.outbound.llm_providers.openai_provider.settings") as mock:
        mock.openai_api_key = "test-key"
        mock.openai_model = "gpt-4"
        yield mock


@pytest.fixture
def mock_settings_anthropic():
    """Mock settings for Anthropic provider."""
    with patch("app.adapters.outbound.llm_providers.anthropic_provider.settings") as mock:
        mock.anthropic_api_key = "test-key"
        mock.anthropic_model = "claude-3-sonnet-20240229"
        yield mock


class TestOpenAIProviderBindTools:
    """Test OpenAI provider tool binding."""

    def test_bind_tools_returns_new_provider(self, mock_settings_openai):
        """Test that bind_tools returns a new provider instance."""
        with patch("app.adapters.outbound.llm_providers.openai_provider.ChatOpenAI"):
            provider = OpenAIProvider()
            bound_provider = provider.bind_tools([add, multiply])

            assert bound_provider is not provider
            assert isinstance(bound_provider, OpenAIProvider)

    def test_bind_tools_calls_underlying_model(self, mock_settings_openai):
        """Test that bind_tools delegates to LangChain model."""
        with patch("app.adapters.outbound.llm_providers.openai_provider.ChatOpenAI") as MockChat:
            mock_model = MagicMock()
            mock_bound_model = MagicMock()
            mock_model.bind_tools.return_value = mock_bound_model
            MockChat.return_value = mock_model

            provider = OpenAIProvider()
            bound_provider = provider.bind_tools([add, multiply], parallel_tool_calls=False)

            mock_model.bind_tools.assert_called_once_with([add, multiply], parallel_tool_calls=False)
            assert bound_provider.model == mock_bound_model


class TestAnthropicProviderBindTools:
    """Test Anthropic provider tool binding."""

    def test_bind_tools_returns_new_provider(self, mock_settings_anthropic):
        """Test that bind_tools returns a new provider instance."""
        with patch("app.adapters.outbound.llm_providers.anthropic_provider.ChatAnthropic"):
            provider = AnthropicProvider()
            bound_provider = provider.bind_tools([add, multiply])

            assert bound_provider is not provider
            assert isinstance(bound_provider, AnthropicProvider)


# Similar tests for Gemini and Ollama providers...
```

**Rationale:**
- Verifies bind_tools() contract across all providers
- Mocks LangChain models to avoid API calls
- Tests return type and delegation pattern
- Validates kwargs are forwarded correctly

### 9.3 Create WebSocket Schema Tests

**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_websocket_schemas.py` (NEW FILE)

**Implementation:**
```python
"""Unit tests for WebSocket message schemas."""
import pytest
from pydantic import ValidationError
from app.adapters.inbound.websocket_schemas import (
    ServerToolStartMessage,
    ServerToolCompleteMessage,
    MessageType,
)


class TestServerToolStartMessage:
    """Tests for ServerToolStartMessage schema."""

    def test_valid_tool_start_message(self):
        """Test creating valid tool start message."""
        msg = ServerToolStartMessage(
            tool_name="add",
            tool_input='{"a": 5, "b": 3}'
        )
        assert msg.type == MessageType.TOOL_START
        assert msg.tool_name == "add"
        assert msg.tool_input == '{"a": 5, "b": 3}'
        assert msg.timestamp is not None

    def test_tool_start_serialization(self):
        """Test that message serializes correctly."""
        msg = ServerToolStartMessage(
            tool_name="multiply",
            tool_input='{"a": 6, "b": 7}'
        )
        dumped = msg.model_dump()
        assert dumped["type"] == "tool_start"
        assert dumped["tool_name"] == "multiply"


class TestServerToolCompleteMessage:
    """Tests for ServerToolCompleteMessage schema."""

    def test_valid_tool_complete_message(self):
        """Test creating valid tool complete message."""
        msg = ServerToolCompleteMessage(
            tool_name="add",
            tool_result="8"
        )
        assert msg.type == MessageType.TOOL_COMPLETE
        assert msg.tool_name == "add"
        assert msg.tool_result == "8"
        assert msg.timestamp is not None
```

**Rationale:**
- Validates Pydantic schema definitions
- Ensures serialization works correctly
- Tests default timestamp generation
- Confirms type literals are enforced

---

## Phase 10: Testing - Backend Integration Tests

### 10.1 Create Graph Tool Execution Test

**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_graph_tool_execution.py` (NEW FILE)

**Implementation:**
```python
"""Integration tests for LangGraph tool execution."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.types import RunnableConfig
from app.langgraph.graphs.streaming_chat_graph import create_streaming_chat_graph
from app.langgraph.tools.add import add
from app.langgraph.tools.multiply import multiply
from app.core.ports.llm_provider import ILLMProvider


class MockLLMProvider(ILLMProvider):
    """Mock LLM provider that returns predefined tool calls."""

    def __init__(self, tool_call_response: AIMessage):
        self.tool_call_response = tool_call_response
        self.model = MagicMock()

    async def generate(self, messages):
        return self.tool_call_response

    async def stream(self, messages):
        yield "test"

    async def get_model_name(self):
        return "mock-model"

    def bind_tools(self, tools, **kwargs):
        # Return self for simplicity in tests
        return self


@pytest.mark.asyncio
async def test_tool_execution_with_add():
    """Test that graph executes add tool and returns result."""
    # Create AIMessage with tool_call
    tool_call_message = AIMessage(
        content="",
        tool_calls=[{
            "name": "add",
            "args": {"a": 5, "b": 3},
            "id": "call_123",
            "type": "tool_call"
        }]
    )

    # Mock checkpointer (no actual persistence needed)
    mock_checkpointer = AsyncMock()

    # Create graph with mock checkpointer
    graph = create_streaming_chat_graph(mock_checkpointer)

    # Mock LLM provider
    mock_provider = MockLLMProvider(tool_call_message)

    # Execute graph
    config = RunnableConfig(
        configurable={
            "thread_id": "test-thread",
            "llm_provider": mock_provider,
            "user_id": "test-user"
        }
    )

    input_data = {
        "messages": [HumanMessage(content="What is 5 + 3?")],
        "conversation_id": "test-conv",
        "user_id": "test-user"
    }

    # Invoke graph and collect events
    events = []
    async for event in graph.astream_events(input_data, config, version="v2"):
        events.append(event)

    # Verify tool execution events exist
    tool_start_events = [e for e in events if e["event"] == "on_tool_start"]
    tool_end_events = [e for e in events if e["event"] == "on_tool_end"]

    assert len(tool_start_events) > 0, "Tool start event should be emitted"
    assert len(tool_end_events) > 0, "Tool end event should be emitted"

    # Verify tool result
    # Note: This is simplified - actual test would check final state
```

**Rationale:**
- Tests full graph execution with tool calling
- Mocks LLM provider to return predictable tool calls
- Verifies tool execution events are emitted
- Validates ToolNode integration

**Note:** This test is complex due to checkpointer mocking. May need adjustment based on actual LangGraph behavior.

---

## Phase 11: Testing - End-to-End Tests

### 11.1 Create WebSocket Tool Flow E2E Test

**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/tests/e2e/test_websocket_tool_flow.py` (NEW FILE)

**Implementation:**
```python
"""End-to-end tests for WebSocket tool execution flow."""
import pytest
import json
from httpx import AsyncClient
from fastapi.testclient import TestClient
from app.main import app


@pytest.mark.asyncio
async def test_tool_execution_via_websocket():
    """
    Test complete flow: user message → tool execution → result streamed to client.

    This test verifies:
    1. User sends message requiring tool
    2. Backend executes tool via ToolNode
    3. TOOL_START message sent to client
    4. TOOL_COMPLETE message sent to client
    5. Final response includes tool result
    """
    # This test requires:
    # - Real WebSocket connection
    # - Mock LLM provider configured to return tool calls
    # - Verification of message sequence

    # Implementation would use websockets library for client-side testing
    # Placeholder for now - requires websocket test client setup
    pass  # TODO: Implement with websocket test client
```

**Rationale:**
- Validates complete user journey
- Tests WebSocket message ordering
- Ensures tool events are emitted correctly
- High-value test but complex setup

**Note:** Requires WebSocket test client infrastructure. Defer to later iteration if time-constrained.

---

## Phase 12: Testing - Frontend Tests

### 12.1 Setup Frontend Testing Infrastructure

**Files to Create:**
- `frontend/vitest.config.ts` (if not exists)
- `frontend/src/setupTests.ts` (test setup file)

**Install Dependencies:**
```bash
cd frontend
npm install --save-dev vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event @vitest/ui jsdom
```

**vitest.config.ts:**
```typescript
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/setupTests.ts',
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

**Rationale:**
- No frontend tests currently exist
- Vitest for fast, modern testing
- Testing Library for React component testing
- jsdom for DOM simulation

### 12.2 Create WebSocket Service Tests

**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/websocketService.test.ts` (NEW FILE)

**Implementation:**
```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { WebSocketService, MessageType } from './websocketService';

describe('WebSocketService', () => {
  let service: WebSocketService;
  let mockWebSocket: any;

  beforeEach(() => {
    // Mock WebSocket
    mockWebSocket = {
      send: vi.fn(),
      close: vi.fn(),
      readyState: WebSocket.OPEN,
    };
    global.WebSocket = vi.fn(() => mockWebSocket) as any;
  });

  it('should handle TOOL_START message', () => {
    const onToolStart = vi.fn();
    service = new WebSocketService({
      url: 'ws://localhost',
      token: 'test-token',
      onToolStart,
    });

    // Simulate receiving TOOL_START message
    const message = {
      type: MessageType.TOOL_START,
      tool_name: 'add',
      tool_input: '{"a": 5, "b": 3}',
      timestamp: new Date().toISOString(),
    };

    mockWebSocket.onmessage({ data: JSON.stringify(message) });

    expect(onToolStart).toHaveBeenCalledWith('add', '{"a": 5, "b": 3}');
  });

  it('should handle TOOL_COMPLETE message', () => {
    const onToolComplete = vi.fn();
    service = new WebSocketService({
      url: 'ws://localhost',
      token: 'test-token',
      onToolComplete,
    });

    const message = {
      type: MessageType.TOOL_COMPLETE,
      tool_name: 'add',
      tool_result: '8',
      timestamp: new Date().toISOString(),
    };

    mockWebSocket.onmessage({ data: JSON.stringify(message) });

    expect(onToolComplete).toHaveBeenCalledWith('add', '8');
  });
});
```

**Rationale:**
- Tests WebSocket message routing for tool events
- Mocks WebSocket API to avoid network calls
- Validates callbacks are invoked correctly

### 12.3 Create ToolExecutionCard Component Tests

**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/ToolExecutionCard.test.tsx` (NEW FILE)

**Implementation:**
```typescript
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ToolExecutionCard } from './ToolExecutionCard';
import type { ToolExecution } from '../../contexts/ChatContext';

describe('ToolExecutionCard', () => {
  it('should render tool name and running status', () => {
    const execution: ToolExecution = {
      id: '1',
      toolName: 'add',
      toolInput: '{"a": 5, "b": 3}',
      status: 'running',
      startTime: new Date().toISOString(),
    };

    render(<ToolExecutionCard execution={execution} />);

    expect(screen.getByText('add')).toBeInTheDocument();
    expect(screen.getByText('Running...')).toBeInTheDocument();
  });

  it('should render tool result when completed', () => {
    const execution: ToolExecution = {
      id: '1',
      toolName: 'multiply',
      toolInput: '{"a": 6, "b": 7}',
      toolResult: '42',
      status: 'completed',
      startTime: new Date().toISOString(),
      endTime: new Date().toISOString(),
    };

    render(<ToolExecutionCard execution={execution} />);

    expect(screen.getByText('multiply')).toBeInTheDocument();
    expect(screen.getByText('Completed')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
  });
});
```

**Rationale:**
- Tests component rendering for different states
- Validates status badge changes
- Ensures tool result displays correctly

---

## Phase 13: Documentation Updates

### 13.1 Update ARCHITECTURE.md

**File:** `/Users/pablolozano/Mac Projects August/genesis/doc/general/ARCHITECTURE.md`

**Section to Add:** "Tool-Calling Architecture"

**Content:**
```markdown
## Tool-Calling Architecture

### Overview
Genesis supports tool-calling through LangGraph's ToolNode, enabling the AI to invoke functions during conversations. Tools are simple Python functions decorated for LangChain compatibility.

### Components

**Tool Definitions** (`backend/app/langgraph/tools/`):
- Simple Python functions with type hints
- Examples: `add(a: int, b: int) -> int`, `multiply(a: int, b: int) -> int`
- Automatically converted to LangChain tool schemas

**LLM Provider Integration**:
- All providers implement `ILLMProvider.bind_tools(tools, **kwargs)`
- Delegation to LangChain's native `model.bind_tools()`
- Returns new provider instance with tools bound

**Graph Structure**:
```
START → process_input → call_llm → tools_condition
                                      ↓ (if tool_calls)
                                    ToolNode → call_llm → END
                                      ↓ (if no tool_calls)
                                     END
```

**WebSocket Event Streaming**:
- `on_chat_model_stream`: LLM tokens
- `on_tool_start`: Tool execution begins
- `on_tool_end`: Tool execution completes
- Frontend receives TOOL_START and TOOL_COMPLETE messages

**State Persistence**:
- ToolMessage objects automatically checkpointed
- Full conversation history includes tool calls and results
- No special handling needed for tool persistence

### Adding New Tools

1. Create tool file in `backend/app/langgraph/tools/`
2. Define function with type hints and docstring
3. Export in `__init__.py`
4. Register in `streaming_chat_graph.py` tools list
5. Register in `call_llm.py` tools list

Example:
```python
# backend/app/langgraph/tools/search.py
def search_web(query: str) -> str:
    """Search the web for information."""
    # Implementation
    return "search results"
```

### Frontend Transparency

Tool executions display as cards inline with messages:
- Tool name badge
- Status indicator (running/completed)
- Result display (final output only)
- Automatic cleanup on message completion
```

**Rationale:**
- Provides high-level overview for developers
- Documents tool addition process
- Explains architecture decisions

### 13.2 Add Docstring to bind_tools Method

**Files:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/openai_provider.py`
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/anthropic_provider.py`
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/gemini_provider.py`
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/ollama_provider.py`

**Current Docstring:**
```python
def bind_tools(self, tools: List[Callable], **kwargs: Any) -> 'ILLMProvider':
    """Bind tools to the provider for tool calling."""
```

**Enhanced Docstring:**
```python
def bind_tools(self, tools: List[Callable], **kwargs: Any) -> 'ILLMProvider':
    """
    Bind tools to the LLM provider for tool calling.

    This method delegates to LangChain's native bind_tools() to add tool schemas
    to the model's API calls. Returns a new provider instance with tools bound,
    following an immutable pattern.

    Args:
        tools: List of callable functions to bind as tools. Each must have type
              hints and a docstring for schema generation.
        **kwargs: Additional arguments passed to LangChain's bind_tools():
                 - parallel_tool_calls (bool): Allow parallel tool execution
                 - tool_choice (str): Force specific tool selection

    Returns:
        New ILLMProvider instance with tools bound to underlying model.

    Example:
        >>> from app.langgraph.tools import add, multiply
        >>> provider = OpenAIProvider()
        >>> provider_with_tools = provider.bind_tools([add, multiply], parallel_tool_calls=False)
        >>> # provider_with_tools.generate() can now invoke tools
    """
```

**Rationale:**
- Documents delegation pattern
- Explains immutability (new instance returned)
- Lists common kwargs
- Provides usage example

---

## Phase 14: Manual Testing Checklist

### 14.1 Backend Testing

**Tool Function Tests:**
```bash
# Run unit tests
cd backend
python -m pytest tests/unit/test_tools.py -v

# Expected: All tests pass
# - test_add_positive_numbers
# - test_add_negative_numbers
# - test_multiply_positive_numbers
# etc.
```

**Provider Binding Tests:**
```bash
python -m pytest tests/unit/test_provider_bind_tools.py -v

# Expected: bind_tools() works for all providers
```

**WebSocket Schema Tests:**
```bash
python -m pytest tests/unit/test_websocket_schemas.py -v

# Expected: TOOL_START and TOOL_COMPLETE schemas validate correctly
```

### 14.2 Integration Testing

**Start Backend:**
```bash
cd backend
docker-compose up -d  # Start MongoDB
python -m pytest tests/integration/test_graph_tool_execution.py -v  # Run integration tests
```

**Expected:**
- Graph executes tools via ToolNode
- Tool events emitted during astream_events()
- ToolMessage persisted in checkpoints

### 14.3 Frontend Testing

**Run Frontend Tests:**
```bash
cd frontend
npm run test

# Expected:
# - WebSocketService handles TOOL_START/TOOL_COMPLETE
# - ToolExecutionCard renders correctly
# - ChatContext manages tool state
```

### 14.4 End-to-End Manual Testing

**Scenario 1: Basic Addition**
1. Start backend: `cd backend && uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Login to application
4. Create new conversation
5. Send message: "What is 25 + 17?"
6. **Verify:**
   - [ ] Streaming tokens appear (LLM reasoning)
   - [ ] Tool execution card appears with "add" badge
   - [ ] Tool card shows "Running..." status
   - [ ] Tool card updates to "Completed" with result "42"
   - [ ] Final AI message incorporates result ("25 + 17 equals 42")

**Scenario 2: Basic Multiplication**
1. Send message: "Multiply 8 by 9"
2. **Verify:**
   - [ ] Tool execution card appears with "multiply" badge
   - [ ] Result displays "72"
   - [ ] AI response uses the result

**Scenario 3: Multiple Tools in Sequence**
1. Send message: "What is (5 + 3) times 2?"
2. **Verify:**
   - [ ] First tool card: "add" with result "8"
   - [ ] Second tool card: "multiply" with result "16"
   - [ ] Both cards display in sequence
   - [ ] Final answer is "16"

**Scenario 4: No Tools Needed**
1. Send message: "Hello, how are you?"
2. **Verify:**
   - [ ] No tool execution cards appear
   - [ ] Normal streaming behavior
   - [ ] Response completes normally

**Scenario 5: Provider Compatibility**

Test with different LLM providers (update .env file):

**OpenAI:**
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview
```
- Send "What is 6 + 7?"
- Verify tool execution works

**Anthropic:**
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-sonnet-20240229
```
- Send "What is 6 + 7?"
- Verify tool execution works

**Gemini:**
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-pro
```
- Send "What is 6 + 7?"
- Verify tool execution works

**Ollama (if available):**
```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama2
OLLAMA_BASE_URL=http://localhost:11434
```
- Send "What is 6 + 7?"
- Verify tool execution works (may not support tool calling depending on model)

### 14.5 Error Handling Tests

**Scenario: Tool with Invalid Arguments (Future)**
- Currently add/multiply are simple and won't error
- Verify error message displayed if tool raises exception
- Verify conversation doesn't crash

**Scenario: WebSocket Disconnection During Tool**
1. Send message requiring tool
2. Disconnect network mid-execution
3. **Verify:**
   - [ ] Frontend shows "Reconnecting..." state
   - [ ] On reconnection, conversation state recovers
   - [ ] Tool execution state is cleared

### 14.6 Checkpointing Tests

**Scenario: Refresh During Tool Execution**
1. Send message "What is 100 + 200?"
2. While tool is executing, refresh browser
3. **Verify:**
   - [ ] Conversation history reloads correctly
   - [ ] Tool execution state clears (tool cards don't persist)
   - [ ] Final message with tool result appears in history

**Scenario: Multiple Tool Calls Per Session**
1. Send "What is 5 + 5?"
2. Wait for completion
3. Send "What is 10 * 2?"
4. **Verify:**
   - [ ] Each message has its own tool execution
   - [ ] Tool cards don't overlap
   - [ ] State clears between messages

---

## Implementation Order & Dependencies

### Critical Path

```
Phase 1 (Tools) → Phase 2 (Backend Protocol) → Phase 3 (Backend Events) → Phase 5 (Frontend Types)
                                                                            ↓
Phase 4 (Graph Updates) ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←Phase 6 (Frontend Service)
                                                                            ↓
                                                                        Phase 7 (Frontend State)
                                                                            ↓
                                                                        Phase 8 (Frontend UI)
                                                                            ↓
                                                                        Phase 14 (Manual Testing)

Phase 9, 10, 11, 12, 13 can run in parallel after Phase 8
```

### Recommended Implementation Sequence

**Day 1: Backend Foundation**
1. Phase 1: Create add tool (15 min)
2. Phase 2: WebSocket protocol (30 min)
3. Phase 3: Event streaming logic (1 hour)
4. Phase 4: Graph tool registration (15 min)
5. Backend manual test (30 min)

**Day 2: Frontend Implementation**
6. Phase 5: TypeScript types (30 min)
7. Phase 6: WebSocket service (30 min)
8. Phase 7: State management (45 min)
9. Phase 8: UI component (1 hour)
10. Frontend manual test (30 min)

**Day 3: Testing & Documentation**
11. Phase 9: Backend unit tests (2 hours)
12. Phase 12: Frontend tests (1.5 hours)
13. Phase 13: Documentation (45 min)
14. Phase 14: Full manual testing (1 hour)

**Optional (Day 4):**
15. Phase 10: Integration tests (2 hours)
16. Phase 11: E2E tests (2 hours)

**Total Estimated Time:** 2-3 days for core implementation + 1 day for comprehensive testing

---

## Risk Mitigation

### Risk 1: LangGraph Event Stream Inconsistency

**Risk:** `astream_events()` may not emit expected tool events in expected order

**Mitigation:**
- Add extensive logging in Phase 3 to observe actual event stream
- Create fallback: if events missing, extract tool info from final state
- Test with multiple providers to identify provider-specific quirks

### Risk 2: Frontend State Desync

**Risk:** Tool state not cleared properly, leading to UI bugs

**Mitigation:**
- Clear tool state in multiple places (message complete, error, disconnect)
- Add defensive checks in ToolExecutionCard (handle missing data gracefully)
- Extensive manual testing of edge cases (refresh, disconnect, rapid messages)

### Risk 3: Tool Execution Timeout

**Risk:** Long-running tools block message streaming

**Mitigation:**
- For POC (add/multiply), not a concern (instant execution)
- For future: Document timeout considerations in ARCHITECTURE.md
- Consider async tool execution pattern for complex tools

### Risk 4: Provider Tool Support Variance

**Risk:** Not all providers support tool calling equally

**Mitigation:**
- Test all four providers manually (Phase 14)
- Document known limitations (e.g., Ollama model-dependent)
- Add provider capability detection (future enhancement)

### Risk 5: Checkpointing Tool Messages

**Risk:** ToolMessage objects may not persist correctly

**Mitigation:**
- Trust LangGraph's MessagesState.add_messages reducer (proven pattern)
- Integration tests verify ToolMessage in checkpoints (Phase 10)
- Manual testing includes refresh scenarios (Phase 14)

---

## Validation Criteria

### Feature Complete When:

**Backend:**
- [ ] `add` tool exists and works
- [ ] `multiply` tool integrated
- [ ] TOOL_START events emit correctly
- [ ] TOOL_COMPLETE events emit correctly
- [ ] Tool metadata (name, result) transmitted accurately
- [ ] All 4 providers support tool binding
- [ ] Checkpoints include ToolMessage objects

**Frontend:**
- [ ] ToolExecutionCard component renders
- [ ] Tool cards display during streaming
- [ ] Tool cards show correct status (running → completed)
- [ ] Tool results display accurately
- [ ] Tool state clears on message completion
- [ ] No visual regressions in existing UI

**Testing:**
- [ ] Unit tests for tools pass
- [ ] Provider bind_tools tests pass
- [ ] WebSocket schema tests pass
- [ ] Frontend component tests pass
- [ ] Manual test scenarios pass for all providers

**Documentation:**
- [ ] ARCHITECTURE.md updated with tool-calling section
- [ ] bind_tools() docstrings enhanced
- [ ] Tool addition process documented

---

## Success Metrics

**Functional:**
- User sends "What is 5 + 3?" → sees tool execution → gets result "8"
- User sends "Multiply 7 by 6" → sees tool execution → gets result "42"
- Tool cards display inline without breaking streaming experience
- Multiple tool calls in sequence work correctly

**Technical:**
- Test coverage: >80% for new code
- No regressions in existing functionality
- All providers tested and working
- Checkpointing verified

**User Experience:**
- Tool execution visible within 100ms of tool start
- Tool result visible within 100ms of tool completion
- No flicker or layout shift
- Clear visual distinction between tool cards and messages

---

## Future Enhancements (Out of Scope)

**Not Included in This Implementation:**

1. **Tool Registry Pattern**: Centralized tool management (currently hardcoded)
2. **Dynamic Tool Loading**: Register tools without code changes
3. **Tool Permissions**: User-level or conversation-level tool access control
4. **Tool Streaming**: Stream tool execution progress (currently only start/complete)
5. **Tool Cancellation**: Ability to cancel long-running tools
6. **Tool Error Recovery**: Retry logic for failed tools
7. **Complex Tools**: API calls, database queries, file operations
8. **Tool Analytics**: Track tool usage, success rates, performance
9. **Frontend Tool Input Display**: Show parsed tool arguments in UI
10. **Tool History**: Persistent record of all tool executions

**Rationale:** Keep POC focused on validating architecture. These enhancements can build on proven foundation.

---

## Conclusion

This plan provides a comprehensive, step-by-step implementation guide for adding tool-calling support to Genesis. The architecture leverages existing infrastructure (bind_tools(), ToolNode, MessagesState) while adding minimal new code for WebSocket event streaming and UI transparency.

**Key Strengths:**
- Builds on proven LangGraph patterns
- Maintains hexagonal architecture boundaries
- Backward compatible WebSocket protocol
- Comprehensive testing strategy
- Clear validation criteria

**Next Steps:**
1. Review this plan with Pablo for approval
2. Begin Phase 1 (Backend tool definitions)
3. Iterate through phases sequentially
4. Validate at each checkpoint
5. Complete manual testing before declaring feature complete

Total implementation time: **2-3 days** for experienced developer familiar with codebase.
