"""High-level Campus Knowledge Assistant API orchestrating extraction, ingestion, and Q&A."""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.chunker import StructureAwareChunker
from src.extractor import PDFExtractor
from src.generator import CampusAnswerGenerator
from src.retriever import HybridRetriever
from src.vector_db import CampusVectorDB


class CampusKnowledgeAssistant:
    """End-to-end Campus Knowledge Assistant."""

    def __init__(
        self,
        vector_db: Optional[CampusVectorDB] = None,
        retriever: Optional[HybridRetriever] = None,
        generator: Optional[CampusAnswerGenerator] = None,
    ):
        self.vector_db = vector_db or CampusVectorDB()
        self.retriever = retriever or HybridRetriever(vector_db=self.vector_db)
        self.generator = generator or CampusAnswerGenerator()
        self.extractor = PDFExtractor()
        self.chunker = StructureAwareChunker()

    def ingest_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Ingest a campus PDF document into the assistant's knowledge base."""
        pages, fingerprint = self.extractor.extract_pdf(pdf_path)
        chunks = self.chunker.create_unique_chunks(pages, fingerprint)
        indexed_count = self.vector_db.upsert_chunks(chunks)

        return {
            "source": Path(pdf_path).name,
            "pages_extracted": len(pages),
            "chunks_created": len(chunks),
            "indexed_count": indexed_count,
            "fingerprint": fingerprint,
        }

    def ask(self, question: str, top_k: int = 3) -> Dict[str, Any]:
        """Ask a campus-related question."""
        start_time = time.time()
        retrieved_docs = self.retriever.retrieve(question, top_k=top_k)

        if not retrieved_docs:
            return {
                "answer": "I could not find relevant information in the available campus documents.",
                "sources": [],
                "response_time": round(time.time() - start_time, 2),
            }

        answer = self.generator.generate(question, retrieved_docs)

        # Collect unique sources
        sources = []
        seen_sources = set()
        for doc in retrieved_docs:
            source_key = (doc["source"], doc["page_number"])
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                sources.append({
                    "source": doc["source"],
                    "page_number": doc["page_number"],
                })

        return {
            "answer": answer,
            "sources": sources,
            "response_time": round(time.time() - start_time, 2),
            "retrieved_chunks": retrieved_docs,
        }
