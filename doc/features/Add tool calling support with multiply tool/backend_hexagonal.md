# Backend Hexagonal Architecture Analysis

## Request Summary

Add tool calling support to the LLM conversation flow, starting with a multiply tool as a proof of concept. This requires integrating LangChain's tool calling capabilities while maintaining clean hexagonal architecture separation.

## Relevant Files & Modules

### Files to Examine

**Core Domain Layer:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/message.py` - Message entity with role, content, metadata. May need extension for tool calls/results
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - ILLMProvider port interface. Needs extension to support tool binding and tool call detection

**LangGraph Orchestration Layer:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - ConversationState TypedDict. Needs fields for tool calls and tool results
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Main conversation graph orchestration. Needs new nodes and edges for tool execution loop
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Streaming version of chat graph. Needs similar tool execution flow
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - LLM invocation node. Needs to detect tool calls in response
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/process_input.py` - Input processing node. Reference for node structure
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/format_response.py` - Response formatting node. Reference for node structure
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/save_history.py` - Message persistence node. May need to save tool call messages

**Adapter Layer:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/anthropic_provider.py` - Anthropic provider implementation. Needs tool binding support
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/openai_provider.py` - OpenAI provider implementation. Needs tool binding support
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/gemini_provider.py` - Gemini provider implementation. Needs tool binding support
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/ollama_provider.py` - Ollama provider implementation. Needs tool binding support
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/provider_factory.py` - Factory for creating LLM providers. Reference for provider instantiation pattern
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket chat handler. May need updates to handle tool execution in streaming context

**Infrastructure Layer:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/requirements.txt` - Dependencies including langchain, langchain-core, and provider integrations

**Testing:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_llm_providers.py` - Unit tests for LLM providers. Template for testing tool calling
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/conftest.py` - Test fixtures and configuration

### Key Functions & Classes

- `ILLMProvider.generate()` and `ILLMProvider.stream()` - Core methods that need tool support
- `call_llm()` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - Invokes LLM and returns response
- `create_chat_graph()` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Constructs the conversation flow graph
- `handle_websocket_chat()` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - Real-time streaming chat handler
- `ConversationState` TypedDict - State schema passed between LangGraph nodes

## Current Architecture Overview

The codebase follows hexagonal architecture with clear separation:

### Domain Core

**Location:** `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/`

**Entities:**
- `Message` - Pure domain model representing conversation messages (user, assistant, system)
- `Conversation` - Conversation metadata and ownership
- `User` - User entity

**Value Objects:**
- `MessageRole` - Enum (USER, ASSISTANT, SYSTEM)

**Characteristics:**
- Zero infrastructure dependencies
- Database-agnostic
- Framework-agnostic

### Ports (Interfaces)

**Location:** `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/`

**Primary Ports (Driving Adapters):**
- Inbound REST API and WebSocket handlers drive the core domain

**Secondary Ports (Driven Adapters):**
- `ILLMProvider` - Abstract interface for LLM operations (generate, stream, get_model_name)
- `IMessageRepository` - Abstract interface for message persistence
- `IConversationRepository` - Abstract interface for conversation persistence
- `IUserRepository` - Abstract interface for user persistence
- `IAuthService` - Abstract interface for authentication

**Key Observation:**
All ports point inward toward the domain. The domain never depends on adapters.

### Adapters

**Inbound Adapters** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/`):
- REST API routers (FastAPI endpoints)
- WebSocket handlers for real-time chat
- Translate HTTP/WebSocket protocols into domain operations

**Outbound Adapters** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/`):
- `MongoUserRepository`, `MongoConversationRepository`, `MongoMessageRepository` - MongoDB implementations
- `OpenAIProvider`, `AnthropicProvider`, `GeminiProvider`, `OllamaProvider` - LLM provider implementations using LangChain

**Adapter Pattern:**
All adapters implement port interfaces. They use LangChain primitives (ChatOpenAI, ChatAnthropic, etc.) internally but expose a clean domain interface.

### LangGraph Layer

**Location:** `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/`

**Role:** Orchestration layer sitting between adapters and domain

**Components:**
- `ConversationState` - TypedDict schema for graph state
- **Nodes:** `process_input`, `call_llm`, `format_response`, `save_history`
- **Graphs:** `chat_graph.py` (synchronous), `streaming_chat_graph.py` (WebSocket streaming)

