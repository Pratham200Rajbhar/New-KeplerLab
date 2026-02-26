"""Embedding and batch storage into ChromaDB.

ChromaDB uses its own built-in ONNX embedding model (all-MiniLM-L6-v2, 384-dim)
to generate vectors from text.  All uploads and queries go through ChromaDB's
internal embedding pipeline — keeping add() and query() consistent without
requiring an external embedding server.

``warm_up_embeddings()`` should be called during application startup to preload
the ONNX model and avoid cold-start latency on the first upload.

``embed_and_store()`` uses UPSERT semantics (via collection.upsert) so that
re-processing the same material is idempotent.
"""

from typing import List, Optional
import logging
import time
import threading

from app.core.config import settings
from app.db.chroma import get_collection

logger = logging.getLogger(__name__)

_BATCH_SIZE = 200     # ChromaDB safe batch size (leaves headroom below 256-item limit)
_MAX_RETRIES = 3      # Per-batch retry attempts


def warm_up_embeddings() -> None:
    """Eagerly warm the ChromaDB ONNX embedding model at startup.

    Performs a dummy query so the ONNX runtime loads the MiniLM model into
    memory before the first real upload arrives.

    Safe to call multiple times — subsequent calls are cheap (< 1 ms).
    """
    try:
        col = get_collection()
        # A query with no hits still forces the ONNX engine to initialise
        col.query(query_texts=["warm-up"], n_results=1)
        logger.info("Embedding model (ChromaDB ONNX) warm-up complete.")
    except Exception as exc:
        # Collection may be empty: that's fine — ONNX model still loaded
        logger.info("Embedding warm-up done (collection empty or minor error: %s).", exc)


def embed_and_store(
    chunks: List[dict],
    material_id: Optional[str] = None,
    user_id: str = "",
    notebook_id: Optional[str] = None,
    filename: Optional[str] = None,
) -> None:
    """UPSERT text chunks into the shared ChromaDB collection.

    Each chunk dict must contain ``id`` and ``text`` keys.
    Tenant metadata (material_id, user_id, notebook_id) is attached for
    per-user filtering at query time.
    
    user_id is REQUIRED — embeddings without user_id break tenant isolation.

    Behaviour:
    - Uses ``collection.upsert()`` (idempotent) instead of ``add()`` so that
      re-processing the same material does not raise duplicate-ID errors.
    - Processes in batches of ``_BATCH_SIZE`` to stay within ChromaDB limits.
    - Each batch is retried up to ``_MAX_RETRIES`` times on transient errors.
    - A single bad batch is logged and skipped; other batches proceed.
    """
    if not chunks:
        return
    
    if not user_id:
        logger.error("embed_and_store called without user_id — skipping to prevent tenant isolation breach")
        return

    collection = get_collection()

    # Build base metadata template
    base_meta: dict = {
        "source": "chapter",
        "embedding_version": settings.EMBEDDING_VERSION,
    }
    if material_id:
        base_meta["material_id"] = material_id
    if user_id:
        base_meta["user_id"] = user_id
    if notebook_id:
        base_meta["notebook_id"] = notebook_id
    if filename:
        # Truncate long filenames to avoid ChromaDB metadata size limits
        base_meta["filename"] = filename[:200]

    stored = 0
    failed_batches = 0

    for start in range(0, len(chunks), _BATCH_SIZE):
        batch = chunks[start : start + _BATCH_SIZE]
        ids   = [c["id"]   for c in batch]
        docs  = [c["text"] for c in batch]
        metas = [base_meta.copy() for _ in batch]

        # Attach any per-chunk section metadata
        for i, chunk in enumerate(batch):
            if "section_title" in chunk:
                metas[i]["section_title"] = str(chunk["section_title"])[:200]
            if "chunk_index" in chunk:
                metas[i]["chunk_index"] = str(chunk["chunk_index"])
            # Structured data: embed only the summary but tag so the retriever
            # can swap in the full dataset at query time.
            if chunk.get("chunk_type") == "structured_summary":
                metas[i]["is_structured"] = "true"
            if "_raw_file_path" in chunk and chunk["_raw_file_path"]:
                metas[i]["raw_file_path"] = str(chunk["_raw_file_path"])[:500]

        # Retry loop for transient ChromaDB / ONNX errors
        # Note: time.sleep() is acceptable here because embed_and_store is called
        # via run_in_executor from async code (worker.py), so it runs in a thread.
        last_exc = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                collection.upsert(ids=ids, documents=docs, metadatas=metas)
                stored += len(batch)
                break
            except Exception as exc:
                last_exc = exc
                wait = 0.5 * attempt
                logger.warning(
                    "Batch upsert attempt %d/%d failed (start=%d): %s — retrying in %.1fs",
                    attempt, _MAX_RETRIES, start, exc, wait,
                )
                # Use threading.Event for interruptible sleep
                threading.Event().wait(timeout=wait)
        else:
            failed_batches += 1
            logger.error(
                "Batch upsert permanently failed (start=%d, size=%d, material=%s): %s",
                start, len(batch), material_id, last_exc,
            )

    if failed_batches:
        logger.error(
            "embed_and_store: %d batch(es) failed — %d/%d chunks stored  material=%s",
            failed_batches, stored, len(chunks), material_id,
        )
        if stored == 0:
            raise RuntimeError(
                f"All embedding batches failed for material {material_id}: {last_exc}"
            )
    else:
        logger.info(
            "Stored %d chunks successfully  material=%s  user=%s",
            stored, material_id, user_id,
        )


def delete_material_embeddings(material_id: str, user_id: str) -> int:
    """Remove all ChromaDB chunks belonging to *material_id* / *user_id*.

    Returns the number of chunks deleted.  Safe to call if material has no
    chunks stored (returns 0).
    
    Raises:
        RuntimeError: If the deletion fails (callers should handle this).
    """
    try:
        collection = get_collection()
        results = collection.get(
            where={"$and": [{"material_id": material_id}, {"user_id": user_id}]},
            include=[],  # IDs only
        )
        ids_to_delete = results.get("ids", [])
        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            logger.info(
                "Deleted %d chunks for material=%s user=%s",
                len(ids_to_delete), material_id, user_id,
            )
        return len(ids_to_delete)
    except Exception as exc:
        logger.error("Failed to delete embeddings for material %s: %s", material_id, exc)
        raise RuntimeError(f"Embedding deletion failed for material {material_id}") from exc
