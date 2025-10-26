# Testing Coverage Analysis: Tool-Calling Implementation

## Request Summary

Implement tool-calling support for Genesis using LangGraph's ToolNode and bind_tools() across all LLM providers (OpenAI, Anthropic, Gemini, Ollama). The feature includes:

1. **Tools**: Simple multiply() and add() tools for demonstration
2. **Provider Integration**: bind_tools() method on all provider implementations
3. **Graph Structure**: LangGraph with ToolNode to handle tool execution
4. **WebSocket Flow**: Tool events emitted to frontend with TOOL_START/TOOL_COMPLETE messages
5. **Frontend UI**: Transparent tool cards displaying tool calls and results
6. **Checkpointing**: Tool messages automatically persisted in LangGraph checkpoints

This analysis identifies all test files, gaps in coverage, and recommendations for comprehensive testing across unit, integration, and end-to-end layers.

---

## Relevant Files & Modules

### Test Files (Backend - Backend Tests)

- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/conftest.py` - Pytest configuration and shared fixtures for database, app, and client setup. Provides reusable fixtures for testing.
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_llm_providers.py` - Unit tests for LLM provider factory testing. Tests provider creation for OpenAI, Anthropic, Gemini, Ollama, and error cases.
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_use_cases.py` - Unit tests for use cases with mocked dependencies. Tests RegisterUser and AuthenticateUser business logic in isolation.
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_domain_models.py` - Tests for domain model validation.
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_dual_database.py` - Tests for dual database pattern.
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_auth_api.py` - Integration tests for authentication endpoints.
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_conversation_api.py` - Integration tests for conversation API endpoints (CRUD operations with authorization).

### Backend Implementation Files

#### Tool Definitions
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/__init__.py` - Tool module initialization.
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/multiply.py` - Simple multiply tool (multiply(a: int, b: int) -> int). Requires add() tool addition.

#### LLM Provider Port & Implementations
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - ILLMProvider interface defining generate(), stream(), get_model_name(), and bind_tools() methods.
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/openai_provider.py` - OpenAI provider implementation with bind_tools() support.
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/anthropic_provider.py` - Anthropic provider implementation with bind_tools() support.
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/gemini_provider.py` - Google Gemini provider implementation with bind_tools() support.
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/ollama_provider.py` - Ollama local model provider implementation with bind_tools() support.
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/provider_factory.py` - Factory for creating provider instances based on configuration.

#### LangGraph Graph & Nodes
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - ConversationState extending MessagesState with conversation_id and user_id fields.
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Main graph with process_input -> call_llm -> tools (conditional) -> call_llm -> END flow. Uses ToolNode(tools) for tool execution.
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - Node that retrieves LLM provider from config, binds tools, and calls generate(). Returns AIMessage with potential tool_calls.
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/process_input.py` - Validates messages exist in state before LLM invocation.

#### WebSocket & Communication
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket handler for chat. Uses graph.astream_events() for token streaming. Creates HumanMessage directly and invokes graph with RunnableConfig containing llm_provider and thread_id.
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py` - WebSocket message protocol (MessageType enum with MESSAGE, TOKEN, COMPLETE, ERROR, PING, PONG). Currently missing TOOL_START and TOOL_COMPLETE message types.
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/langgraph_checkpointer.py` - AsyncMongoDBSaver integration for automatic message persistence.

#### Infrastructure
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py` - Configuration settings including LLM provider selection and API keys.

### Frontend Implementation Files

#### Services
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/websocketService.ts` - WebSocketService handling connection, message sending, and message type routing (TOKEN, COMPLETE, ERROR, PONG). Missing TOOL_START and TOOL_COMPLETE handling.
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/conversationService.ts` - HTTP service for conversation CRUD operations.
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/authService.ts` - Authentication token management.

#### Hooks
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/hooks/useWebSocket.ts` - React hook managing WebSocket state, message sending, and streaming message state. Uses StreamingMessage interface with content and isComplete flag.

