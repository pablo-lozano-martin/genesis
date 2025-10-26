# ABOUTME: Vector store port interface defining the contract for document storage and retrieval
# ABOUTME: Abstract interface following hexagonal architecture principles

from abc import ABC, abstractmethod
from typing import List, Optional
from app.core.domain.document import Document, RetrievalResult


class IVectorStore(ABC):
    """
    Vector store port interface.

    Defines the contract for document storage, retrieval, and management.
    Implementations handle embedding generation and similarity search
    without the core domain knowing about vector database details.
    """

    @abstractmethod
    async def store_documents(self, documents: List[Document]) -> List[str]:
        """
        Store documents in the vector store.

        Args:
            documents: List of Document objects to store

        Returns:
            List of stored document IDs

        Raises:
            Exception: If document storage fails
        """
        pass

    @abstractmethod
    async def retrieve(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        """
        Retrieve documents similar to the query.

        Args:
            query: Search query string
            top_k: Number of top results to return

        Returns:
            List of RetrievalResult with documents and similarity scores

        Raises:
            Exception: If retrieval fails
        """
        pass

    @abstractmethod
    async def delete(self, document_id: str) -> bool:
        """Delete a document from the store."""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all documents from the store."""
        pass
