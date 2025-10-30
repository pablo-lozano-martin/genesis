# Backend Hexagonal Architecture Analysis

## Request Summary

Analyze the backend architecture of the Orbio assignment project with focus on:
- Overall hexagonal architecture implementation
- How domain models, ports, and adapters are structured
- Key services and their responsibilities
- Dependency flow and layer boundaries
- How the conversational agent fits into the architecture

## Relevant Files & Modules

### Core Domain Layer (`backend/app/core/`)

#### Domain Models (`backend/app/core/domain/`)
- `user.py` - User entity with authentication fields (email, username, hashed_password)
- `conversation.py` - Conversation entity with metadata (user_id, title, timestamps)
- `document.py` - Document entity for knowledge base with metadata and retrieval results

#### Ports (Interfaces) (`backend/app/core/ports/`)
- `user_repository.py` - IUserRepository interface for user data operations
- `conversation_repository.py` - IConversationRepository interface for conversation metadata
- `llm_provider.py` - ILLMProvider interface for LLM operations using LangChain BaseMessage types
- `vector_store.py` - IVectorStore interface for document storage and semantic retrieval
- `auth_service.py` - IAuthService interface for authentication operations
- `transcription_service.py` - ITranscriptionService interface for speech-to-text

#### Use Cases (`backend/app/core/use_cases/`)
- `register_user.py` - RegisterUser use case with validation and password hashing
- `authenticate_user.py` - AuthenticateUser use case for login
- `create_conversation.py` - CreateConversation use case for conversation initialization

### Adapter Layer (`backend/app/adapters/`)

#### Inbound Adapters (`backend/app/adapters/inbound/`)
- `auth_router.py` - FastAPI router for authentication endpoints
- `user_router.py` - FastAPI router for user management endpoints
- `conversation_router.py` - FastAPI router for conversation CRUD endpoints
- `message_router.py` - FastAPI router for legacy message endpoints
- `websocket_router.py` - FastAPI router for WebSocket connections
- `websocket_handler.py` - WebSocket handler using LangGraph astream_events for real-time streaming
- `transcription_router.py` - FastAPI router for speech-to-text endpoints
- `message_schemas.py` - Pydantic schemas for message validation
- `websocket_schemas.py` - Pydantic schemas for WebSocket message types
- `transcription_schemas.py` - Pydantic schemas for audio transcription

#### Outbound Adapters - Repositories (`backend/app/adapters/outbound/repositories/`)
- `mongo_user_repository.py` - MongoDB implementation of IUserRepository using Beanie ODM
- `mongo_conversation_repository.py` - MongoDB implementation of IConversationRepository
- `mongo_models.py` - Beanie document models (UserDocument, ConversationDocument)

#### Outbound Adapters - LLM Providers (`backend/app/adapters/outbound/llm_providers/`)
- `openai_provider.py` - OpenAI implementation of ILLMProvider using ChatOpenAI
- `anthropic_provider.py` - Anthropic implementation using ChatAnthropic
- `gemini_provider.py` - Google Gemini implementation using ChatGoogleGenerativeAI
- `ollama_provider.py` - Ollama implementation using ChatOllama
- `provider_factory.py` - Factory function to instantiate provider based on environment config

#### Outbound Adapters - Vector Stores (`backend/app/adapters/outbound/vector_stores/`)
- `chroma_vector_store.py` - ChromaDB implementation of IVectorStore with embedding generation
- `vector_store_factory.py` - Factory function for vector store instantiation

#### Outbound Adapters - Transcription (`backend/app/adapters/outbound/transcription/`)
- `openai_whisper_service.py` - OpenAI Whisper implementation of ITranscriptionService

### Infrastructure Layer (`backend/app/infrastructure/`)

#### Configuration (`backend/app/infrastructure/config/`)
- `settings.py` - Pydantic BaseSettings for environment configuration
- `logging_config.py` - Centralized logging setup

#### Database (`backend/app/infrastructure/database/`)
- `mongodb.py` - Two database connection managers (AppDatabase for users/conversations, LangGraphDatabase for checkpoints)
- `langgraph_checkpointer.py` - AsyncMongoDBSaver factory for LangGraph state persistence
- `chromadb_client.py` - ChromaDB client singleton for vector database

