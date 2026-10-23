"""Structure-aware chunking preserving paragraphs, sentences, and document scopes."""

import hashlib
import re
from dataclasses import dataclass
from typing import Dict, List, Set
from src.config import config
from src.extractor import ExtractedPage


@dataclass
class DocumentChunk:
    """A single chunk ready for vector storage."""

    text: str
    source: str
    page_number: int
    document_fingerprint: str
    chunk_id: str
    doc_scope: str = "official"  # "official" or "personal"


class StructureAwareChunker:
    """Splits extracted text pages into structure-aware, overlapping chunks."""

    def __init__(
        self,
        chunk_size: int = config.chunk_size,
        chunk_overlap: int = config.chunk_overlap,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_into_chunks(self, text: str) -> List[str]:
        """Split text by paragraphs, then sentences, preserving context overlap."""
        paragraphs = re.split(r"\n\s*\n", text)
        if len(paragraphs) == 1:
            paragraphs = text.splitlines()

        result: List[str] = []
        current_chunk = ""

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            if len(paragraph) > self.chunk_size:
                sentences = re.split(r"(?<=[.!?])\s+", paragraph)
            else:
                sentences = [paragraph]

            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                if len(current_chunk) + len(sentence) + 1 <= self.chunk_size:
                    current_chunk = (current_chunk + " " + sentence).strip()
                else:
                    if current_chunk:
                        result.append(current_chunk)

                    if current_chunk and self.chunk_overlap > 0:
                        current_chunk = current_chunk[-self.chunk_overlap :].strip()
                    else:
                        current_chunk = ""

                    while len(sentence) > self.chunk_size:
                        result.append(sentence[: self.chunk_size])
                        sentence = sentence[self.chunk_size :]

                    current_chunk = (current_chunk + " " + sentence).strip()

        if current_chunk:
            result.append(current_chunk)

        return result

    def create_unique_chunks(
        self,
        pages: List[ExtractedPage],
        document_fingerprint: str,
    ) -> List[DocumentChunk]:
        """Generate deduplicated chunks with unique hash identifiers and scope tags."""
        unique_chunks: List[DocumentChunk] = []
        seen_chunk_hashes: Set[str] = set()

        for page in pages:
            raw_chunks = self.split_into_chunks(page.text)

            for chunk_index, chunk_text in enumerate(raw_chunks, start=1):
                chunk_hash = hashlib.sha256(
                    (
                        document_fingerprint
                        + "|"
                        + str(page.page_number)
                        + "|"
                        + chunk_text.strip()
                    ).encode("utf-8")
                ).hexdigest()

                if chunk_hash in seen_chunk_hashes:
                    continue
                seen_chunk_hashes.add(chunk_hash)

                unique_chunks.append(
                    DocumentChunk(
                        text=chunk_text,
                        source=page.source,
                        page_number=page.page_number,
                        document_fingerprint=document_fingerprint,
                        chunk_id=chunk_hash,
                        doc_scope=page.doc_scope,
                    )
                )

        return unique_chunks
