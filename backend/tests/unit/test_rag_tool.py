import pytest
from unittest.mock import AsyncMock, MagicMock
from app.langgraph.tools.rag_search import rag_search
from app.core.domain.document import Document, DocumentMetadata, RetrievalResult
from datetime import datetime


@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing."""
    mock = AsyncMock()
    return mock


@pytest.fixture
def sample_retrieval_results():
    """Sample retrieval results for testing."""
    metadata = DocumentMetadata(
        source="test_doc.md",
        created_at=datetime.utcnow(),
        content_length=100,
        document_type="md"
    )

    doc = Document(
        id="test_1",
        content="This is a test document about Python programming.",
        metadata=metadata
    )

    return [RetrievalResult(document=doc, similarity_score=0.95)]


@pytest.mark.asyncio
class TestRAGSearch:
    """Tests for RAG search tool."""

    async def test_rag_search_found_results(self, mock_vector_store, sample_retrieval_results, monkeypatch):
        """Test RAG search with found results."""
        mock_vector_store.retrieve.return_value = sample_retrieval_results

        from app import main
        monkeypatch.setattr(main.app.state, 'vector_store', mock_vector_store)

        result = await rag_search("test query")

        assert "Knowledge Base Search Results" in result
        assert "Result 1" in result
        assert "test_doc.md" in result
        assert "95.00%" in result
        mock_vector_store.retrieve.assert_called_once()

    async def test_rag_search_no_results(self, mock_vector_store, monkeypatch):
        """Test RAG search with no results."""
        mock_vector_store.retrieve.return_value = []

        from app import main
        monkeypatch.setattr(main.app.state, 'vector_store', mock_vector_store)

        result = await rag_search("nonexistent query")

        assert "No relevant documents found" in result

    async def test_rag_search_empty_query(self, mock_vector_store, monkeypatch):
        """Test RAG search with empty query."""
        from app import main
        monkeypatch.setattr(main.app.state, 'vector_store', mock_vector_store)

        result = await rag_search("")

        assert "Invalid query" in result
        mock_vector_store.retrieve.assert_not_called()

    async def test_rag_search_service_unavailable(self, monkeypatch):
        """Test RAG search when service is unavailable."""
        from app import main

        mock_state = MagicMock()
        delattr(type(mock_state), 'vector_store')
        monkeypatch.setattr(main.app, 'state', mock_state)

        result = await rag_search("test query")

        assert "service not available" in result

    async def test_rag_search_exception_handling(self, mock_vector_store, monkeypatch):
        """Test RAG search handles exceptions gracefully."""
        mock_vector_store.retrieve.side_effect = Exception("ChromaDB connection error")

        from app import main
        monkeypatch.setattr(main.app.state, 'vector_store', mock_vector_store)

        result = await rag_search("test query")

        assert "Error searching knowledge base" in result