#### Security (`backend/app/infrastructure/security/`)
- `auth_service.py` - Concrete implementation of IAuthService with JWT and bcrypt
- `dependencies.py` - FastAPI dependency injection for authentication
- `websocket_auth.py` - WebSocket authentication middleware

#### MCP Integration (`backend/app/infrastructure/mcp/`)
- `mcp_client_manager.py` - MCP client manager for connecting to MCP servers and discovering tools

#### Storage & Validation (`backend/app/infrastructure/`)
- `storage/temp_file_handler.py` - Temporary file handling for audio uploads
- `validation/audio_validator.py` - Audio file validation

### LangGraph Layer (`backend/app/langgraph/`)

#### State (`backend/app/langgraph/`)
- `state.py` - ConversationState schema extending LangGraph's MessagesState with onboarding fields
- `state_retrieval.py` - Utilities for retrieving state from checkpointer

#### Graphs (`backend/app/langgraph/graphs/`)
- `onboarding_graph.py` - Onboarding agent graph using create_react_agent prebuilt
- `chat_graph.py` - Generic chat graph (legacy)
- `streaming_chat_graph.py` - Streaming chat graph with tool support

#### Tools (`backend/app/langgraph/tools/`)
- `read_data.py` - Tool for reading collected onboarding data from state
- `write_data.py` - Tool for writing validated onboarding data to state with Pydantic validation
- `export_data.py` - Tool for generating conversation summary and exporting to JSON
- `rag_search.py` - Tool for semantic search in knowledge base using vector store
- `add.py` - Simple addition tool (demo)
- `multiply.py` - Simple multiplication tool (demo)
- `mcp_adapter.py` - Adapter wrapping MCP tools as Python callables

#### Prompts (`backend/app/langgraph/prompts/`)
- `onboarding_prompts.py` - System prompt for onboarding agent

#### Tool Metadata (`backend/app/langgraph/`)
- `tool_metadata.py` - Tool registry tracking tool sources (local vs MCP)

### Application Entry Point
- `backend/app/main.py` - FastAPI application setup with lifespan management for database connections and graph compilation

### Key Functions & Classes

#### Domain Use Cases
- `RegisterUser.execute()` in `register_user.py` - Orchestrates user registration with validation
- `AuthenticateUser.execute()` in `authenticate_user.py` - Validates credentials and generates JWT
- `CreateConversation.execute()` in `create_conversation.py` - Creates conversation metadata

#### Repository Implementations
- `MongoUserRepository._to_domain()` - Converts MongoDB documents to domain models
- `MongoUserRepository.create()` - Persists user with duplicate checking
- `MongoConversationRepository.create()` - Persists conversation metadata

#### LLM Provider Implementations
- `OpenAIProvider.generate()` - Invokes LLM with BaseMessage list
- `OpenAIProvider.stream()` - Streams tokens from LLM
- `OpenAIProvider.bind_tools()` - Binds tools for function calling
- `OpenAIProvider.get_model()` - Returns underlying LangChain ChatModel

#### LangGraph Components
- `create_onboarding_graph()` in `onboarding_graph.py` - Factory creating ReAct agent with tools
- `_initialize_onboarding_state()` in `onboarding_graph.py` - Pre-model hook initializing state fields
- `handle_websocket_chat()` in `websocket_handler.py` - WebSocket handler streaming LLM responses via astream_events

#### Tools
- `write_data()` - Validates and writes onboarding data to state using Command pattern
- `read_data()` - Reads collected onboarding data from state
- `export_data()` - Generates LLM summary and exports data to JSON
- `rag_search()` - Searches knowledge base and formats results for LLM

#### Infrastructure
- `MCPClientManager.initialize()` - Connects to MCP servers and discovers tools
- `get_checkpointer()` - Creates AsyncMongoDBSaver instance for state persistence
- `ChromaDBClient.initialize()` - Initializes ChromaDB client singleton

## Current Architecture Overview

The backend implements a **pure hexagonal architecture** (Ports & Adapters pattern) with a **LangGraph-first approach** for conversational AI orchestration. The architecture strictly adheres to dependency inversion: dependencies always point inward toward the domain core.

