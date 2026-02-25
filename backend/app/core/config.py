"""
Centralized application configuration.

Uses pydantic BaseSettings for automatic env-var loading and validation.
Import the singleton ``settings`` instance throughout the app.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    """Application settings — validated from environment variables."""

    # ── Database ──────────────────────────────────────────
    DATABASE_URL: str = ""

    # ── ChromaDB ──────────────────────────────────────────
    CHROMA_DIR: str = "./data/chroma"

    # ── File Storage ──────────────────────────────────────
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 25

    # ── Output Directories ────────────────────────────────
    PODCAST_OUTPUT_DIR: str = "output/podcasts"
    PRESENTATIONS_OUTPUT_DIR: str = "output/presentations"
    TEMPLATES_DIR: str = "./templates"

    # ── JWT / Auth ────────────────────────────────────────
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    FILE_TOKEN_EXPIRE_MINUTES: int = 5

    # ── Cookie Settings ───────────────────────────────────
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: Optional[str] = None
    COOKIE_NAME: str = "refresh_token"

    # ── CORS ──────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    # ── LLM ───────────────────────────────────────────────
    LLM_PROVIDER: str = "MYOPENLM"  # Fast AI provider for better performance
    OLLAMA_MODEL: str = "llama3"
    GOOGLE_MODEL: str = "models/gemini-2.5-flash"
    GOOGLE_API_KEY: str = ""
    NVIDIA_MODEL: str = "qwen/qwen3.5-397b-a17b"
    NVIDIA_API_KEY: str = ""
    MYOPENLM_MODEL: str = "default"
    MYOPENLM_API_URL: str = "https://openlmfallback-0adc8b183b77.herokuapp.com/api/chat"
    LLM_TIMEOUT: int = 120
    
    # ── LLM Generation Control ───────────────────────────
    LLM_TEMPERATURE_STRUCTURED: float = 0.1
    LLM_TEMPERATURE_CHAT: float = 0.2
    LLM_TEMPERATURE_CREATIVE: float = 0.7
    LLM_TEMPERATURE_CODE: float = 0.1
    LLM_TOP_P_STRUCTURED: float = 0.9
    LLM_TOP_P_CHAT: float = 0.95
    LLM_MAX_TOKENS: int = 4000
    LLM_MAX_TOKENS_CHAT: int = 3000
    LLM_FREQUENCY_PENALTY: float = 0.0
    LLM_PRESENCE_PENALTY: float = 0.0
    LLM_TOP_K: int = 50


    # ── Embeddings ────────────────────────────────────────
    MODELS_DIR: str = "./data/models"
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_VERSION: str = "bge_m3_v1"  # Bump when model or chunking strategy changes
    EMBEDDING_DIMENSION: int = 1024
    
    # ── Reranking ─────────────────────────────────────────
    RERANKER_MODEL: str = "BAAI/bge-reranker-large"
    USE_RERANKER: bool = True
    
    # ── Retrieval Configuration ──────────────────────────
    INITIAL_VECTOR_K: int = 10
    MMR_K: int = 8
    FINAL_K: int = 10
    MMR_LAMBDA: float = 0.5
    MAX_CONTEXT_TOKENS: int = 6000
    MIN_CHUNK_LENGTH: int = 100   # Minimum chars to store a chunk in ChromaDB
    MIN_CONTEXT_CHUNK_LENGTH: int = 150  # Minimum chars after retrieval (context building)
    MIN_SIMILARITY_SCORE: float = 0.3
    CHUNK_OVERLAP_TOKENS: int = 150

    # ── Processing Timeouts & Retries ─────────────────────
    OCR_TIMEOUT_SECONDS: int = 300
    WHISPER_TIMEOUT_SECONDS: int = 600
    LIBREOFFICE_TIMEOUT_SECONDS: int = 120
    PROCESSING_MAX_RETRIES: int = 2

    # ── Image Generation ──────────────────────────────────
    IMAGE_GENERATION_ENDPOINT: Optional[str] = None

    # ── External Search Service ───────────────────────────
    SEARCH_SERVICE_URL: str = "http://159.89.166.91:8002"

    @field_validator("LLM_PROVIDER", mode="after")
    @classmethod
    def _uppercase_provider(cls, v: str) -> str:
        return v.upper()

    @field_validator("JWT_SECRET_KEY", mode="after")
    @classmethod
    def _validate_jwt(cls, v: str) -> str:
        if not v:
            raise ValueError(
                "JWT_SECRET_KEY must be set. "
                'Generate: python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )
        return v

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()
