# LLM Integration Analysis

## Request Summary

Analyze the LLM integration implementation in the Orbio onboarding chatbot assignment. This analysis examines which LLM provider(s) are used and why, how LangGraph is integrated for conversation flow, prompt engineering strategies and patterns, how conversation state is managed, and the overall integration architecture with key design decisions.

## Relevant Files & Modules

### Files to Examine

#### LLM Provider Abstraction (Hexagonal Architecture - Ports)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - Abstract interface (ILLMProvider) defining the contract for all LLM operations using LangChain BaseMessage types

#### LLM Provider Implementations (Hexagonal Architecture - Adapters)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/provider_factory.py` - Factory pattern for creating provider instances based on LLM_PROVIDER environment variable
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/openai_provider.py` - OpenAI implementation (ChatOpenAI from langchain-openai)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/anthropic_provider.py` - Anthropic/Claude implementation (ChatAnthropic from langchain-anthropic)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/gemini_provider.py` - Google Gemini implementation (ChatGoogleGenerativeAI from langchain-google-genai)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/ollama_provider.py` - Ollama implementation for local models (ChatOllama from langchain-community)

#### LangGraph State Management
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - ConversationState schema extending LangGraph's native MessagesState with onboarding fields
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/langgraph_checkpointer.py` - AsyncMongoDBSaver factory for state persistence

#### LangGraph Graphs
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/onboarding_graph.py` - Onboarding agent using LangGraph's create_react_agent prebuilt
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Streaming chat graph with custom ReAct loop
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Standard chat graph with tool execution

#### LangGraph Nodes (Custom ReAct Implementation)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - Node for invoking LLM provider with tool binding
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/process_input.py` - Node for validating and creating HumanMessage from user input

#### Prompt Engineering
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/prompts/onboarding_prompts.py` - System prompt for onboarding ReAct agent with detailed tool usage instructions

#### LangGraph Tools
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/read_data.py` - Tool for querying collected onboarding fields from state
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/write_data.py` - Tool for writing validated data to state with Pydantic validation
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/export_data.py` - Tool for finalizing onboarding with LLM-generated summary
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/rag_search.py` - Tool for semantic search in ChromaDB knowledge base

#### API Layer (Inbound Adapters)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket handler for real-time streaming using graph.astream_events()
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/transcription_router.py` - Speech-to-text endpoint using OpenAI Whisper API

#### Configuration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py` - Pydantic settings for LLM provider configuration (API keys, models, endpoints)
- `/Users/pablolozano/Mac Projects August/genesis/backend/requirements.txt` - Python dependencies including LangChain/LangGraph and provider-specific packages

#### RAG Knowledge Base
- `/Users/pablolozano/Mac Projects August/genesis/backend/knowledge_base/` - Directory containing 6 company documents for RAG
  - `benefits_and_perks.md` - Employee benefits information
  - `starter_kit_options.md` - Hardware choices
  - `office_locations.md` - Office access information
  - `it_setup_guide.md` - Technology setup
  - `onboarding_schedule.md` - First 90 days timeline
  - `company_culture.md` - Culture and values

#### Testing
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_llm_providers.py` - Unit tests for LLM provider implementations

### Key Functions & Classes

#### Core Abstractions
- `ILLMProvider` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - Abstract base class defining generate(), stream(), bind_tools(), get_model()
- `LLMProviderFactory.create_provider()` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/provider_factory.py` - Factory method for provider instantiation

#### Provider Implementations
- `OpenAIProvider`, `AnthropicProvider`, `GeminiProvider`, `OllamaProvider` - Concrete implementations of ILLMProvider using LangChain chat models

#### State Management
- `ConversationState` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - Extends MessagesState with onboarding fields
- `get_checkpointer()` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/langgraph_checkpointer.py` - Factory for AsyncMongoDBSaver

#### Graph Creation
- `create_onboarding_graph()` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/onboarding_graph.py` - Creates ReAct agent using create_react_agent prebuilt
- `_initialize_onboarding_state()` in same file - Pre-model hook for initializing custom state fields