### Architectural Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                    Inbound Adapters                             │
│  FastAPI Routers + WebSocket Handler                            │
│  - Translate HTTP/WebSocket to domain operations                │
│  - auth_router, user_router, conversation_router                │
│  - websocket_handler (uses LangGraph graphs directly)           │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                    Core Domain (Pure Business Logic)            │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐        │
│  │   Domain     │   │    Ports     │   │  Use Cases   │        │
│  │   Models     │───│ (Interfaces) │───│   (Logic)    │        │
│  │              │   │              │   │              │        │
│  │ User         │   │IUserRepo     │   │RegisterUser  │        │
│  │Conversation  │   │ILLMProvider  │   │Authenticate  │        │
│  │Document      │   │IVectorStore  │   │CreateConvo   │        │
│  └──────────────┘   └──────────────┘   └──────────────┘        │
│                                                                  │
│  Zero infrastructure dependencies                               │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                  Outbound Adapters                              │
│  Implementations of Port Interfaces                             │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │  Repositories    │  │  LLM Providers   │                    │
│  │  - MongoUserRepo │  │  - OpenAI        │                    │
│  │  - MongoConvoRepo│  │  - Anthropic     │                    │
│  │                  │  │  - Gemini        │                    │
│  │  Vector Stores   │  │  - Ollama        │                    │
│  │  - ChromaDB      │  │                  │                    │
│  └──────────────────┘  └──────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   LangGraph Layer (Parallel)                    │
│  AI Orchestration with Native Checkpointing                     │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │  Graphs          │  │  Tools           │                    │
│  │  - onboarding    │  │  - write_data    │                    │
│  │  - streaming     │  │  - read_data     │                    │
│  │  - chat          │  │  - rag_search    │                    │
│  │                  │  │  - export_data   │                    │
│  └──────────────────┘  └──────────────────┘                    │
│                                                                  │
│  Uses ILLMProvider and IVectorStore ports                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                          │
│  Cross-cutting Concerns                                         │
│  - Config, Logging, Security                                    │
│  - Database connections (AppDB, LangGraphDB)                    │
│  - ChromaDB client singleton                                    │
│  - MCP client manager                                           │
└─────────────────────────────────────────────────────────────────┘
```

### Domain Core

**Philosophy**: Pure business logic with zero infrastructure dependencies.

#### Domain Models
- **User**: Authentication entity (email, username, hashed_password, metadata)
- **Conversation**: Conversation metadata entity (user_id, title, timestamps)
- **Document**: Knowledge base document with metadata and retrieval scores

All domain models use Pydantic BaseModel for validation and are completely database-agnostic.

#### Ports (Interfaces)
Ports define contracts between the domain and external concerns:

**Primary Ports (Driving Adapters - Inbound)**:
- Use cases expose domain operations to inbound adapters
- RegisterUser, AuthenticateUser, CreateConversation

**Secondary Ports (Driven Adapters - Outbound)**:
- IUserRepository - User data persistence contract
- IConversationRepository - Conversation metadata persistence
- ILLMProvider - LLM operations with LangChain BaseMessage types
- IVectorStore - Document storage and semantic retrieval
- IAuthService - Authentication operations (JWT, password hashing)
- ITranscriptionService - Speech-to-text operations

#### Use Cases
Use cases encapsulate business logic and depend ONLY on port interfaces:

- **RegisterUser**: Validates email/username uniqueness, hashes password, persists user
- **AuthenticateUser**: Validates credentials, generates JWT token
- **CreateConversation**: Creates conversation metadata for user

Use cases follow dependency inversion: they receive port implementations via constructor injection.

### Adapters

#### Inbound Adapters (REST + WebSocket)
Translate external protocols to domain operations:

- **auth_router**: POST /api/auth/register, POST /api/auth/login
- **user_router**: GET /api/users/me, PATCH /api/users/me
- **conversation_router**: POST /api/conversations, GET /api/conversations
- **websocket_router**: WebSocket endpoint for real-time chat
- **transcription_router**: POST /api/transcribe for speech-to-text

**Key Pattern**: Routers receive domain use cases via dependency injection and translate HTTP requests to domain operations.

#### Outbound Adapters (Persistence + External Services)

**Repositories**:
- **MongoUserRepository**: Implements IUserRepository using Beanie ODM
- **MongoConversationRepository**: Implements IConversationRepository

**Pattern**: Repositories translate between domain models (User, Conversation) and MongoDB documents (UserDocument, ConversationDocument).

**LLM Providers**:
- **OpenAIProvider**: Implements ILLMProvider using LangChain ChatOpenAI
- **AnthropicProvider**: Implements ILLMProvider using LangChain ChatAnthropic
- **GeminiProvider**: Implements ILLMProvider using LangChain ChatGoogleGenerativeAI
- **OllamaProvider**: Implements ILLMProvider using LangChain ChatOllama

**Pattern**: All providers wrap LangChain chat models and work with BaseMessage types (HumanMessage, AIMessage, SystemMessage). They expose get_model() to provide the underlying LangChain model for LangGraph integration.

**Vector Stores**:
- **ChromaDBVectorStore**: Implements IVectorStore for semantic search with automatic embedding generation

**Transcription**:
- **OpenAIWhisperService**: Implements ITranscriptionService using OpenAI Whisper API

### Infrastructure Layer

Infrastructure handles cross-cutting concerns WITHOUT defining business logic:

#### Database Connections
**Two-Database Pattern**:
1. **AppDatabase** (genesis_app): User accounts and conversation metadata
2. **LangGraphDatabase** (genesis_langgraph): Message history via LangGraph checkpoints

**Rationale**: Separates authorization (who owns what) from execution state (what was said).

**Connection Management**:
- `AppDatabase.connect()` - Initializes Beanie ODM with document models
- `LangGraphDatabase.connect()` - Provides Motor client for AsyncMongoDBSaver
- `get_checkpointer()` - Creates AsyncMongoDBSaver with proper context management

#### ChromaDB Client
- Singleton pattern for embedded ChromaDB client
- Manages collection lifecycle (get_or_create_collection)
- Used by ChromaDBVectorStore adapter

#### Security
- **IAuthService Implementation**: JWT generation/validation, bcrypt password hashing
- **Dependencies**: FastAPI dependency injection for route protection
- **WebSocket Auth**: Token-based WebSocket authentication

#### MCP Integration
- **MCPClientManager**: Connects to MCP servers, discovers tools, maintains sessions
- **Pattern**: Infrastructure-layer concern (not a domain port) for dynamic tool discovery

### LangGraph Layer

LangGraph orchestrates conversational AI flows **in parallel** with the domain core. It uses domain ports (ILLMProvider, IVectorStore) but implements its own execution model.

#### State Management
- **ConversationState**: Extends LangGraph's MessagesState with onboarding fields
- **Messages**: Native LangChain BaseMessage types (HumanMessage, AIMessage, SystemMessage, ToolMessage)
- **Checkpointing**: Automatic persistence to LangGraphDatabase via AsyncMongoDBSaver

#### Graphs
- **onboarding_graph**: Uses create_react_agent prebuilt for ReAct loop (Reason → Act → Observe)
- **streaming_chat_graph**: Custom graph with tool support and streaming
- **chat_graph**: Legacy generic chat graph

**Pattern**: Graphs are compiled with checkpointer and tools at application startup, not per-request.

#### Tools
Tools are simple Python functions with type hints and docstrings:

- **write_data**: Validates and writes onboarding data to state (uses Command pattern for state updates)
- **read_data**: Reads collected onboarding data from state
- **export_data**: Generates LLM summary and exports data to JSON
- **rag_search**: Searches knowledge base using IVectorStore port

**Integration**: Tools use dependency injection via InjectedState and InjectedToolCallId for state access.

#### ReAct Agent Pattern
The onboarding graph uses LangGraph's create_react_agent:

```
User Message → Process Input → LLM (Reason) → Tool Selection (Act)
                                     ↓              ↓
                                     ↓         Tool Execution
                                     ↓              ↓
                                     ↓         Observe Result
                                     ↓              ↓
                                     └──────────────┘
                                           Loop until complete
                                           ↓
                                       Final Response
