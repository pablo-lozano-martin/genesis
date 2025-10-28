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

## MCP (Model Context Protocol) Development

Genesis supports dynamic tool discovery via MCP servers, allowing you to extend chatbot capabilities without code changes.

### Setting Up MCP Servers

**1. Create MCP configuration file:**

```bash
# Copy example config
cp backend/genesis_mcp.example.json backend/genesis_mcp.json
```

**2. Enable MCP in `.env`:**

```bash
# Add to .env
MCP_ENABLED=true
MCP_CONFIG_PATH=./genesis_mcp.json
```

**3. Install MCP server package:**

```bash
# Example: Install fetch server for web requests
docker-compose exec backend pip install mcp-server-fetch

# Rebuild container to persist
docker-compose build backend
```

**4. Configure server in `backend/genesis_mcp.json`:**

```json
[
  {
    "name": "fetch",
    "transport": "stdio",
    "command": "python",
    "args": ["-m", "mcp_server_fetch"],
    "env": {}
  }
]
```

**5. Restart backend:**

```bash
docker-compose restart backend
```

**6. Verify in logs:**

```bash
docker-compose logs backend | grep MCP

# Expected output:
# INFO - Initializing 1 MCP server(s)
# INFO - Connecting to MCP server 'fetch' via stdio
# INFO - Discovered tool: fetch:fetch
# INFO - Registered MCP tool: fetch:fetch
# INFO - MCP initialization complete. 1 tools available
```

### Testing with MCP Simple Tool

For development and testing, use the official `mcp-server-fetch`:

```bash
# Install
docker-compose exec backend pip install mcp-server-fetch

# Configure
cat > backend/genesis_mcp.json <<EOF
[
  {
    "name": "fetch",
    "transport": "stdio",
    "command": "python",
    "args": ["-m", "mcp_server_fetch"]
  }
]
EOF

# Enable and restart
docker-compose restart backend
```

Test the tool in the chat:
> "Fetch the content from https://example.com"

The chatbot will use the MCP fetch tool, and you'll see a purple "MCP" badge in the UI.

### Available MCP Servers

Common MCP servers you can install:

- `mcp-server-fetch`: Web content fetching
- `mcp-server-sqlite`: SQLite database queries
- `mcp-server-filesystem`: File system operations
- `mcp-server-git`: Git operations
- Custom servers: Build your own with the MCP SDK

### Creating Custom MCP Servers

**Python Example:**

```python
# my_mcp_server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("MyServer")

@mcp.tool()
def greet(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run()
```

**Configuration:**

```json
{
  "name": "my-server",
  "transport": "stdio",
  "command": "python",
  "args": ["path/to/my_mcp_server.py"]
}
```

See: https://modelcontextprotocol.io/quickstart/server

### Debugging MCP Integration

**Enable debug logging:**

```bash
# In .env
LOG_LEVEL=DEBUG
```

**Check MCP initialization:**

```bash
docker-compose logs backend | grep -A 20 "MCP"
```

**Common issues:**

1. **Timeout errors**: Server takes >10s to respond
   - Solution: Increase timeout in `mcp_client_manager.py` or optimize server startup

2. **Module not found**: MCP server not installed
   - Solution: `docker-compose exec backend pip install <package>` and rebuild

3. **Connection hangs**: Server process doesn't respond
   - Solution: Check server logs, ensure correct command/args

4. **Tools not appearing**: MCP disabled or config not loaded
   - Solution: Verify `MCP_ENABLED=true` and restart backend

**Test MCP without chatbot:**

```bash
# Test server directly
docker-compose exec backend python -m mcp_server_fetch --help

# Should show help message without errors
```

### Disabling MCP

To disable MCP during development:

```bash
# In .env
MCP_ENABLED=false

# Restart
docker-compose restart backend
```

The application will work normally with only local Python tools.

### MCP Configuration Options

**Stdio transport:**
```json
{
  "name": "server-name",
  "transport": "stdio",
  "command": "python",           // or "node", "bash", etc.
  "args": ["-m", "module_name"], // command arguments
  "env": {                       // environment variables
    "API_KEY": "secret"
  }
}
```

**SSE transport (HTTP):**
```json
{
  "name": "server-name",
  "transport": "sse",
  "url": "http://localhost:8001/mcp"
}
```

### MCP Testing

**Unit tests:**
```bash
docker-compose exec backend pytest tests/unit/test_mcp_client_manager.py -v
docker-compose exec backend pytest tests/unit/test_mcp_tool_adapter.py -v
```

**Manual testing checklist:**
- [ ] Backend starts with `MCP_ENABLED=false` (graceful disable)
- [ ] Backend starts with `MCP_ENABLED=true` and valid config
- [ ] Backend starts with `MCP_ENABLED=true` and missing config (graceful error)
- [ ] Backend starts with invalid MCP server (timeout, continues)
- [ ] Tools appear in chat with MCP badge (purple border)
- [ ] MCP tools execute successfully
- [ ] Tool results display correctly
- [ ] Application works with only local tools if MCP fails

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
