"""Persistent ChromaDB vector database with document versioning & deduplication."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import chromadb
from src.chunker import DocumentChunk
from src.config import config
from src.embeddings import EmbeddingEngine


class CampusVectorDB:
    """Manages the persistent vector database for campus documents."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        collection_name: Optional[str] = None,
        embedding_engine: Optional[EmbeddingEngine] = None,
    ):
        self.db_path = db_path or config.chroma_db_path
        Path(self.db_path).mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=self.db_path)
        self.collection_name = collection_name or config.collection_name
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self.embedding_engine = embedding_engine or EmbeddingEngine()

    def remove_old_document_versions(
        self,
        filename: str,
        document_fingerprint: str,
    ) -> int:
        """Remove previously indexed chunks if the filename or fingerprint is re-uploaded."""
        existing_data = self.collection.get(include=["metadatas"])
        ids_to_delete = []

        if existing_data and "metadatas" in existing_data and existing_data["metadatas"]:
            for chunk_id, metadata in zip(
                existing_data["ids"], existing_data["metadatas"]
            ):
                existing_source = metadata.get("source", "")
                existing_fingerprint = metadata.get("document_fingerprint", "")

                if existing_source == filename or existing_fingerprint == document_fingerprint:
                    ids_to_delete.append(chunk_id)

        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)

        return len(ids_to_delete)

    def upsert_chunks(self, chunks: List[DocumentChunk]) -> int:
        """Generate embeddings and upsert unique chunks into ChromaDB."""
        if not chunks:
            return 0

        # Remove previous revisions of this document
        filename = chunks[0].source
        fingerprint = chunks[0].document_fingerprint
        self.remove_old_document_versions(filename, fingerprint)

        texts = [c.text for c in chunks]
        embeddings = self.embedding_engine.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )

        self.collection.upsert(
            ids=[c.chunk_id for c in chunks],
            documents=texts,
            embeddings=embeddings.tolist(),
            metadatas=[
                {
                    "source": c.source,
                    "page_number": c.page_number,
                    "chunk_id": c.chunk_id,
                    "document_fingerprint": c.document_fingerprint,
                }
                for c in chunks
            ],
        )

        return len(chunks)

    def count(self) -> int:
        """Total chunks in collection."""
        return self.collection.count()

    def clear(self) -> None:
        """Clear all entries in the collection."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
