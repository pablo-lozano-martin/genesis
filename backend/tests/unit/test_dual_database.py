# ABOUTME: Unit tests for dual database setup (AppDatabase and LangGraphDatabase)
# ABOUTME: Tests database connection, initialization, and lifecycle management

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from motor.motor_asyncio import AsyncIOMotorClient

from app.infrastructure.database.mongodb import AppDatabase, LangGraphDatabase, MongoDB
from app.infrastructure.database.langgraph_checkpointer import get_checkpointer
from app.adapters.outbound.repositories.mongo_models import UserDocument, ConversationDocument


class TestAppDatabase:
    """Tests for AppDatabase connection manager."""

    @pytest.mark.asyncio
    async def test_app_database_connect_success(self):
        """Test successful connection to App Database."""
        with patch('app.infrastructure.database.mongodb.AsyncIOMotorClient') as mock_client, \
             patch('app.infrastructure.database.mongodb.init_beanie') as mock_init_beanie:

            # Setup mock
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance
            mock_instance.__getitem__.return_value = MagicMock()

            # Test connection
            await AppDatabase.connect(document_models=[UserDocument, ConversationDocument])

            # Verify
            assert AppDatabase.client is not None
            assert AppDatabase.database is not None
            mock_client.assert_called_once()
            mock_init_beanie.assert_called_once()

    @pytest.mark.asyncio
    async def test_app_database_connect_failure(self):
        """Test App Database connection failure handling."""
        with patch('app.infrastructure.database.mongodb.AsyncIOMotorClient') as mock_client:
            mock_client.side_effect = Exception("Connection failed")

            # Test connection failure
            with pytest.raises(Exception, match="Connection failed"):
                await AppDatabase.connect(document_models=[UserDocument, ConversationDocument])

    @pytest.mark.asyncio
    async def test_app_database_close(self):
        """Test App Database connection closure."""
        # Setup
        AppDatabase.client = MagicMock()
        AppDatabase.client.close = MagicMock()

        # Test closure
        await AppDatabase.close()

        # Verify
        AppDatabase.client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_app_database_close_when_no_client(self):
        """Test App Database closure when no client exists."""
        # Setup
        AppDatabase.client = None

        # Test closure (should not raise)
        await AppDatabase.close()


class TestLangGraphDatabase:
    """Tests for LangGraphDatabase connection manager."""

    @pytest.mark.asyncio
    async def test_langgraph_database_connect_success(self):
        """Test successful connection to LangGraph Database."""
        with patch('app.infrastructure.database.mongodb.AsyncIOMotorClient') as mock_client:
            # Setup mock
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance
            mock_instance.__getitem__.return_value = MagicMock()

            # Test connection
            await LangGraphDatabase.connect()

            # Verify
            assert LangGraphDatabase.client is not None
            assert LangGraphDatabase.database is not None
            mock_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_langgraph_database_connect_failure(self):
        """Test LangGraph Database connection failure handling."""
        with patch('app.infrastructure.database.mongodb.AsyncIOMotorClient') as mock_client:
            mock_client.side_effect = Exception("Connection failed")

            # Test connection failure
            with pytest.raises(Exception, match="Connection failed"):
                await LangGraphDatabase.connect()

    @pytest.mark.asyncio
    async def test_langgraph_database_close(self):
        """Test LangGraph Database connection closure."""
        # Setup
        LangGraphDatabase.client = MagicMock()
        LangGraphDatabase.client.close = MagicMock()

        # Test closure
        await LangGraphDatabase.close()

        # Verify
        LangGraphDatabase.client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_langgraph_database_close_when_no_client(self):
        """Test LangGraph Database closure when no client exists."""
        # Setup
        LangGraphDatabase.client = None

        # Test closure (should not raise)
        await LangGraphDatabase.close()


class TestBackwardCompatibility:
    """Tests for backward compatibility alias."""

    def test_mongodb_alias_points_to_app_database(self):
        """Test that MongoDB alias points to AppDatabase."""
        assert MongoDB is AppDatabase


class TestLangGraphCheckpointer:
    """Tests for LangGraph checkpointer setup."""

    @pytest.mark.asyncio
    async def test_get_checkpointer_success(self):
        """Test successful checkpointer creation."""
        # Setup
        LangGraphDatabase.client = MagicMock(spec=AsyncIOMotorClient)

        with patch('app.infrastructure.database.langgraph_checkpointer.AsyncMongoDBSaver') as mock_saver_class:
            # Setup the async context manager mock
            mock_saver_instance = MagicMock()
            mock_context_manager = MagicMock()
            mock_context_manager.__aenter__ = AsyncMock(return_value=mock_saver_instance)
            mock_saver_class.from_conn_string = MagicMock(return_value=mock_context_manager)

            # Test checkpointer creation
            checkpointer = await get_checkpointer()

            # Verify
            mock_saver_class.from_conn_string.assert_called_once()
            assert checkpointer == mock_saver_instance

    @pytest.mark.asyncio
    async def test_get_checkpointer_raises_when_not_connected(self):
        """Test checkpointer creation fails when database not connected."""
        # Setup
        LangGraphDatabase.client = None

        # Test checkpointer creation failure
        with pytest.raises(RuntimeError, match="LangGraphDatabase not connected"):
            await get_checkpointer()


class TestDualDatabaseIndependence:
    """Tests for independence of App and LangGraph databases."""

    @pytest.mark.asyncio
    async def test_app_and_langgraph_databases_are_independent(self):
        """Test that AppDatabase and LangGraphDatabase maintain separate connections."""
        with patch('app.infrastructure.database.mongodb.AsyncIOMotorClient') as mock_client:
            # Setup separate mock clients
            app_client = MagicMock()
            langgraph_client = MagicMock()
            mock_client.side_effect = [app_client, langgraph_client]

            app_client.__getitem__.return_value = MagicMock()
            langgraph_client.__getitem__.return_value = MagicMock()

            # Connect both databases
            with patch('app.infrastructure.database.mongodb.init_beanie'):
                await AppDatabase.connect(document_models=[UserDocument])
            await LangGraphDatabase.connect()

            # Verify separate clients
            assert AppDatabase.client is not LangGraphDatabase.client
            assert AppDatabase.database is not LangGraphDatabase.database

    @pytest.mark.asyncio
    async def test_closing_app_database_does_not_affect_langgraph_database(self):
        """Test that closing AppDatabase doesn't affect LangGraphDatabase."""
        # Setup
        AppDatabase.client = MagicMock()
        LangGraphDatabase.client = MagicMock()

        # Close AppDatabase
        await AppDatabase.close()

        # Verify LangGraphDatabase client still exists
        assert LangGraphDatabase.client is not None
        AppDatabase.client.close.assert_called_once()
