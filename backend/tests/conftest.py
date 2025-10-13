# ABOUTME: Pytest configuration and shared fixtures for testing
# ABOUTME: Provides reusable test fixtures for database, app, and client setup

import pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from app.main import create_app


@pytest.fixture
async def app() -> FastAPI:
    """Create a FastAPI application instance for testing."""
    return create_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing API endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
