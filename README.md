# Genesis

A full-stack AI chatbot application built with FastAPI, React, and LangGraph. Features a hexagonal architecture backend, modern React frontend with TailwindCSS, and support for multiple LLM providers (OpenAI, Anthropic, Google Gemini, and Ollama).

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

## License

MIT License