#### Context & Components
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx` - Chat context providing conversations, messages, streamingMessage, and control functions. Integrates with useWebSocket hook.
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/pages/Chat.tsx` - Main chat page component.
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MessageList.tsx` - Component rendering message history and current streaming response.
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MessageInput.tsx` - Component for user input submission.
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/ConversationSidebar.tsx` - Conversation list sidebar.

### No Frontend Test Files
**Note**: No `__tests__`, `*.test.ts`, `*.test.tsx`, `*.spec.ts`, or `*.spec.tsx` files exist in the frontend directory. Frontend testing infrastructure does not yet exist.

---

## Current Testing Overview

### Unit Tests (Backend)

**LLM Provider Factory** (`test_llm_providers.py`):
- Tests provider creation for OpenAI, Anthropic, Gemini, Ollama
- Tests unsupported provider error
- Uses @patch to mock settings

**Status**: Minimal coverage - factory only, does not test:
- bind_tools() method on any provider
- Tool binding result validation
- Tool call execution

**Use Cases** (`test_use_cases.py`):
- RegisterUser: Happy path, duplicate email, duplicate username
- AuthenticateUser: Success, invalid username, invalid password, inactive user
- Uses AsyncMock for repositories

**Status**: Use case tests are comprehensive but unrelated to tool-calling feature.

### Integration Tests (Backend)

**Conversation API** (`test_conversation_api.py`):
- CRUD operations (create, list, get, delete, update)
- Authorization checks (user isolation)
- Validation (title length limits)
- Helper method for user creation and login flow

**Status**: API endpoint testing is comprehensive but does not test:
- WebSocket chat with tool calls
- Tool execution flow
- Tool message persistence

**Missing**: No integration tests for WebSocket chat, graph execution, or tool execution.

### End-to-End Tests (Backend)

**Status**: No e2e tests exist.

### Test Utilities & Fixtures

**conftest.py**:
- `app`: FastAPI application fixture
- `client`: AsyncClient for HTTP testing
- Mock repositories (user, conversation, message)
- Mock LLM provider with stream() generator
- Sample domain objects (User, UserCreate, Conversation)
- AuthService instance

**Status**: Fixtures provide basic mocking but are insufficient for tool-calling tests. Missing:
- Actual LLM provider instances with tools bound
- Tool call response mocking (AIMessage with tool_calls)
- Graph execution fixtures
- WebSocket test utilities

### Frontend Tests

**Status**: No frontend tests exist.

---

## Coverage Analysis

### Tools (multiply.py, add.py - needs creation)

**Current Coverage**:
- multiply.py exists as simple function returning a * b
- No tests exist for tool functions

**Gaps**:
- No unit tests for multiply() - input validation, boundary cases (negative numbers, zero, large numbers)
- No add() tool - needs to be created with same test requirements
- No tests for tool function signatures expected by LangGraph

### LLM Provider bind_tools() Method

**Current Coverage**:
- Method exists on all 4 providers (OpenAI, Anthropic, Gemini, Ollama)
- Implementation creates new provider instance with bound model
- No tests validate the binding

**Gaps**:
- No tests verify bind_tools() returns provider with callable interface
- No tests verify tools are correctly passed to LangChain bind_tools()
- No tests verify bound model can generate tool_calls in AIMessage
- No tests verify each provider's bind_tools() works identically
- No tests for parallel_tool_calls parameter behavior
- No integration tests between bind_tools() and generate()

### Graph Execution with Tools

**Current Coverage**:
- streaming_chat_graph.py includes ToolNode(tools) in graph
- call_llm node binds tools and calls generate()
- No tests validate the full flow

**Gaps**:
- No tests verify ToolNode receives tool_calls from AIMessage
- No tests verify ToolNode executes tools and returns ToolMessage
- No tests verify tools_condition routes correctly (tool_calls -> tools node, no tool_calls -> END)
- No tests verify message accumulation in ConversationState
- No tests for loop handling (multiple tool calls before final response)
- No tests for tool execution errors
- No checkpointer tests verifying tool messages persisted

### WebSocket -> Graph Integration

**Current Coverage**:
- websocket_handler.py invokes graph.astream_events()
- Graph is called with RunnableConfig including llm_provider
- astream_events filters for on_chat_model_stream events
- No tests exist

**Gaps**:
- No tests for full WebSocket message flow (ClientMessage -> graph.astream_events() -> ServerTokenMessage)
- No tests for authorization verification before graph execution
- No tests for error handling in graph execution
- No tests for tool event streaming (should include TOOL_START, TOOL_COMPLETE events)
- No tests for checkpointing integration
- No tests for concurrent WebSocket connections

### WebSocket Message Protocol

**Current Coverage**:
- websocket_schemas.py defines message types: MESSAGE, TOKEN, COMPLETE, ERROR, PING, PONG
- ClientMessage, ServerTokenMessage, ServerCompleteMessage, ServerErrorMessage defined
- No tests for message validation or serialization

**Gaps**:
- Missing TOOL_START message type for transparent UI
- Missing TOOL_COMPLETE message type for transparent UI
- No tests validate message schema serialization/deserialization
- No tests for unknown message type handling
- No tests for invalid JSON handling

### Frontend WebSocket Service

**Current Coverage**:
- WebSocketService.handleMessage() routes TOKEN, COMPLETE, ERROR, PONG
- onToken, onComplete, onError callbacks provided
- Connection lifecycle (connect, disconnect, reconnect)
- Ping interval for keep-alive
- No tests exist

**Gaps**:
- No tests for TOOL_START/TOOL_COMPLETE handling (not yet implemented)
- No tests for message parsing
- No tests for callback invocation
- No tests for reconnection logic
- No tests for connection error handling

### Frontend React Hook

**Current Coverage**:
- useWebSocket hook manages WebSocket state and callbacks
- Provides isConnected, error, sendMessage, streamingMessage state
- Auto-connect and disconnect lifecycle
- No tests exist

**Gaps**:
- No tests for hook state management
- No tests for sendMessage behavior
- No tests for streaming message accumulation
- No tests for error state handling
- No tests for connection state tracking

### Frontend Chat Context

**Current Coverage**:
- ChatContext provides conversations, messages, streamingMessage, isStreaming state
- Integrates with useWebSocket hook
- No tests exist

**Gaps**:
- No tests for state updates from WebSocket events
- No tests for conversation loading
- No tests for message list refresh on stream complete
- No tests for tool message handling in streamingMessage
- No tests for error state propagation

### Frontend UI Components

**Current Coverage**:
- MessageList displays messages and streamingMessage
- Components consume ChatContext
- No component tests exist

**Gaps**:
- No tests for rendering streaming content
- No tests for tool card rendering (not yet implemented)
- No tests for message type differentiation
- No tests for error message display

---

## Testing Recommendations

### Proposed Unit Tests

#### Tools Unit Tests

**New file**: `backend/tests/unit/test_tools.py`

```
Test Cases Needed:
1. test_multiply_positive_integers() - multiply(3, 4) == 12
2. test_multiply_negative_numbers() - multiply(-2, 5) == -10
3. test_multiply_zero() - multiply(0, 5) == 0
4. test_multiply_large_numbers() - multiply(1000000, 1000000)
5. test_add_positive_integers() - add(5, 3) == 8
6. test_add_negative_numbers() - add(-5, -3) == -8
7. test_add_mixed_numbers() - add(-5, 3) == -2
8. test_add_zero() - add(0, 0) == 0
9. test_add_large_numbers() - add(10**9, 10**9)
10. test_tool_signatures() - Verify tools have correct docstrings and type hints
```

**File Location**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_tools.py`

**Rationale**: Tools are pure functions that should be tested in isolation. These tests verify correctness and ensure tools follow LangGraph tool expectations.

#### LLM Provider bind_tools() Tests

**New file**: `backend/tests/unit/test_provider_bind_tools.py`

