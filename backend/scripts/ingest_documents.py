# ABOUTME: Document ingestion script for batch loading knowledge base files
# ABOUTME: Processes files, chunks content, and stores in ChromaDB

import asyncio
import argparse
import sys
from pathlib import Path
from typing import List
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger
from app.infrastructure.database.chromadb_client import ChromaDBClient
from app.adapters.outbound.vector_stores.vector_store_factory import get_vector_store
from app.core.domain.document import Document, DocumentMetadata

logger = get_logger(__name__)


async def load_text_file(file_path: Path) -> str:
    """Load content from text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load {file_path}: {e}")
        raise


async def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks.

    Simple implementation - can be enhanced with semantic chunking later.
    """
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)

    return chunks


async def process_file(file_path: Path) -> List[Document]:
    """Process a file and return Document objects."""
    logger.info(f"Processing file: {file_path}")

    suffix = file_path.suffix.lower()

    if suffix in ['.txt', '.md']:
        content = await load_text_file(file_path)
    elif suffix == '.pdf':
        logger.warning(f"PDF support not yet implemented, skipping {file_path}")
        return []
    else:
        logger.warning(f"Unsupported file type {suffix}, skipping {file_path}")
        return []

    chunks = await chunk_text(
        content,
        chunk_size=settings.retrieval_chunk_size,
        overlap=settings.retrieval_chunk_overlap
    )

    documents = []
    for i, chunk in enumerate(chunks):
        doc_id = f"{file_path.stem}_chunk_{i}"

        metadata = DocumentMetadata(
            source=str(file_path),
            created_at=datetime.utcnow(),
            content_length=len(chunk),
            document_type=suffix[1:]
        )

        document = Document(
            id=doc_id,
            content=chunk,
            metadata=metadata
        )

        documents.append(document)

    logger.info(f"Created {len(documents)} document chunks from {file_path}")
    return documents


async def ingest_directory(directory: Path, vector_store):
    """Ingest all supported files from directory."""
    logger.info(f"Scanning directory: {directory}")

    supported_extensions = ['.txt', '.md', '.pdf']
    files = []

    for ext in supported_extensions:
        files.extend(directory.glob(f"**/*{ext}"))

    logger.info(f"Found {len(files)} files to process")

    all_documents = []
    for file_path in files:
        try:
            documents = await process_file(file_path)
            all_documents.extend(documents)
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            continue

    if all_documents:
        logger.info(f"Storing {len(all_documents)} document chunks in vector store")
        await vector_store.store_documents(all_documents)
        logger.info("Ingestion complete")
    else:
        logger.warning("No documents to store")


async def main(directory_path: str):
    """Main ingestion workflow."""
    try:
        await ChromaDBClient.initialize()

        vector_store = get_vector_store(ChromaDBClient.client)

        directory = Path(directory_path)
        if not directory.exists():
            logger.error(f"Directory does not exist: {directory}")
            return 1

        await ingest_directory(directory, vector_store)

        return 0

    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        return 1
    finally:
        ChromaDBClient.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest documents into knowledge base"
    )
    parser.add_argument(
        "directory",
        type=str,
        help="Directory containing documents to ingest"
    )

    args = parser.parse_args()

    sys.exit(asyncio.run(main(args.directory)))