#### Streaming & Invocation
- `handle_websocket_chat()` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket handler using graph.astream_events() for token-by-token streaming

## Current Integration Overview

### Provider Abstraction

The system implements a clean hexagonal architecture separating LLM concerns:

**Port Interface (ILLMProvider)**:
- Defines provider-agnostic contract for LLM operations
- Uses LangChain BaseMessage types (HumanMessage, AIMessage, SystemMessage, ToolMessage)
- Methods:
  - `generate(messages)` - Non-streaming response generation
  - `stream(messages)` - Async generator for token-by-token streaming
  - `bind_tools(tools)` - Attach callable tools for function calling
  - `get_model()` - Expose underlying LangChain model for LangGraph integration
  - `get_model_name()` - Return model identifier string

**Factory Pattern**:
- `LLMProviderFactory.create_provider()` reads `settings.llm_provider` and instantiates the appropriate concrete implementation
- Supports: `"openai"`, `"anthropic"`, `"gemini"`, `"ollama"`
- Lazy imports prevent loading unused provider dependencies

### Provider Implementations

All four providers follow identical structure:

**OpenAI (Default for Orbio Assignment)**:
- Model: `ChatOpenAI` from `langchain-openai`
- Configuration: `OPENAI_API_KEY`, `OPENAI_MODEL` (default: `gpt-4-turbo-preview`)
- Features: Streaming enabled, temperature=0.7, tool calling support
- Use case: Production deployment (assignment uses OpenAI)

**Anthropic (Claude)**:
- Model: `ChatAnthropic` from `langchain-anthropic`
- Configuration: `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` (default: `claude-3-sonnet-20240229`)
- Features: Streaming enabled, temperature=0.7, tool calling support
- Use case: Alternative production provider with strong reasoning capabilities

**Google Gemini**:
- Model: `ChatGoogleGenerativeAI` from `langchain-google-genai`
- Configuration: `GOOGLE_API_KEY`, `GOOGLE_MODEL` (default: `gemini-pro`)
- Features: Streaming enabled, temperature=0.7, tool calling support
- Use case: Alternative production provider, cost optimization

**Ollama (Local)**:
- Model: `ChatOllama` from `langchain-community`
- Configuration: `OLLAMA_BASE_URL` (default: `http://localhost:11434`), `OLLAMA_MODEL` (default: `llama2`)
- Features: Temperature=0.7, tool calling support (streaming handled by LangChain)
- Use case: Development/testing without API costs, on-premise deployments

### Configuration Management

**Pydantic Settings** (`Settings` class):
- Environment-based configuration via `.env` file
- Required settings:
  - `LLM_PROVIDER` - Provider selection (openai/anthropic/gemini/ollama)
  - Provider-specific API keys (conditional validation)
  - Model names for each provider
- Optional settings:
  - Temperature, streaming, tool calling behavior (hardcoded in implementations)

**Configuration Flow**:
1. `.env` file loaded by Pydantic Settings
2. `LLMProviderFactory.create_provider()` reads `settings.llm_provider`
3. Provider constructor validates required settings (raises ValueError if API key missing)
4. LangChain model instantiated with provider-specific configuration

### Request/Response Handling

**Message Flow (LangGraph-First Architecture)**:
1. User input arrives via WebSocket as JSON
2. `handle_websocket_chat()` creates `HumanMessage(content=user_input)`
3. Graph invoked with `input_data = {"messages": [human_message], ...}`
4. LangGraph automatically manages message history via MessagesState
5. `call_llm` node (or create_react_agent prebuilt) invokes `llm_provider.generate(messages)`
6. LLM returns `AIMessage` (with optional tool_calls)
7. LangGraph appends AIMessage to state.messages
8. If tool_calls present, ToolNode executes tools and returns ToolMessage
9. Loop continues until no more tool calls
10. Final AIMessage content streamed to client

**Streaming Flow**:
- WebSocket handler uses `graph.astream_events(input_data, config, version="v2")`
- Events captured:
  - `on_chat_model_stream` - Token chunks from LLM (chunk.content)
  - `on_chat_model_end` - Detect tool_calls in AIMessage
  - `on_tool_start` - Tool execution begins
  - `on_tool_end` - Tool execution completes