```
Test Cases Needed:
1. test_openai_bind_tools_returns_provider()
   - Mock ChatOpenAI.bind_tools()
   - Verify returns OpenAIProvider instance
   - Verify provider has model attribute

2. test_anthropic_bind_tools_returns_provider()
   - Mock ChatAnthropic.bind_tools()
   - Verify returns AnthropicProvider instance

3. test_gemini_bind_tools_returns_provider()
   - Mock ChatGoogleGenerativeAI.bind_tools()
   - Verify returns GeminiProvider instance

4. test_ollama_bind_tools_returns_provider()
   - Mock ChatOllama.bind_tools()
   - Verify returns OllamaProvider instance

5. test_bind_tools_passes_tools_list()
   - Mock all providers
   - Verify tools list passed to bind_tools()
   - Verify parallel_tool_calls parameter passed

6. test_bind_tools_additional_kwargs()
   - Verify kwargs like parallel_tool_calls=False passed correctly

7. test_bound_provider_still_has_methods()
   - Verify bound provider has generate() and stream() methods
   - Verify model attribute is set (for binding validation)

8. test_bind_tools_with_empty_list()
   - Verify bind_tools([]) works (edge case)

9. test_bind_tools_called_multiple_times()
   - Verify can call bind_tools() on already bound provider
   - Verify new binding overwrites old binding
```

**File Location**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_provider_bind_tools.py`

**Rationale**: bind_tools() is critical infrastructure. Tests verify each provider implements it correctly and returns a callable provider instance.

#### LLM Provider generate() with Tool Calls

**Add to existing**: `backend/tests/unit/test_llm_providers.py`

```
Test Cases Needed:
1. test_openai_generate_with_tool_calls()
   - Mock ChatOpenAI to return AIMessage with tool_calls
   - Call generate(messages)
   - Verify AIMessage returned with tool_calls attribute

2. test_anthropic_generate_with_tool_calls()
   - Mock ChatAnthropic to return AIMessage with tool_calls
   - Verify tool_calls in response

3. test_gemini_generate_with_tool_calls()
   - Mock ChatGoogleGenerativeAI to return AIMessage with tool_calls
   - Verify tool_calls in response

4. test_ollama_generate_with_tool_calls()
   - Mock ChatOllama to return AIMessage with tool_calls
   - Verify tool_calls in response

5. test_generate_without_tool_calls()
   - Verify AIMessage returned without tool_calls when model doesn't call tools
```

**Rationale**: Tests verify providers correctly handle tool_calls in LLM responses.

### Proposed Integration Tests

#### Tool Execution Integration Tests

**New file**: `backend/tests/integration/test_graph_tools.py`

```
Test Cases Needed:
1. test_toolnode_receives_tool_calls()
   - Create mock AIMessage with tool_calls for multiply(3, 4)
   - Invoke ToolNode with this message
   - Verify ToolNode calls multiply function
   - Verify ToolMessage returned with result=12

2. test_toolnode_executes_add()
   - Create mock AIMessage with tool_calls for add(5, 3)
   - Invoke ToolNode
   - Verify add executed correctly
   - Verify ToolMessage returned

3. test_toolnode_multiple_tool_calls()
   - Create AIMessage with multiple tool_calls
   - Verify ToolNode executes all tools
   - Verify ToolMessage list includes all results

4. test_toolnode_tool_execution_error()
   - Create AIMessage with invalid tool call (wrong args)
   - Invoke ToolNode
   - Verify error handling (ToolMessage with error info)

5. test_tools_condition_routes_to_tools()
   - Create AIMessage with tool_calls
   - Call tools_condition()
   - Verify returns "tools" route

6. test_tools_condition_routes_to_end()
   - Create AIMessage without tool_calls
   - Call tools_condition()
   - Verify returns "end" route (or END constant)

7. test_graph_full_tool_loop()
   - Mock LLM to return multiply tool call (3, 4)
   - Invoke full graph
   - Verify:
     - process_input node executes
     - call_llm invokes LLM with bound tools
     - tools node executes multiply
     - call_llm invoked again with tool result
     - Final response includes all messages including ToolMessage
```

**File Location**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_graph_tools.py`

**Rationale**: Integration tests verify tools work correctly within LangGraph flow, including conditional routing and message accumulation.

#### Provider bind_tools() Integration Tests

**New file**: `backend/tests/integration/test_provider_tools_integration.py`

```
Test Cases Needed:
1. test_openai_provider_bind_and_generate()
   - Create real OpenAIProvider (or mock API)
   - Bind tools
   - Mock the LLM to return tool_calls
   - Call generate()
   - Verify AIMessage with tool_calls returned

2. test_anthropic_provider_bind_and_generate()
   - Create AnthropicProvider with tools
   - Verify tool binding integrates with generate()

3. test_gemini_provider_bind_and_generate()
   - Create GeminiProvider with tools
   - Verify tool binding integrates with generate()

4. test_ollama_provider_bind_and_generate()
   - Create OllamaProvider with tools
   - Verify tool binding integrates with generate()

5. test_provider_tool_serialization()
   - Verify tools correctly serialized for LLM API
   - Verify schema includes tool name, description, parameters

6. test_tool_parameter_validation()
   - Tools should have correct parameter names (a, b for multiply/add)
   - Tools should have correct type hints
   - LLM should be able to generate valid tool calls
```

**File Location**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_provider_tools_integration.py`

**Rationale**: Verify real provider implementations work correctly with tool binding and generation, catching serialization or API-specific issues.

#### WebSocket -> Graph -> Tools Integration

**New file**: `backend/tests/integration/test_websocket_tools_flow.py`

```
Test Cases Needed:
1. test_websocket_receives_tool_event()
   - Start WebSocket handler
   - Mock graph to return TOOL_START event
   - Receive WebSocket server event
   - Verify ServerTokenMessage or TOOL_START sent to client

2. test_websocket_tool_complete_event()
   - Mock graph to emit on_tool_end event
   - Verify TOOL_COMPLETE sent to client

3. test_websocket_full_tool_execution_flow()
   - Mock client sends message "multiply 3 by 4"
   - Mock LLM to return multiply tool call
   - Mock graph execution returns:
     - HumanMessage (user input)
     - AIMessage with tool_calls
     - ToolMessage with result
     - AIMessage with final response
   - Verify WebSocket sends:
     - TOKEN events with streaming response
     - Possibly TOOL_START and TOOL_COMPLETE events

4. test_websocket_authorization_before_tool_execution()
   - Mock unauthorized user accessing conversation
   - Verify ERROR message sent
   - Verify graph.astream_events() not called

5. test_websocket_tool_execution_error_handling()
   - Mock graph to raise exception during tool execution
   - Verify ERROR message sent to client

6. test_websocket_multiple_concurrent_tool_executions()
   - Create two WebSocket connections
   - Send messages to both simultaneously
   - Verify each receives correct responses
   - Verify no cross-contamination

