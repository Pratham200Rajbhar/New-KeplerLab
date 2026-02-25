"""Background jobs polling endpoint."""

from fastapi import APIRouter, Depends, HTTPException

from app.services.auth import get_current_user
from app.services.job_service import get_job

router = APIRouter(prefix="/jobs")


@router.get("/{job_id}")
async def get_job_status(
    job_id: str,
    current_user=Depends(get_current_user),
):
    """Poll a background job's status."""
    job = await get_job(job_id, str(current_user.id))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    response = {
        "id": str(job.id),
        "type": job.jobType,
        "status": job.status,
        "created_at": job.createdAt.isoformat(),
        "updated_at": job.updatedAt.isoformat(),
    }
    if job.result is not None:
        response["result"] = job.result
    if job.error is not None:
        response["error"] = job.error
    return response
