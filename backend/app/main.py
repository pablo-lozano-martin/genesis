# ABOUTME: FastAPI application entry point and configuration
# ABOUTME: Sets up the application with middleware, routing, and lifecycle events

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import setup_logging, get_logger
from app.infrastructure.database.mongodb import MongoDB, AppDatabase
from app.infrastructure.database.chromadb_client import ChromaDBClient
from app.infrastructure.database.langgraph_checkpointer import get_checkpointer
from app.adapters.inbound.auth_router import router as auth_router
from app.adapters.inbound.user_router import router as user_router
from app.adapters.inbound.conversation_router import router as conversation_router
from app.adapters.inbound.message_router import router as message_router
from app.adapters.inbound.websocket_router import router as websocket_router
from app.adapters.inbound.transcription_router import router as transcription_router

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
        ConversationDocument
    )

    # Connect to App Database (for backward compatibility, also use MongoDB alias)
    await AppDatabase.connect(document_models=[
        UserDocument,
        ConversationDocument
    ])

    # Initialize ChromaDB
    await ChromaDBClient.initialize()
    app.state.chroma_client = ChromaDBClient.client

    # Create vector store instance
    from app.adapters.outbound.vector_stores.vector_store_factory import get_vector_store
    app.state.vector_store = get_vector_store(ChromaDBClient.client)
    logger.info("Vector store initialized")

    # Initialize MCP client manager
    from app.infrastructure.mcp import MCPClientManager
    try:
        await MCPClientManager.initialize()
        app.state.mcp_manager = MCPClientManager
        logger.info("MCP client manager initialized")
    except Exception as e:
        logger.error(f"MCP initialization failed: {e}")
        app.state.mcp_manager = None

    # Initialize LangGraph checkpointer with proper lifecycle management
    checkpointer_context, checkpointer = await get_checkpointer()
    app.state.checkpointer_context = checkpointer_context
    app.state.checkpointer = checkpointer

    # Compile LangGraph graphs with checkpointer and combined tools
    from app.langgraph.graphs.chat_graph import create_chat_graph
    from app.langgraph.graphs.streaming_chat_graph import create_streaming_chat_graph
    from app.langgraph.tools.multiply import multiply
    from app.langgraph.tools.add import add
    from app.langgraph.tools.rag_search import rag_search

    # Combine local and MCP tools
    local_tools = [multiply, add, rag_search]
    mcp_tools = MCPClientManager.get_tools() if app.state.mcp_manager else []
    all_tools = local_tools + mcp_tools

    # Register tools in metadata registry
    from app.langgraph.tool_metadata import get_tool_registry, ToolMetadata, ToolSource

    tool_registry = get_tool_registry()

    # Register local tools
    for tool in local_tools:
        # Local tools can be Python functions or StructuredTool instances
        tool_name = getattr(tool, 'name', getattr(tool, '__name__', 'unknown'))
        tool_description = getattr(tool, 'description', getattr(tool, '__doc__', ''))
        tool_registry.register_tool(ToolMetadata(
            name=tool_name,
            description=tool_description or f"Local tool: {tool_name}",
            source=ToolSource.LOCAL
        ))

    # Register MCP tools
    for tool in mcp_tools:
        # MCP tools are StructuredTool instances with .name and .description
        tool_name = getattr(tool, 'name', getattr(tool, '__name__', 'unknown'))
        tool_description = getattr(tool, 'description', getattr(tool, '__doc__', ''))
        tool_registry.register_tool(ToolMetadata(
            name=tool_name,
            description=tool_description,
            source=ToolSource.MCP
        ))

    app.state.tool_registry = tool_registry
    logger.info(f"Tool registry initialized with {len(tool_registry.get_all_tools())} tools")

    logger.info(f"Compiling graphs with {len(local_tools)} local tools and {len(mcp_tools)} MCP tools")

    app.state.chat_graph = create_chat_graph(checkpointer, all_tools)
    app.state.streaming_chat_graph = create_streaming_chat_graph(checkpointer, all_tools)
    logger.info("LangGraph graphs compiled with checkpointing enabled")

    logger.info("Application startup complete")

    yield

    # Shutdown: Close database connections
    logger.info("Shutting down application")

    # Shutdown MCP
    if hasattr(app.state, 'mcp_manager') and app.state.mcp_manager:
        from app.infrastructure.mcp import MCPClientManager
        await MCPClientManager.shutdown()

    ChromaDBClient.close()
    await AppDatabase.close()
    # Properly exit AsyncMongoDBSaver context manager
    await checkpointer_context.__aexit__(None, None, None)
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
    app.include_router(transcription_router)

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