7. test_checkpointer_persists_tool_messages()
   - Execute graph with tool call
   - Verify checkpoint includes:
     - HumanMessage
     - AIMessage with tool_calls
     - ToolMessage
     - Final AIMessage
```

**File Location**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_websocket_tools_flow.py`

**Rationale**: Comprehensive integration tests verify the full flow from WebSocket client to tool execution to persisted state. These tests catch end-to-end issues.

#### WebSocket Message Protocol Tests

**New file**: `backend/tests/integration/test_websocket_schemas.py`

```
Test Cases Needed:
1. test_client_message_validation()
   - Valid message: {type: "message", conversation_id: "...", content: "..."}
   - Invalid message: missing fields
   - Invalid message: wrong type
   - Verify validation errors raised

2. test_server_token_message_serialization()
   - Create ServerTokenMessage(content="test")
   - Serialize to JSON
   - Verify JSON valid and contains content field

3. test_server_complete_message_serialization()
   - Create ServerCompleteMessage(message_id="...", conversation_id="...")
   - Serialize to JSON
   - Verify both fields present

4. test_server_error_message_serialization()
   - Create ServerErrorMessage(message="...", code="...")
   - Serialize to JSON
   - Verify message and code fields

5. test_tool_start_message_schema()
   - Define ServerToolStartMessage schema
   - Verify includes: type="tool_start", tool_name, tool_input
   - Test serialization

6. test_tool_complete_message_schema()
   - Define ServerToolCompleteMessage schema
   - Verify includes: type="tool_complete", tool_name, tool_result, execution_time
   - Test serialization

7. test_message_roundtrip()
   - Create message -> serialize -> deserialize -> verify equal

8. test_unknown_message_type_handling()
   - Send message with unknown type
   - Verify graceful handling (no crash, error logged)

9. test_ping_pong_messages()
   - Send PING message
   - Verify PONG response
```

**File Location**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_websocket_schemas.py`

**Rationale**: Tests verify WebSocket message protocol correctness, especially new TOOL_START and TOOL_COMPLETE messages for transparent UI.

### Proposed End-to-End Tests

#### WebSocket Chat with Tool Execution E2E

**New file**: `backend/tests/e2e/test_chat_with_tools.py`

```
Test Cases Needed:
1. test_user_asks_for_calculation_e2e()
   - Register user and authenticate
   - Create conversation
   - Open WebSocket connection
   - Send message: "Calculate 3 * 4"
   - Verify flow:
     - UserMessage in WebSocket
     - Tool execution (multiply)
     - Final response with calculation
     - All messages persisted in LangGraph checkpoint

2. test_tool_execution_with_streaming_e2e()
   - Send message requesting multiple calculations
   - Verify:
     - Multiple TOKEN events from streaming response
     - Tool execution and results visible
     - Complete message sent at end

3. test_tool_error_handling_e2e()
   - Mock tool execution error
   - Verify error message displayed to client
   - Verify conversation not corrupted

4. test_conversation_history_with_tool_calls_e2e()
   - Execute conversation with tool calls
   - Load conversation messages
   - Verify all messages including ToolMessages present
   - Verify correct order and content

5. test_multiple_tool_calls_in_one_response_e2e()
   - LLM calls multiply and add in one response
   - Verify both tools executed
   - Verify results visible to client

6. test_tool_output_used_in_followup_e2e()
   - First message: "Calculate 3 * 4"
   - Second message: "Now add 5 to the result"
   - Verify LLM can see tool result from first message
   - Verify final answer correct (3*4+5 = 17)
```

**File Location**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/e2e/test_chat_with_tools.py`

**Note**: E2E tests may need to mock LLM responses since real API calls are expensive/slow. Use response fixtures.

**Rationale**: E2E tests verify the complete user-facing flow, ensuring tools work end-to-end for users.

#### Provider-Specific E2E Tests

**New file**: `backend/tests/e2e/test_tools_all_providers.py`

```
Test Cases Needed (parameterized for all 4 providers):
1. test_provider_can_call_tools[openai]()
2. test_provider_can_call_tools[anthropic]()
3. test_provider_can_call_tools[gemini]()
4. test_provider_can_call_tools[ollama]()

Each test:
- Set LLM_PROVIDER environment variable
- Initialize provider
- Create conversation
- Send message requesting calculation
- Verify tool called and result correct
```

**File Location**: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/e2e/test_tools_all_providers.py`

**Rationale**: Ensures tool calling works consistently across all provider implementations.

### Proposed Frontend Tests

#### Frontend Tests Setup

**Prerequisites**:
1. Add testing libraries to `frontend/package.json`:
   - `vitest` (modern test runner)
   - `@vitest/ui` (test UI)
   - `@testing-library/react` (component testing)
   - `@testing-library/user-event` (user interaction simulation)
   - `@testing-library/jest-dom` (DOM assertions)
   - `msw` (API mocking)
   - `vi` (vitest mock utilities)

2. Create `frontend/vitest.config.ts`

3. Create `frontend/test/setup.ts` for global mocks

#### WebSocket Service Tests

**New file**: `frontend/src/services/__tests__/websocketService.test.ts`

```
Test Cases Needed:
1. test_websocket_connects_successfully()
   - Mock WebSocket constructor
   - Create WebSocketService
   - Call connect()
   - Verify onConnect callback called
   - Verify ping interval started

2. test_websocket_handles_token_message()
   - Mock WebSocket
   - Call handleMessage with TOKEN message JSON
   - Verify onToken callback called with content

3. test_websocket_handles_complete_message()
   - Mock WebSocket
   - Call handleMessage with COMPLETE message JSON
   - Verify onComplete callback called with message_id and conversation_id

4. test_websocket_handles_error_message()
   - Mock WebSocket
   - Call handleMessage with ERROR message JSON
   - Verify onError callback called with message and code

5. test_websocket_handles_tool_start_message()
   - Call handleMessage with TOOL_START message
   - Verify onToolStart callback called (needs to be added)
   - Verify tool_name and tool_input extracted

6. test_websocket_handles_tool_complete_message()
   - Call handleMessage with TOOL_COMPLETE message
   - Verify onToolComplete callback called (needs to be added)
   - Verify tool_result and execution_time available

