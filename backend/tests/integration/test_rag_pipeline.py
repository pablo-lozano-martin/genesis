import pytest
import chromadb
from app.adapters.outbound.vector_stores.vector_store_factory import get_vector_store
from app.core.domain.document import Document, DocumentMetadata
from datetime import datetime


@pytest.fixture
async def chromadb_instance():
    """Real ChromaDB instance for integration tests (ephemeral)."""
    client = chromadb.EphemeralClient()
    yield client


@pytest.mark.integration
class TestRAGPipeline:
    """Integration tests for RAG pipeline."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve_documents(self, chromadb_instance):
        """Test full pipeline: store documents and retrieve them."""
        vector_store = get_vector_store(chromadb_instance)

        metadata = DocumentMetadata(
            source="test.md",
            created_at=datetime.utcnow(),
            content_length=100,
            document_type="md"
        )

        documents = [
            Document(id="doc1", content="Python is a programming language", metadata=metadata),
            Document(id="doc2", content="JavaScript runs in browsers", metadata=metadata)
        ]

        ids = await vector_store.store_documents(documents)
        assert len(ids) == 2

        results = await vector_store.retrieve("programming language", top_k=5)

        assert len(results) > 0
        assert results[0].document.id == "doc1"
        assert results[0].similarity_score > 0.5

    @pytest.mark.asyncio
    async def test_semantic_search_quality(self, chromadb_instance):
        """Test semantic search returns relevant results."""
        vector_store = get_vector_store(chromadb_instance)

        metadata = DocumentMetadata(
            source="test.md",
            created_at=datetime.utcnow(),
            content_length=100,
            document_type="md"
        )

        documents = [
            Document(id="cats", content="Cats are feline animals that meow", metadata=metadata),
            Document(id="dogs", content="Dogs are canine animals that bark", metadata=metadata),
            Document(id="cars", content="Cars are vehicles with four wheels", metadata=metadata)
        ]

        await vector_store.store_documents(documents)

        results = await vector_store.retrieve("feline animals", top_k=3)

        assert results[0].document.id == "cats"
        assert results[0].similarity_score > results[1].similarity_score

    @pytest.mark.asyncio
    async def test_empty_knowledge_base(self, chromadb_instance):
        """Test retrieval from empty knowledge base."""
        vector_store = get_vector_store(chromadb_instance)

        results = await vector_store.retrieve("any query", top_k=5)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_delete_document(self, chromadb_instance):
        """Test document deletion."""
        vector_store = get_vector_store(chromadb_instance)

        metadata = DocumentMetadata(
            source="test.md",
            created_at=datetime.utcnow(),
            content_length=50,
            document_type="md"
        )

        documents = [
            Document(id="doc_to_delete", content="This will be deleted", metadata=metadata)
        ]

        await vector_store.store_documents(documents)

        success = await vector_store.delete("doc_to_delete")
        assert success is True

        results = await vector_store.retrieve("deleted", top_k=5)
        assert len(results) == 0
