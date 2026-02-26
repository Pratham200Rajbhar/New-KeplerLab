"""Async background worker — document processing pipeline.

A single ``asyncio.Task`` is created at application startup (``lifespan``
in ``main.py``).  It runs an infinite loop that:

1. Fetches the oldest ``pending`` ``material_processing`` job.
2. Atomically claims it (``status → processing``).
3. Delegates to :func:`process_material_by_id`.
4. Marks the job ``completed`` or ``failed``.

The worker never raises — all exceptions are caught, logged, and stored on
the job record so the loop continues for subsequent jobs.

Status lifecycle
----------------
::

    [upload route]
    pending ─────┐
                 │ worker picks up job
                 ▼
             processing ──► ocr_running / transcribing (transient)
                 │
                 ▼
             embedding
                 │
                 ▼
             completed
                 │ (on any error)
                 └──► failed
"""

from __future__ import annotations

import asyncio
import logging
import time

from app.db.prisma_client import get_prisma
from app.services.job_service import fetch_next_pending_job
from app.services.material_service import (
    process_material_by_id,
    process_url_material_by_id,
    process_text_material_by_id,
)
from app.services.storage_service import load_material_text

logger = logging.getLogger(__name__)

_POLL_SECONDS: float = 2.0    # idle wait between queue checks
_ERROR_BACKOFF: float = 5.0   # extra wait after an unexpected error
MAX_CONCURRENT_JOBS: int = 5  # Maximum number of concurrent resource extractions
_STUCK_JOB_TIMEOUT_MINUTES: int = 30  # Jobs processing longer than this are considered stuck


# ── Stuck Job Recovery ──────────────────────────────────────────

async def _recover_stuck_jobs() -> None:
    """Reset jobs stuck in 'processing' state back to 'pending'.

    Called once at startup. If the server crashed mid-processing, affected
    jobs would remain in 'processing' forever since no worker will pick
    them up (workers only claim 'pending' jobs).

    Only resets jobs older than _STUCK_JOB_TIMEOUT_MINUTES to avoid
    interfering with legitimately running jobs in multi-worker setups.
    """
    try:
        result = await get_prisma().query_raw(
            """
            UPDATE background_jobs
            SET    status     = 'pending',
                   updated_at = NOW(),
                   error      = 'Auto-reset: stuck in processing after server restart'
            WHERE  status     = 'processing'
              AND  updated_at < NOW() - INTERVAL '1 minute' * $1::int
            RETURNING id
            """,
            _STUCK_JOB_TIMEOUT_MINUTES,
        )
        if result:
            logger.warning(
                "[WORKER] Recovered %d stuck job(s) → reset to pending: %s",
                len(result), [r["id"] for r in result],
            )
    except Exception as exc:
        logger.warning("[WORKER] Stuck job recovery failed (non-fatal): %s", exc)


# ── Event-driven job queue notification ───────────────────────

