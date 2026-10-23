"""Embedding model wrapper using all-MiniLM-L6-v2 via ONNX or sentence-transformers."""

from typing import List
from src.config import config

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    import chromadb.utils.embedding_functions as ef
except ImportError:
    ef = None


class EmbeddingEngine:
    """Generates dense vector embeddings (all-MiniLM-L6-v2) using ONNX or sentence-transformers."""

    def __init__(self, model_name: str = config.embedding_model_name):
        self.model_name = model_name
        self._st_model = None
        self._ef_model = None

    def encode(
        self,
        texts: List[str],
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
    ):
        """Encode list of strings into normalized embedding vectors."""
        if not texts:
            import numpy as np
            return np.empty((0, 384), dtype=np.float32)

        if SentenceTransformer is not None:
            if self._st_model is None:
                self._st_model = SentenceTransformer(self.model_name)
            return self._st_model.encode(
                texts,
                normalize_embeddings=normalize_embeddings,
                show_progress_bar=show_progress_bar,
            )
        elif ef is not None:
            if self._ef_model is None:
                self._ef_model = ef.DefaultEmbeddingFunction()
            embeddings = self._ef_model(texts)
            import numpy as np
            arr = np.array(embeddings, dtype=np.float32)
            if normalize_embeddings:
                norms = np.linalg.norm(arr, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                arr = arr / norms
            return arr
        else:
            raise RuntimeError(
                "Neither sentence-transformers nor chromadb embedding functions are available."
            )