```

**Key Features**:
- System prompt injection via prompt parameter
- Pre-model hook (_initialize_onboarding_state) ensures state fields are initialized
- Automatic checkpointing after each node execution
- Streaming via astream_events() for token-by-token delivery

## Impact Analysis

### Components Affected by Conversational Agent

The conversational agent (onboarding chatbot) impacts multiple architectural layers:

#### Domain Layer (Minimal Impact)
- **Conversation entity**: Stores metadata (title, user_id, timestamps)
- **Document entity**: Supports knowledge base for RAG

**Isolation**: Domain models remain unchanged by agent implementation details.

#### LangGraph Layer (Primary Impact)
- **onboarding_graph**: Core agent implementation using create_react_agent
- **ConversationState**: Extended with onboarding-specific fields (employee_name, employee_id, etc.)
- **Tools**: Agent uses write_data, read_data, export_data, rag_search for data collection
- **Prompts**: System prompt defines agent personality and data collection requirements

#### Infrastructure Layer
- **LangGraphDatabase**: Stores message history and checkpoints
- **ChromaDB**: Provides knowledge base for RAG
- **MCP Integration**: Optional external tool access

#### Adapter Layer
- **websocket_handler**: Streams agent responses via graph.astream_events()
- **Vector Store**: Used by rag_search tool for semantic search

### Data Flow: Onboarding Conversation

```
1. User connects to WebSocket (Frontend)
   ↓
