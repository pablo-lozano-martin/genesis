# ABOUTME: RAG search tool for semantic knowledge base queries
# ABOUTME: Integrates with ChromaDB vector store for document retrieval

from typing import Optional
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


async def rag_search(query: str) -> str:
    """
    Search the shared knowledge base for relevant documents.

    Uses vector similarity to find documents matching the query.
    The LLM can use this to augment its responses with retrieved context.

    Args:
        query: The search query string to find relevant documents

    Returns:
        A string containing the top matching documents formatted for LLM consumption,
        or a message if no results found
    """
    try:
        from app.main import app

        if not hasattr(app.state, 'vector_store'):
            return "Knowledge base service not available"

        vector_store = app.state.vector_store

        if not query or not query.strip():
            return "Invalid query: Query cannot be empty"

        from app.infrastructure.config.settings import settings
        results = await vector_store.retrieve(
            query=query.strip(),
            top_k=settings.retrieval_top_k
        )

        if not results:
            return f"No relevant documents found in knowledge base for query: '{query}'"

        formatted_results = "Knowledge Base Search Results:\n\n"

        for i, result in enumerate(results, 1):
            doc = result.document
            score = result.similarity_score

            excerpt = doc.content[:300] + "..." if len(doc.content) > 300 else doc.content

            formatted_results += f"[Result {i}] (Relevance: {score:.2%})\n"
            formatted_results += f"Source: {doc.metadata.source}\n"
            formatted_results += f"Content: {excerpt}\n\n"

        logger.info(f"RAG search found {len(results)} documents for query: '{query}'")
        return formatted_results

    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        return f"Error searching knowledge base: {str(e)}"
