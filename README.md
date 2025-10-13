# Genesis

A full-stack AI chatbot application built with FastAPI, React, and LangGraph. Features a hexagonal architecture backend, modern React frontend with TailwindCSS, and support for multiple LLM providers.

## Features

- **Backend**: FastAPI with hexagonal architecture for clean separation of concerns
- **Frontend**: React + TypeScript + Vite + TailwindCSS
- **Database**: MongoDB with Beanie ODM
- **LLM Support**: OpenAI, Anthropic, Google Gemini, and Ollama
- **Real-time**: WebSocket support for streaming LLM responses
- **Auth**: JWT-based authentication with OAuth2
- **Orchestration**: LangGraph for conversation flow management
- **Docker**: One-command setup with docker-compose

## Project Structure

```
genesis/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── core/              # Domain models, ports, and use cases
│   │   ├── adapters/          # Inbound (API) and outbound (DB, LLM) adapters
│   │   ├── infrastructure/    # Config, logging, database, security
│   │   ├── langgraph/         # LangGraph conversation flows
│   │   └── main.py            # Application entry point
│   ├── tests/                 # Unit and integration tests
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── lib/               # Utilities
│   │   └── main.tsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- An API key for your chosen LLM provider (OpenAI, Anthropic, Google, or Ollama)

### Setup

1. **Clone the repository**

```bash
cd genesis
```

2. **Configure environment variables**

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# Required: Choose your LLM provider
LLM_PROVIDER=openai

# Add your API key for the chosen provider
OPENAI_API_KEY=your-key-here
# OR
ANTHROPIC_API_KEY=your-key-here
# OR
GOOGLE_API_KEY=your-key-here

# Required: Set a secret key for JWT
SECRET_KEY=your-random-secret-key-here
```

3. **Start the application**

```bash
docker-compose up
```

This will start:
- Backend API at `http://localhost:8000`
- Frontend at `http://localhost:5173`
- MongoDB at `localhost:27017`

4. **Access the application**

- Frontend: http://localhost:5173
- API Documentation: http://localhost:8000/docs
- API Health Check: http://localhost:8000/api/health

## Development

### Backend Development

The backend uses hot-reloading, so changes to Python files will automatically restart the server.

**Run tests**:
```bash
docker-compose exec backend pytest
```

**Access backend shell**:
```bash
docker-compose exec backend bash
```

### Frontend Development

The frontend uses Vite's hot-reloading for instant updates.

**Access frontend shell**:
```bash
docker-compose exec frontend sh
```

**Install new packages**:
```bash
docker-compose exec frontend npm install <package-name>
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Architecture

### Hexagonal Architecture (Backend)

The backend follows hexagonal architecture principles:

- **Core Domain** (`app/core/`): Business logic and domain models
  - `domain/`: Entity models
  - `ports/`: Interfaces (contracts)
  - `use_cases/`: Business logic implementations

- **Adapters** (`app/adapters/`): External interfaces
  - `inbound/`: API controllers (REST, WebSocket)
  - `outbound/`: External services (Database, LLM providers)

- **Infrastructure** (`app/infrastructure/`): Cross-cutting concerns
  - Configuration, logging, database, security

This architecture makes the code:
- **Testable**: Core logic can be tested without external dependencies
- **Flexible**: Easy to swap databases or LLM providers
- **Maintainable**: Clear separation of concerns

### LangGraph Integration

LangGraph manages conversation flows as state machines, enabling:
- Stateful multi-turn conversations
- Easy addition of tools and agentic behaviors
- Built-in streaming support
- Conversation history tracking

## Technology Stack

### Backend
- **FastAPI**: Modern, fast web framework
- **Beanie**: Async MongoDB ODM
- **LangChain/LangGraph**: LLM orchestration
- **Pydantic**: Data validation
- **Python-Jose**: JWT authentication
- **Passlib**: Password hashing

### Frontend
- **React 18**: UI library
- **TypeScript**: Type safety
- **Vite**: Fast build tool
- **TailwindCSS**: Utility-first CSS
- **Axios**: HTTP client
- **React Router**: Routing

### Infrastructure
- **Docker**: Containerization
- **MongoDB**: Document database
- **Uvicorn**: ASGI server

## Configuration

All configuration is managed through environment variables. See `.env.example` for available options.

Key settings:
- `LLM_PROVIDER`: Choose between openai, anthropic, gemini, or ollama
- `SECRET_KEY`: JWT signing key (generate a secure random string)
- `DEBUG`: Enable debug mode (false in production)
- `LOG_LEVEL`: Logging verbosity (INFO, DEBUG, WARNING, ERROR)

## What's Next?

This is Phase 1 of the implementation. Future phases will add:

- **Phase 2**: Core domain models and hexagonal architecture implementation
- **Phase 3**: Authentication system with OAuth2 and JWT
- **Phase 4**: Database repositories and data persistence
- **Phase 5**: LLM provider abstractions (OpenAI, Anthropic, Gemini, Ollama)
- **Phase 6**: LangGraph conversation flows
- **Phase 7**: WebSocket real-time communication
- **Phase 8**: REST API endpoints
- **Phase 9**: Complete chat interface UI
- **Phase 10**: Comprehensive testing
- **Phase 11**: Production deployment configuration
- **Phase 12**: Documentation and developer experience

See `doc/INITIAL_PLAN.md` for the complete implementation roadmap.

## License

MIT License