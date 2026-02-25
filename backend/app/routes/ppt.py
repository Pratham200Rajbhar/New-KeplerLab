"""Presentation (PPT) generation route.

Supports both synchronous generation and background-job-based generation.
All parameters except material_id are optional — the AI decides sensible defaults.
"""

from __future__ import annotations

import json
import traceback

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Optional
import os
import logging

from app.services.ppt.generator import generate_presentation
from app.services.auth import get_current_user
from app.services.job_service import create_job, update_job_status
from app.core.config import settings
from .utils import require_material, require_material_text, require_materials_text, safe_path

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request / Response models ─────────────────────────────


class PresentationRequest(BaseModel):
    """All fields except material_id are optional — AI picks smart defaults."""

    material_id: Optional[str] = None
    material_ids: Optional[list[str]] = None
    max_slides: Optional[int] = Field(
        default=None,
        ge=3,
        le=60,
        description="Target number of slides (3-60). AI decides if omitted.",
    )
    theme: Optional[str] = Field(
        default=None,
        description="Theme description, e.g. 'dark blue gradient', 'minimalist white'. AI decides if omitted.",
    )
    additional_instructions: Optional[str] = Field(
        default=None,
        description="Extra guidance for the AI, e.g. 'focus on key statistics', 'make it executive-level'.",
    )


# ── Synchronous endpoint ──────────────────────────────────


@router.post("/presentation")
async def generate_ppt(
    request: PresentationRequest,
    current_user=Depends(get_current_user),
):
    """Generate an HTML presentation from a material's full text.

    Returns the complete presentation data including HTML.
    """
    logger.info(
        "PPT request received | user=%s | material=%s | max_slides=%s | theme=%s",
        current_user.id,
        request.material_id,
        request.max_slides,
        request.theme,
    )

    ids = request.material_ids or ([request.material_id] if request.material_id else [])
    if not ids:
        raise HTTPException(status_code=400, detail="No material selected")

    if len(ids) == 1:
        text = await require_material_text(ids[0], current_user.id)
    else:
        text = await require_materials_text(ids, current_user.id)

    logger.info(
        "PPT material loaded | material_ids=%s | text_length=%d",
        ids,
        len(text),
    )

    try:
        result = await generate_presentation(
            material_text=text,
            user_id=str(current_user.id),
            max_slides=request.max_slides,
            theme=request.theme,
            additional_instructions=request.additional_instructions,
        )
        logger.info(
            "PPT generation successful | user=%s | title=%s | slides=%d | html_size=%d",
            current_user.id,
            result["title"],
            result["slide_count"],
            len(result["html"]),
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(
            "PPT generation FAILED | user=%s | material=%s | error=%s\n%s",
            current_user.id,
            request.material_id,
            str(e),
            traceback.format_exc(),
        )
        raise HTTPException(status_code=500, detail=f"Failed to generate presentation: {str(e)}")


# ── Background job endpoint ───────────────────────────────


@router.post("/presentation/async")
async def generate_ppt_async(
    request: PresentationRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
):
    """Start presentation generation as a background job.

    Returns a job_id that can be polled via GET /jobs/{job_id}.
    """
    logger.info(
        "PPT async request received | user=%s | material=%s",
        current_user.id,
        request.material_id,
    )

    text = await require_material_text(request.material_id, current_user.id)

    job_id = await create_job(str(current_user.id), "presentation")
    logger.info("PPT background job created | job_id=%s", job_id)

    background_tasks.add_task(
        _run_ppt_job,
        job_id,
        text,
        request.max_slides,
        request.theme,
        request.additional_instructions,
        str(current_user.id),
    )

    return {"job_id": job_id, "status": "pending"}


async def _run_ppt_job(
    job_id: str,
    text: str,
    max_slides: int | None,
    theme: str | None,
    additional_instructions: str | None,
    user_id: str,
) -> None:
    """Async background task — runs inside the running event loop via BackgroundTasks."""
    logger.info("PPT background job STARTED | job_id=%s | user=%s", job_id, user_id)
    try:
        await update_job_status(job_id, "processing")
        result = await generate_presentation(
            material_text=text,
            user_id=user_id,
            max_slides=max_slides,
            theme=theme,
            additional_instructions=additional_instructions,
        )
        await update_job_status(job_id, "completed", result=json.dumps(result))
        logger.info(
            "PPT background job COMPLETED | job_id=%s | title=%s | slides=%d",
            job_id,
            result["title"],
            result["slide_count"],
        )
    except Exception as exc:
        logger.error(
            "PPT background job FAILED | job_id=%s | error=%s",
            job_id,
            str(exc),
            exc_info=True,
        )
        await update_job_status(job_id, "failed", error=str(exc))


# ── Slide image serving endpoint ──────────────────────────


@router.get("/presentation/slides/{user_id}/{presentation_id}/{filename}")
@router.get("/api/presentation/slides/{user_id}/{presentation_id}/{filename}", include_in_schema=False)
async def get_slide_image(
    user_id: str,
    presentation_id: str, 
    filename: str,
    current_user=Depends(get_current_user)
):
    """Serve individual slide images.
    
    Only allows users to access their own slide images for security.
    """
    # Verify user can only access their own slides
    if str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Construct and validate file path
    presentations_dir = settings.PRESENTATIONS_OUTPUT_DIR
    slide_path = safe_path(presentations_dir, user_id, presentation_id, filename)
    
    if not os.path.exists(slide_path):
        logger.warning("Slide image not found: %s", slide_path)
        raise HTTPException(status_code=404, detail="Slide image not found")
    
    if not filename.endswith('.png'):
        raise HTTPException(status_code=400, detail="Invalid file format")
    
    return FileResponse(
        path=slide_path,
        media_type="image/png",
        filename=filename
    )