**Current Flow:**
```
START → process_input → [conditional] → call_llm → format_response → save_history → END
```

**Dependency Injection:**
Nodes receive dependencies (llm_provider, repositories) as parameters via lambda closures in graph construction.

**Key Observation:**
LangGraph acts as an orchestration adapter. It coordinates calls to domain ports but doesn't contain business logic.

## Impact Analysis

### Components Affected

1. **Core Domain Layer**
   - `Message` entity may need optional `tool_calls` and `tool_call_id` fields in metadata
   - No new entities required (tools are operational, not domain entities)

2. **Port Interfaces**
   - `ILLMProvider` needs extension to support tool binding
   - Possible new port: `ITool` for defining tool contracts (CRITICAL DECISION)

3. **LangGraph Orchestration**
   - `ConversationState` needs new fields: `tool_calls`, `tool_results`, `pending_tool_calls`
   - New nodes: `execute_tools`, `check_tool_calls`
   - Graph flow needs conditional loop: LLM → check tools → execute tools → LLM (if tools called)

4. **Outbound Adapters**
   - All LLM provider implementations need tool binding via LangChain's `bind_tools()`
   - May need to detect `AIMessage.tool_calls` after LLM invocation

5. **Testing**
   - Unit tests for tool definitions and execution
   - Integration tests for tool calling flow through LangGraph
   - Mocking strategies for tool execution

### Data Flow Changes

**Current Flow:**
```
User Input → process_input → call_llm → format_response → save_history → Response
```

**Tool-Enhanced Flow:**
```
User Input → process_input → call_llm → check_tool_calls
                                              ↓ (if tools requested)
                                         execute_tools
                                              ↓
                                         call_llm (with tool results)
                                              ↓ (loop until no tool calls)
                                         format_response → save_history → Response
```

## Architectural Recommendations

### 1. Tool Definition Layer

**Question:** Where should tools be defined in hexagonal architecture?

**Recommendation:** Define tools at the **LangGraph orchestration layer**, NOT in the domain core.

**Rationale:**
- Tools are **operational capabilities** provided by the system, not business entities
- Tools are tightly coupled to LangChain's tool framework (decorators, schemas)
- Keeping tools in LangGraph preserves domain purity
- Tools can be thought of as "outbound adapters that the LLM can invoke"

**Proposed Structure:**
```
/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/
├── __init__.py
├── multiply.py          # Multiply tool implementation
├── tool_registry.py     # Central registry of available tools
```

**Why not in domain?**
- Tools use LangChain decorators (`@tool`) which are infrastructure concerns
- Domain should remain framework-agnostic
- Tools are execution mechanisms, not business rules

**Why not in adapters?**
- Tools aren't adapters to external systems (like databases or APIs)
- They're functions that LangGraph makes available to the LLM
- They fit naturally alongside nodes and graphs as orchestration primitives

### 2. Port Extension Strategy

**Option A: Extend ILLMProvider with tool methods**
```python
class ILLMProvider(ABC):
    @abstractmethod
    async def generate(self, messages: List[Message]) -> str:
        pass

    @abstractmethod
    async def stream(self, messages: List[Message]) -> AsyncGenerator[str, None]:
        pass

    # NEW: Tool binding support
    @abstractmethod
    def bind_tools(self, tools: List[Any]) -> 'ILLMProvider':
        """Bind tools to the LLM provider for tool calling."""
        pass

    @abstractmethod
    def supports_tools(self) -> bool:
        """Check if this provider supports tool calling."""
        pass
```

**Option B: Create separate IToolCallableLLM port**
```python
class IToolCallableLLM(ILLMProvider):
    @abstractmethod
    def bind_tools(self, tools: List[Any]) -> 'IToolCallableLLM':
        pass
```

**Recommendation: Option A (Extend ILLMProvider)**

**Rationale:**
- Simpler: Single interface to maintain
- All modern LLMs support tools (OpenAI, Anthropic, Gemini, Ollama with compatible models)
- Backward compatible: Default implementation returns `self` for providers that don't support tools
- Follows YAGNI principle: Don't create abstraction layers until needed

**Trade-off:**
- Violates Interface Segregation Principle slightly
- BUT: Tool calling is becoming standard LLM capability, not a special case

### 3. Message Model Extension