- Each token sent as `ServerTokenMessage` to client
- Checkpointing happens automatically after graph execution

**Tool Binding**:
- Tools defined as LangChain @tool decorated functions
- `llm_provider.bind_tools(tools, parallel_tool_calls=False)` creates bound model
- Bound model passed to graph invocation
- LangChain handles tool schema generation and parsing

## Impact Analysis

This analysis focuses on understanding the current implementation rather than proposing changes. The key integration components are:

**Provider Abstraction Layer**:
- Clean separation between domain logic and LLM provider specifics
- Easy to add new providers (implement ILLMProvider interface)
- Testable via mock providers

**LangGraph Integration**:
- Two approaches used:
  1. **create_react_agent prebuilt** (onboarding_graph.py) - Simplified implementation
  2. **Custom StateGraph** (chat_graph.py, streaming_chat_graph.py) - Explicit control
- Both share common state management via ConversationState

**State Persistence**:
- MongoDB-backed checkpointing via AsyncMongoDBSaver
- Automatic message history persistence
- Custom state fields (onboarding data) persisted alongside messages

**Streaming Architecture**:
- Token-by-token streaming via graph.astream_events()
- WebSocket transport for real-time updates
- Tool execution events exposed to frontend

**RAG Integration**:
- ChromaDB embedded mode for vector storage
- Sentence transformers for embeddings
- rag_search tool provides semantic knowledge base access
- 6 company documents chunked and indexed

**Speech-to-Text**:
- OpenAI Whisper API for transcription
- Separate endpoint from LLM provider
- Auth-protected with conversation ownership validation

## LLM Integration Recommendations

### Current Architecture Strengths

**1. Clean Provider Abstraction**:
- Hexagonal architecture properly separates concerns
- ILLMProvider port defines clear contract
- Factory pattern enables runtime provider switching
- All providers use LangChain models for consistency

**2. LangGraph-First Design**:
- Native MessagesState integration
- Automatic message history management
- Built-in checkpointing reduces boilerplate
- create_react_agent prebuilt simplifies ReAct implementation

**3. Tool Architecture**:
- @tool decorators provide clean interface
- InjectedState enables tools to access graph state
- Command return type allows tools to update state
- Pydantic validation in write_data ensures data quality

**4. Streaming Implementation**:
- graph.astream_events() provides fine-grained event access
- WebSocket protocol handles real-time delivery
- Tool execution visibility improves UX transparency

### Proposed Interfaces

No new interfaces needed. Current abstractions are well-designed:

**ILLMProvider** covers all necessary operations:
- `generate()` - Synchronous completion
- `stream()` - Token streaming
- `bind_tools()` - Tool attachment
- `get_model()` - LangGraph compatibility
- `get_model_name()` - Model identification

**ConversationState** appropriately extends MessagesState:
- Inherits messages field with add_messages reducer
- Adds onboarding-specific fields
- remaining_steps field required by create_react_agent

### Proposed Implementations

Current implementations are production-ready. Potential enhancements:

**1. Provider Fallback Strategy**:
- Add fallback provider if primary fails
- Implement retry logic with exponential backoff
- Log provider failures for monitoring

**2. Cost Tracking**:
- Track token usage per conversation
- Log model usage for cost attribution
- Implement budget limits per user/conversation

**3. Prompt Caching**:
- Leverage provider-specific prompt caching (Anthropic, OpenAI)
- Cache system prompt across invocations
- Reduce latency and costs for repeated prompts

**4. Provider-Specific Optimizations**:
- Use Anthropic's extended thinking mode for complex reasoning
- Leverage OpenAI's structured outputs for data extraction
- Implement model-specific temperature tuning

### Configuration Changes

Current configuration is adequate. Potential additions:

**Environment Variables**:
- `LLM_TEMPERATURE` - Make temperature configurable (currently hardcoded to 0.7)
- `LLM_MAX_TOKENS` - Set response length limits
- `LLM_TIMEOUT` - Request timeout configuration
- `LLM_FALLBACK_PROVIDER` - Backup provider on failure

