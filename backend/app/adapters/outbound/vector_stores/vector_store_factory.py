# ABOUTME: Vector store factory for creating store instances based on configuration
# ABOUTME: Currently supports ChromaDB, extensible for other vector databases

from app.core.ports.vector_store import IVectorStore
from app.infrastructure.config.settings import settings


class VectorStoreFactory:
    """Factory for creating vector store instances."""

    @staticmethod
    def create_vector_store(chroma_client) -> IVectorStore:
        """Create appropriate vector store based on configuration."""
        from app.adapters.outbound.vector_stores.chroma_vector_store import ChromaDBVectorStore
        return ChromaDBVectorStore(chroma_client)


def get_vector_store(chroma_client) -> IVectorStore:
    """Get the configured vector store instance."""
    return VectorStoreFactory.create_vector_store(chroma_client)
