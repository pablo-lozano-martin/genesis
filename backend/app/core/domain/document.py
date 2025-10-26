# ABOUTME: Document domain models for knowledge base and RAG operations
# ABOUTME: Pure domain entities independent of persistence layer

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class DocumentMetadata:
    """Metadata about a stored document."""
    source: str
    created_at: datetime
    content_length: int
    document_type: str


@dataclass
class Document:
    """Document entity for knowledge base."""
    id: str
    content: str
    metadata: DocumentMetadata


@dataclass
class RetrievalResult:
    """Result of a document retrieval."""
    document: Document
    similarity_score: float