2. websocket_handler authenticates user (via auth dependencies)
   ↓
3. Handler verifies conversation ownership (AppDatabase)
   ↓
4. User sends message → HumanMessage created
   ↓
5. graph.astream_events(input_data, config) invoked
   ├── config contains thread_id = conversation.id
   ├── Checkpointer loads previous state from LangGraphDatabase
   └── Agent executes ReAct loop:
       ├── LLM reasons about next action (via ILLMProvider)
       ├── Tool selected (e.g., write_data, rag_search)
       ├── Tool executes (validates data, searches knowledge base)
       ├── ToolMessage added to state
       ├── State checkpointed to LangGraphDatabase
       └── Loop continues until final response
   ↓
6. Tokens streamed to client via on_chat_model_stream events
   ↓
7. Tool executions broadcast via on_tool_start/on_tool_end events
   ↓
8. Final state automatically persisted to LangGraphDatabase
```

**Key Architectural Properties**:
- **Authorization in AppDatabase**: Conversation ownership verified before accessing LangGraph state
- **Automatic Persistence**: No manual message repository needed
- **thread_id Mapping**: conversation.id (AppDB) = thread_id (LangGraphDB) for 1:1 mapping
- **Dependency Inversion**: Agent uses ILLMProvider and IVectorStore ports, not concrete implementations

## Architectural Recommendations

### Strengths

1. **Pure Dependency Inversion**: Dependencies consistently point inward toward domain
2. **Clean Separation**: Domain models have zero infrastructure dependencies
3. **Testability**: Use cases can be tested with mock port implementations
4. **Flexibility**: Easy to swap LLM providers, databases, or vector stores
5. **LangGraph-First**: Leverages native checkpointing instead of manual message persistence
6. **Two-Database Pattern**: Clear security boundary between authorization and execution
7. **Multi-Provider LLM**: Abstract ILLMProvider enables switching providers without code changes

### Proposed Ports

No new ports needed for the current onboarding implementation. The existing ports adequately support the conversational agent.

**Future Extensions** (if needed):
- **ISchedulingService**: For calendar integration (meeting scheduling)
- **INotificationService**: For sending emails or Slack messages
- **IWorkflowService**: For triggering IT provisioning workflows

### Proposed Adapters

No new adapters needed for core onboarding functionality.

**Future Extensions**:
- **GoogleCalendarAdapter**: Implements ISchedulingService for meeting scheduling
- **SlackAdapter**: Implements INotificationService for manager notifications
- **JiraAdapter**: Implements IWorkflowService for IT ticket creation

### Domain Changes

No domain model changes required for current onboarding implementation.

**State vs. Domain**:
- Onboarding data (employee_name, employee_id, etc.) lives in **LangGraph state**, not domain models
- This is correct: onboarding data is ephemeral conversation state, not persistent domain data
- If onboarding data needs to be persisted long-term, create new domain model (e.g., OnboardingProfile) with corresponding repository

### Dependency Flow

Current dependency flow is **correct** and follows hexagonal architecture:

```
Inbound Adapters (FastAPI Routers, WebSocket Handler)
    ↓ depends on
Use Cases (RegisterUser, AuthenticateUser, CreateConversation)
    ↓ depends on
Ports (IUserRepository, ILLMProvider, IVectorStore)
    ↑ implemented by
Outbound Adapters (MongoUserRepository, OpenAIProvider, ChromaDBVectorStore)

LangGraph Layer (parallel execution path)
    ↓ depends on
