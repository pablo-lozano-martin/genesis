# ABOUTME: ChromaDB implementation of vector store port interface
# ABOUTME: Manages document storage, embedding generation, and semantic search

from typing import List
from app.core.ports.vector_store import IVectorStore
from app.core.domain.document import Document, RetrievalResult, DocumentMetadata
from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger
from datetime import datetime

logger = get_logger(__name__)


class ChromaDBVectorStore(IVectorStore):
    """ChromaDB implementation of vector store."""

    def __init__(self, chroma_client):
        """Initialize with ChromaDB client."""
        self.client = chroma_client
        self.collection = self._get_or_create_collection()

    def _get_or_create_collection(self):
        """Get or create the knowledge base collection."""
        try:
            collection = self.client.get_or_create_collection(
                name=settings.chroma_collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Collection '{settings.chroma_collection_name}' ready")
            return collection
        except Exception as e:
            logger.error(f"Failed to get/create collection: {e}")
            raise

    async def store_documents(self, documents: List[Document]) -> List[str]:
        """
        Store documents in ChromaDB with automatic embedding.

        ChromaDB will auto-generate embeddings using configured model.
        """
        try:
            ids = [doc.id for doc in documents]
            contents = [doc.content for doc in documents]
            metadatas = [
                {
                    "source": doc.metadata.source,
                    "created_at": doc.metadata.created_at.isoformat(),
                    "content_length": doc.metadata.content_length,
                    "document_type": doc.metadata.document_type
                }
                for doc in documents
            ]

            self.collection.add(
                ids=ids,
                documents=contents,
                metadatas=metadatas
            )

            logger.info(f"Stored {len(documents)} documents in ChromaDB")
            return ids

        except Exception as e:
            logger.error(f"Failed to store documents: {e}")
            raise

    async def retrieve(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        """
        Retrieve documents similar to query using semantic search.
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )

            retrieval_results = []

            if not results["documents"] or not results["documents"][0]:
                return retrieval_results

            for i in range(len(results["ids"][0])):
                doc_id = results["ids"][0][i]
                content = results["documents"][0][i]
                metadata_dict = results["metadatas"][0][i]
                distance = results["distances"][0][i]

                # Convert distance to similarity score (0-1, higher is better)
                similarity_score = 1.0 - (distance / 2.0)

                metadata = DocumentMetadata(
                    source=metadata_dict.get("source", "unknown"),
                    created_at=datetime.fromisoformat(metadata_dict.get("created_at")),
                    content_length=metadata_dict.get("content_length", 0),
                    document_type=metadata_dict.get("document_type", "unknown")
                )

                document = Document(
                    id=doc_id,
                    content=content,
                    metadata=metadata
                )

                retrieval_results.append(
                    RetrievalResult(
                        document=document,
                        similarity_score=similarity_score
                    )
                )

            logger.info(f"Retrieved {len(retrieval_results)} documents for query")
            return retrieval_results

        except Exception as e:
            logger.error(f"Failed to retrieve documents: {e}")
            raise

    async def delete(self, document_id: str) -> bool:
        """Delete a document from ChromaDB."""
        try:
            self.collection.delete(ids=[document_id])
            logger.info(f"Deleted document {document_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False

    async def clear(self) -> bool:
        """Clear all documents from collection."""
        try:
            self.client.delete_collection(name=settings.chroma_collection_name)
            self.collection = self._get_or_create_collection()
            logger.info("Cleared all documents from collection")
            return True
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            return False
