# ABOUTME: FastAPI application entry point and configuration
# ABOUTME: Sets up the application with middleware, routing, and lifecycle events

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import setup_logging, get_logger
from app.infrastructure.database.mongodb import MongoDB
from app.adapters.inbound.auth_router import router as auth_router
from app.adapters.inbound.websocket_router import router as websocket_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Startup: Connect to database and register Beanie document models
    from app.adapters.outbound.repositories.mongo_models import (
        UserDocument,
        ConversationDocument,
        MessageDocument
    )

    await MongoDB.connect(document_models=[
        UserDocument,
        ConversationDocument,
        MessageDocument
    ])

    logger.info("Application startup complete")

    yield

    # Shutdown: Close database connection
    logger.info("Shutting down application")
    await MongoDB.close()
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
