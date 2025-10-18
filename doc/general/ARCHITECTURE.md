# Architecture Overview

Genesis uses hexagonal architecture (ports and adapters) to create clean separation between business logic and infrastructure.

## Hexagonal Architecture

```
┌─────────────────────────────────────────┐
│        Inbound Adapters                 │
│   (REST API, WebSocket)                 │
│   app/adapters/inbound/                 │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│          Core Domain                    │
│                                         │
│  Domain Models ──► Ports ──► Use Cases │
│  (Entities)      (Interfaces) (Logic)  │
│                                         │
│  app/core/domain/ ports/ use_cases/    │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│       Outbound Adapters                 │
│   (MongoDB, LLM Providers)              │
│   app/adapters/outbound/                │
└─────────────────────────────────────────┘
```

## Layer Responsibilities

### Core Domain (`app/core/`)

**Pure business logic with zero infrastructure dependencies.**

- **Domain Models** (`domain/`): User, Conversation, Message entities
- **Ports** (`ports/`): Interfaces defining contracts
  - `IUserRepository`, `IConversationRepository`, `IMessageRepository`
  - `ILLMProvider`: Abstract LLM interface
  - `IAuthService`: Authentication interface
- **Use Cases** (`use_cases/`): Business logic implementations
  - `RegisterUser`, `AuthenticateUser`, `CreateConversation`, `SendMessage`

### Adapters

**Implementations of port interfaces.**

**Inbound** (`app/adapters/inbound/`):
- REST API routers (FastAPI)
- WebSocket handlers
- Translate HTTP/WebSocket to domain operations

**Outbound** (`app/adapters/outbound/`):
- **Repositories**: MongoDB implementations
  - `MongoUserRepository`, `MongoConversationRepository`, `MongoMessageRepository`
- **LLM Providers**: Multiple provider implementations
  - `OpenAIProvider`, `AnthropicProvider`, `GeminiProvider`, `OllamaProvider`
  - All implement `ILLMProvider` interface

### Infrastructure (`app/infrastructure/`)

**Cross-cutting concerns.**

- **Config**: Environment variables, settings
- **Security**: JWT authentication, password hashing
- **Database**: MongoDB connection management
- **Logging**: Centralized logging

### LangGraph (`app/langgraph/`)

**Conversation flow orchestration.**

- **State** (`state.py`): Conversation state schema
- **Nodes** (`nodes/`): Processing nodes
  - `process_user_input`: Input validation
  - `call_llm`: LLM invocation
  - `format_response`: Response formatting
  - `save_to_history`: Message persistence
- **Graphs** (`graphs/`): Flow definitions
  - `chat_graph.py`: Main conversation flow
  - `streaming_chat_graph.py`: Streaming support

## Why Hexagonal Architecture?

**Benefits:**
- ✅ **Testable**: Core logic tested without database/APIs
- ✅ **Flexible**: Easy to swap MongoDB for PostgreSQL or change LLM providers
- ✅ **Clear**: Obvious separation of concerns
- ✅ **Maintainable**: Add features without refactoring

**Trade-offs:**
- More initial setup (interfaces, adapters)
- May feel over-engineered for simple use cases

**Verdict**: Worth it for maintainable, extensible systems.

## Data Flow Examples

### User Registration
```
1. User submits form (Frontend)
   ↓
2. POST /api/auth/register (Inbound Adapter)
   ↓
3. RegisterUser.execute() (Use Case)
   ↓
4. IUserRepository.create() (Port)
   ↓
5. MongoUserRepository.create() (Outbound Adapter)
   ↓
6. MongoDB (Database)
```

### Chat Message
```
1. User sends message via WebSocket (Frontend)
   ↓
2. WebSocket handler (Inbound Adapter)
   ↓
3. LangGraph processes message
   - process_user_input node
   - call_llm node (uses ILLMProvider)
   - format_response node
   - save_to_history node (uses repositories)
   ↓
4. Stream tokens to client (WebSocket)
   ↓
5. Frontend displays streaming response
```

## Key Technology Decisions

### Why FastAPI?
- Modern async framework
- Automatic API documentation
- Type safety with Pydantic
- WebSocket support

### Why MongoDB?
- Flexible schema for evolving conversation structures
- Good performance for document-based data
- Easy nested conversation history storage
- Native async support with Beanie

**Alternative**: PostgreSQL with SQLAlchemy also works well with this architecture.

### Why LangGraph?
- Built for agentic AI workflows
- Clear state management
- Native streaming support
- Easy to extend with tools and multi-step reasoning

### Why React + TailwindCSS?
- Component-based architecture
- TypeScript support
- Fast development with Vite
- Utility-first styling

## Security

### Authentication
- JWT tokens for stateless authentication
- Bcrypt password hashing (12 rounds)
- OAuth2 password flow
- Token expiration (30 minutes default)

### Authorization
- User isolation (users only access their own data)
- Conversation ownership checks
- Protected WebSocket connections

## Extension Points

The architecture makes it easy to add:

### RAG (Retrieval-Augmented Generation)
1. Create `IVectorStore` port
2. Implement vector database adapter
3. Add retrieval node to LangGraph
4. Update use cases

### Tool Calling
1. Create `ITool` port
2. Implement tool adapters
3. Add tool nodes to LangGraph
4. Update conversation flow

### Multi-modal Support
1. Extend `Message` model for images/audio
2. Update LLM providers for multi-modal models
3. Add file upload handling
4. Update frontend components

All extensions fit naturally without modifying core business logic.
