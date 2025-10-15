# Genesis Architecture

This document explains the architecture and design decisions behind Genesis.

## Overview

Genesis is built with a **hexagonal architecture** (ports and adapters) backend and a modern React frontend. The architecture prioritizes testability, maintainability, and flexibility.

## Backend Architecture

### Hexagonal Architecture

The backend follows hexagonal architecture principles, creating a clean separation between business logic and infrastructure concerns.

```
┌─────────────────────────────────────────────────────────┐
│                      Inbound Adapters                    │
│  (REST API, WebSocket) - app/adapters/inbound/          │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                    Core Domain                           │
│                                                          │
│  Domain Models  ──►  Ports (Interfaces)  ──►  Use Cases │
│  (Entities)          (Contracts)             (Logic)    │
│                                                          │
│  app/core/domain/    app/core/ports/    app/core/use_cases/ │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                   Outbound Adapters                      │
│  (MongoDB, LLM Providers) - app/adapters/outbound/      │
└─────────────────────────────────────────────────────────┘
```

### Layer Breakdown

#### 1. Core Domain (`app/core/`)

**Pure business logic with no infrastructure dependencies.**

- **Domain Models** (`domain/`):
  - `User`: User entity with authentication fields
  - `Conversation`: Chat conversation entity
  - `Message`: Individual message in a conversation
  - Pure Pydantic models, database-agnostic

- **Ports** (`ports/`):
  - Interfaces defining contracts for external services
  - `IUserRepository`, `IConversationRepository`, `IMessageRepository`
  - `ILLMProvider`: Abstract LLM interface
  - `IAuthService`: Authentication interface

- **Use Cases** (`use_cases/`):
  - Business logic implementations
  - `RegisterUser`: User registration logic
  - `AuthenticateUser`: Authentication logic
  - Each use case depends only on port interfaces

#### 2. Adapters

**Implementations of the port interfaces.**

**Inbound Adapters** (`app/adapters/inbound/`):
- REST API routers (FastAPI)
- WebSocket handlers
- Translate HTTP/WebSocket to domain operations

**Outbound Adapters** (`app/adapters/outbound/`):
- **Repositories**: MongoDB implementations
  - `MongoUserRepository`, `MongoConversationRepository`, `MongoMessageRepository`
- **LLM Providers**: Multiple provider implementations
  - `OpenAIProvider`, `AnthropicProvider`, `GeminiProvider`, `OllamaProvider`
  - All implement `ILLMProvider` interface

#### 3. Infrastructure (`app/infrastructure/`)

**Cross-cutting concerns.**

- **Config**: Environment variables, settings
- **Security**: JWT authentication, password hashing
- **Database**: MongoDB connection management
- **Logging**: Centralized logging configuration

#### 4. LangGraph (`app/langgraph/`)

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

### Why Hexagonal Architecture?

**Benefits:**
- ✅ **Testability**: Core logic tested without database/APIs
- ✅ **Flexibility**: Easy to swap MongoDB for PostgreSQL or change LLM providers
- ✅ **Clarity**: Clear separation of concerns
- ✅ **Future-proof**: Add features without refactoring

**Trade-offs:**
- More initial setup (interfaces, adapters)
- May feel over-engineered for simple use cases

**Verdict:** Worth it for a maintainable, extensible system.

## Frontend Architecture

### Component Structure

```
frontend/src/
├── components/
│   ├── auth/          # Authentication components
│   └── chat/          # Chat interface components
├── contexts/          # React contexts for state
│   ├── AuthContext    # Authentication state
│   └── ChatContext    # Chat state & WebSocket
├── hooks/             # Custom React hooks
│   └── useWebSocket   # WebSocket connection hook
├── pages/             # Route pages
│   ├── Login          # Login page
│   └── Chat           # Main chat page
├── services/          # API clients
│   ├── authService    # Authentication API
│   ├── conversationService  # Conversation API
│   └── websocketService     # WebSocket client
└── types/             # TypeScript types
```