7. test_websocket_sends_message()
   - Mock WebSocket
   - Call sendMessage("conv-id", "content")
   - Verify JSON message with correct structure sent

8. test_websocket_reconnect_logic()
   - Mock WebSocket to disconnect
   - Verify reconnectAttempts incremented
   - Verify exponential backoff delay calculated
   - Verify reconnects up to maxReconnectAttempts

9. test_websocket_manual_disconnect()
   - Connect then call disconnect()
   - Verify isManualClose flag prevents reconnect
   - Verify ws set to null

10. test_websocket_ping_keep_alive()
    - Mock WebSocket
    - Verify ping interval started on connect
    - Verify ping message sent periodically (every 30s)

11. test_websocket_invalid_json_handling()
    - Send invalid JSON
    - Verify error logged
    - Verify onError not called (graceful degradation)

12. test_websocket_unknown_message_type()
    - Send message with unknown type
    - Verify console.warn logged
    - Verify no callbacks invoked
```

**File Location**: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/__tests__/websocketService.test.ts`

**Rationale**: Comprehensive WebSocket service tests verify connection, message handling, reconnection, and tool event routing.

#### useWebSocket Hook Tests

**New file**: `frontend/src/hooks/__tests__/useWebSocket.test.ts`

```
Test Cases Needed:
1. test_usewwebsocket_initializes_connected_false()
   - Render hook
   - Verify isConnected = false initially

2. test_usewwebsocket_auto_connects()
   - Render hook with autoConnect=true
   - Verify connect() called automatically

3. test_usewwebsocket_does_not_auto_connect()
   - Render hook with autoConnect=false
   - Verify connect() not called
   - Call connect() manually
   - Verify isConnected = true

4. test_usewwebsocket_send_message()
   - Render hook and connect
   - Call sendMessage("conv-id", "test")
   - Verify streamingMessage initialized with isComplete=false

5. test_usewwebsocket_accumulates_streaming_message()
   - Send message
   - Mock onToken callbacks with "Hello ", "world"
   - Verify streamingMessage.content = "Hello world"

6. test_usewwebsocket_marks_complete()
   - Send message
   - Mock onComplete callback
   - Verify streamingMessage.isComplete = true
   - After timeout, streamingMessage = null

7. test_usewwebsocket_handles_error()
   - Mock onError callback
   - Verify error state set
   - Verify streamingMessage cleared

8. test_usewwebsocket_disconnect_cleanup()
   - Render hook, connect, unmount
   - Verify disconnect called
   - Verify state cleaned up

9. test_usewwebsocket_connection_status_updates()
   - Render hook
   - Call connect()
   - Verify isConnected updates
   - Call disconnect()
   - Verify isConnected = false

10. test_usewwebsocket_handles_tool_start_event()
    - Mock onToolStart callback (needs to be added to hook)
    - Verify tool event creates tool_message state (new feature)

11. test_usewwebsocket_handles_tool_complete_event()
    - Mock onToolComplete callback (needs to be added to hook)
    - Verify tool complete updates tool_message state

12. test_usewwebsocket_multiple_sends_create_separate_messages()
    - Send message A
    - Complete message A
    - Send message B
    - Verify messages tracked separately in state history
```

**File Location**: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/hooks/__tests__/useWebSocket.test.ts`

**Rationale**: Tests verify hook manages WebSocket connection lifecycle, message streaming, and tool events.

#### ChatContext Tests

**New file**: `frontend/src/contexts/__tests__/ChatContext.test.tsx`

```
Test Cases Needed:
1. test_chatcontext_initializes_empty()
   - Render ChatProvider
   - Verify conversations = []
   - Verify messages = []
   - Verify streamingMessage = null

2. test_chatcontext_send_message()
   - Create conversation
   - Call sendMessage("test content")
   - Verify message added to messages with role="user"
   - Verify isStreaming = true

3. test_chatcontext_streaming_message_updates()
   - Send message
   - Mock WebSocket to emit token events
   - Verify streamingMessage accumulates content
   - Verify isStreaming = true

4. test_chatcontext_streaming_complete()
   - Send message, stream response, complete
   - Verify streamingMessage.isComplete = true
   - After timeout, streamingMessage = null
   - Verify isStreaming = false
   - Verify messages reloaded with AI response

5. test_chatcontext_create_conversation()
   - Call createConversation()
   - Verify new conversation added to conversations
   - Verify currentConversation set to new conversation
   - Verify HTTP POST called

6. test_chatcontext_select_conversation()
   - Create conversation A and B
   - Select conversation A
   - Verify currentConversation = A
   - Verify messages loaded for A

7. test_chatcontext_delete_conversation()
   - Create conversation
   - Delete conversation
   - Verify removed from conversations list
   - If current, currentConversation = null

8. test_chatcontext_update_conversation_title()
   - Create conversation with "New Chat"
   - Call updateConversationTitle("New Title")
   - Verify conversations list updated
   - Verify currentConversation updated

9. test_chatcontext_load_conversations()
   - Mock HTTP to return 3 conversations
   - Call loadConversations()
   - Verify conversations state updated

10. test_chatcontext_auto_name_first_message()
    - Create conversation
    - Send message "Write a poem"
    - Verify updateConversationTitle called with generated title
    - Verify title contains "poem" or similar

11. test_chatcontext_handles_websocket_error()
    - Send message
    - Mock WebSocket error
    - Verify error state set
    - Verify error cleared on next successful send

12. test_chatcontext_tool_messages_in_history()
    - (New feature) Send message with tool call
    - Verify tool message displayed in messages
    - Verify includes tool_name, tool_input, tool_result

13. test_chatcontext_tool_streaming()
    - (New feature) Send message
    - Mock tool events: TOOL_START, TOOL_COMPLETE
    - Verify streamingMessage includes tool execution info
```

**File Location**: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/__tests__/ChatContext.test.tsx`

**Note**: These tests need to mock conversationService HTTP calls and WebSocket events.

**Rationale**: Tests verify context state management, conversation lifecycle, and tool message handling.

#### MessageList Component Tests

**New file**: `frontend/src/components/chat/__tests__/MessageList.test.tsx`