class _JobQueue:
    """Event-driven notification for the background worker.

    Instead of polling every 2 seconds, call ``notify()`` after creating
    a BackgroundJob so the worker wakes up immediately.
    Falls back to periodic polling if no notification arrives.
    """

    def __init__(self):
        self._event = asyncio.Event()

    def notify(self):
        """Wake the worker immediately (called from upload routes)."""
        self._event.set()

    async def wait(self, timeout: float = _POLL_SECONDS):
        """Wait for notification or timeout (fallback polling)."""
        try:
            await asyncio.wait_for(self._event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass
        self._event.clear()


job_queue = _JobQueue()


async def job_processor() -> None:
    """Long-running coroutine — start as an ``asyncio.Task`` at startup.

    Polls the ``background_jobs`` table for pending material-processing jobs
    and processes up to MAX_CONCURRENT_JOBS concurrently using asyncio.Task objects.
    Runs until the process exits.
    """
    logger.info("Background job processor started (poll_interval=%.1fs, concurrent_limit=%d)", _POLL_SECONDS, MAX_CONCURRENT_JOBS)

    # Recover jobs stuck from a previous crash
    await _recover_stuck_jobs()

    active_tasks: set[asyncio.Task] = set()

    while True:
        try:
            # 1. Clean up completed tasks
            # Collect results / surface exceptions (although _process_job should catch all)
            done = {t for t in active_tasks if t.done()}
            for t in done:
                active_tasks.remove(t)
                try:
                    await t
                except Exception as e:
                    logger.exception("Task explicitly failed inside worker pool: %s", e)

            # 2. Fill up to maximum concurrent capacity
            jobs_to_fetch = MAX_CONCURRENT_JOBS - len(active_tasks)
            jobs_added = 0

            if jobs_to_fetch > 0:
                for _ in range(jobs_to_fetch):
                    # Sequentially fetch and claim jobs to avoid race conditions via fetch_first -> update
                    job = await fetch_next_pending_job("material_processing")
                    # If queue empty, break early instead of burning loop cycles
                    if not job:
                        break
                    
                    # Create async task for this specific job
                    task = asyncio.create_task(_process_job(job))
                    active_tasks.add(task)
                    jobs_added += 1

            # 3. Wait block
            if not active_tasks:
                # Idle state: wait for notification or fallback poll
                await job_queue.wait(timeout=_POLL_SECONDS)
            else:
                # If we're at capacity OR there were no new jobs but we have active ones, 
                # wait until at least ONE task finishes so we can immediately pick up the next available job
                if len(active_tasks) >= MAX_CONCURRENT_JOBS or jobs_added == 0:
                     await asyncio.wait(active_tasks, return_when=asyncio.FIRST_COMPLETED)

        except Exception as exc:
            # Should never reach here unless absolute database failure occurs
            logger.exception("Unhandled error in job_processor event loop: %s", exc)
            await asyncio.sleep(_ERROR_BACKOFF)


async def _process_job(job) -> None:
    """Extract parameters from the claimed job and process it through the AI pipeline."""
    payload: dict = job.result or {}
    material_id: str | None = payload.get("material_id")
    user_id: str | None = payload.get("user_id")
    notebook_id: str | None = payload.get("notebook_id")
    source_type: str = payload.get("source_type", "file")

    if not material_id or not user_id:
        logger.error(
            "Job %s has incomplete payload — marking failed.  payload=%s",
            job.id, payload,
        )
        await _fail_job(job.id, "Incomplete job payload: missing material_id or user_id")
        return

    logger.info(
        "Processing job %s | material=%s type=%s user=%s",
        job.id, material_id, source_type, user_id,
    )
    _t_job = time.perf_counter()

    # ── Run pipeline ────────────────────────────────────────────────
    try:
        if source_type == "file":
            file_path: str | None = payload.get("file_path")
            filename: str = payload.get("filename", "unknown")
            if not file_path:
                raise ValueError("Missing file_path for file source_type")
            await process_material_by_id(
                material_id=material_id,
                file_path=file_path,
                filename=filename,
                user_id=user_id,
                notebook_id=notebook_id,
            )
        elif source_type in ("url", "youtube"):
            url: str | None = payload.get("url")
            if not url:
                raise ValueError("Missing url for url source_type")
            await process_url_material_by_id(
                material_id=material_id,
                url=url,
                user_id=user_id,
                notebook_id=notebook_id,
                source_type=source_type,
            )
        elif source_type == "text":
            text: str | None = payload.get("text")
            title: str = payload.get("title", "unknown")
            if not text:
                raise ValueError("Missing text content for text source_type")
            await process_text_material_by_id(
                material_id=material_id,
                text_content=text,
                title=title,
                user_id=user_id,
                notebook_id=notebook_id,
            )
        else:
            raise ValueError(f"Unknown source_type: {source_type}")
        job_processing_time = (time.perf_counter() - _t_job) * 1000
        await get_prisma().backgroundjob.update(
            where={"id": job.id},
            data={"status": "completed"},
        )
        logger.info(
            "[WORKER] job_processing_time=%.1fms  job=%s  material=%s  status=completed",
            job_processing_time, job.id, material_id,
        )
        # ── Optional: improve notebook name with LLM now that text is ready ──
        # This runs AFTER 202 was already returned, so it never blocks upload.
        if notebook_id:
            await _maybe_rename_notebook(notebook_id, material_id)
    except Exception as exc:
        job_processing_time = (time.perf_counter() - _t_job) * 1000
        logger.exception(
            "[WORKER] job_processing_time=%.1fms  job=%s  material=%s  status=failed  error=%s",
            job_processing_time, job.id, material_id, exc,
        )
        await _fail_job(job.id, str(exc))


async def _fail_job(job_id: str, error: str) -> None:
    """Update job to ``failed`` status with the error message."""
    try:
        await get_prisma().backgroundjob.update(
            where={"id": job_id},
            data={"status": "failed", "error": error},
        )
    except Exception as exc:
        logger.error("Could not mark job %s as failed: %s", job_id, exc)


# ── Auto-generated names that should be upgraded by LLM ───────────────────────
_AUTO_NAME_PREFIXES = ("notebook ", "untitled")


async def _maybe_rename_notebook(notebook_id: str, material_id: str) -> None:
    """If the notebook still has an auto-generated placeholder name, use the
    material's extracted text to generate a better title via LLM.

    This runs entirely inside the background worker — it never blocks the HTTP
    upload response.  Failures are logged and silently ignored.
    """
    if notebook_id == "draft":
        return

    try:
        notebook = await get_prisma().notebook.find_unique(where={"id": notebook_id})
        if notebook is None:
            return

        current_name: str = (notebook.name or "").strip()

        # Only improve clearly auto-generated placeholder names
        if not any(current_name.lower().startswith(p) for p in _AUTO_NAME_PREFIXES):
            return  # Already has a meaningful name — skip

        # Load the extracted text saved by the processing pipeline
        loop = asyncio.get_running_loop()
        from functools import partial
        text: str = await loop.run_in_executor(
            None, partial(load_material_text, material_id)
        ) or ""
        if len(text.strip()) < 30:
            return  # Not enough content for a good name

        # Generate better name with LLM (blocking call — off event loop via executor)
        from app.services.notebook_name_generator import generate_notebook_name
        new_name: str = await loop.run_in_executor(
            None, partial(generate_notebook_name, text[:2000], None)
        )
        if not new_name or len(new_name) < 3 or new_name == current_name:
            return

        await get_prisma().notebook.update(
            where={"id": notebook_id},
            data={"name": new_name},
        )
        logger.info(
            "[WORKER] notebook_renamed  id=%s  old='%s'  new='%s'",
            notebook_id, current_name, new_name,
        )
    except Exception as exc:
        logger.warning("[WORKER] _maybe_rename_notebook failed (non-fatal): %s", exc)