### State Management

- **AuthContext**: Global authentication state (user, login, logout)
- **ChatContext**: Chat state (conversations, messages, streaming)
- **React hooks**: Encapsulate logic (useWebSocket, useAuth)

### Design Principles

- **Minimal UI**: Clean, distraction-free interface
- **Component composition**: Small, reusable components
- **Type safety**: TypeScript throughout
- **Real-time updates**: WebSocket integration

## Data Flow

### User Registration Flow

```
1. User submits registration form (Frontend)
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

### Chat Message Flow

```
1. User sends message via WebSocket (Frontend)
   ↓
2. WebSocket handler receives message (Inbound Adapter)
   ↓
3. LangGraph processes message (LangGraph)
   - process_user_input node
   - call_llm node (uses ILLMProvider)
   - format_response node
   - save_to_history node (uses repositories)
   ↓
4. Stream tokens back to client (WebSocket)
   ↓
5. Frontend displays streaming response (ChatContext)
```

## Technology Decisions

### Why FastAPI?

- Modern async framework
- Automatic API documentation
- Type safety with Pydantic
- High performance
- WebSocket support

### Why MongoDB?

- Flexible schema for evolving conversation structures
- Good performance for document-based data
- Easy to store nested conversation history
- Native async support with Beanie

**Alternative:** PostgreSQL with SQLAlchemy would also work well with this architecture.

### Why LangGraph?

- Built for agentic AI workflows
- Clear state management
- Native streaming support
- Easy to extend with tools and multi-step reasoning
- Future-ready for complex AI behaviors

### Why React?

- Component-based architecture
- Large ecosystem
- TypeScript support
- Excellent developer experience with Vite

### Why TailwindCSS?

- Utility-first approach
- Fast development
- Consistent design
- Small bundle size with purging

## Security

### Authentication

- JWT tokens for stateless authentication
- Bcrypt for password hashing (12 rounds)
- OAuth2 password flow
- Token expiration (30 minutes default)

### Authorization

- User isolation (users can only access their own data)
- Conversation ownership checks
- Protected WebSocket connections

### Container Security

- Non-root users in containers
- Multi-stage builds (smaller attack surface)
- Health checks for auto-recovery
- Resource limits

## Performance

### Backend

- Async/await throughout for non-blocking I/O
- Connection pooling for MongoDB
- Efficient Beanie ODM queries
- Streaming responses for LLM

### Frontend

- Code splitting with Vite
- Lazy loading of routes
- Optimized bundle size
- Gzip compression in production

### Database

- Indexes on frequently queried fields
- Pagination for large result sets
- Efficient query patterns

## Testing Strategy

### Unit Tests

- Domain model validation
- Use case business logic
- Mocked dependencies

### Integration Tests

- API endpoint testing
- Database operations
- Authentication flows

### Test Isolation

- Mock repositories and providers
- Test fixtures in conftest.py
- Separate test database (optional)

## Deployment

### Development

- Docker Compose with hot-reload
- Volume mounts for live code changes
- Debug mode enabled

### Production

- Multi-stage Docker builds
- Non-root users
- Health checks
- Resource limits
- Nginx for frontend static files
- Reverse proxy for API

## Extensibility

The architecture makes it easy to add:

### RAG (Retrieval-Augmented Generation)

1. Create `IVectorStore` port
2. Implement vector database adapter (Pinecone, Weaviate, ChromaDB)
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

All these extensions fit naturally into the hexagonal architecture without modifying core business logic.

## Conclusion

Genesis demonstrates how hexagonal architecture, combined with modern frameworks and clear separation of concerns, creates a maintainable, testable, and extensible AI chatbot application.

The architecture prioritizes:
- **Flexibility**: Easy to swap components
- **Testability**: Core logic isolated from infrastructure
- **Clarity**: Clear boundaries and responsibilities
- **Future-proofing**: Easy to extend and maintain
