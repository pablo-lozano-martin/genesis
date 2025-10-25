# ABOUTME: FastAPI application entry point and configuration
# ABOUTME: Sets up the application with middleware, routing, and lifecycle events

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import setup_logging, get_logger
from app.infrastructure.database.mongodb import MongoDB, AppDatabase, LangGraphDatabase
from app.infrastructure.database.langgraph_checkpointer import get_checkpointer
from app.adapters.inbound.auth_router import router as auth_router
from app.adapters.inbound.user_router import router as user_router
from app.adapters.inbound.conversation_router import router as conversation_router
from app.adapters.inbound.message_router import router as message_router
from app.adapters.inbound.websocket_router import router as websocket_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Startup: Connect to databases and register Beanie document models
    from app.adapters.outbound.repositories.mongo_models import (
        UserDocument,
        ConversationDocument,
        MessageDocument
    )

    # Connect to App Database (for backward compatibility, also use MongoDB alias)
    await AppDatabase.connect(document_models=[
        UserDocument,
        ConversationDocument,
        MessageDocument
    ])

    # Connect to LangGraph Database
    await LangGraphDatabase.connect()

    # Initialize LangGraph checkpointer
    checkpointer = await get_checkpointer()
    app.state.checkpointer = checkpointer

    # Compile LangGraph graphs with checkpointer
    from app.langgraph.graphs.chat_graph import create_chat_graph
    from app.langgraph.graphs.streaming_chat_graph import create_streaming_chat_graph

    app.state.chat_graph = create_chat_graph(checkpointer)
    app.state.streaming_chat_graph = create_streaming_chat_graph(checkpointer)
    logger.info("LangGraph graphs compiled with checkpointing enabled")

    logger.info("Application startup complete")

    yield

    # Shutdown: Close database connections
    logger.info("Shutting down application")
    await AppDatabase.close()
    await LangGraphDatabase.close()
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    # Setup logging
    setup_logging()

    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(auth_router)
    app.include_router(user_router)
    app.include_router(conversation_router)
    app.include_router(message_router)
    app.include_router(websocket_router)

    # Health check endpoint
    @app.get("/api/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version
        }

    return app


app = create_app()
