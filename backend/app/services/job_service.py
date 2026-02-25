"""Background job service for tracking async task status."""

import json
from types import SimpleNamespace
from typing import Optional

from app.db.prisma_client import prisma
import logging

logger = logging.getLogger(__name__)


async def create_job(
    user_id: str,
    job_type: str,
    payload: Optional[dict] = None,
) -> str:
    """Create a new background job record.  Returns job ID.

    Args:
        user_id:  Owner of this job.
        job_type: Logical type label (e.g. ``"material_processing"``).
        payload:  Arbitrary JSON dict stored in the ``result`` column so the
                  worker can reconstruct everything it needs without a join.
    """
    data: dict = {
        "userId": user_id,
        "jobType": job_type,
        "status": "pending",
    }
    if payload is not None:
        # Prisma Python requires json.dumps() for Json? fields in create()
        data["result"] = json.dumps(payload)
    job = await prisma.backgroundjob.create(data=data)
    logger.info("Created background job %s type=%s for user=%s", job.id, job_type, user_id)
    return str(job.id)


async def fetch_next_pending_job(job_type: str = "material_processing"):
    """Atomically claim the oldest pending job of *job_type*.

    Uses ``UPDATE … WHERE id = (SELECT … FOR UPDATE SKIP LOCKED) RETURNING *``
    so that only ONE worker can claim any given job even when multiple workers
    run concurrently.  If the raw-SQL path fails (e.g. unit-test mock) the
    function returns ``None`` rather than raising.

    Returns a SimpleNamespace with ``id`` and ``result`` attributes (mirroring
    the Prisma ORM object shape) or ``None`` when the queue is empty.
    """
    try:
        rows = await prisma.query_raw(
            """
            UPDATE background_jobs
            SET    status     = 'processing',
                   updated_at = NOW()
            WHERE  id = (
                SELECT id
                FROM   background_jobs
                WHERE  status   = 'pending'
                  AND  job_type = $1
                ORDER BY created_at ASC
                LIMIT  1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id, status, job_type, result, error, user_id,
                      created_at, updated_at
            """,
            job_type,
        )
    except Exception as exc:
        logger.debug(
            "fetch_next_pending_job: raw SQL failed (%s) — queue check skipped.", exc
        )
        return None

    if not rows:
        return None

    row = rows[0]

    # result column is JSONB → asyncpg already deserialises to dict or None.
    # Guard against it coming back as a raw string in edge-case environments.
    raw_result = row.get("result")
    if isinstance(raw_result, str):
        try:
            raw_result = json.loads(raw_result)
        except (ValueError, TypeError):
            raw_result = {}

    return SimpleNamespace(
        id=str(row["id"]),
        result=raw_result or {},
        status=row.get("status", "processing"),
        jobType=row.get("job_type", job_type),
        userId=str(row.get("user_id", "")),
    )


async def update_job_status(
    job_id: str,
    status: str,
    result: dict = None,
    error: str = None,
) -> None:
    """Update a background job's status, result, or error."""
    data: dict = {"status": status}
    if result is not None:
        data["result"] = json.dumps(result) if isinstance(result, (dict, list)) else result
    if error is not None:
        data["error"] = error

    await prisma.backgroundjob.update(
        where={"id": job_id},
        data=data,
    )
    logger.info(f"Updated job {job_id} status={status}")


async def get_job(job_id: str, user_id: str):
    """Get a job by ID, verifying user ownership."""
    return await prisma.backgroundjob.find_first(
        where={
            "id": job_id,
            "userId": user_id,
        }
    )
