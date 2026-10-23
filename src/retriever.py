"""Hybrid Retrieval with 70/30 Semantic + Keyword Search and Scope Filtering."""

import re
from typing import Any, Dict, List, Optional
from src.config import config
from src.embeddings import EmbeddingEngine
from src.vector_db import CampusVectorDB


STOP_WORDS = {
    "what", "is", "are", "the", "a", "an", "of",
    "in", "on", "for", "to", "and", "or", "do",
    "does", "how", "can", "i", "we", "you", "it",
    "about", "tell", "me", "please", "with", "when",
    "where", "why", "which", "who", "whom", "will",
}


class HybridRetriever:
    """Executes hybrid retrieval: 70% semantic similarity + 30% keyword match with scope filtering."""

    def __init__(
        self,
        vector_db: Optional[CampusVectorDB] = None,
        embedding_engine: Optional[EmbeddingEngine] = None,
        semantic_weight: float = config.semantic_weight,
        keyword_weight: float = config.keyword_weight,
    ):
        self.vector_db = vector_db or CampusVectorDB()
        self.embedding_engine = embedding_engine or EmbeddingEngine()
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight

    def retrieve(
        self,
        question: str,
        top_k: Optional[int] = None,
        scope: str = "all",  # "all", "official", or "personal"
    ) -> List[Dict[str, Any]]:
        """Retrieve the top-k most relevant chunks using hybrid scoring and optional scope filter."""
        k = top_k or config.default_top_k
        total_chunks = self.vector_db.count()
        if total_chunks == 0:
            return []

        where_clause = None
        if scope in {"official", "personal"}:
            where_clause = {"doc_scope": scope}

        # 1. SEMANTIC SEARCH
        query_embedding = self.embedding_engine.encode(
            [question], normalize_embeddings=True
        )[0].tolist()

        query_kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": min(k * 2, total_chunks),
            "include": ["documents", "metadatas", "distances"],
        }
        if where_clause:
            query_kwargs["where"] = where_clause

        try:
            semantic_results = self.vector_db.collection.query(**query_kwargs)
        except Exception:
            # Fallback if filtered collection has fewer elements
            semantic_results = self.vector_db.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(k, total_chunks),
                include=["documents", "metadatas", "distances"],
            )

        combined_results: Dict[str, Dict[str, Any]] = {}

        if semantic_results and "ids" in semantic_results and semantic_results["ids"]:
            for i, chunk_id in enumerate(semantic_results["ids"][0]):
                meta = semantic_results["metadatas"][0][i]
                dist = semantic_results["distances"][0][i]
                text = semantic_results["documents"][0][i]

                combined_results[chunk_id] = {
                    "text": text,
                    "source": meta.get("source", "Unknown"),
                    "page_number": meta.get("page_number", 1),
                    "doc_scope": meta.get("doc_scope", "official"),
                    "chunk_id": chunk_id,
                    "semantic_distance": dist,
                    "keyword_score": 0.0,
                }

        # 2. KEYWORD SEARCH
        question_words = set(re.findall(r"\b[a-zA-Z0-9]+\b", question.lower()))
        keywords = question_words - STOP_WORDS

        get_kwargs = {"include": ["documents", "metadatas"]}
        if where_clause:
            get_kwargs["where"] = where_clause

        try:
            all_results = self.vector_db.collection.get(**get_kwargs)
        except Exception:
            all_results = self.vector_db.collection.get(include=["documents", "metadatas"])

        if all_results and "ids" in all_results:
            for i, chunk_id in enumerate(all_results["ids"]):
                text = all_results["documents"][i]
                meta = all_results["metadatas"][i]

                text_words = set(re.findall(r"\b[a-zA-Z0-9]+\b", text.lower()))
                matched_words = keywords.intersection(text_words)
                keyword_score = len(matched_words) / len(keywords) if keywords else 0.0

                if chunk_id in combined_results:
                    combined_results[chunk_id]["keyword_score"] = keyword_score
                elif keyword_score > 0:
                    combined_results[chunk_id] = {
                        "text": text,
                        "source": meta.get("source", "Unknown"),
                        "page_number": meta.get("page_number", 1),
                        "doc_scope": meta.get("doc_scope", "official"),
                        "chunk_id": chunk_id,
                        "semantic_distance": None,
                        "keyword_score": keyword_score,
                    }

        # 3. COMBINE SCORES AND RANK CHUNKS
        ranked_results = []
        for result in combined_results.values():
            if result["semantic_distance"] is not None:
                semantic_score = max(0.0, 1.0 - float(result["semantic_distance"]))
            else:
                semantic_score = 0.0

            result["combined_score"] = (
                self.semantic_weight * semantic_score
                + self.keyword_weight * result["keyword_score"]
            )
            ranked_results.append(result)

        ranked_results.sort(key=lambda item: item["combined_score"], reverse=True)
        return ranked_results[:k]
