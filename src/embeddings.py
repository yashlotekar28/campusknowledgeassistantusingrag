"""Embedding model wrapper using sentence-transformers."""

from typing import List
from src.config import config

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None


class EmbeddingEngine:
    """Generates dense vector embeddings using sentence-transformers."""

    _instance = None

    def __init__(self, model_name: str = config.embedding_model_name):
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        if self._model is None:
            if SentenceTransformer is None:
                raise ImportError(
                    "sentence-transformers is required for local embeddings. "
                    "Run: pip install sentence-transformers"
                )
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(
        self,
        texts: List[str],
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
    ):
        """Encode list of strings into normalized embedding vectors."""
        return self.model.encode(
            texts,
            normalize_embeddings=normalize_embeddings,
            show_progress_bar=show_progress_bar,
        )
