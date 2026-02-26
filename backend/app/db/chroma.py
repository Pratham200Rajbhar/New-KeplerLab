"""ChromaDB client and collection management — thread-safe singleton pattern."""

from __future__ import annotations

import os
import logging
import threading

# ── Disable ALL Chroma / posthog telemetry before importing chromadb ──────────
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

logging.getLogger("chromadb").setLevel(logging.ERROR)
logging.getLogger("posthog").setLevel(logging.CRITICAL)

try:
    import posthog  # type: ignore
    posthog.capture = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    posthog.disabled = True
    posthog.Posthog.disabled = True  # type: ignore[attr-defined]
except Exception:
    pass

import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.config import settings

os.environ["SENTENCE_TRANSFORMERS_HOME"] = os.path.join(
    os.path.dirname(settings.CHROMA_DIR), "models"
)

logger = logging.getLogger(__name__)

_client: chromadb.PersistentClient | None = None
_collection: chromadb.Collection | None = None
_lock = threading.RLock()  # RLock: get_collection() → get_client() re-enters the lock


def get_client() -> chromadb.PersistentClient:
    """Thread-safe lazily initialised singleton ChromaDB client."""
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                try:
                    _client = chromadb.PersistentClient(
                        path=settings.CHROMA_DIR,
                        settings=ChromaSettings(anonymized_telemetry=False),
                    )
                    logger.info("ChromaDB client initialised at %s", settings.CHROMA_DIR)
                except Exception:
                    logger.exception("Failed to initialise ChromaDB client")
                    raise
    return _client


def get_collection() -> chromadb.Collection:
    """Thread-safe singleton shared collection."""
    global _collection
    if _collection is None:
        with _lock:
            if _collection is None:
                try:
                    _collection = get_client().get_or_create_collection(name="chapters")
                    logger.info("ChromaDB collection 'chapters' ready")
                except Exception:
                    logger.exception("Failed to get/create ChromaDB collection")
                    raise
    return _collection


def reset_client() -> None:
    """Reset singletons — useful for reconnecting after ChromaDB failures."""
    global _client, _collection
    with _lock:
        _client = None
        _collection = None
        logger.info("ChromaDB client and collection reset")


def backup_chroma(backup_dir: str | None = None) -> str:
    """Create a backup of the ChromaDB data directory.

    Copies the entire CHROMA_DIR to a timestamped subdirectory.
    Returns the path to the backup directory.

    Args:
        backup_dir: Parent directory for backups. Defaults to
                    ``{CHROMA_DIR}/../chroma_backups/``.

    Returns:
        Absolute path of the created backup.
    """
    import shutil
    from datetime import datetime

    source = settings.CHROMA_DIR
    if backup_dir is None:
        backup_dir = os.path.join(os.path.dirname(source), "chroma_backups")

    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(backup_dir, f"chroma_backup_{timestamp}")

    shutil.copytree(source, dest)
    logger.info("ChromaDB backup created: %s", dest)
    return dest


def get_collection_stats() -> dict:
    """Return basic statistics about the ChromaDB collection.

    Returns:
        Dict with count, name, and metadata.
    """
    try:
        collection = get_collection()
        count = collection.count()
        return {
            "name": collection.name,
            "count": count,
            "chroma_dir": settings.CHROMA_DIR,
        }
    except Exception as e:
        logger.error("Failed to get ChromaDB stats: %s", e)
        return {"error": str(e)}