```
Test Cases Needed:
1. test_messagelist_renders_messages()
   - Render MessageList with 3 messages
   - Verify all messages rendered

2. test_messagelist_renders_user_message()
   - Render message with role="user"
   - Verify correct styling/alignment
   - Verify content displayed

3. test_messagelist_renders_ai_message()
   - Render message with role="assistant"
   - Verify correct styling/alignment
   - Verify content displayed

4. test_messagelist_renders_streaming_message()
   - Render with streamingMessage prop
   - Verify displays in progress state
   - Verify content accumulates

5. test_messagelist_renders_tool_message()
   - (New feature) Render message with type="tool"
   - Verify includes tool_name
   - Verify includes tool_input
   - Verify includes tool_result
   - Verify styled differently from user/assistant messages

6. test_messagelist_renders_tool_card()
   - (New feature) Render message with tool call
   - Verify tool card rendered with:
     - Tool name
     - Input parameters
     - Execution status (running/complete)
     - Result (if complete)

7. test_messagelist_empty_state()
   - Render MessageList with empty messages
   - Verify appropriate empty message shown

8. test_messagelist_scrolls_to_bottom_on_new_message()
   - Render MessageList
   - Add new message
   - Verify container scrolled to bottom

9. test_messagelist_markdown_rendering()
   - Render message with markdown content
   - Verify markdown rendered correctly

10. test_messagelist_code_block_rendering()
    - Render message with code block
    - Verify syntax highlighting (if using highlight library)

11. test_messagelist_tool_execution_timeline()
    - (New feature) Render multiple tool calls in one response
    - Verify displays in correct order:
      - User message
      - Tool call 1 start
      - Tool call 1 result
      - Tool call 2 start
      - Tool call 2 result
      - Final AI response
```

**File Location**: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/__tests__/MessageList.test.tsx`

**Rationale**: Component tests verify correct rendering of tool cards and transparent tool execution display.

#### New Tool Card Component Tests

**New file**: `frontend/src/components/chat/__tests__/ToolCard.test.tsx`

```
Test Cases Needed (new component):
1. test_toolcard_displays_tool_name()
   - Render ToolCard with tool_name="multiply"
   - Verify name displayed

2. test_toolcard_displays_input_parameters()
   - Render ToolCard with tool_input={a: 3, b: 4}
   - Verify displays "3 × 4" or similar

3. test_toolcard_displays_status_running()
   - Render with status="running"
   - Verify spinner/loading indicator shown

4. test_toolcard_displays_status_complete()
   - Render with status="complete"
   - Verify result displayed
   - Verify checkmark icon

5. test_toolcard_displays_execution_time()
   - Render with execution_time=250
   - Verify displays "250ms" or similar

6. test_toolcard_displays_error()
   - Render with status="error" and error_message
   - Verify error displayed in red/warning color

7. test_toolcard_expand_collapse()
   - Render ToolCard
   - Click expand button
   - Verify detailed view shown
   - Verify can collapse back

8. test_toolcard_copy_result()
   - Render with result=42
   - Click copy button
   - Verify result copied to clipboard

9. test_toolcard_styling()
   - Verify card has appropriate border/shadow
   - Verify color-coded by status (running: blue, complete: green, error: red)
   - Verify responsive on mobile
```

**File Location**: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/ToolCard.tsx` (new component)

**Note**: This is a new component that needs to be created.

**Rationale**: Dedicated component tests for transparent tool card display.

---

## Test Data & Fixtures

### Backend Fixtures

**Existing Fixtures** (conftest.py):
- `mock_llm_provider` - Basic mock with generate() and stream()
- `sample_conversation`, `sample_user` - Domain objects
- `client`, `app` - HTTP test utilities

**New Fixtures Needed**:

1. **Tool Functions Fixture**
```python
@pytest.fixture
def sample_tools():
    """Provide multiply and add tools for testing."""
    from app.langgraph.tools.multiply import multiply
    from app.langgraph.tools.add import add
    return [multiply, add]
```

2. **Bound Provider Fixtures**
```python
@pytest.fixture
def openai_provider_with_tools(sample_tools):
    """Create OpenAI provider with tools bound."""
    provider = OpenAIProvider()
    return provider.bind_tools(sample_tools)

@pytest.fixture
def anthropic_provider_with_tools(sample_tools):
    """Create Anthropic provider with tools bound."""
    provider = AnthropicProvider()
    return provider.bind_tools(sample_tools)
# ... similar for Gemini and Ollama
```

3. **Tool Call Response Fixtures**
```python
@pytest.fixture
def ai_message_with_multiply_call():
    """AIMessage with multiply tool call."""
    return AIMessage(
        content="Let me multiply those for you...",
        tool_calls=[{
            "id": "call_123",
            "type": "tool_call",
            "function": {
                "name": "multiply",
                "arguments": '{"a": 3, "b": 4}'
            }
        }]
    )

@pytest.fixture
def tool_message_with_result():
    """ToolMessage with result from tool execution."""
    return ToolMessage(
        tool_call_id="call_123",
        name="multiply",
        content="12"
    )
```

4. **Graph Execution Fixtures**
```python
@pytest.fixture
def mock_graph():
    """Mock LangGraph for testing."""
    mock = AsyncMock()
    async def mock_astream_events(*args, **kwargs):
        # Yield events: HumanMessage, AIMessage with tool_calls, ToolMessage, final AIMessage
        yield {"event": "on_chat_model_stream", "data": {"chunk": AIMessage(content="Result: ")}}
        yield {"event": "on_chat_model_stream", "data": {"chunk": AIMessage(content="12")}}

    mock.astream_events = mock_astream_events
    return mock
```

5. **WebSocket Event Fixtures**
```python
@pytest.fixture
def tool_start_event():
    """WebSocket event for tool execution start."""
    return {
        "type": "tool_start",
        "tool_name": "multiply",
        "tool_input": {"a": 3, "b": 4}
    }

@pytest.fixture
def tool_complete_event():
    """WebSocket event for tool execution complete."""
    return {
        "type": "tool_complete",
        "tool_name": "multiply",
        "tool_result": "12",
        "execution_time": 45
    }
```

### Frontend Fixtures

**New Setup Files**:

