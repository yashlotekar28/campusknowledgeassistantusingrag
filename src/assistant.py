"""High-level Campus Knowledge Assistant API with scoping and multi-format support."""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.chunker import StructureAwareChunker
from src.extractor import MultiFormatExtractor
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
        self.extractor = MultiFormatExtractor()
        self.chunker = StructureAwareChunker()

    def ingest_document(
        self, file_path: Path, doc_scope: str = "official"
    ) -> Dict[str, Any]:
        """Ingest a campus document (PDF, DOCX, image) into the knowledge base."""
        pages, fingerprint = self.extractor.extract_document(file_path, doc_scope=doc_scope)
        chunks = self.chunker.create_unique_chunks(pages, fingerprint)
        indexed_count = self.vector_db.upsert_chunks(chunks)

        return {
            "source": Path(file_path).name,
            "doc_scope": doc_scope,
            "pages_extracted": len(pages),
            "chunks_created": len(chunks),
            "indexed_count": indexed_count,
            "fingerprint": fingerprint,
        }

    # Backward compatibility
    def ingest_pdf(self, pdf_path: Path, doc_scope: str = "official") -> Dict[str, Any]:
        return self.ingest_document(pdf_path, doc_scope=doc_scope)

    def ask(
        self,
        question: str,
        top_k: int = 3,
        scope: str = "all",
    ) -> Dict[str, Any]:
        """Ask a campus-related question with optional scope filter ('all', 'official', 'personal')."""
        start_time = time.time()
        retrieved_docs = self.retriever.retrieve(question, top_k=top_k, scope=scope)

        if not retrieved_docs:
            scope_desc = f" ({scope} scope)" if scope != "all" else ""
            return {
                "answer": f"I could not find relevant information in the available campus documents{scope_desc}.",
                "sources": [],
                "response_time": round(time.time() - start_time, 2),
                "retrieved_chunks": [],
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
                    "doc_scope": doc.get("doc_scope", "official"),
                    "snippet": doc.get("text", "")[:300] + "...",
                })

        return {
            "answer": answer,
            "sources": sources,
            "response_time": round(time.time() - start_time, 2),
            "retrieved_chunks": retrieved_docs,
        }