**Current Message Model:**
```python
class Message(BaseModel):
    id: Optional[str] = None
    conversation_id: str
    role: MessageRole
    content: str
    created_at: datetime
    metadata: Optional[dict] = None
```

**Recommendation:** Use `metadata` field for tool-related data, add new MessageRole values

**Proposed Changes:**
```python
class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"  # NEW: For tool execution results

# In Message metadata, store:
# - tool_calls: List[dict] for assistant messages requesting tool execution
# - tool_call_id: str for tool messages responding to a specific tool call
```

**Rationale:**
- Minimally invasive: Uses existing metadata field
- Domain model stays clean and simple
- LangChain already uses similar pattern with AIMessage.tool_calls and ToolMessage
- Keeps tool-specific details out of core domain structure

**Alternative Considered:**
Creating separate `ToolCallMessage` and `ToolResultMessage` entities was rejected because:
- Adds complexity to domain model
- Tool calling is metadata about messages, not a fundamental message type
- Harder to persist and query with existing repository patterns

### 4. LangGraph Node Strategy

**New Nodes Required:**

**Node 1: `check_tool_calls`**
- **Purpose:** Inspect LLM response for tool call requests
- **Input:** ConversationState with llm_response
- **Output:** Updates state with tool_calls list or proceeds to format_response
- **Location:** `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/check_tool_calls.py`

**Node 2: `execute_tools`**
- **Purpose:** Execute requested tools and collect results
- **Input:** ConversationState with pending_tool_calls
- **Output:** Updates state with tool_results, adds tool messages to history
- **Location:** `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/execute_tools.py`
- **Dependencies:** Tool registry (NOT injected via port, accessed directly from langgraph.tools)

**Modified Node: `call_llm`**
- **Change:** Return full AIMessage object (not just content string) to preserve tool_calls
- **Rationale:** Need access to AIMessage.tool_calls attribute from LangChain

**Graph Flow with Tools:**
```python
# Conditional edges
def should_continue_after_process(state):
    if state.get("error"):
        return "end"
    return "call_llm"

def should_execute_tools(state):
    if state.get("tool_calls"):
        return "execute_tools"
    return "format_response"

# Graph construction
START → process_input → [should_continue_after_process] → call_llm
                                                             ↓
                                                     check_tool_calls
                                                             ↓
                                             [should_execute_tools]
                                            /                    \
                                    execute_tools          format_response
                                           ↓                      ↓
                                    call_llm (loop)         save_history → END
```

### 5. Tool Registry Pattern

**Proposed Implementation:**
```python
# /Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/tool_registry.py
from typing import List, Callable
from langchain_core.tools import BaseTool

class ToolRegistry:
    """Registry of available tools for LLM use."""

    _tools: List[BaseTool] = []

    @classmethod
    def register(cls, tool: BaseTool) -> None:
        cls._tools.append(tool)

    @classmethod
    def get_all_tools(cls) -> List[BaseTool]:
        return cls._tools.copy()

    @classmethod
    def get_tool_by_name(cls, name: str) -> Optional[BaseTool]:
        return next((t for t in cls._tools if t.name == name), None)

# In tools/__init__.py, register tools at module import
from .multiply import multiply_tool
ToolRegistry.register(multiply_tool)
```

**Rationale:**
- Centralized tool discovery
- Easy to add new tools without modifying graph code
- Tools are registered declaratively at module load time
- Simple pattern that doesn't require dependency injection

**Alternative Considered:**
Dependency injection of tools via ports was rejected because:
- Tools are internal orchestration primitives, not external dependencies
- Over-engineering for the current use case
- Would require new port interfaces and adapters

### 6. Dependency Inversion Considerations

**Key Principle:** Dependencies flow inward toward the domain core.

**Tool Calling Dependency Flow:**
```
Domain Core (Message, MessageRole)
       ↑
       | (depends on via ILLMProvider interface)
       |
LangGraph Orchestration (nodes, graphs, tools)
       ↑
       | (depends on via ILLMProvider, IMessageRepository)
       |
Outbound Adapters (AnthropicProvider, OpenAIProvider)
       ↑
       | (uses)
       |
LangChain Framework (ChatAnthropic, bind_tools, ToolMessage)
```

**Preserved Principles:**
- Core domain has NO dependency on LangGraph or LangChain
- LangGraph depends on domain via port interfaces
- Adapters implement ports using LangChain primitives
- Tools live in LangGraph layer, not domain