1. **Test Setup** (`frontend/test/setup.ts`)
```typescript
import { expect, afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock WebSocket
global.WebSocket = vi.fn(() => ({
  send: vi.fn(),
  close: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  readyState: WebSocket.OPEN,
})) as any;
```

2. **WebSocket Mock Factory** (`frontend/test/mocks/websocket.ts`)
```typescript
export function createMockWebSocket() {
  return {
    send: vi.fn(),
    close: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    readyState: WebSocket.OPEN,
    onopen: null,
    onclose: null,
    onerror: null,
    onmessage: null,
  };
}
```

3. **API Mock Factory** (`frontend/test/mocks/api.ts`)
```typescript
import { setupServer } from 'msw';
import { http, HttpResponse } from 'msw';

export function createMockServer() {
  const server = setupServer(
    http.get('/api/conversations', () => {
      return HttpResponse.json([
        { id: 'conv-1', title: 'Test Conversation', message_count: 0 }
      ]);
    }),
    // ... more handlers
  );

  return server;
}
```

---

## Implementation Guidance

### Phase 1: Tool Definitions (Foundation)

1. Create `backend/app/langgraph/tools/add.py`:
   - Implement `add(a: int, b: int) -> int`
   - Add docstring
   - Ensure type hints correct for LangGraph

2. Update `backend/app/langgraph/tools/__init__.py`:
   - Export both multiply and add

3. Write `backend/tests/unit/test_tools.py`:
   - Test multiply with various inputs
   - Test add with various inputs
   - Verify signatures match LangGraph expectations

### Phase 2: Provider Tool Binding (Unit Testing)

1. Write `backend/tests/unit/test_provider_bind_tools.py`:
   - Test bind_tools() on all 4 providers
   - Mock LangChain bind_tools() calls
   - Verify return provider instances

2. Update `backend/tests/unit/test_llm_providers.py`:
   - Add tests for generate() with tool_calls
   - Mock provider responses with tool_calls

### Phase 3: Graph & Tool Execution (Integration)

1. Write `backend/tests/integration/test_graph_tools.py`:
   - Test ToolNode receives AIMessage with tool_calls
   - Test tools_condition routing logic
   - Test full graph loop with tool execution

2. Update `backend/app/langgraph/graphs/streaming_chat_graph.py`:
   - Verify ToolNode correctly initialized
   - Verify tools_condition correctly configured

### Phase 4: WebSocket Protocol (Schema Update)

1. Update `backend/app/adapters/inbound/websocket_schemas.py`:
   - Add `TOOL_START = "tool_start"` to MessageType enum
   - Add `TOOL_COMPLETE = "tool_complete"` to MessageType enum
   - Create `ServerToolStartMessage` class:
     ```python
     class ServerToolStartMessage(BaseModel):
         type: MessageType = Field(default=MessageType.TOOL_START)
         tool_name: str
         tool_input: dict
     ```
   - Create `ServerToolCompleteMessage` class:
     ```python
     class ServerToolCompleteMessage(BaseModel):
         type: MessageType = Field(default=MessageType.TOOL_COMPLETE)
         tool_name: str
         tool_result: str
         execution_time: int  # milliseconds
     ```

2. Write `backend/tests/integration/test_websocket_schemas.py`:
   - Test message validation and serialization

### Phase 5: WebSocket Tool Events (Event Emission)

1. Update `backend/app/adapters/inbound/websocket_handler.py`:
   - In graph.astream_events() loop, add handlers:
     ```python
     if event["event"] == "on_tool_start":
         # Extract tool_name and tool_input
         # Send ServerToolStartMessage
     if event["event"] == "on_tool_end":
         # Extract tool_name and tool_result
         # Send ServerToolCompleteMessage
     ```

2. Write `backend/tests/integration/test_websocket_tools_flow.py`:
   - Test WebSocket receives tool events
   - Test full flow with tool execution

### Phase 6: Frontend WebSocket Service (Tool Events)

1. Update `frontend/src/services/websocketService.ts`:
   - Add `onToolStart` callback to WebSocketConfig
   - Add `onToolComplete` callback to WebSocketConfig
   - In handleMessage(), add cases for TOOL_START and TOOL_COMPLETE:
     ```typescript
     case MessageType.TOOL_START:
       this.config.onToolStart?.(message.tool_name, message.tool_input);
       break;
     case MessageType.TOOL_COMPLETE:
       this.config.onToolComplete?.(message.tool_name, message.tool_result, message.execution_time);
       break;
     ```

2. Write `frontend/src/services/__tests__/websocketService.test.ts`:
   - Test tool event handling

### Phase 7: Frontend Hook (Tool State)

1. Update `frontend/src/hooks/useWebSocket.ts`:
   - Add `onToolStart` and `onToolComplete` callbacks
   - Track tool state in streaming message (new field: `toolInfo` with name, input, result, status)

2. Write `frontend/src/hooks/__tests__/useWebSocket.test.ts`:
   - Test tool event integration

### Phase 8: Frontend Context (Tool Display)

1. Update `frontend/src/contexts/ChatContext.tsx`:
   - Update ChatContextType to include `toolInfo` or extend `streamingMessage`
   - Pass tool callbacks to useWebSocket

2. Write `frontend/src/contexts/__tests__/ChatContext.test.tsx`:
   - Test tool message display

### Phase 9: Frontend Components (Tool Card UI)

1. Create `frontend/src/components/chat/ToolCard.tsx`:
   - Display tool execution transparently
   - Show tool name, input, result, execution time
   - Handle running/complete/error states

2. Update `frontend/src/components/chat/MessageList.tsx`:
   - Render ToolCard for tool messages
   - Integrate with streaming message state

3. Write component tests:
   - `frontend/src/components/chat/__tests__/ToolCard.test.tsx`
   - `frontend/src/components/chat/__tests__/MessageList.test.tsx`

### Phase 10: End-to-End Tests

1. Write `backend/tests/e2e/test_chat_with_tools.py`:
   - Full flow tests from user message to tool execution to response

2. Write `backend/tests/e2e/test_tools_all_providers.py`:
   - Parameterized tests for all providers

---

## Risks and Considerations

### Critical Testing Gaps

1. **Tool Binding Validation**: No tests currently verify bind_tools() works on real providers. Risk: Tool binding fails silently at runtime.
   - **Mitigation**: Comprehensive unit tests with mocked LangChain models

