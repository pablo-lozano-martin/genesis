# Development Guide

Quick reference for developing on Genesis.

## Project Structure

```
genesis/
├── backend/
│   ├── app/
│   │   ├── core/              # Domain models, ports, use cases
│   │   ├── adapters/          # Inbound (API) and outbound (DB, LLM) adapters
│   │   ├── infrastructure/    # Config, logging, database, security
│   │   ├── langgraph/         # LangGraph conversation flows
│   │   └── main.py
│   ├── tests/                 # Unit and integration tests
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── lib/               # Utilities
│   │   └── main.tsx
│   ├── package.json
│   └── Dockerfile
└── docker-compose.yml
```

## Technology Stack

### Backend
- **FastAPI**: Web framework
- **Beanie**: MongoDB ODM
- **LangChain/LangGraph**: LLM orchestration
- **Pydantic**: Data validation
- **Python-Jose**: JWT authentication
- **Passlib**: Password hashing

### Frontend
- **React 18**: UI library
- **TypeScript**: Type safety
- **Vite**: Build tool
- **TailwindCSS**: Styling
- **Axios**: HTTP client

### Infrastructure
- **Docker**: Containerization
- **MongoDB**: Database

## Development Workflow

### Backend

The backend uses hot-reloading for automatic server restarts.

```bash
# Run tests
docker-compose exec backend pytest

# Run specific tests
docker-compose exec backend pytest tests/unit/
docker-compose exec backend pytest -m integration

# Access backend shell
docker-compose exec backend bash

# View logs
docker-compose logs -f backend
```

### Frontend

The frontend uses Vite's hot-reloading for instant updates.

```bash
# Install new packages
docker-compose exec frontend npm install <package-name>

# Access frontend shell
docker-compose exec frontend sh

# View logs
docker-compose logs -f frontend
```

### Database

```bash
# Access MongoDB shell
docker-compose exec mongodb mongosh

# View database
docker-compose exec mongodb mongosh --eval "show dbs"
```

## Testing

```bash
# All tests
docker-compose exec backend pytest

# Unit tests only
docker-compose exec backend pytest -m unit

# Integration tests only
docker-compose exec backend pytest -m integration

# With coverage
docker-compose exec backend pytest --cov=app
```

## Code Quality

### Linting

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

Install pre-commit hooks to automatically lint code:

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
- `SECRET_KEY`: JWT signing key (generate with `openssl rand -hex 32`)
- `DEBUG`: Enable debug mode (false in production)
- `LOG_LEVEL`: Logging verbosity (INFO, DEBUG, WARNING, ERROR)

## Common Tasks

### Adding a New LLM Provider

1. Create provider class in `app/adapters/outbound/llm_providers/`
2. Implement `ILLMProvider` interface
3. Add configuration to `.env.example`
4. Update provider factory

### Adding a New API Endpoint

1. Create use case in `app/core/use_cases/`
2. Add router in `app/adapters/inbound/api/`
3. Register router in `main.py`
4. Add tests in `tests/`

### Adding a New Domain Model

1. Create model in `app/core/domain/`
2. Create port interface in `app/core/ports/`
3. Create MongoDB document in `app/adapters/outbound/repositories/`
4. Implement repository

## Useful Commands

```bash
# View all services
docker-compose ps

# Restart specific service
docker-compose restart backend

# Rebuild service
docker-compose up -d --build backend

# View all logs
docker-compose logs -f

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```
