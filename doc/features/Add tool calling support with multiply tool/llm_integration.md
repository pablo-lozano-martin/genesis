# LLM Integration Analysis

## Request Summary
Add tool calling support to the existing LLM provider abstraction with a multiply tool as the initial implementation. This requires evaluating how to integrate tool binding (using LangChain's `.bind_tools()` or native provider APIs) across multiple LLM providers (OpenAI, Anthropic, Gemini, Ollama) while maintaining the hexagonal architecture's provider abstraction principles.

## Relevant Files & Modules

### Files to Examine

#### Core Provider Abstraction
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - Abstract interface defining LLM provider contract (generate, stream, get_model_name methods)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/message.py` - Message domain model with role enumeration (USER, ASSISTANT, SYSTEM)

#### Provider Implementations
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/openai_provider.py` - OpenAI implementation using LangChain's ChatOpenAI
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/anthropic_provider.py` - Anthropic implementation using LangChain's ChatAnthropic
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/gemini_provider.py` - Gemini implementation using LangChain's ChatGoogleGenerativeAI
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/ollama_provider.py` - Ollama implementation using LangChain's ChatOllama
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/provider_factory.py` - Factory for creating provider instances based on LLM_PROVIDER env variable

#### LangGraph Integration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - ConversationState TypedDict schema with message list, conversation_id, llm_response
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - Node that invokes llm_provider.generate() for non-streaming
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Main conversation graph (process_input -> call_llm -> format_response -> save_history)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Streaming graph with call_llm_stream function using llm_provider.stream()
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/process_input.py` - Validates user input and creates USER message
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/format_response.py` - Converts llm_response string to ASSISTANT message

#### Application Layer
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket handler that streams tokens using llm_provider.stream()
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/use_cases/send_message.py` - SendMessage use case calling llm_provider.generate()

#### Configuration & Testing
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py` - Settings with provider selection and API keys
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_llm_providers.py` - Unit tests for provider factory and message conversion
- `/Users/pablolozano/Mac Projects August/genesis/backend/requirements.txt` - Dependencies including langchain, langchain-core, provider-specific packages

### Key Functions & Classes

#### Interface Definition
- `ILLMProvider` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py`
  - `async def generate(messages: List[Message]) -> str` - Non-streaming generation
  - `async def stream(messages: List[Message]) -> AsyncGenerator[str, None]` - Token streaming
  - `async def get_model_name() -> str` - Model name retrieval

#### Provider Implementations
- `OpenAIProvider._convert_messages(messages: List[Message]) -> List` - Converts domain messages to LangChain format (HumanMessage, AIMessage, SystemMessage)
- `OpenAIProvider.generate()` - Calls `self.model.ainvoke(langchain_messages)` and returns `response.content`
- `OpenAIProvider.stream()` - Calls `self.model.astream(langchain_messages)` and yields `chunk.content`
- Similar patterns in `AnthropicProvider`, `GeminiProvider`, `OllamaProvider`

#### LangGraph Nodes
- `call_llm(state, llm_provider)` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - Invokes provider.generate() and returns llm_response
- `call_llm_stream(state, llm_provider)` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Generator that yields tokens from provider.stream()

## Current Integration Overview

### Provider Abstraction

The system uses a clean hexagonal architecture with:

1. **Port Interface (`ILLMProvider`)**: Defines the contract all providers must implement
   - Three abstract methods: `generate()`, `stream()`, `get_model_name()`
   - Works with domain `Message` objects, not provider-specific types
   - Returns simple strings (generate) or async generators of strings (stream)

2. **Provider Selection**: Factory pattern based on `LLM_PROVIDER` environment variable
   - Supports: "openai", "anthropic", "gemini", "ollama"
   - Raises ValueError for unsupported providers

### Provider Implementations

All four providers follow identical patterns:

1. **Initialization**: Creates LangChain chat model instance (ChatOpenAI, ChatAnthropic, etc.)
   - Validates API keys/configuration from settings
   - Sets temperature=0.7 and streaming=True
   - Stores model instance as `self.model`

2. **Message Conversion**: `_convert_messages()` method transforms domain Messages to LangChain messages
   - USER role -> HumanMessage
   - ASSISTANT role -> AIMessage
   - SYSTEM role -> SystemMessage

3. **Generation**:
   - Calls `self.model.ainvoke(langchain_messages)`
   - Extracts and returns `response.content` string
   - Wraps errors with provider-specific context

4. **Streaming**:
   - Calls `self.model.astream(langchain_messages)`
   - Yields `chunk.content` for each token
   - Wraps errors with provider-specific context

### Current Request/Response Flow

#### Non-Streaming (SendMessage Use Case)
```
User Input -> SendMessage.execute()
          -> message_repository.create(user_message)
          -> llm_provider.generate(conversation_history)
          -> message_repository.create(assistant_message)
          -> Return assistant_message
```

#### Streaming (WebSocket Handler)
```
WebSocket Message -> message_repository.create(user_message)
                  -> llm_provider.stream(messages)
                  -> Yield tokens via WebSocket
                  -> message_repository.create(full_response)
                  -> Send complete message
```

#### LangGraph Flow
```
process_input -> call_llm (uses generate()) -> format_response -> save_history
```

### Configuration Management

Settings in `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py`:
- `llm_provider: str = "openai"` - Provider selection
- Provider-specific API keys and models:
  - OpenAI: `openai_api_key`, `openai_model` (default: "gpt-4-turbo-preview")
  - Anthropic: `anthropic_api_key`, `anthropic_model` (default: "claude-3-sonnet-20240229")
  - Google: `google_api_key`, `google_model` (default: "gemini-pro")
  - Ollama: `ollama_base_url`, `ollama_model` (default: "llama2", "http://localhost:11434")

## Impact Analysis

### Components Affected by Tool Calling Integration

1. **ILLMProvider Interface** - Needs new methods or parameters for tool binding
2. **All Provider Implementations** - Must implement tool calling logic
3. **Message Domain Model** - May need to support tool call messages and tool result messages
4. **ConversationState** - May need fields for tool execution state
5. **LangGraph Nodes** - New nodes for tool execution and result handling
6. **Chat Graphs** - Extended flow to handle tool calling loops
7. **WebSocket Handler** - Streaming of tool calls and results
8. **Response Formatting** - Handling tool call responses vs text responses

### Tool Calling Capabilities Across Providers

**LangChain Support Matrix**:
- **OpenAI**: Full support via `.bind_tools()` - uses function calling API
- **Anthropic**: Full support via `.bind_tools()` - uses Claude's tool use API
- **Gemini**: Full support via `.bind_tools()` - uses Gemini's function calling
- **Ollama**: Partial support - depends on model (llama3.1+ supports tools, older models don't)

All LangChain chat models support the same `.bind_tools()` interface, which provides provider abstraction.

## LLM Integration Recommendations

### Strategic Decision: LangChain vs Native APIs

**Recommendation: Use LangChain's `.bind_tools()` abstraction**

**Rationale**:
1. All four current providers already use LangChain chat models
2. LangChain provides unified tool calling interface across providers
3. Maintains existing architectural consistency
4. Reduces provider-specific code
5. LangChain handles schema conversion (Pydantic -> provider format) automatically
6. Future provider additions likely to have LangChain support

**Trade-offs**:
- Slight dependency on LangChain's abstraction layer
- May lag behind native API features
- For this codebase: acceptable given existing LangChain dependency

### Proposed Interface Extension

**Option 1: Add optional tools parameter to existing methods** (Recommended for backward compatibility)

```python
class ILLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        tools: Optional[List[Any]] = None  # Pydantic models or tool definitions
    ) -> Union[str, dict]:
        """
        Generate a response, optionally with tool calling support.

        Returns:
            - str: Text response when no tool call made
            - dict: Tool call response with 'tool_calls' key
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[Any]] = None
    ) -> AsyncGenerator[Union[str, dict], None]:
        """
        Stream responses with optional tool calling.

        Yields:
            - str: Text tokens
            - dict: Tool call chunks
        """
        pass
```

**Option 2: Add separate tool-enabled methods**

```python
class ILLMProvider(ABC):
    # Existing methods unchanged

    @abstractmethod
    async def generate_with_tools(
        self,
        messages: List[Message],
        tools: List[Any]
    ) -> dict:
        """Generate with tool calling enabled."""
        pass
```

**Recommendation**: Option 1 - extends existing methods cleanly, maintains single code path.

### Proposed Domain Model Extensions

**New MessageRole Values**:
```python
class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL_CALL = "tool_call"      # Assistant requesting tool execution
    TOOL_RESULT = "tool_result"   # Result of tool execution
```

**Message.metadata field usage**:
Store tool call information in existing `metadata: Optional[dict]` field:
```python
# Tool call message
metadata = {
    "tool_calls": [
        {
            "id": "call_123",
            "name": "multiply",
            "arguments": {"a": 5, "b": 3}
        }
    ]
}

# Tool result message
metadata = {
    "tool_call_id": "call_123",
    "tool_name": "multiply",
    "result": 15
}
```

**Advantage**: No schema changes needed, uses existing extensibility.

### Proposed Implementation Pattern

**Provider Implementation Example (OpenAI)**:
```python
class OpenAIProvider(ILLMProvider):
    def __init__(self):
        # ... existing initialization ...
        self._tools = None  # Store bound tools

    def bind_tools(self, tools: List[Any]):
        """Bind tools to the model for subsequent calls."""
        self.model = self.model.bind_tools(tools)
        self._tools = tools

    async def generate(
        self,
        messages: List[Message],
        tools: Optional[List[Any]] = None
    ) -> Union[str, dict]:
        langchain_messages = self._convert_messages(messages)

        # Use bound tools or passed tools
        model = self.model
        if tools:
            model = model.bind_tools(tools)

        response = await model.ainvoke(langchain_messages)

        # Check if response contains tool calls
        if response.tool_calls:
            return {
                "type": "tool_calls",
                "tool_calls": response.tool_calls
            }

        return response.content
```

### LangGraph Integration Strategy

**New Nodes Needed**:

1. **`execute_tools` node**:
   - Input: State with tool_calls in llm_response
   - Execute tool functions
   - Return: Tool results added to messages

2. **`should_execute_tools` conditional edge**:
   - Check if llm_response contains tool calls
   - Route to execute_tools or format_response

**Extended Graph Flow**:
```
process_input -> call_llm -> [has tools?]
                               ├─ Yes -> execute_tools -> call_llm (loop)
                               └─ No  -> format_response -> save_history -> END
```

**Tool Execution Loop**: LLM can call tools multiple times until final text response.

### Streaming Mode Tool Calling

**Challenge**: Tool calls typically arrive as complete JSON, not streamable tokens.

**Approach Options**:

1. **Buffer and Parse** (Recommended for initial implementation):
   - Accumulate stream chunks until tool call complete
   - Send special "tool_call" message type via WebSocket
   - Execute tool and continue streaming

2. **LangChain's Built-in Handling**:
   - LangChain's `.astream()` with tools returns complete tool call chunks
   - Can detect chunk type and handle accordingly

**WebSocket Message Types to Add**:
```python
class ServerToolCallMessage(BaseModel):
    type: str = "tool_call"
    tool_name: str
    arguments: dict

class ServerToolResultMessage(BaseModel):
    type: str = "tool_result"
    tool_name: str
    result: Any
```

### Tool Definition and Registration

**Recommended Approach**: Pydantic models with LangChain compatibility

**Example Multiply Tool**:
```python
from pydantic import BaseModel, Field

class MultiplyInput(BaseModel):
    """Input schema for multiply tool."""
    a: float = Field(description="First number")
    b: float = Field(description="Second number")

class MultiplyTool(BaseModel):
    """Multiply two numbers together."""

    name: str = "multiply"
    description: str = "Multiply two numbers and return the result"

    def execute(self, a: float, b: float) -> float:
        return a * b
```

**Tool Registry Pattern**:
```python
# In new file: app/core/ports/tool_registry.py
class IToolRegistry(ABC):
    @abstractmethod
    def get_tools(self) -> List[Any]:
        """Return list of available tools."""
        pass

    @abstractmethod
    async def execute_tool(self, tool_name: str, arguments: dict) -> Any:
        """Execute a tool by name with arguments."""
        pass
```

## Implementation Guidance

### Step-by-Step Approach

**Phase 1: Core Abstraction** (Smallest initial change)
1. Extend `ILLMProvider` interface with optional `tools` parameter
2. Create `ITool` port interface and `IToolRegistry` port
3. Add TOOL_CALL and TOOL_RESULT to MessageRole enum
4. Implement MultiplyTool as first concrete tool

**Phase 2: Provider Implementation**
1. Update `OpenAIProvider` to support `.bind_tools()`
2. Handle tool call responses vs text responses
3. Test with multiply tool
4. Replicate pattern for Anthropic, Gemini, Ollama (in that order)
5. Update provider factory tests

**Phase 3: LangGraph Integration**
1. Add `tool_calls` field to ConversationState
2. Create `execute_tools` node
3. Add conditional edge logic for tool routing
4. Update `call_llm` node to pass tools
5. Modify `format_response` to handle tool messages

**Phase 4: Streaming Support**
1. Update `call_llm_stream` to detect tool calls
2. Add WebSocket message types for tool calls/results
3. Handle buffering and parsing in stream
4. Test end-to-end streaming with tools

**Phase 5: Testing**
1. Unit tests for each provider with tools
2. Integration tests for tool execution node
3. End-to-end tests for complete tool calling flow
4. WebSocket streaming tests with tools

### Code Organization

**New Files to Create**:
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/tool_registry.py` - Tool registry interface
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/tool.py` - Tool domain model
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/tools/multiply_tool.py` - Multiply tool implementation
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/tools/tool_registry.py` - Concrete tool registry
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/execute_tools.py` - Tool execution node
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_tools.py` - Tool unit tests
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_tool_calling.py` - Tool integration tests

**Files to Modify**:
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - Add tools parameter
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/message.py` - Add tool roles
- All provider files in `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/` - Implement tool support
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - Add tool_calls field
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Add tool execution flow
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Add streaming tool support
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py` - Add tool message types
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - Handle tool messages

### Data Flow with Tool Calling

**Complete Flow Example**:
```
1. User: "What is 5 times 3?"
   -> process_input creates USER message

2. call_llm with tools=[multiply]
   -> OpenAI returns tool_call: multiply(a=5, b=3)
   -> State: tool_calls = [{"name": "multiply", "args": {"a": 5, "b": 3}}]

3. Conditional edge: has_tool_calls? -> execute_tools

4. execute_tools node
   -> Calls multiply_tool.execute(5, 3) -> 15
   -> Creates TOOL_RESULT message with result=15
   -> Adds to message history

5. Loop back to call_llm
   -> LLM sees tool result
   -> Generates text response: "5 times 3 equals 15"

6. format_response -> save_history -> END
```

## Risks and Considerations

### Provider-Specific Quirks

1. **Ollama**:
   - Tool support depends on underlying model
   - llama3.1+ supports tools, llama2 does not
   - Need graceful fallback or validation
   - Recommendation: Document supported models, validate at initialization

2. **Streaming Complexity**:
   - Tool calls arrive as complete JSON, not tokens
   - May create UX "pause" in streaming
   - Consider sending "thinking" indicator during tool execution

3. **Tool Execution Safety**:
   - Tools execute arbitrary code
   - Multiply is safe, but future tools may not be
   - Recommendation: Implement tool execution timeout, sandboxing considerations for future

4. **Error Handling**:
   - Tool execution can fail (validation, runtime errors)
   - LLM should receive error as tool result
   - Need clear error message format in TOOL_RESULT

### Performance Considerations

1. **Latency**: Tool calling adds roundtrip(s) to response time
   - Each tool call requires: LLM call -> tool execute -> LLM call
   - Multiply is fast, but consider timeout for future tools

2. **Token Usage**: Tool definitions consume tokens
   - Each tool adds ~50-200 tokens to context
   - Monitor cost impact for multiple tools

3. **Rate Limiting**: Multiple LLM calls per user message
   - Could hit provider rate limits faster
   - Existing error handling should catch this

### Architecture Preservation

**Critical**: Maintain hexagonal architecture principles:
- Tools should be defined via port interfaces
- Tool implementations are adapters
- Core domain never imports tool implementations directly
- Factory pattern for tool registry (like LLM providers)

**Good**:
```python
# Core depends on port
from app.core.ports.tool_registry import IToolRegistry

# Adapter implements port
class ToolRegistryImpl(IToolRegistry):
    pass
```

**Bad**:
```python
# Core imports adapter directly
from app.adapters.outbound.tools.multiply_tool import MultiplyTool
```

## Testing Strategy

### Unit Tests

**Provider Tool Calling**:
- Mock LangChain model with tool_calls in response
- Verify tool binding works
- Test tool call parsing and formatting
- One test suite per provider

**Tool Execution**:
- Test multiply tool with various inputs
- Test edge cases (zero, negative, large numbers)
- Test invalid input handling

**Message Conversion**:
- Test TOOL_CALL and TOOL_RESULT role handling
- Test metadata serialization/deserialization

### Integration Tests

**LangGraph Tool Flow**:
- Create test conversation
- Send message requiring tool call
- Verify: user message saved, tool executed, result message created, final response generated
- Verify message count and state transitions

**Multi-Tool Loop**:
- Test scenario where LLM calls tool multiple times
- Verify loop termination

**Provider Switching**:
- Run same tool calling test against each provider
- Verify consistent behavior across OpenAI, Anthropic, Gemini
- Mark Ollama tests with model requirements

### End-to-End Tests

**WebSocket Tool Calling**:
- Connect WebSocket client
- Send "What is 6 times 7?"
- Verify: tool_call message, tool_result message, final text tokens
- Verify complete message saved to database

**Error Scenarios**:
- Tool execution failure
- LLM returns invalid tool call
- Network error during tool execution
- Verify graceful error messages to user

### Test Data and Fixtures

**Fixtures Needed**:
- Conversation with tool calling enabled
- Mock tool registry with multiply tool
- Mock LLM responses with tool calls
- WebSocket client for streaming tests

**Example Test Cases**:
```python
async def test_multiply_tool_execution():
    """Test multiply tool executes correctly."""
    tool = MultiplyTool()
    result = await tool.execute(5, 3)
    assert result == 15

async def test_openai_provider_with_tools():
    """Test OpenAI provider handles tool calls."""
    provider = OpenAIProvider()
    messages = [Message(role=USER, content="What is 4 * 8?")]
    tools = [MultiplyTool]

    # Mock the response
    with patch.object(provider.model, 'ainvoke') as mock:
        mock.return_value.tool_calls = [
            {"name": "multiply", "args": {"a": 4, "b": 8}}
        ]
        result = await provider.generate(messages, tools)

    assert result["type"] == "tool_calls"
    assert result["tool_calls"][0]["name"] == "multiply"
```

### Testing Without API Costs

**Strategy**:
- Mock LangChain model responses at provider level
- Don't call actual LLM APIs in unit/integration tests
- Use pytest fixtures to provide consistent mock responses
- Only hit real APIs in optional E2E tests (marked with `@pytest.mark.e2e`)

**Benefit**: Fast test execution, no API costs, consistent test results.

## Dependencies

**Existing Dependencies** (already in requirements.txt):
- `langchain>=0.1.0` - Core abstractions
- `langchain-core>=0.1.0` - Message types
- `langchain-openai>=0.0.2` - OpenAI integration
- `langchain-anthropic>=0.0.1` - Anthropic integration
- `langchain-google-genai>=0.0.5` - Gemini integration

**No New Dependencies Required**: LangChain tool calling support is built-in.

**Optional Dependencies** (for advanced tool features later):
- `jsonschema` - Tool schema validation (if not using Pydantic)
- `timeout-decorator` - Tool execution timeouts

## Summary

### Key Recommendations

1. **Use LangChain's `.bind_tools()`**: Maintains provider abstraction and consistency
2. **Extend existing interface methods**: Add optional `tools` parameter to `generate()` and `stream()`
3. **Use Message.metadata for tool data**: No schema changes needed
4. **Add MessageRole.TOOL_CALL and TOOL_RESULT**: Minimal enum extension
5. **Create tool registry port**: Maintains hexagonal architecture
6. **Implement execute_tools LangGraph node**: Clean separation of concerns
7. **Start with OpenAI**: Prove pattern, then replicate to other providers
8. **Buffer tool calls in streaming**: Send complete tool call messages via WebSocket

### Critical Success Factors

- **Maintain provider abstraction**: No provider-specific code in core domain
- **Preserve backward compatibility**: Existing non-tool flows continue working
- **Test comprehensively**: Unit, integration, and E2E tests for each provider
- **Document model requirements**: Especially for Ollama
- **Handle errors gracefully**: Tool execution failures, invalid tool calls

### Next Steps for Implementation

1. Create tool port interfaces and multiply tool
2. Extend ILLMProvider with tools parameter
3. Implement in OpenAIProvider first
4. Add execute_tools LangGraph node
5. Test end-to-end with OpenAI
6. Replicate to other providers
7. Add streaming support
8. Complete test coverage

This approach provides a clean, maintainable tool calling integration that respects the existing hexagonal architecture while leveraging LangChain's provider abstraction capabilities.