2. **ToolNode Integration**: No tests verify ToolNode correctly receives tool_calls from AIMessage. Risk: ToolNode silently drops tool calls.
   - **Mitigation**: Integration tests with full graph execution

3. **Event Streaming**: No tests verify TOOL_START/TOOL_COMPLETE events emitted. Risk: UI never sees tool execution.
   - **Mitigation**: WebSocket integration tests with mocked graph events

4. **Message Persistence**: No tests verify tool messages (ToolMessage) persisted in checkpoints. Risk: Conversation history missing tool context.
   - **Mitigation**: Checkpointer integration tests verifying message types

5. **Frontend No Tests**: No frontend test infrastructure exists. Risk: UI regressions undetected.
   - **Mitigation**: Create vitest setup, comprehensive component and hook tests

### Architectural Concerns

1. **Tool Registration**: Tools hardcoded in two places (streaming_chat_graph.py and call_llm.py). Risk: Adding new tools requires code changes in multiple locations.
   - **Mitigation**: Create tools registry pattern (later enhancement)

2. **Provider bind_tools() Pattern**: Each provider creates new instance with bound model. Risk: Inconsistent behavior if not careful.
   - **Mitigation**: Establish consistent pattern in tests, document in comments

3. **Tool Error Handling**: No tests for invalid tool calls or tool execution errors. Risk: Errors propagate unhandled.
   - **Mitigation**: Add error handling tests, verify graceful degradation

4. **Concurrent Tool Calls**: Not tested with multiple parallel tool calls. Risk: Race conditions in tool execution.
   - **Mitigation**: Add tests for `parallel_tool_calls=False` and `parallel_tool_calls=True`

5. **Tool Input Validation**: Tools (multiply, add) don't validate inputs. Risk: Invalid inputs cause errors.
   - **Mitigation**: Add input type hints and tests for edge cases (None, wrong types)

### Testing Best Practices to Enforce

1. **Test Isolation**: Each test should be independent. Don't rely on test execution order.
   - Fixture usage in conftest ensures isolation

2. **Mock vs Real**: Unit tests should mock LangChain, integration tests can mock APIs but test real graph nodes.
   - Clear separation in test file naming

3. **Assertion Clarity**: Assertions should be specific and readable.
   - Test names describe what's being tested

4. **Error Path Testing**: Every error path needs a test.
   - Test bind_tools() with invalid inputs, tool execution errors, etc.

5. **Performance**: Don't add tests that are slow or flaky.
   - Avoid real API calls, use mocks and fixtures

### Coverage Goals

- **Unit Tests**: 100% for pure functions (tools, providers)
- **Integration Tests**: All critical paths (bind_tools, graph execution, WebSocket flow)
- **E2E Tests**: Happy path and main error cases
- **Frontend**: All components, hooks, context with tool features
- **WebSocket**: All message types including TOOL_START and TOOL_COMPLETE

---

## Testing Strategy

### Test Pyramid Balance

```
        /\
       /  \  E2E Tests (10%)
      /____\
     /      \
    /        \  Integration Tests (30%)
   /  ________\
  /  /          \
 /  /            \  Unit Tests (60%)
/__/______________\
```

- **Unit Tests (60%)**: Tools, providers, message schemas
- **Integration Tests (30%)**: Graph, WebSocket, provider binding
- **E2E Tests (10%)**: Full user flows with tool execution

### CI/CD Integration

1. **Unit tests**: Run on every commit (fast, <2 minutes)
2. **Integration tests**: Run on every commit (medium, <5 minutes)
3. **E2E tests**: Run on pull requests and main branch (slow, <15 minutes)
4. **Coverage**: Target 80%+ overall, 100% for critical paths

### Test Execution

**Backend**:
```bash
# Unit tests only
pytest backend/tests/unit -v

# Unit + Integration
pytest backend/tests -v -m "unit or integration"

# All including E2E
pytest backend/tests -v

# Specific test file
pytest backend/tests/unit/test_tools.py -v

# With coverage
pytest backend/tests --cov=backend/app --cov-report=html
```

**Frontend**:
```bash
# All tests
vitest run

# Watch mode
vitest watch

# With coverage
vitest run --coverage

# Specific test file
vitest run MessageList.test.tsx
```

### Test Documentation

Each test file should have:

1. **Module docstring**:
   ```python
   """
   Tests for [component/feature].

   Tests verify:
   - [key behavior 1]
   - [key behavior 2]
   - [error handling]

   Fixtures used:
   - [fixture 1]
   - [fixture 2]
   """
   ```

2. **Class docstring** (for grouped tests):
   ```python
   class TestMultiplyTool:
       """Tests for multiply() tool function."""
   ```

3. **Test docstring** (clear description):
   ```python
   def test_multiply_positive_integers():
       """Multiply 3 * 4 should return 12."""
   ```

### Continuous Improvement

After initial implementation:

1. **Measure Coverage**: Use pytest-cov and coverage.py to identify gaps
2. **Monitor Failures**: Track which tests fail most often (brittle tests)
3. **Refactor Tests**: Consolidate repeated test patterns into fixtures/factories
4. **Documentation**: Update test README if test infrastructure changes
5. **Performance**: Monitor test execution time, optimize slow tests

---

## Summary

The tool-calling feature requires comprehensive testing across all layers:

1. **Tool Functions**: Simple pure function tests (unit)
2. **Provider Tool Binding**: Mocked provider tests (unit) + integration with real LangChain
3. **Graph Execution**: ToolNode routing and execution (integration)
4. **WebSocket Flow**: Message protocol and event streaming (integration)
5. **Frontend UI**: Component and hook tests for tool display (unit) + full flow tests (e2e)

All major components need test coverage before merging. The existing test infrastructure provides a good foundation (conftest fixtures, AsyncClient testing) but needs significant expansion for tool-specific scenarios.

**Key Files to Create/Modify**:
- Backend: 7 new test files, 2 schema updates
- Frontend: 6 new test files, 2 component updates, vitest setup
- Total: ~1000+ lines of test code across unit, integration, and e2e layers

This analysis provides a complete roadmap for implementing comprehensive test coverage for tool-calling functionality.