**MongoDB Connection Pooling**:
- `MONGODB_LANGGRAPH_POOL_SIZE` - Optimize checkpoint operations
- `MONGODB_LANGGRAPH_MAX_IDLE_TIME` - Connection lifecycle management

### Data Flow

**Current Onboarding Flow**:

```
User (WebSocket)
    ↓
[ClientMessage] → handle_websocket_chat()
    ↓
Create HumanMessage(content)
    ↓
graph.astream_events({messages: [HumanMessage], ...}, config)
    ↓
create_react_agent loop:
    ↓
1. _initialize_onboarding_state (pre-model hook)
    ↓
2. System prompt injection (ONBOARDING_SYSTEM_PROMPT)
    ↓
3. LLM invocation (llm_provider.get_model().ainvoke(messages))
    ↓
4. AIMessage returned (with optional tool_calls)
    ↓
5. If tool_calls present:
    → ToolNode executes tool (read_data/write_data/rag_search/export_data)
    → Tool returns Command(update={...}) or ToolMessage
    → State updated
    → Loop back to step 3
    ↓
6. If no tool_calls:
    → Final AIMessage content streamed to client
    → Checkpointer persists state to MongoDB
    ↓
[ServerTokenMessage, ServerCompleteMessage] → User
```

**Tool Execution Cycle**:

```
AIMessage.tool_calls → [{"name": "write_data", "args": {"field_name": "employee_name", "value": "John"}}]
    ↓
ToolNode extracts tool_calls
    ↓
Invoke write_data(field_name="employee_name", value="John", state=<injected>, tool_call_id=<injected>)
    ↓
Pydantic validation via OnboardingDataSchema
    ↓
If valid:
    → Return Command(update={employee_name: "John", messages: [ToolMessage(...)]})
If invalid:
    → Return Command(update={messages: [ToolMessage(error_msg)]})
    ↓
LangGraph merges update into state
    ↓
Loop continues with updated state
```

**RAG Search Flow**:

```
User asks "What are the benefits?"
    ↓
LLM decides to call rag_search tool
    ↓
AIMessage.tool_calls → [{"name": "rag_search", "args": {"query": "employee benefits"}}]
    ↓
rag_search(query="employee benefits")
    ↓
app.state.vector_store.retrieve(query, top_k=5)
    ↓
ChromaDB semantic search → Returns documents with similarity scores
    ↓
Format results as string with source, relevance, content
    ↓
Return formatted_results
    ↓
LLM receives ToolMessage(content=formatted_results)
    ↓
LLM generates AIMessage incorporating retrieved context
```

## Implementation Guidance

### For Adding New Provider

1. Create new file: `backend/app/adapters/outbound/llm_providers/{provider}_provider.py`
2. Implement ILLMProvider interface:
   - Import appropriate LangChain chat model (e.g., ChatCohere, ChatHuggingFace)
   - Implement `__init__()` with configuration validation
   - Implement `generate()` using `self.model.ainvoke(messages)`
   - Implement `stream()` using `self.model.astream(messages)`
   - Implement `bind_tools()` using `self.model.bind_tools(tools)`
   - Implement `get_model()` returning `self.model`
   - Implement `get_model_name()` returning model string
3. Add provider to factory in `provider_factory.py`:
   ```python
   elif provider_name == "newprovider":
       from app.adapters.outbound.llm_providers.newprovider_provider import NewProvider
       return NewProvider()
   ```
4. Add configuration to `settings.py`:
   ```python
   newprovider_api_key: Optional[str] = None
   newprovider_model: str = "default-model"
   ```
5. Add dependency to `requirements.txt`:
   ```
   langchain-newprovider>=0.0.1
   ```
6. Update `.env.example` with new provider settings
7. Write unit tests in `tests/unit/test_llm_providers.py`

### For Modifying Prompt Engineering

1. Locate prompt in `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/prompts/onboarding_prompts.py`
2. Edit `ONBOARDING_SYSTEM_PROMPT` string:
   - Keep clear structure (responsibilities, tools, flow, critical instructions)
   - Use explicit tool calling instructions (avoid ambiguity)
   - Include validation error handling guidance
   - Specify completion criteria clearly