**Risk Mitigation:**
If tool implementations need external dependencies (e.g., database access, API calls), create:
- Tool adapter pattern: Tool calls a port interface for external operations
- Example: A "search_database" tool would call `ISearchRepository` port

## Implementation Guidance

### Step 1: Extend Core Domain (Minimal Changes)

1. Add `TOOL` to `MessageRole` enum in `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/message.py`
2. Document metadata schema for tool-related fields (keep as dict, don't create new fields)
3. No new entities required

### Step 2: Extend ILLMProvider Port

1. Add `bind_tools()` and `supports_tools()` methods to `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py`
2. Modify `generate()` return type to return full message object (not just string) - BREAKING CHANGE
3. Add type hints for tool-related return values

**Breaking Change Mitigation:**
- Create `generate_text()` method that returns string (backward compatible)
- Create `generate_message()` method that returns full AIMessage
- Deprecate old `generate()` method over time

**Alternative:** Keep `generate()` for text, add `generate_with_tools()` for tool-enabled calls

### Step 3: Implement Tools Layer

1. Create `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/` directory
2. Implement `multiply.py` using LangChain's `@tool` decorator
3. Create `tool_registry.py` for centralized tool management
4. Write unit tests for multiply tool

**Multiply Tool Example:**
```python
from langchain_core.tools import tool

@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers together.

    Args:
        a: First number
        b: Second number

    Returns:
        Product of a and b
    """
    return a * b
```

### Step 4: Update LLM Provider Adapters

1. Implement `bind_tools()` in all providers (OpenAI, Anthropic, Gemini, Ollama)
2. Update `generate()` to return full AIMessage object
3. Ensure streaming still works with tool-enabled models
4. Add provider capability checks (some Ollama models don't support tools)

**Example Implementation (OpenAI):**
```python
def bind_tools(self, tools: List[BaseTool]) -> 'OpenAIProvider':
    self.model = self.model.bind_tools(tools)
    return self

def supports_tools(self) -> bool:
    return True  # OpenAI GPT-4+ supports tools
```

### Step 5: Create Tool Execution Nodes

1. Create `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/check_tool_calls.py`
   - Inspect AIMessage for tool_calls attribute
   - Update state with pending tool calls

2. Create `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/execute_tools.py`
   - Execute tools using ToolRegistry
   - Collect results and create ToolMessages
   - Handle tool execution errors gracefully

### Step 6: Update ConversationState Schema

1. Add fields to `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py`:
   - `tool_calls: Optional[List[dict]]` - Pending tool calls from LLM
   - `tool_results: Optional[List[dict]]` - Results from tool execution
   - `ai_message: Optional[Any]` - Full AIMessage object (temporary field)

### Step 7: Modify Chat Graph

1. Update `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py`
   - Add `check_tool_calls` and `execute_tools` nodes
   - Add conditional edges for tool execution loop
   - Bind tools to LLM provider during graph construction

2. Update `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py`
   - Apply same changes for streaming context
   - Ensure streaming continues to work during tool execution

### Step 8: Update WebSocket Handler (Optional)

1. Modify `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py`
   - Consider sending intermediate messages during tool execution
   - Example: "Calling multiply function..."
   - Maintain streaming UX during multi-turn tool interactions

### Step 9: Write Comprehensive Tests

**Unit Tests:**
- Test tool definitions and execution in isolation
- Test tool registry registration and retrieval
- Test LLM provider tool binding
- Test node logic (check_tool_calls, execute_tools)

**Integration Tests:**
- Test full flow: User message → LLM requests tool → Tool executes → LLM responds
- Test tool error handling
- Test streaming with tools
- Test conversation history with tool messages

**End-to-End Tests:**
- Test via WebSocket with real LLM provider (using test mode or mocked LLM)
- Test tool persistence in message history
- Test conversation continuity after tool use

## Risks and Considerations

### Architectural Risks

**Risk 1: LangGraph becoming a "god layer"**
- **Description:** Tool logic, orchestration, and business logic could all accumulate in LangGraph
- **Mitigation:** Keep tools simple and stateless. Complex business logic belongs in use cases
- **Example:** If a tool needs to create a conversation, it should call a use case, not access repositories directly

**Risk 2: Tight coupling to LangChain**
- **Description:** Tool calling requires LangChain-specific primitives (AIMessage, ToolMessage, @tool decorator)
- **Impact:** Harder to swap LangChain for alternatives
- **Assessment:** ACCEPTABLE TRADE-OFF because:
  - LangChain is industry standard for LLM orchestration
  - Tool calling is standardized across providers (function calling spec)
  - Abstraction cost would exceed benefit (YAGNI principle)

**Risk 3: Breaking changes to ILLMProvider**
- **Description:** Changing `generate()` return type breaks existing code
- **Mitigation:** Create separate `generate_with_tools()` method for tool-enabled calls
- **Alternative:** Use backward-compatible wrapper that detects tool calls in metadata

### Implementation Risks

**Risk 4: Tool execution errors breaking conversation flow**
- **Description:** Tool execution failure could crash the entire conversation
- **Mitigation:**
  - Wrap tool execution in try/except
  - Return error message to LLM as tool result
  - LLM can recover and explain error to user

**Risk 5: Infinite tool calling loops**
- **Description:** LLM repeatedly calls tools without producing final answer
- **Mitigation:**
  - Add max_iterations parameter to graph execution
  - Count tool call rounds in ConversationState
  - Abort after N iterations (default: 5)

**Risk 6: Streaming UX degradation**
- **Description:** Tool execution introduces delay in streaming responses
- **Mitigation:**
  - Send interim messages to user ("Calculating...")
  - Stream tool execution steps if verbose mode enabled
  - Set user expectations that tool use may pause streaming

### Performance Risks

**Risk 7: Additional LLM round trips**
- **Description:** Each tool call requires new LLM invocation
- **Impact:** Increased latency and API costs
- **Assessment:** ACCEPTABLE because:
  - Tool calling provides value that justifies cost
  - Users expect slight delay for computed results
  - Can be optimized later with parallel tool execution

### Testing Risks

**Risk 8: Testing complexity increases**
- **Description:** More code paths, more state combinations, harder to mock
- **Mitigation:**
  - Test each component in isolation first (tools, nodes, providers)
  - Use fixtures for common state setups
  - Mock LLM responses with tool_calls attribute
  - Create reusable test helpers for tool execution flows

### Security Risks

**Risk 9: Tool execution security**
- **Description:** LLM-controlled tool execution could be exploited
- **Mitigation:**
  - Validate all tool inputs against schemas (LangChain does this automatically)
  - Whitelist allowed tools (ToolRegistry pattern)
  - Never allow arbitrary code execution via tools
  - Audit tool implementations for security issues

**Risk 10: Tool results exposing sensitive data**
- **Description:** Tool results stored in message history could leak data
- **Mitigation:**
  - Sanitize tool results before storage
  - Apply same authorization checks as regular messages
  - Consider encrypting tool results in database

## Testing Strategy

### Unit Testing Layers

**Layer 1: Tool Definitions**
- Test multiply tool with various inputs (positive, negative, zero, floats)
- Test tool schema generation
- Test tool error handling

**Layer 2: Tool Registry**
- Test tool registration and retrieval
- Test duplicate tool name handling
- Test tool listing

**Layer 3: LLM Provider Extensions**
- Test `bind_tools()` method on each provider
- Test `supports_tools()` capability detection
- Mock LangChain's bind_tools to avoid API calls

**Layer 4: LangGraph Nodes**
- Test `check_tool_calls` with AIMessage containing tool_calls
- Test `execute_tools` with various tool invocations
- Test error handling in tool execution
- Mock tool registry to control tool behavior

**Layer 5: State Management**
- Test ConversationState updates through tool flow
- Test state serialization/deserialization with tool fields

### Integration Testing

**Test 1: Full Tool Execution Flow**
```python
@pytest.mark.integration
async def test_multiply_tool_execution():
    # Setup: Create conversation with multiply tool enabled
    # Action: Send "What is 6 times 7?"
    # Assert: LLM calls multiply(6, 7), receives 42, responds to user
    # Assert: Message history contains user, assistant, tool, assistant messages
```

**Test 2: Tool Error Handling**
```python
@pytest.mark.integration
async def test_tool_execution_error():
    # Setup: Mock tool to raise exception
    # Action: LLM attempts to call tool
    # Assert: Error message sent to LLM
    # Assert: LLM explains error to user
    # Assert: Conversation continues (doesn't crash)
```

**Test 3: Multi-Turn Tool Usage**
```python
@pytest.mark.integration
async def test_multiple_tool_calls():
    # Action: User asks question requiring 2 tool calls
    # Assert: Both tools execute
    # Assert: LLM synthesizes final answer from both results
```

**Test 4: Streaming with Tools**
```python
@pytest.mark.integration
async def test_streaming_with_tools():
    # Setup: WebSocket connection with streaming enabled
    # Action: Send message that triggers tool use
    # Assert: Tokens stream normally
    # Assert: Tool execution doesn't break streaming
    # Assert: Final response includes tool results
```

### End-to-End Testing

**Test Approach:**
- Use pytest-asyncio for async test support
- Mock LLM responses with predefined tool_calls
- Use test database (MongoDB in-memory or Docker container)
- Create fixture for conversation setup with tools enabled

**Example E2E Test:**
```python
@pytest.mark.e2e
async def test_multiply_tool_e2e(test_client, authenticated_user, test_conversation):
    # Connect to WebSocket
    # Send: "Calculate 123 * 456"
    # Expect: LLM requests multiply(123, 456)
    # Expect: Tool executes, returns 56088
    # Expect: LLM responds "The result is 56,088"
    # Verify: Message history persisted correctly
    # Verify: Tool call stored in metadata
```

### Test Coverage Goals

- **Unit tests:** 100% coverage of tool definitions, registry, and nodes
- **Integration tests:** All tool execution paths (success, error, multi-turn)
- **E2E tests:** At least one full flow per adapter (REST + WebSocket)

### Mocking Strategy

**Mock LLM Responses:**
```python
# Use LangChain's FakeChatModel for testing
from langchain_core.messages import AIMessage, ToolCall

mock_response = AIMessage(
    content="",
    tool_calls=[
        ToolCall(
            name="multiply",
            args={"a": 6, "b": 7},
            id="call_123"
        )
    ]
)
```

**Mock Tool Registry:**
```python
@pytest.fixture
def mock_tool_registry():
    with patch('app.langgraph.tools.ToolRegistry.get_all_tools') as mock:
        mock.return_value = [multiply_tool]
        yield mock
```

## Summary of Key Architectural Decisions

1. **Tools live in LangGraph layer** - Not in domain core, not in adapters. They are orchestration primitives.

2. **Extend ILLMProvider port** - Single interface with tool support methods, not separate interface.

3. **Use Message.metadata for tool data** - Don't create new message entity types. Keep domain simple.

4. **Add TOOL to MessageRole enum** - Minimal domain change to support tool result messages.

5. **Tool Registry pattern** - Centralized, declarative tool registration without dependency injection.

6. **Conditional graph edges for tool loop** - Standard LangGraph pattern for multi-turn interactions.

7. **Accept LangChain coupling for tools** - Pragmatic choice given LangChain's standard status and tool calling standardization.

8. **Graceful degradation** - Tool execution errors don't crash conversations, LLM can explain errors.

9. **Test at all layers** - Unit, integration, and E2E tests with appropriate mocking.

10. **Preserve dependency inversion** - Domain remains independent, dependencies flow inward.

## Final Recommendations for Pablo

### Start Simple

Begin with the multiply tool as a proof of concept. Avoid over-engineering:
- Don't create complex tool frameworks
- Don't add tool discovery APIs yet
- Don't implement tool authentication/authorization yet
- Focus on: One tool, one flow, full test coverage

### Maintain Architectural Boundaries

Keep these layers clean:
- **Domain:** Add TOOL role, use metadata. No LangChain imports.
- **Ports:** Add tool methods to ILLMProvider. No implementation details.
- **LangGraph:** Implement tools, nodes, and orchestration. This is where tool complexity lives.
- **Adapters:** Implement port methods using LangChain primitives.

### Test Thoroughly

For each commit:
1. Write unit tests first for the component
2. Add integration tests for the flow
3. Verify E2E with WebSocket
4. Ensure pristine test output (no warnings, clean logs)

### Evolution Path

Once multiply tool works:
1. Add 2-3 more simple tools (add, divide, search_messages)
2. Refactor common patterns into base classes
3. Add tool authorization (user can only call certain tools)
4. Add tool usage analytics
5. Consider tool marketplace or plugin system

### Keep It Simple

Remember: The goal is tool calling support, not a tool framework. Build the simplest thing that works, then iterate based on real usage patterns.
