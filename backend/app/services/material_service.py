"""Material lifecycle management — upload, process, query, delete.

All three ingestion paths (file, URL, text) share a common pipeline:
  1. Create a ``pending`` record in Prisma
  2. Extract text  (status → ``processing`` / ``ocr_running`` / ``transcribing``)
  3. Chunk text
  4. Embed & store chunks in ChromaDB  (status → ``embedding``)
  5. Update the record to ``completed``

If any step fails the record is marked ``failed``, the failure reason is
persisted in the ``error`` column, and the exception is **not** re-raised
so that the caller (route handler / background worker) never crashes due
to a single document failure.

STORAGE ARCHITECTURE:
  - Full text is stored in file system: data/material_text/{material_id}.txt
  - Database stores only: summary (first 1000 chars), metadata, chunkCount
  - Use get_material_text() to retrieve full text when needed for generation
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import traceback
from functools import partial
from typing import List, Optional

from app.core.config import settings
from app.db.prisma_client import prisma
from app.core.utils import sanitize_null_bytes
from app.services.rag.embedder import embed_and_store
from app.services.text_processing.chunker import chunk_text
from app.services.storage_service import (
    save_material_text,
    load_material_text,
    delete_material_text,
    get_material_summary,
)

# File extensions that should bypass chunking and be passed raw to the LLM
_STRUCTURED_SOURCE_TYPES = frozenset({"csv", "excel", "xlsx", "xls", "tsv", "ods"})

logger = logging.getLogger(__name__)


# ── Status helpers ────────────────────────────────────────────


async def _emit_material_ws(user_id: str, material_id: str, status: str, **extra) -> None:
    """Best-effort push of a material_update event via WebSocket.

    Never raises — if the user has no open WS connection the event is
    silently dropped (the client can always poll /jobs/{job_id} as fallback).
    """
    try:
        from app.services.ws_manager import ws_manager
        payload: dict = {"type": "material_update", "material_id": material_id, "status": status}
        if extra:
            payload.update(extra)
        await ws_manager.send_to_user(user_id, payload)
    except Exception as exc:
        logger.debug("WS emit skipped (material=%s status=%s): %s", material_id, status, exc)


async def _set_status(material_id: str, status: str, user_id: Optional[str] = None, **extra) -> None:
    """Persist a status transition (and optional extra fields) safely.

    If *user_id* is provided the new status is also pushed to any open
    WebSocket connections for that user (best-effort; never raises).
    """
    data: dict = {"status": status, **extra}
    try:
        await prisma.material.update(where={"id": material_id}, data=data)
    except Exception:
        logger.exception("Failed to update material %s to status=%s", material_id, status)
        return
    if user_id:
        await _emit_material_ws(user_id, material_id, status, **extra)


async def _fail_material(material_id: str, reason: str, user_id: Optional[str] = None) -> None:
    """Mark a material as ``failed`` and store the reason."""
    logger.error("Material %s failed: %s", material_id, reason)
    await _set_status(material_id, "failed", user_id=user_id, error=reason)


# ── Structured data helpers ───────────────────────────────────

def _make_structured_summary_chunk(raw_file_path: str, fallback_text: str) -> tuple:
    """Build a (full_data_string, [summary_chunk]) pair for CSV/Excel files.

    Returns
    -------
    full_data_string:
        ``df.to_string()`` of every sheet — saved to ``data/material_text/``
        so the LLM receives the *complete* dataset on retrieval.
    summary_chunks:
        A single-element list containing a chunk whose ``text`` is a compact
        schema header (column names + dtypes + shape + first 5 rows) suitable
        for semantic indexing.  The chunk is tagged ``chunk_type=structured_summary``
        and ``is_structured=true`` so the retriever knows to swap in the full
        data at query time.
    """
    import uuid
    import pandas as pd
    from pathlib import Path

    full_text = fallback_text
    summary_text = fallback_text

    try:
        if not raw_file_path:
            raise ValueError("No raw_file_path available")

        ext = Path(raw_file_path).suffix.lower()
        stem = Path(raw_file_path).stem

        if ext == ".csv":
            df = pd.read_csv(raw_file_path, encoding_errors="replace")
            sheets: dict = {"data": df}
        elif ext in (".xlsx", ".xls"):
            sheets = pd.read_excel(raw_file_path, sheet_name=None)
            if not isinstance(sheets, dict):
                sheets = {"Sheet1": sheets}
        elif ext == ".ods":
            sheets = pd.read_excel(raw_file_path, engine="odf", sheet_name=None)
            if not isinstance(sheets, dict):
                sheets = {"Sheet1": sheets}
        elif ext == ".tsv":
            df = pd.read_csv(raw_file_path, sep="\t", encoding_errors="replace")
            sheets = {"data": df}
        else:
            raise ValueError(f"Unsupported structured extension: {ext}")

        full_parts: list = []
        summary_parts: list = []
        for sheet_name, df in sheets.items():
            label = f"Sheet: {sheet_name}" if len(sheets) > 1 else stem
            full_parts.append(f"=== {label} ===\n{df.to_string()}")
            summary_parts.append(
                f"=== {label} ===\n"
                f"Shape: {df.shape[0]} rows × {df.shape[1]} columns\n"
                f"Columns: {', '.join(str(c) for c in df.columns)}\n"
                f"Column types: {', '.join(f'{c}: {t}' for c, t in df.dtypes.items())}\n"
                f"\nFirst 5 rows:\n{df.head(5).to_string()}"
            )

        full_text = "\n\n".join(full_parts)
        summary_text = "\n\n".join(summary_parts)

    except Exception as exc:
        logger.warning(
            "Structured fast-path read failed for %s: %s — using extractor text as fallback",
            raw_file_path, exc,
        )

    chunk = {
        "id": str(uuid.uuid4()),
        "text": summary_text,
        "section_title": "Structured Data Summary",
        "chunk_type": "structured_summary",
        "chunk_index": 0,
        "total_chunks": 1,
        # Internal keys (stripped before ChromaDB storage):
        "_raw_file_path": raw_file_path,
    }
    return full_text, [chunk]


# ── Internal pipeline helper ──────────────────────────────────


async def _process_material(
    material_id: str,
    text: str,
    user_id: str,
    notebook_id: Optional[str],
    *,
    title: Optional[str] = None,
    filename: Optional[str] = None,
    extraction_metadata: Optional[dict] = None,
    source_type: str = "prose",
):
    """Shared pipeline: chunk → embed → update record.

    On failure the material is marked ``failed`` with a persisted error
    message.  The exception is **not** re-raised — the worker stays alive.
    
    STORAGE: Full text saved to file storage (data/material_text/{material_id}.txt),
             only summary (first 1000 chars) stored in database.
    
    Args:
        material_id: Material record ID
        text: Extracted text content
        user_id: User ID
        notebook_id: Optional notebook ID
        title: Optional title
        extraction_metadata: Optional metadata from extraction (tables_detected, ocr_pages, etc.)
    """
    try:
        if not text or len(text.strip()) < 10:
            await _fail_material(material_id, "Extracted text is too short (< 10 chars)", user_id=user_id)
            return None

        _t_total = time.perf_counter()
        loop = asyncio.get_running_loop()

        # ── Structured data short-circuit (CSV / Excel / TSV / ODS) ──────────
        # Bypass RecursiveCharacterTextSplitter entirely.  Instead:
        #   • Re-read the raw file with pandas and store the FULL df.to_string()
        #     so the LLM receives the complete dataset on context retrieval.
        #   • Create exactly ONE summary chunk (schema + first 5 rows) for
        #     semantic indexing — row-by-row chunking destroys tabular structure.
        _pre_computed_chunks = None
        if source_type in _STRUCTURED_SOURCE_TYPES:
            raw_path = (extraction_metadata or {}).get("upload_path", "")
            from functools import partial as _partial
            full_data, _pre_computed_chunks = await loop.run_in_executor(
                None,
                _partial(_make_structured_summary_chunk, raw_path, text),
            )
            text = full_data  # save the full df.to_string() to material_text/
            if extraction_metadata is None:
                extraction_metadata = {}
            extraction_metadata.setdefault("raw_file_path", raw_path)
            extraction_metadata["is_structured"] = True
            logger.info(
                "Structured fast-path: skipping chunker, 1 summary chunk  "
                "material=%s  raw_path=%s",
                material_id, raw_path,
            )

        # ── Save full text to file storage (I/O — offloaded to thread pool) ──
        try:
            _t0 = time.perf_counter()
            await loop.run_in_executor(None, partial(save_material_text, material_id, text))
            logger.info(
                "PERF save_text: %.1fms  material=%s  chars=%d",
                (time.perf_counter() - _t0) * 1000, material_id, len(text),
            )
        except Exception as e:
            logger.error(f"Failed to save text to storage for material {material_id}: {e}")
            await _fail_material(material_id, f"Failed to save text to storage: {e}", user_id=user_id)
            return None

        # ── Chunking (CPU-bound — offloaded to thread pool) ───────────────────
        _t0 = time.perf_counter()
        if _pre_computed_chunks is not None:
            # Structured file: pre-computed single summary chunk — skip splitter
            chunks = _pre_computed_chunks
        else:
            chunks = await loop.run_in_executor(
                None,
                partial(chunk_text, text, True, source_type),  # semantic chunking ON
            )
        logger.info(
            "PERF chunking: %.1fms  chunks=%d  material=%s",
            (time.perf_counter() - _t0) * 1000, len(chunks), material_id,
        )

        if not chunks and len(text.strip()) > 50:
            logger.error(f"Material {material_id} produced 0 chunks from {len(text)} chars")
            await _fail_material(
                material_id, 
                "Document processing failed: Could not extract searchable content (text might be low quality or unsupported format).", 
                user_id=user_id
            )
            return None

        # ── Embedding step (CPU-bound — thread pool) ──────────────────────────
        await _set_status(material_id, "embedding", user_id=user_id)

        # ── Store summary instead of full text ────────────────────────────────
        summary = get_material_summary(text, max_chars=1000)

        # ── Run embedding AND AI title generation in parallel ──────────────────
        # Fetch the db record first (fast) to get the filename for title generation.
        _title_filename = filename
        if not title and not _title_filename:
            try:
                _mat_rec = await prisma.material.find_unique(where={"id": material_id})
                _title_filename = _mat_rec.filename if _mat_rec else None
            except Exception:
                pass

        _t0 = time.perf_counter()

        async def _embed():
            await loop.run_in_executor(
                None,
                partial(
                    embed_and_store,
                    chunks,
                    material_id=material_id,
                    user_id=user_id,
                    notebook_id=notebook_id,
                    filename=filename,
                ),
            )

        # ── Critical path: embedding only — complete immediately ─────────────
        # Title generation is decoupled into a background task so the material
        # becomes "completed" as soon as the vectors are stored, letting users
        # start chatting without waiting for the LLM title call (which can
        # take 10–90 seconds on local inference backends).
        await _embed()

        embed_ms = (time.perf_counter() - _t0) * 1000
        logger.info(
            "PERF embedding: %.1fms  chunks=%d  material=%s",
            embed_ms, len(chunks), material_id,
        )

        # Fast placeholder title derived from filename (no LLM needed).
        fast_title: str
        if title:
            fast_title = title
        elif _title_filename:
            fast_title = _title_filename.rsplit(".", 1)[0][:60]
        else:
            fast_title = "Untitled Material"

        update_data: dict = {
            "originalText": sanitize_null_bytes(summary),  # Store only summary
            "chunkCount": len(chunks),
            "status": "completed",
            "error": None,          # clear any previous error
            "title": sanitize_null_bytes(fast_title),
        }

        # Store extraction metadata as JSON string (sanitize for null bytes)
        if extraction_metadata:
            import json
            sanitized_meta = sanitize_null_bytes(extraction_metadata)
            update_data["metadata"] = json.dumps(sanitized_meta)

        result = await prisma.material.update(
            where={"id": material_id},
            data=update_data,
        )
        # Eagerly populate the context_formatter filename cache so citations
        # show human-readable names immediately after processing completes.
        if filename:
            try:
                from app.services.rag.context_formatter import set_material_name
                set_material_name(material_id, filename)
            except Exception:
                pass
        # Push completed event via WebSocket IMMEDIATELY — user can now chat.
        if user_id:
            await _emit_material_ws(user_id, material_id, "completed", chunk_count=len(chunks))

        logger.info(
            "PERF _process_material total (critical path): %.1fms  material=%s",
            (time.perf_counter() - _t_total) * 1000, material_id,
        )

        # ── Background task: AI title generation (non-blocking) ───────────────
        # Runs after "completed" is emitted so the UI doesn't wait for it.
        # On completion it updates the DB and re-emits a WS event so the
        # sidebar refreshes the displayed title.
        if not title:
            _bg_text = text[:2000]
            _bg_filename = _title_filename
            _bg_material_id = material_id
            _bg_user_id = user_id

            async def _background_title_update() -> None:
                try:
                    from app.services.notebook_name_generator import generate_material_title
                    ai_title = await loop.run_in_executor(
                        None,
                        partial(generate_material_title, _bg_text, _bg_filename),
                    )
                    ai_title = sanitize_null_bytes(str(ai_title)[:60])
                    await prisma.material.update(
                        where={"id": _bg_material_id},
                        data={"title": ai_title},
                    )
                    logger.info(
                        "Background AI title updated: material=%s  title='%s'",
                        _bg_material_id, ai_title,
                    )
                    # Re-emit completed so the sidebar calls loadMaterials()
                    # and shows the new title without a page refresh.
                    if _bg_user_id:
                        await _emit_material_ws(
                            _bg_user_id, _bg_material_id, "completed",
                            title=ai_title,
                        )
                except Exception as bg_exc:
                    logger.warning(
                        "Background title generation failed for material %s: %s",
                        _bg_material_id, bg_exc,
                    )

            asyncio.create_task(_background_title_update())

        return result

    except Exception as exc:
        tb = traceback.format_exc()
        await _fail_material(material_id, f"{exc}\n{tb}", user_id=user_id)
        return None


# ── Public ingestion API ──────────────────────────────────────


async def process_material(
    file_path: str,
    filename: str,
    user_id,
    notebook_id=None,
):
    """Process an uploaded file.

    Never raises — on failure the material record is marked ``failed``
    with the error persisted in the database.
    """
    uid, nid = str(user_id), str(notebook_id) if notebook_id else None

    data: dict = {"filename": filename, "userId": uid, "status": "pending"}
    if nid:
        data["notebookId"] = nid
    material = await prisma.material.create(data=data)

    try:
        await _set_status(material.id, "processing")

        from app.services.text_processing.extractor import EnhancedTextExtractor
        from app.services.text_processing.file_detector import FileTypeDetector

        # Determine granular status based on file category
        file_info = FileTypeDetector.detect_file_type(file_path)
        category = file_info.get("category", "document")
        if category == "image":
            await _set_status(material.id, "ocr_running")
        elif category in ("audio", "video"):
            await _set_status(material.id, "transcribing")

        result = EnhancedTextExtractor().extract_text(file_path, source_type="file")
        if result["status"] != "success":
            error_msg = result.get("error", "unknown extraction error")
            await _fail_material(material.id, f"Extraction failed: {error_msg}")
            return material

        # Extract metadata from result
        extraction_metadata = result.get("metadata", {})
        extraction_metadata["upload_path"] = file_path
        
        return await _process_material(
            material.id,
            result["text"],
            uid,
            nid,
            filename=filename,
            extraction_metadata=extraction_metadata,
            source_type=result.get("source_type") or extraction_metadata.get("source_type", "prose"),
        ) or material

    except Exception as exc:
        tb = traceback.format_exc()
        await _fail_material(material.id, f"{exc}\n{tb}")
        return material


async def create_material_record(
    filename: str,
    user_id,
    notebook_id=None,
    source_type: str = "file",
    title: Optional[str] = None,
) -> str:
    """Create a Material DB record in ``pending`` state and return its ID.

    Call this from the upload route **before** enqueuing a background job.
    The background worker will later call :func:`process_material_by_id`.
    """
    uid = str(user_id)
    nid = str(notebook_id) if notebook_id and notebook_id != "draft" else None
    data: dict = {
        "filename": filename,
        "userId": uid,
        "status": "pending",
        "sourceType": source_type,
    }
    if nid:
        data["notebookId"] = nid
    if title:
        data["title"] = title
    material = await prisma.material.create(data=data)
    logger.info("Created material record %s (pending) for user %s", material.id, uid)
    return str(material.id)


async def process_material_by_id(
    material_id: str,
    file_path: str,
    filename: str,
    user_id: str,
    notebook_id: Optional[str] = None,
) -> None:
    """Run the full document processing pipeline for a file already on disk.

    This is called by the background worker **after** the upload route has
    already created the Material record (status ``pending``).

    Pipeline:
      1. ``pending``    → ``processing``  (or ``ocr_running`` / ``transcribing``)
      2. Extract text   (run in thread-pool executor — CPU-bound)
      3. ``processing`` → ``embedding``
      4. Chunk + embed  (run in thread-pool executor — CPU-bound)
      5.               → ``completed``

    On any failure the record is updated to ``failed`` with the error message.
    The exception is **not** re-raised so the worker loop stays alive.
    """
    uid = str(user_id)
    nid = str(notebook_id) if notebook_id and notebook_id != "draft" else None
    loop = asyncio.get_running_loop()
    _t_total = time.perf_counter()

    try:
        await _set_status(material_id, "processing", user_id=uid)

        from app.services.text_processing.extractor import EnhancedTextExtractor
        from app.services.text_processing.file_detector import FileTypeDetector

        # Choose a granular transient status based on file category
        file_info = FileTypeDetector.detect_file_type(file_path)
        category = file_info.get("category", "document")
        if category == "image":
            await _set_status(material_id, "ocr_running", user_id=uid)
        elif category in ("audio", "video"):
            await _set_status(material_id, "transcribing", user_id=uid)

        # Text extraction is CPU/IO-bound — run in thread pool
        extractor = EnhancedTextExtractor()
        _t_extract = time.perf_counter()
        result = await loop.run_in_executor(
            None,
            partial(extractor.extract_text, file_path, source_type="file"),
        )
        logger.info(
            "PERF extraction: %.1fms  material=%s  category=%s",
            (time.perf_counter() - _t_extract) * 1000, material_id, category,
        )

        if result["status"] != "success":
            error_msg = result.get("error", "unknown extraction error")
            await _fail_material(material_id, f"Extraction failed: {error_msg}", user_id=uid)
            return

        extraction_metadata = result.get("metadata", {})
        # Persist the original upload path so downstream tools (data_profiler,
        # workspace_builder) can locate the raw file without re-deriving the path.
        extraction_metadata["upload_path"] = file_path
        await _process_material(
            material_id,
            result["text"],
            uid,
            nid,
            filename=filename,
            extraction_metadata=extraction_metadata,
            # source_type lives at the top level of the extraction result, NOT
            # inside result["metadata"], so we must read it from result directly.
            source_type=result.get("source_type") or extraction_metadata.get("source_type", "prose"),
        )
        logger.info(
            "PERF process_material_by_id total: %.1fms  material=%s",
            (time.perf_counter() - _t_total) * 1000, material_id,
        )

    except Exception as exc:
        tb = traceback.format_exc()
        await _fail_material(material_id, f"{exc}\n{tb}", user_id=uid)


async def filter_completed_material_ids(
    material_ids: List[str],
    user_id: str,
) -> List[str]:
    """Return only the material IDs that are ``completed`` and owned by *user_id*.

    Insert this guard before every RAG call so that partially-processed or
    failed materials are never searched.

    Args:
        material_ids: Candidate IDs supplied by the client.
        user_id:      The authenticated user — authorisation check included.

    Returns:
        Filtered list preserving original order.
    """
    if not material_ids:
        return []
    # status is an enum in Prisma; pass the string value
    materials = await prisma.material.find_many(
        where={"id": {"in": material_ids}, "userId": str(user_id), "status": "completed"},
    )
    completed_set = {str(m.id) for m in materials}
    # Preserve caller order
    return [mid for mid in material_ids if mid in completed_set]


async def process_url_material_by_id(
    material_id: str,
    url: str,
    user_id: str,
    notebook_id: Optional[str] = None,
    source_type: str = "auto",
):
    """Process a URL material that already has a pending DB record."""
    uid, nid = str(user_id), str(notebook_id) if notebook_id and notebook_id != "draft" else None
    
    try:
        await _set_status(material_id, "processing", user_id=uid)

        from app.services.text_processing.extractor import EnhancedTextExtractor

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            partial(EnhancedTextExtractor().extract_text, url, source_type=source_type),
        )

        if result["status"] != "success":
            error_msg = result.get("error", "unknown extraction error")
            await _fail_material(material_id, f"URL extraction failed: {error_msg}", user_id=uid)
            return

        title = result.get("title", url)
        extraction_metadata = result.get("metadata", {})
        # Use title or the URL domain as the human-readable filename
        from urllib.parse import urlparse as _urlparse
        _parsed = _urlparse(url)
        url_filename = title or _parsed.netloc or url

        await _process_material(
            material_id,
            result["text"],
            uid,
            nid,
            title=title,
            filename=url_filename,
            extraction_metadata=extraction_metadata,
            source_type=extraction_metadata.get("source_type", "prose"),
        )

    except Exception as exc:
        tb = traceback.format_exc()
        await _fail_material(material_id, f"{exc}\n{tb}", user_id=uid)


async def process_url_material(
    url: str,
    user_id,
    notebook_id=None,
    source_type: str = "auto",
):
    """Process content from a URL (Legacy sync wrapper)."""
    uid, nid = str(user_id), str(notebook_id) if notebook_id and notebook_id != "draft" else None

    data: dict = {
        "filename": url,
        "userId": uid,
        "status": "pending",
        "sourceType": source_type,
    }
    if nid:
        data["notebookId"] = nid
    material = await prisma.material.create(data=data)

    await process_url_material_by_id(material.id, url, uid, nid, source_type)
    return await prisma.material.find_unique(where={"id": material.id})


async def process_text_material_by_id(
    material_id: str,
    text_content: str,
    title: str,
    user_id: str,
    notebook_id: Optional[str] = None,
):
    """Process direct text input that already has a pending DB record."""
    uid, nid = str(user_id), str(notebook_id) if notebook_id and notebook_id != "draft" else None

    try:
        await _set_status(material_id, "processing", user_id=uid)
        await _process_material(material_id, text_content, uid, nid, title=title, filename=title)
    except Exception as exc:
        tb = traceback.format_exc()
        await _fail_material(material_id, f"{exc}\n{tb}", user_id=uid)


async def process_text_material(
    text_content: str,
    title: str,
    user_id,
    notebook_id=None,
):
    """Process direct text input (Legacy sync wrapper)."""
    uid, nid = str(user_id), str(notebook_id) if notebook_id and notebook_id != "draft" else None

    data: dict = {
        "filename": title,
        "title": title,
        "userId": uid,
        "status": "pending",
        "sourceType": "text",
    }
    if nid:
        data["notebookId"] = nid
    material = await prisma.material.create(data=data)

    await process_text_material_by_id(material.id, text_content, title, uid, nid)
    return await prisma.material.find_unique(where={"id": material.id})


# ── Query helpers ─────────────────────────────────────────────


async def get_material(material_id: str):
    return await prisma.material.find_unique(where={"id": material_id})


async def get_material_for_user(material_id: str, user_id):
    return await prisma.material.find_first(
        where={"id": str(material_id), "userId": str(user_id)}
    )


async def get_material_text(material_id: str, user_id: str) -> Optional[str]:
    """Retrieve full text for a material from file storage.
    
    Use this helper when you need the full text for generation tasks
    (PPT, podcast, flashcards, quiz, etc.).
    
    Args:
        material_id: Material ID
        user_id: User ID (for authorization)
    
    Returns:
        Full text content or None if not found/unauthorized
    """
    # Verify ownership
    material = await get_material_for_user(material_id, user_id)
    if not material:
        logger.warning(f"Material {material_id} not found or unauthorized for user {user_id}")
        return None
    
    # Load from storage (sync I/O → thread pool)
    try:
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, load_material_text, material_id)
        return text
    except FileNotFoundError:
        logger.error(f"Full text file not found for material {material_id}")
        return None
    except Exception as e:
        logger.error(f"Failed to load text for material {material_id}: {e}")
        return None


async def get_user_materials(user_id, notebook_id=None) -> list:
    where: dict = {"userId": str(user_id)}
    if notebook_id and notebook_id != "draft":
        where["notebookId"] = str(notebook_id)
    elif notebook_id == "draft":
        where["notebookId"] = None
    return await prisma.material.find_many(where=where, order={"createdAt": "desc"})


async def update_material(
    material_id: str,
    user_id,
    filename: Optional[str] = None,
    title: Optional[str] = None,
):
    """Update material metadata. Returns updated record or ``None``."""
    material = await get_material_for_user(material_id, user_id)
    if not material:
        return None
    data: dict = {}
    if filename is not None:
        data["filename"] = filename
    if title is not None:
        data["title"] = title
    if not data:
        return material
    return await prisma.material.update(where={"id": material.id}, data=data)


async def delete_material(material_id: str, user_id) -> bool:
    """Delete material record and clean up ALL associated storage.

    Cleanup order: ChromaDB vectors → file storage → upload file → DB record.
    Storage is cleaned BEFORE the DB record is deleted so that on partial
    failure the reference is still intact and cleanup can be retried.
    """
    material = await get_material_for_user(material_id, user_id)
    if not material:
        return False

    loop = asyncio.get_running_loop()

    # 1. Delete ChromaDB embeddings (sync → thread pool)
    try:
        from app.db.chroma import get_collection
        collection = get_collection()
        await loop.run_in_executor(
            None, lambda: collection.delete(where={"material_id": str(material_id)})
        )
        logger.info("Deleted ChromaDB embeddings for material %s", material_id)
    except Exception as e:
        logger.warning("Failed to delete ChromaDB embeddings for material %s: %s", material_id, e)

    # 2. Delete extracted text file (sync → thread pool)
    try:
        await loop.run_in_executor(None, delete_material_text, material_id)
        logger.info("Deleted text storage for material %s", material_id)
    except Exception as e:
        logger.warning("Failed to delete text storage for material %s: %s", material_id, e)

    # 3. Delete original uploaded file on disk
    try:
        if material.filename:
            import glob
            upload_dir = os.path.join(settings.UPLOAD_DIR, str(user_id))
            pattern = os.path.join(upload_dir, f"*_{material.filename}")
            # Also try exact match with material_id prefix
            pattern2 = os.path.join(upload_dir, f"{material_id}_*")
            for p in (pattern, pattern2):
                for fpath in glob.glob(p):
                    if os.path.isfile(fpath):
                        os.remove(fpath)
                        logger.info("Deleted upload file: %s", fpath)
    except Exception as e:
        logger.warning("Failed to delete upload file for material %s: %s", material_id, e)

    # 4. Delete from database LAST (so reference exists for retry on earlier failures)
    await prisma.material.delete(where={"id": material.id})
    logger.info("Deleted material record %s", material_id)
    return True