3. Test prompt changes:
   - Run manual conversation tests
   - Verify tool calling behavior
   - Check error handling scenarios
4. No code changes needed - prompt is passed to create_react_agent at graph creation

### For Adding New Tools

1. Create new file: `backend/app/langgraph/tools/{tool_name}.py`
2. Define tool function:
   ```python
   from langchain_core.tools import tool
   from langgraph.prebuilt import InjectedState
   from typing import Annotated, Dict, Any

   @tool
   def my_tool(
       param: str,
       state: Annotated[Dict[str, Any], InjectedState]
   ) -> str:
       """Clear docstring describing tool purpose and parameters."""
       # Tool logic here
       return result
   ```
3. Import tool in graph creation:
   ```python
   from app.langgraph.tools.my_tool import my_tool
   tools = [read_data, write_data, rag_search, export_data, my_tool]
   ```
4. Update system prompt to document new tool
5. Write unit tests for tool behavior

### For Optimizing RAG

1. Adjust retrieval settings in `.env`:
   - `RETRIEVAL_TOP_K` - Increase for more context (default: 5)
   - `RETRIEVAL_SIMILARITY_THRESHOLD` - Raise for stricter matches (default: 0.5)
   - `RETRIEVAL_CHUNK_SIZE` - Adjust chunk granularity (default: 512)
2. Re-chunk documents if needed:
   - Delete `backend/chroma_db/` directory
   - Run `python scripts/ingest_documents.py knowledge_base/`
3. Test retrieval quality:
   - Run manual queries via `test_orbio_rag.py`
   - Verify similarity scores and relevance

### For Implementing Streaming

Streaming is already implemented. To add streaming to a new endpoint:

1. Use `graph.astream_events(input_data, config, version="v2")`
2. Filter events by type:
   - `on_chat_model_stream` - LLM tokens
   - `on_tool_start` - Tool execution begins
   - `on_tool_end` - Tool execution completes
3. Send events via WebSocket:
   ```python
   async for event in graph.astream_events(input_data, config, version="v2"):
       if event["event"] == "on_chat_model_stream":
           chunk = event["data"]["chunk"]
           if chunk.content:
               await websocket.send_json({"type": "token", "content": chunk.content})
   ```
4. Use Pydantic schemas from `websocket_schemas.py` for message validation

## Risks and Considerations

### LLM Provider Risks

**1. API Rate Limiting**:
- OpenAI: 3,500 requests/min (Tier 1), 10,000 tokens/min
- Anthropic: 50 requests/min (default), 100,000 tokens/min
- Google: 60 requests/min (default)
- **Mitigation**: Implement retry with exponential backoff, consider provider fallback

**2. Cost Management**:
- gpt-4-turbo-preview: $10/1M input tokens, $30/1M output tokens
- claude-3-sonnet: $3/1M input tokens, $15/1M output tokens
- gemini-pro: $0.50/1M input tokens, $1.50/1M output tokens
- **Mitigation**: Track token usage, set budget alerts, use caching

**3. Provider Outages**:
- Single provider dependency creates availability risk
- **Mitigation**: Implement fallback provider, graceful degradation

### LangGraph Checkpointing Risks

**1. MongoDB Performance**:
- Checkpoint writes on every graph invocation
- Large conversation histories increase storage and retrieval time
- **Mitigation**: Connection pooling, index optimization, conversation archival

**2. State Consistency**:
- Custom state fields must be initialized before tool access
- Missing initialization causes tool errors
- **Mitigation**: Use pre_model_hook (_initialize_onboarding_state) to ensure defaults

### RAG Performance Risks

**1. Embedding Costs**:
- ChromaDB uses sentence-transformers (local, no API cost)
- Switching to OpenAI embeddings: $0.13/1M tokens
- **Mitigation**: Current setup uses free local embeddings

