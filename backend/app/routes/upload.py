import asyncio
import logging
import os
import shutil
import tempfile
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, Depends, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from urllib.parse import urlparse, parse_qs

from app.services.material_service import (
    create_material_record,
    process_url_material,
    process_text_material,
    get_user_materials,
    delete_material,
    update_material,
    get_material_for_user,
)
from app.services.job_service import create_job
from app.services.notebook_service import create_notebook
from app.services.auth import get_current_user
from app.services.text_processing.file_detector import FileTypeDetector
from app.services.text_processing.youtube_service import YouTubeService
from app.services.text_processing.web_scraping import WebScrapingService
from app.services.file_validator import validate_upload, FileValidationError
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = settings.UPLOAD_DIR
MAX_UPLOAD_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

# ── Allowed MIME types (server-side whitelist) ────────────────────
ALLOWED_MIME_TYPES: set[str] = set(FileTypeDetector.SUPPORTED_TYPES.keys())


# ── Unified error response ────────────────────────────────────────


def _upload_error(
    status_code: int,
    error_code: str,
    message: str,
    details: str = "",
) -> JSONResponse:
    """Return a structured upload error in the unified format."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error_code": error_code,
            "message": message,
            "details": details,
            "request_id": uuid.uuid4().hex,
        },
    )


# ── Validation helpers ────────────────────────────────────────────


async def _validate_upload_file(file: UploadFile, temp_path: str) -> Optional[JSONResponse]:
    """Run strict security validation on uploaded file.

    Intentionally lightweight — only reads the file header (via python-magic)
    and stat().  The sync call is offloaded to a thread-pool executor so it
    never blocks the event loop.

    Returns an error response on failure, or ``None`` if validation passes.
    """
    file_size = os.path.getsize(temp_path)
    loop = asyncio.get_event_loop()

    try:
        # python-magic reads a few hundred header bytes — sync I/O offloaded
        # to thread pool so the event loop is never stalled.
        from functools import partial
        validation_result = await loop.run_in_executor(
            None,
            partial(
                validate_upload,
                file_path=temp_path,
                filename=file.filename or "unknown",
                file_size=file_size,
            ),
        )
        logger.info(
            "Validation passed: %s -> %s (%s)",
            validation_result["original_filename"],
            validation_result["internal_filename"],
            validation_result["mime_type"],
        )
        return None

    except FileValidationError as e:
        logger.warning("File validation failed: %s", e)
        return _upload_error(400, "VALIDATION_FAILED", "File validation failed", str(e))
    except Exception as e:
        logger.error("Unexpected validation error: %s", e)
        return _upload_error(500, "VALIDATION_ERROR", "Could not validate file", str(e))


class URLUploadRequest(BaseModel):
    url: str
    notebook_id: Optional[str] = None
    auto_create_notebook: Optional[bool] = False
    source_type: Optional[str] = "auto"  # 'auto', 'web', 'youtube'
    title: Optional[str] = None


class TextUploadRequest(BaseModel):
    text: str
    title: str
    notebook_id: Optional[str] = None
    auto_create_notebook: Optional[bool] = False


@router.post("/upload", status_code=202)
async def upload_file(
    file: UploadFile,
    notebook_id: Optional[str] = Form(None),
    auto_create_notebook: Optional[str] = Form(None),
    current_user=Depends(get_current_user),
):
    """Accept a file upload, validate it, and enqueue async processing.

    Returns **HTTP 202 Accepted** immediately.  Heavy work (text extraction,
    OCR, transcription, chunking, embedding) runs in the background worker.

    Poll status via:
      - ``GET /jobs/{job_id}``
      - ``GET /materials`` (check ``status`` field on the material)

    Status lifecycle:
        pending → processing → [ocr_running | transcribing] → embedding → completed
    """
    temp_path = None
    final_path = None
    try:
        _t_total = time.perf_counter()
        logger.info(
            "[UPLOAD] START  file=%s  user=%s",
            file.filename, current_user.id,
        )

        # ── 1. Stream file to temp path (chunked async write) ─────────────
        # 1 MiB chunks → never loads full file into memory, never blocks
        # the event loop. This delegates chunk writing to a thread-pool.
        _t_write = time.perf_counter()
        loop = asyncio.get_event_loop()
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
            temp_path = tmp.name
            while chunk := await file.read(1024 * 1024):
                await loop.run_in_executor(None, tmp.write, chunk)
        file_write_time = (time.perf_counter() - _t_write) * 1000
        file_size_bytes = os.path.getsize(temp_path)
        logger.info(
            "[UPLOAD] file_write_time=%.1fms  file=%s  size=%d bytes",
            file_write_time, file.filename, file_size_bytes,
        )

        # ── 2. Lightweight validation (runs in thread pool) ────────────────
        # python-magic reads only the file header — fast and non-blocking.
        # No full-file read, no hash, no PDF structure inspection.
        _t_validate = time.perf_counter()
        validation_err = await _validate_upload_file(file, temp_path)
        if validation_err:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            return validation_err
        logger.info(
            "[UPLOAD] validation_time=%.1fms  file=%s",
            (time.perf_counter() - _t_validate) * 1000, file.filename,
        )

        # ── 3. Move to permanent storage with UUID-safe name ──────────────
        user_upload_dir = os.path.join(UPLOAD_DIR, str(current_user.id))
        os.makedirs(user_upload_dir, exist_ok=True)
        unique_name = f"{uuid.uuid4().hex}_{file.filename}"
        final_path = os.path.join(user_upload_dir, unique_name)
        shutil.move(temp_path, final_path)
        temp_path = None
        logger.info("[UPLOAD] file_saved  path=%s", final_path)

        # ── 4. Optional notebook auto-creation ────────────────────────────
        # Instant: derive name from filename stem only — NO LLM, NO I/O.
        # Worker will optionally improve the name after full processing.
        nb_id: Optional[str] = notebook_id or None
        created_notebook = None
        if auto_create_notebook == "true" and not nb_id:
            stem = os.path.splitext(file.filename or "upload")[0][:40].strip()
            notebook_name = stem if stem else f"Notebook {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            created_notebook = await create_notebook(str(current_user.id), notebook_name, None)
            nb_id = created_notebook.id
            logger.info("[UPLOAD] auto_notebook  name='%s'  id=%s", notebook_name, nb_id)

        # ── 5 & 6. Insert Material + BackgroundJob (both → pending) ───────
        # Two fast DB inserts — nothing else happens in the request lifecycle.
        _t_db = time.perf_counter()
        material_id = await create_material_record(
            filename=file.filename,
            user_id=current_user.id,
            notebook_id=nb_id,
            source_type="file",
        )
        job_id = await create_job(
            user_id=str(current_user.id),
            job_type="material_processing",
            payload={
                "material_id": material_id,
                "file_path": final_path,
                "filename": file.filename,
                "user_id": str(current_user.id),
                "notebook_id": str(nb_id) if nb_id else None,
            },
        )
        db_insert_time = (time.perf_counter() - _t_db) * 1000
        logger.info(
            "[UPLOAD] db_insert_time=%.1fms  material=%s  job=%s",
            db_insert_time, material_id, job_id,
        )

        # ── 7. Return HTTP 202 — done, worker takes it from here ──────────
        # Wake the worker immediately instead of waiting for next poll cycle
        from app.services.worker import job_queue
        job_queue.notify()

        total_upload_time = (time.perf_counter() - _t_total) * 1000
        # upload_request_time == total_upload_time: both measure the full
        # synchronous slice of the HTTP request lifecycle seen by this handler.
        upload_request_time = total_upload_time
        logger.info(
            "[UPLOAD] upload_request_time=%.1fms  total_upload_time=%.1fms  "
            "file_write_time=%.1fms  db_insert_time=%.1fms  "
            "material=%s  job=%s  target=<300ms %s",
            upload_request_time, total_upload_time, file_write_time, db_insert_time,
            material_id, job_id,
            "OK" if total_upload_time < 300 else "SLOW",
        )
        response_body: dict = {
            "material_id": material_id,
            "job_id": job_id,
            "filename": file.filename,
            "status": "pending",
        }
        if created_notebook:
            response_body["notebook"] = {
                "id": str(created_notebook.id),
                "name": created_notebook.name,
            }
        return JSONResponse(status_code=202, content=response_body)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Upload failed: %s", e)
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        return _upload_error(
            500,
            "UPLOAD_FAILED",
            "Upload failed",
            str(e) if str(e) else "An unexpected error occurred during upload.",
        )

async def _process_single_batch_file(file: UploadFile, current_user_id: str, nb_id: Optional[str]) -> dict:
    """Process a single file within a batch upload concurrently."""
    temp_path = None
    try:
        _t_batch_file_start = time.perf_counter()
        
        # ── Thread-pool offloaded file writing ──
        # Prevent large files from blocking the main async loop
        loop = asyncio.get_event_loop()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
            temp_path = tmp.name
            while chunk := await file.read(1024 * 1024):
                # Write chunk to disk in a separate thread
                await loop.run_in_executor(None, tmp.write, chunk)
                
        logger.info(
            "Batch stream: %.1fms  file=%s  size=%d bytes",
            (time.perf_counter() - _t_batch_file_start) * 1000,
            file.filename, os.path.getsize(temp_path),
        )

        # ── Validate File ──
        validation_err = await _validate_upload_file(file, temp_path)
        if validation_err:
            logger.warning("Validation failed for %s in batch", file.filename)
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            return {"filename": file.filename, "status": "error", "error": "File validation failed"}

        if not FileTypeDetector.is_supported(temp_path):
            file_info = FileTypeDetector.detect_file_type(temp_path)
            try:
                os.remove(temp_path)
            except OSError:
                pass
            return {
                "filename": file.filename,
                "status": "error",
                "error": f"Unsupported file type: {file_info['extension']}",
            }

        # ── Storage & DB ──
        user_upload_dir = os.path.join(UPLOAD_DIR, current_user_id)
        os.makedirs(user_upload_dir, exist_ok=True)
        unique_name = f"{uuid.uuid4().hex}_{file.filename}"
        final_path = os.path.join(user_upload_dir, unique_name)
        shutil.move(temp_path, final_path)
        temp_path = None

        material_id = await create_material_record(
            filename=file.filename,
            user_id=current_user_id,
            notebook_id=nb_id,
            source_type="file",
        )
        job_id = await create_job(
            user_id=current_user_id,
            job_type="material_processing",
            payload={
                "material_id": material_id,
                "file_path": final_path,
                "filename": file.filename,
                "user_id": current_user_id,
                "notebook_id": str(nb_id) if nb_id else None,
            },
        )
        from app.services.worker import job_queue
        job_queue.notify()
        
        return {
            "material_id": material_id,
            "job_id": job_id,
            "filename": file.filename,
            "status": "pending",
        }

    except Exception as e:
        logger.error("Failed to enqueue %s in batch: %s", file.filename, e)
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        return {"filename": file.filename, "status": "error", "error": str(e)}


@router.post("/upload/batch", status_code=202)
async def upload_batch(
    files: List[UploadFile],
    notebook_id: Optional[str] = Form(None),
    auto_create_notebook: Optional[str] = Form(None),
    current_user=Depends(get_current_user),
):
    """Accept a batch of file uploads and enqueue each for async processing concurrently.

    Returns **HTTP 202 Accepted**.  Each entry in ``materials`` has
    ``status: "pending"`` (or ``status: "error"`` if validation failed).
    """
    logger.info("Batch upload started: %d files user=%s", len(files), current_user.id)

    nb_id: Optional[str] = notebook_id or None
    created_notebook = None

    # ── 1. Optional single notebook for the whole batch ───────
    if auto_create_notebook == "true" and not nb_id and files:
        first_name = files[0].filename or "batch"
        stem = os.path.splitext(first_name)[0][:40].strip()
        notebook_name = stem if stem else f"Notebook {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        created_notebook = await create_notebook(str(current_user.id), notebook_name, None)
        nb_id = created_notebook.id
        logger.info("Auto-created notebook '%s' id=%s for batch", notebook_name, nb_id)

    # ── 2. Validate and enqueue each file concurrently ────────
    tasks = [
        _process_single_batch_file(file, str(current_user.id), nb_id)
        for file in files
    ]
    
    results = await asyncio.gather(*tasks)

    response: dict = {"materials": results}
    if created_notebook:
        response["notebook"] = {"id": str(created_notebook.id), "name": created_notebook.name}
    return JSONResponse(status_code=202, content=response)


@router.post("/upload/url", status_code=202)
async def upload_url(
    request: URLUploadRequest,
    current_user=Depends(get_current_user),
):
    """Upload and process content from a URL (web page or YouTube) asynchronously"""
    logger.info(f"URL upload started - {request.url} by user {current_user.id}")

    # Validate URL
    if not request.url.startswith(('http://', 'https://')):
        raise HTTPException(status_code=400, detail="Invalid URL format")

    # Determine source type
    source_type = request.source_type
    if source_type == "auto":
        youtube_service = YouTubeService()
        if youtube_service.is_youtube_url(request.url):
            source_type = "youtube"
        else:
            source_type = "url"

    nb_id = request.notebook_id
    created_notebook = None

    # Auto-create notebook if requested
    if request.auto_create_notebook and not nb_id:
        logger.info("Stage: Deriving notebook name from URL (no LLM)")
        try:
            if source_type == "youtube":
                # Quick title-only for YouTube to avoid slow full metadata
                vid = parse_qs(urlparse(request.url).query).get('v', [None])[0] or request.url.rstrip('/').split('/')[-1]
                content_preview = f"YouTube video {vid}"
            else:
                web_service = WebScrapingService()
                content_preview = web_service.get_page_title_fast(request.url) or request.url
        except Exception:
            content_preview = request.url

        notebook_name = content_preview[:50].strip() or f"Notebook {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        created_notebook = await create_notebook(str(current_user.id), notebook_name, None)
        nb_id = created_notebook.id
        logger.info(f"Stage: Created notebook '{notebook_name}' with id {nb_id}")

    # Create Material Record
    material_id = await create_material_record(
        filename=request.url,
        user_id=current_user.id,
        notebook_id=nb_id,
        source_type=source_type,
        title=request.title,
    )
    
    # Enqueue Background Job
    job_id = await create_job(
        user_id=str(current_user.id),
        job_type="material_processing",
        payload={
            "material_id": material_id,
            "url": request.url,
            "filename": request.url,
            "source_type": source_type,
            "user_id": str(current_user.id),
            "notebook_id": str(nb_id) if nb_id else None,
        },
    )
    from app.services.worker import job_queue
    job_queue.notify()

    response = {
        "material_id": material_id,
        "job_id": job_id,
        "filename": request.url,
        "title": request.title or request.url,
        "status": "pending",
        "source_type": source_type,
    }

    if created_notebook:
        response["notebook"] = {
            "id": str(created_notebook.id),
            "name": created_notebook.name,
        }

    return response


@router.post("/upload/text", status_code=202)
async def upload_text(
    request: TextUploadRequest,
    current_user=Depends(get_current_user),
):
    """Upload and process direct text content asynchronously"""
    logger.info(f"Text upload started - '{request.title}' by user {current_user.id}")

    # Validate text content
    if not request.text or len(request.text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Text content is too short (minimum 10 characters)")

    nb_id = request.notebook_id
    created_notebook = None

    # Auto-create notebook if requested
    if request.auto_create_notebook and not nb_id:
        logger.info("Stage: Deriving notebook name from text title (no LLM)")
        notebook_name = (request.title or "")[:50].strip() or f"Notebook {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        created_notebook = await create_notebook(str(current_user.id), notebook_name, None)
        nb_id = created_notebook.id
        logger.info(f"Stage: Created notebook '{notebook_name}' with id {nb_id}")

    # Create Material Record
    material_id = await create_material_record(
        filename=request.title,
        user_id=current_user.id,
        notebook_id=nb_id,
        source_type="text",
    )
    
    # Enqueue Background Job
    job_id = await create_job(
        user_id=str(current_user.id),
        job_type="material_processing",
        payload={
            "material_id": material_id,
            "text": request.text,
            "filename": request.title,
            "title": request.title,
            "source_type": "text",
            "user_id": str(current_user.id),
            "notebook_id": str(nb_id) if nb_id else None,
        },
    )
    from app.services.worker import job_queue
    job_queue.notify()

    response = {
        "material_id": material_id,
        "job_id": job_id,
        "filename": request.title,
        "title": request.title,
        "status": "pending",
        "source_type": "text",
    }

    if created_notebook:
        response["notebook"] = {
            "id": str(created_notebook.id),
            "name": created_notebook.name,
        }

    return response


@router.get("/upload/supported-formats")
async def get_supported_formats():
    """Get list of supported file formats and upload limits"""
    return {
        "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB,
        "file_extensions": FileTypeDetector.get_supported_extensions(),
        "categories": {
            "documents": ["pdf", "docx", "doc", "txt", "md", "pptx", "ppt", "xlsx", "xls", "csv", "rtf"],
            "images": ["jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp"],
            "audio": ["mp3", "wav", "m4a", "aac", "ogg", "flac"],
            "video": ["mp4", "avi", "mov", "mkv", "webm"],
            "web": ["youtube_urls", "web_pages"],
            "text": ["direct_text_input"]
        },
        "notes": {
            "ocr": "Images and scanned PDFs are processed using OCR",
            "transcription": "Audio and video files are transcribed using Whisper AI",
            "web_scraping": "Web pages are scraped for text content",
            "youtube": "YouTube videos use transcript extraction"
        }
    }


@router.get("/materials")
async def list_materials(
    notebook_id: Optional[str] = None,
    current_user=Depends(get_current_user),
):
    nb_id = notebook_id if notebook_id else None
    materials = await get_user_materials(current_user.id, nb_id)
    return [
        {
            "id": str(m.id),
            "filename": m.filename,
            "title": getattr(m, "title", None),
            "status": m.status,
            "chunk_count": m.chunkCount,
            "source_type": getattr(m, "sourceType", None) or "file",
            "created_at": m.createdAt.isoformat(),
            **({"error": m.error} if getattr(m, "error", None) else {}),
        }
        for m in materials
    ]


class MaterialUpdateBody(BaseModel):
    filename: Optional[str] = None
    title: Optional[str] = None


@router.patch("/materials/{material_id}")
async def patch_material(
    material_id: str,
    body: MaterialUpdateBody,
    current_user=Depends(get_current_user),
):
    updated = await update_material(
        material_id, current_user.id,
        filename=body.filename,
        title=body.title,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Material not found")
    return {
        "id": str(updated.id),
        "filename": updated.filename,
        "status": updated.status,
        "chunk_count": updated.chunkCount,
        "source_type": getattr(updated, "sourceType", None) or "file",
    }


@router.delete("/materials/{material_id}")
async def remove_material(
    material_id: str,
    current_user=Depends(get_current_user),
):
    deleted = await delete_material(material_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Material not found")
    return {"deleted": True}


@router.get("/materials/{material_id}/text")
async def get_material_text_endpoint(
    material_id: str,
    current_user=Depends(get_current_user),
):
    """Get full material text from file storage."""
    from app.services.material_service import get_material_text
    
    text = await get_material_text(material_id, str(current_user.id))
    if not text:
        raise HTTPException(status_code=404, detail="Material text not found")
    return {"text": text}
