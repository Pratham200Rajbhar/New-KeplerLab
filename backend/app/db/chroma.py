"""ChromaDB client and collection management — singleton pattern."""

from __future__ import annotations

import os
import logging

# ── Disable ALL Chroma / posthog telemetry before importing chromadb ──────────
# Prevents the "capture() takes 1 positional argument but 3 were given" error
# that arises when the posthog library version mismatches Chroma's call signature.
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

# Silence chromadb's own logger and suppress the posthog module entirely
logging.getLogger("chromadb").setLevel(logging.ERROR)
logging.getLogger("posthog").setLevel(logging.CRITICAL)  # mute posthog noise

try:
    import posthog  # type: ignore
    # Monkey-patch capture() to accept any signature without raising
    posthog.capture = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    posthog.disabled = True
    posthog.Posthog.disabled = True  # type: ignore[attr-defined]
except Exception:
    pass  # posthog not installed — nothing to do

import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.config import settings

os.environ["SENTENCE_TRANSFORMERS_HOME"] = os.path.join(
    os.path.dirname(settings.CHROMA_DIR), "models"
)

_client: chromadb.PersistentClient | None = None
_collection = None


def get_client() -> chromadb.PersistentClient:
    """Lazily initialised singleton ChromaDB client."""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=settings.CHROMA_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def get_collection():
    """Singleton shared collection — all user data isolated via metadata filters."""
    global _collection
    if _collection is None:
        _collection = get_client().get_or_create_collection(name="chapters")
    return _collection
