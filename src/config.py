"""Configuration settings for Campus Knowledge Assistant."""

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass


@dataclass
class Config:
    """Application configuration."""

    # Gemini API
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Embedding & Vector Database
    embedding_model_name: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    chroma_db_path: str = os.getenv(
        "CHROMA_DB_PATH", str(PROJECT_ROOT / "data" / "chroma_db")
    )
    collection_name: str = "campus_knowledge_collection"

    # Chunking Hyperparameters
    chunk_size: int = int(os.getenv("CHUNK_SIZE", 1200))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", 200))

    # Hybrid Search Weights
    semantic_weight: float = float(os.getenv("HYBRID_SEMANTIC_WEIGHT", 0.7))
    keyword_weight: float = float(os.getenv("HYBRID_KEYWORD_WEIGHT", 0.3))
    default_top_k: int = int(os.getenv("DEFAULT_TOP_K", 3))

    # Server Settings
    server_host: str = os.getenv("SERVER_HOST", "127.0.0.1")
    server_port: int = int(os.getenv("SERVER_PORT", 8000))


config = Config()