Ports (ILLMProvider, IVectorStore)
    ↑ implemented by
Outbound Adapters (OpenAIProvider, ChromaDBVectorStore)
```

**Key Property**: No layer depends on layers further from the core. Infrastructure and adapters depend on ports, never the reverse.

## Implementation Guidance

### Adding New Onboarding Fields

**Step 1**: Update ConversationState schema
```python
# backend/app/langgraph/state.py
class ConversationState(MessagesState):
    # Add new field
    emergency_contact: Optional[str] = None
```

**Step 2**: Update write_data tool validation schema
```python
# backend/app/langgraph/tools/write_data.py
class OnboardingDataSchema(BaseModel):
    emergency_contact: Optional[str] = Field(None, max_length=255)
```

**Step 3**: Update system prompt to collect new field
```python
# backend/app/langgraph/prompts/onboarding_prompts.py
ONBOARDING_SYSTEM_PROMPT += """
5. emergency_contact - Emergency contact name and phone number
"""
```

No domain model changes required. Onboarding data is conversation state, not persistent domain data.

### Adding New Tool

**Step 1**: Create tool function
```python
# backend/app/langgraph/tools/new_tool.py
from langchain_core.tools import tool

@tool
async def new_tool(param: str) -> str:
    """Tool description for LLM."""
    # Implementation
    return "result"
```

**Step 2**: Export tool
```python
# backend/app/langgraph/tools/__init__.py
from .new_tool import new_tool
```

**Step 3**: Register in graph
```python
# backend/app/main.py
from app.langgraph.tools.new_tool import new_tool

onboarding_tools = [read_data, write_data, rag_search, export_data, new_tool]
```

No infrastructure changes needed. Tools are discovered at startup.

### Adding New LLM Provider

**Step 1**: Create provider implementation
```python
# backend/app/adapters/outbound/llm_providers/new_provider.py
from app.core.ports.llm_provider import ILLMProvider
from langchain_new import ChatNew

class NewProvider(ILLMProvider):
    def __init__(self):
        self.model = ChatNew(api_key=settings.new_api_key)

    async def generate(self, messages: List[BaseMessage]) -> BaseMessage:
        return await self.model.ainvoke(messages)

    # Implement other methods...
```

**Step 2**: Update provider factory
```python
# backend/app/adapters/outbound/llm_providers/provider_factory.py
def get_llm_provider() -> ILLMProvider:
    if settings.llm_provider == "new":
        return NewProvider()
    # ...
```

**Step 3**: Update settings
```python
# backend/app/infrastructure/config/settings.py
class Settings(BaseSettings):
    llm_provider: str = Field(default="openai")
    new_api_key: Optional[str] = None
```

No use case or domain changes required. Provider swap is transparent.

### Testing Strategy

**Unit Tests** (Test domain and use cases with mock ports):
```python
def test_register_user():
    mock_repo = Mock(spec=IUserRepository)
    mock_auth = Mock(spec=IAuthService)

    use_case = RegisterUser(mock_repo, mock_auth)
    result = await use_case.execute(user_data)

    # Assertions...
```

**Integration Tests** (Test adapters with real infrastructure):
```python
def test_mongo_user_repository():
    repo = MongoUserRepository()
    user = await repo.create(user_data, hashed_password)

    # Assertions...
```

**End-to-End Tests** (Test full conversation flow):
```python
async def test_onboarding_conversation():
    # Connect to WebSocket
    # Send user message
    # Verify agent responses
    # Check state persistence
```

**LangGraph Tests** (Test tool execution and state management):
```python
def test_write_data_tool():
    result = await write_data(
        field_name="employee_name",
        value="John Doe",
        state=mock_state,
        tool_call_id="test_id"
    )

    assert result.update["employee_name"] == "John Doe"
