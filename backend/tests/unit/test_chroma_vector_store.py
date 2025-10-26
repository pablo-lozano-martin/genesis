import pytest
from unittest.mock import MagicMock, AsyncMock
from app.adapters.outbound.vector_stores.chroma_vector_store import ChromaDBVectorStore
from app.core.domain.document import Document, DocumentMetadata
from datetime import datetime


@pytest.fixture
def mock_chroma_client():
    """Mock ChromaDB client."""
    mock = MagicMock()
    mock_collection = MagicMock()
    mock.get_or_create_collection.return_value = mock_collection
    return mock


@pytest.fixture
def sample_documents():
    """Sample documents for testing."""
    metadata = DocumentMetadata(
        source="test.txt",
        created_at=datetime.utcnow(),
        content_length=50,
        document_type="txt"
    )

    return [
        Document(id="doc1", content="Content 1", metadata=metadata),
        Document(id="doc2", content="Content 2", metadata=metadata)
    ]


class TestChromaDBVectorStore:
    """Tests for ChromaDB vector store adapter."""

    @pytest.mark.asyncio
    async def test_store_documents(self, mock_chroma_client, sample_documents):
        """Test storing documents in ChromaDB."""
        store = ChromaDBVectorStore(mock_chroma_client)

        ids = await store.store_documents(sample_documents)

        assert len(ids) == 2
        assert ids == ["doc1", "doc2"]
        store.collection.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_documents(self, mock_chroma_client):
        """Test retrieving documents from ChromaDB."""
        mock_chroma_client.get_or_create_collection().query.return_value = {
            "ids": [["doc1"]],
            "documents": [["Content 1"]],
            "distances": [[0.1]],
            "metadatas": [[{
                "source": "test.txt",
                "created_at": datetime.utcnow().isoformat(),
                "content_length": 50,
                "document_type": "txt"
            }]]
        }

        store = ChromaDBVectorStore(mock_chroma_client)
        results = await store.retrieve("test query", top_k=5)

        assert len(results) == 1
        assert results[0].document.id == "doc1"
        assert results[0].similarity_score > 0

    @pytest.mark.asyncio
    async def test_delete_document(self, mock_chroma_client):
        """Test deleting document from ChromaDB."""
        store = ChromaDBVectorStore(mock_chroma_client)

        success = await store.delete("doc1")

        assert success is True
        store.collection.delete.assert_called_once_with(ids=["doc1"])

    @pytest.mark.asyncio
    async def test_clear_collection(self, mock_chroma_client):
        """Test clearing all documents from collection."""
        store = ChromaDBVectorStore(mock_chroma_client)

        success = await store.clear()

        assert success is True
        mock_chroma_client.delete_collection.assert_called_once()