**2. Retrieval Quality**:
- Chunk size affects context coherence
- Too small: fragmented context; too large: irrelevant content
- **Mitigation**: Test with various chunk sizes (current: 512 words is reasonable)

### Tool Calling Risks

**1. Tool Hallucination**:
- LLM may invent non-existent tools or parameters
- **Mitigation**: Clear system prompt instructions, validate tool calls

**2. Validation Failures**:
- write_data validation may fail repeatedly
- **Mitigation**: Prompt includes retry guidance, error messages guide LLM

**3. Infinite Loops**:
- Agent may get stuck in tool calling loop
- **Mitigation**: create_react_agent has built-in max_iterations (default: 25)

### Security Risks

**1. Prompt Injection**:
- User input could attempt to override system prompt
- **Mitigation**: LangGraph separates system prompt from user messages

**2. Data Leakage**:
- Conversation data sent to third-party LLM providers
- **Mitigation**: Use Ollama for sensitive deployments, implement data sanitization

**3. API Key Exposure**:
- API keys stored in environment variables
- **Mitigation**: Use secrets management (AWS Secrets Manager, HashiCorp Vault)

## Testing Strategy

### Unit Tests

**LLM Provider Tests** (`test_llm_providers.py`):
- Mock LangChain models to avoid API calls
- Test generate() returns AIMessage
- Test stream() yields tokens
- Test bind_tools() returns bound provider
- Test get_model() returns correct type
- Test error handling (missing API key, network failures)

**Tool Tests**:
- Test read_data returns formatted field values
- Test write_data validates and updates state
- Test export_data generates summary and saves JSON
- Test rag_search retrieves relevant documents
- Use mock InjectedState for state access

### Integration Tests

**Graph Execution Tests**:
- Test complete onboarding flow with mock LLM
- Verify state transitions (fields collected sequentially)
- Test tool execution and state updates
- Test error recovery (validation failures)

**RAG Pipeline Tests**:
- Ingest test documents
- Query knowledge base
- Verify retrieval quality (similarity scores)
- Test chunk overlap and context coherence

**Streaming Tests**:
- Mock graph.astream_events()
- Verify token streaming behavior
- Test tool event emission
- Test WebSocket message formatting

### End-to-End Tests

**Manual Conversation Tests**:
- Complete full onboarding conversation
- Test RAG-powered question answering
- Test validation error handling
- Test export_data finalization

**Speech-to-Text Tests**:
- Record audio in browser
- Verify transcription accuracy
- Test with various audio formats (webm, wav, mp3)
- Test file size limits and error messages

### Mock Strategies

**Mock LLM Provider**:
```python
class MockLLMProvider(ILLMProvider):
    async def generate(self, messages):
        # Return predefined AIMessage with tool_calls
        return AIMessage(
            content="Mock response",
            tool_calls=[{"name": "write_data", "args": {"field_name": "employee_name", "value": "Test"}}]
        )
```

**Mock Vector Store**:
```python
class MockVectorStore:
    async def retrieve(self, query, top_k):
        # Return predefined documents
        return [
            RetrievalResult(
                document=Document(content="Mock content", metadata={"source": "test.md"}),
                similarity_score=0.95
            )
        ]
```

**Fixture Data**:
- Sample conversation states with partial onboarding data
- Example RAG documents for retrieval testing
- Predefined tool call sequences for graph execution

### Testing Checklist

- [ ] All providers tested with mocks (no real API calls)
- [ ] All tools tested with injected state
- [ ] Graph execution tested end-to-end
- [ ] RAG retrieval tested with sample documents
- [ ] Streaming events tested via astream_events()
- [ ] Validation logic tested (Pydantic schemas)
- [ ] Error handling tested (API failures, validation errors)
- [ ] WebSocket protocol tested (message schemas)
- [ ] Speech-to-text tested with sample audio
- [ ] Checkpointing tested (state persistence and retrieval)

## Key Architectural Insights

### Why LangGraph with create_react_agent?

**Decision**: Use LangGraph's prebuilt create_react_agent for onboarding graph