```

## Risks and Considerations

### Architectural Risks

1. **LangGraph State vs. Domain Models**
   - **Risk**: Confusion about where onboarding data lives (state vs. domain)
   - **Mitigation**: Clearly document that onboarding data is ephemeral conversation state. If data needs persistence, create domain model.

2. **Two-Database Complexity**
   - **Risk**: Coordinating operations across AppDB and LangGraphDB (e.g., cascade delete)
   - **Mitigation**: Document cascade policies. Consider implementing soft delete for conversations.

3. **Tool State Access**
   - **Risk**: Tools accessing state via InjectedState requires proper initialization
   - **Mitigation**: Use pre_model_hook in create_react_agent to ensure state fields exist before tool execution.

4. **MCP Tool Naming Conflicts**
   - **Risk**: MCP tools may have same names as local tools
   - **Mitigation**: Use namespacing (server:tool_name) or enforce unique names at registration.

5. **LLM Provider Switching**
   - **Risk**: Different providers have different capabilities (tool calling, streaming)
   - **Mitigation**: ILLMProvider abstracts common operations. Test all providers with integration tests.

### Performance Considerations

1. **WebSocket Streaming**: graph.astream_events() streams tokens efficiently but adds overhead vs. direct LLM streaming
2. **Checkpointing**: Every state update writes to LangGraphDatabase. Acceptable for conversation cadence but may be expensive for high-frequency updates.
3. **ChromaDB Embedded**: Adequate for 6 documents but may need migration to client-server mode for larger knowledge bases.
4. **MongoDB Queries**: Repository methods use Beanie find_one/find_all. Add indexes for user lookups (email, username).

### Security Considerations

1. **Authorization Boundary**: Conversation ownership ALWAYS verified in AppDatabase before accessing LangGraph state
2. **JWT Expiration**: Tokens expire after 30 minutes. WebSocket connections should handle re-authentication.
3. **Tool Execution**: Tools run with full privileges. Validate all tool inputs to prevent injection attacks.
4. **MCP Tools**: External MCP servers have full access to tool execution context. Only connect to trusted MCP servers.

### Maintainability Considerations

1. **Hexagonal Boundaries**: Preserve clean separation. Never import adapters from domain or use cases.
2. **Port Stability**: Port interfaces are contracts. Changes to ports require updating all adapters.
3. **LangGraph Updates**: create_react_agent is a prebuilt. LangGraph updates may change behavior. Pin versions in production.
4. **Tool Versioning**: Tools are discovered at startup. Changing tool signatures requires agent prompt updates.

## Testing Strategy

### Unit Tests (Domain + Use Cases)

**Test**: Business logic in isolation with mock ports

```python
# test_register_user.py
async def test_register_user_success():
    mock_repo = Mock(spec=IUserRepository)
    mock_auth = Mock(spec=IAuthService)

    mock_repo.get_by_email.return_value = None
    mock_repo.get_by_username.return_value = None
    mock_auth.hash_password.return_value = "hashed"
    mock_repo.create.return_value = User(id="123", email="test@example.com")

    use_case = RegisterUser(mock_repo, mock_auth)
    result = await use_case.execute(UserCreate(email="test@example.com", ...))

    assert result.id == "123"
    mock_repo.create.assert_called_once()
```

**Benefits**:
- Fast execution (no database)
- Tests business logic only
- Easy to test edge cases (duplicate email, validation errors)

### Integration Tests (Adapters)

**Test**: Adapter implementations with real infrastructure

```python
# test_mongo_user_repository.py
async def test_create_user():
    repo = MongoUserRepository()
    user = await repo.create(
        UserCreate(email="test@example.com", username="test"),
        hashed_password="hashed"
    )

    assert user.id is not None
    assert user.email == "test@example.com"

    # Verify duplicate protection
    with pytest.raises(ValueError):
        await repo.create(same_user_data, "hashed")
```

**Benefits**:
- Tests real database interactions
- Verifies MongoDB schema and indexes
- Catches ODM configuration issues

### LangGraph Tests (Tools + State)

**Test**: Tool execution and state management

```python
# test_write_data_tool.py
async def test_write_data_valid():
    state = {"conversation_id": "123", "user_id": "456"}

    result = await write_data(
        field_name="employee_name",
        value="John Doe",
        state=state,
        tool_call_id="test_id"
    )

    assert isinstance(result, Command)
    assert result.update["employee_name"] == "John Doe"
    assert "Successfully recorded" in result.update["messages"][0].content

async def test_write_data_invalid_field():
    result = await write_data(
        field_name="invalid_field",
        value="value",
        state={},
        tool_call_id="test_id"
    )

    assert "Unknown field" in result.update["messages"][0].content
