
# Genesis

A ready-to-use template for building your own AI-powered applications with LangGraph. Whether you want to create a chatbot, a smart assistant, or any kind of agentic app, Genesis gives you a flexible starting point. It’s designed for all kinds of projects and purposes—just customize it to fit your needs and ideas. No deep technical setup required: simply use Genesis as your foundation and start building the agentic app you imagine!

## 🚀 Quick Start

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

## 🤖 Development Workflow

This project follows a state-of-the-art structured AI-assisted development workflow inspired by [flype/dot-claude](https://github.com/flype/dot-claude).  

> **Note:** The `.claude` directory and the Claude workflow are an integral part of this project.

The process starts by defining clear issues or features, then specialized sub-agents explore the codebase from different perspectives (backend, frontend, architecture, etc.) to gather insights before any implementation begins.  

Their findings are consolidated into a planning phase, followed by implementation, testing, and refinement.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