**Rationale**:
- Reduces boilerplate (no need for process_input, inject_system_prompt, call_llm nodes)
- Built-in ReAct loop (reason → act → repeat)
- Automatic system prompt injection via `prompt` parameter
- Streaming support maintained via astream_events()
- Production-tested by LangGraph team

**Trade-offs**:
- Less control over node execution order
- Requires understanding of LangGraph prebuilt internals
- Custom state fields need pre_model_hook initialization
- Balanced by simpler implementation and faster development

### Why Hexagonal Architecture for LLM Providers?

**Decision**: Abstract LLM providers behind ILLMProvider port interface

**Rationale**:
- Domain logic doesn't depend on specific LLM provider
- Easy to swap providers (change environment variable)
- Testable with mock providers (no API costs)
- Future-proof (add new providers without changing core logic)

**Trade-offs**:
- Additional abstraction layer
- Need to maintain multiple provider implementations
- Worth it for operational flexibility and testability

### Why MongoDB for LangGraph Checkpoints?

**Decision**: Use AsyncMongoDBSaver for conversation state persistence

**Rationale**:
- LangGraph official MongoDB integration
- Async support for FastAPI compatibility
- Automatic state serialization/deserialization
- Scales with existing MongoDB infrastructure

**Trade-offs**:
- Additional MongoDB database (separate from app DB)
- Checkpoint write overhead on every graph invocation
- Justified by clean separation and LangGraph native support

### Why ChromaDB Embedded Mode?

**Decision**: Use ChromaDB in embedded mode for RAG

**Rationale**:
- No separate service required (simpler deployment)
- File-based persistence (good for MVP)
- Strong performance for 6-document knowledge base
- Free local embeddings (sentence-transformers)

**Trade-offs**:
- Embedded mode limits multi-process scaling
- Less advanced features than production vector DBs
- Sufficient for current scale, migration path available

### Why Multi-Provider Support?

**Decision**: Support OpenAI, Anthropic, Gemini, and Ollama

**Rationale**:
- Operational flexibility (switch providers for cost/quality)
- Risk mitigation (provider outages, API changes)
- Development efficiency (Ollama for local testing)
- Customer choice (self-hosted vs. cloud)

**Trade-offs**:
- Maintain four provider implementations
- Test across all providers
- Worth it for reduced vendor lock-in

## Summary

Pablo, the Orbio onboarding chatbot demonstrates a well-architected LLM integration using LangGraph and a multi-provider abstraction layer. The implementation follows hexagonal architecture principles with clean separation between domain logic, ports, and adapters.

**Key Strengths**:
1. **Provider Abstraction**: ILLMProvider port enables easy provider switching (OpenAI, Anthropic, Gemini, Ollama)
2. **LangGraph Integration**: create_react_agent prebuilt simplifies ReAct implementation while maintaining streaming support
3. **State Management**: ConversationState extends MessagesState with onboarding fields, persisted via MongoDB checkpoints
4. **Prompt Engineering**: Clear system prompt with explicit tool usage instructions and validation error handling
5. **Tool Architecture**: Clean @tool decorators with InjectedState for state access and Command return types for state updates
6. **RAG Implementation**: ChromaDB provides semantic search over 6 company documents with sentence-transformers embeddings
7. **Streaming**: graph.astream_events() enables token-by-token delivery via WebSocket with tool execution visibility

**Architecture Highlights**:
- **Hexagonal Architecture**: Core domain isolated from LLM provider specifics
- **LangGraph-First**: Native MessagesState integration, automatic checkpointing, built-in tool execution
- **Two-Database Pattern**: Separate MongoDB instances for app data and LangGraph checkpoints
- **Multi-Provider Support**: Four LLM providers with identical interfaces

**Integration Flow**:
1. User sends message via WebSocket
2. HumanMessage created and passed to graph
3. create_react_agent runs ReAct loop (LLM → tools → LLM)
4. Tools update state (read_data, write_data, rag_search, export_data)
5. Tokens streamed to client via astream_events()
6. State persisted to MongoDB automatically

The implementation is production-ready with comprehensive error handling, validation, and testing. The architecture provides excellent extensibility for adding new providers, tools, or features while maintaining clean separation of concerns.
