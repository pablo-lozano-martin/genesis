# Development Guide

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

## Features

- **Backend**: FastAPI with hexagonal architecture for clean separation of concerns
- **Frontend**: React + TypeScript + Vite + TailwindCSS
- **Database**: MongoDB with Beanie ODM
- **LLM Support**: OpenAI, Anthropic, Google Gemini, and Ollama
- **Real-time**: WebSocket support for streaming LLM responses
- **Auth**: JWT-based authentication with OAuth2
- **Orchestration**: LangGraph for conversation flow management
- **Docker**: One-command setup with docker-compose

## Development Workflow

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

## Testing

Run the test suite:
```bash
# All tests
docker-compose exec backend pytest

# Unit tests only
docker-compose exec backend pytest -m unit

# Integration tests only
docker-compose exec backend pytest -m integration
```

## Code Quality

### Linting

The project includes automated linting for both backend and frontend:

**Python (Backend)**:
```bash
# Run Ruff linter
docker-compose exec backend ruff check .

# Auto-fix issues
docker-compose exec backend ruff check --fix .

# Format code
docker-compose exec backend ruff format .
```

**TypeScript (Frontend)**:
```bash
# Run ESLint
docker-compose exec frontend npm run lint
```

### Pre-commit Hooks

Install pre-commit hooks to automatically lint code before commits:

```bash
# Install pre-commit hooks
bash .pre-commit-install.sh

# Or manually
pip install pre-commit
pre-commit install

# Run hooks on all files
pre-commit run --all-files
```

## Configuration

All configuration is managed through environment variables. See `.env.example` for available options.

Key settings:
- `LLM_PROVIDER`: Choose between openai, anthropic, gemini, or ollama
- `SECRET_KEY`: JWT signing key (generate a secure random string)
- `DEBUG`: Enable debug mode (false in production)
- `LOG_LEVEL`: Logging verbosity (INFO, DEBUG, WARNING, ERROR)