```

**Benefits**:
- Tests tool validation logic
- Verifies Command pattern usage
- Catches state update issues

### End-to-End Tests (Full Conversation Flow)

**Test**: Complete conversation from WebSocket to database

```python
# test_onboarding_flow.py
async def test_complete_onboarding():
    async with TestClient(app) as client:
        # Register user
        auth_response = await client.post("/api/auth/register", json={...})
        token = auth_response.json()["access_token"]

        # Create conversation
        convo_response = await client.post(
            "/api/conversations",
            headers={"Authorization": f"Bearer {token}"}
        )
        conversation_id = convo_response.json()["id"]

        # Connect to WebSocket
        async with client.websocket_connect(
            f"/api/ws/chat?token={token}"
        ) as websocket:
            # Send messages
            await websocket.send_json({
                "type": "message",
                "conversation_id": conversation_id,
                "content": "My name is John Doe"
            })

            # Receive streamed tokens
            tokens = []
            while True:
                message = await websocket.receive_json()
                if message["type"] == "token":
                    tokens.append(message["content"])
                elif message["type"] == "complete":
                    break

            # Verify agent collected data
            # Check state in LangGraphDB
```

**Benefits**:
- Tests full request-to-response flow
- Verifies WebSocket streaming
- Catches integration issues between layers

### Testing Hexagonal Boundaries

**Test**: Verify no layer depends on inner layers

```python
# test_architecture.py
def test_domain_has_no_infrastructure_imports():
    """Domain models should not import from infrastructure."""
    for file in Path("app/core/domain").glob("*.py"):
        content = file.read_text()
        assert "from app.infrastructure" not in content
        assert "from app.adapters" not in content

def test_use_cases_depend_only_on_ports():
    """Use cases should only import from domain and ports."""
    for file in Path("app/core/use_cases").glob("*.py"):
        content = file.read_text()
        assert "from app.adapters" not in content
        assert "from app.infrastructure" not in content
```

**Benefits**:
- Enforces architectural boundaries
- Prevents dependency violations
- Catches accidental imports during development

## Summary

### Key Architectural Characteristics

1. **Hexagonal Architecture**: Pure implementation with clean separation between domain, ports, and adapters
2. **Dependency Inversion**: All dependencies point inward toward domain core
3. **LangGraph-First**: Conversational AI orchestration with native checkpointing
4. **Two-Database Pattern**: Clear security boundary between authorization and execution
5. **Multi-Provider LLM**: Abstract ILLMProvider enables provider flexibility
6. **Tool-Based Agent**: ReAct pattern with read_data, write_data, export_data, rag_search tools
7. **RAG Integration**: Vector store port enables semantic search in knowledge base
8. **MCP Support**: Optional external tool discovery via MCP protocol

### Key Dependencies

- **Domain → Ports**: Use cases depend on port interfaces (IUserRepository, ILLMProvider)
- **Adapters → Ports**: Adapters implement port interfaces
- **Infrastructure → Adapters**: Infrastructure provides adapter instances
- **LangGraph → Ports**: Graphs use ILLMProvider and IVectorStore via tools
- **WebSocket Handler → LangGraph**: Handler streams graph responses via astream_events

### Architectural Pitfalls to Avoid

1. **Domain Coupling**: NEVER import adapters or infrastructure from domain or use cases
2. **Port Bypass**: NEVER call adapters directly. Always use port interfaces.
3. **State Confusion**: Onboarding data lives in LangGraph state, not domain models. If data needs persistence, create domain model.
4. **Manual Checkpointing**: LangGraph handles checkpointing automatically. Don't create message repositories.
5. **Tool State Access**: Always use InjectedState annotation. Never access state globally.
6. **Provider Leakage**: Never expose provider-specific types in port interfaces. Use LangChain BaseMessage types.

### Success Criteria for Future Changes

Any change should:
1. ✅ Maintain dependency direction (inward toward domain)
2. ✅ Keep domain models infrastructure-agnostic
3. ✅ Use port interfaces instead of concrete implementations
4. ✅ Leverage LangGraph checkpointing instead of manual persistence
5. ✅ Test business logic with mock ports (unit tests)
6. ✅ Test adapters with real infrastructure (integration tests)
7. ✅ Preserve clear boundaries between layers

The architecture is **production-ready** and demonstrates excellent adherence to hexagonal architecture principles. The conversational agent integrates cleanly via LangGraph without compromising architectural integrity.
