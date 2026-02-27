"""Explainer video generation routes.

Endpoints:
  POST /explainer/check-presentations  — Find existing PPTs for materials
  POST /explainer/generate             — Start explainer video generation
  GET  /explainer/{id}/status          — Poll generation progress
  GET  /explainer/{id}/video           — Download finished video
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.db.prisma_client import prisma
from app.services.auth import get_current_user
from app.services.explainer.processor import EXPLAINER_OUTPUT_DIR, process_explainer_video
from app.services.explainer.tts import get_voice_id, EDGE_TTS_VOICES

logger = logging.getLogger("explainer.route")
router = APIRouter()


# ── Request / Response models ─────────────────────────────


class CheckPresentationsRequest(BaseModel):
    material_ids: list[str] = Field(..., min_length=1)
    notebook_id: str


class GenerateExplainerRequest(BaseModel):
    material_ids: list[str] = Field(..., min_length=1)
    notebook_id: str
    ppt_language: str = Field(default="en", description="Language for PPT content")
    narration_language: str = Field(default="en", description="Language for voice narration")
    voice_gender: str = Field(default="female", pattern="^(male|female)$")
    presentation_id: Optional[str] = None  # Reuse an existing presentation
    create_new_ppt: bool = False


# ── Helpers ───────────────────────────────────────────────


SUPPORTED_LANGUAGES = list(EDGE_TTS_VOICES.keys())


def _validate_language(lang: str, label: str) -> None:
    if lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported {label}: '{lang}'. Supported: {', '.join(SUPPORTED_LANGUAGES)}",
        )


# ── Routes ────────────────────────────────────────────────


@router.post("/explainer/check-presentations")
async def check_presentations(
    request: CheckPresentationsRequest,
    current_user=Depends(get_current_user),
):
    """Check if presentations already exist for the given materials."""
    user_id = str(current_user.id)

    # Find GeneratedContent with contentType='presentation' created by this user
    # in this notebook, matching any of the material IDs.
    presentations = await prisma.generatedcontent.find_many(
        where={
            "userId": user_id,
            "notebookId": request.notebook_id,
            "contentType": "presentation",
        },
        order={"createdAt": "desc"},
    )

    # Filter to only those that match the requested material_ids
    matching = []
    requested_set = set(request.material_ids)
    for pres in presentations:
        # Check via materialId (single material) or materialIds array
        pres_materials = set(pres.materialIds or [])
        if pres.materialId and pres.materialId in requested_set:
            pres_materials.add(pres.materialId)

        # Match if there's any overlap
        if pres_materials & requested_set:
            data = pres.data if isinstance(pres.data, dict) else {}
            matching.append({
                "id": str(pres.id),
                "title": pres.title or data.get("title", "Untitled"),
                "slide_count": data.get("slide_count", 0),
                "created_at": pres.createdAt.isoformat() if pres.createdAt else None,
                "language": pres.language,
            })

    return {
        "found": len(matching) > 0,
        "presentations": matching,
    }


@router.post("/explainer/generate")
async def generate_explainer(
    request: GenerateExplainerRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
):
    """Start an explainer video generation job.

    If presentation_id is provided, reuses that presentation.
    If create_new_ppt is True or no presentation_id given, generates a new one first.
    """
    user_id = str(current_user.id)

    _validate_language(request.ppt_language, "PPT language")
    _validate_language(request.narration_language, "narration language")

    voice_id = get_voice_id(request.narration_language, request.voice_gender)

    # ── Resolve or create presentation ────────────────────
    presentation = None
    presentation_data: dict = {}
    presentation_html: str = ""

    if request.presentation_id and not request.create_new_ppt:
        # Reuse existing presentation
        presentation = await prisma.generatedcontent.find_first(
            where={
                "id": request.presentation_id,
                "userId": user_id,
                "contentType": "presentation",
            }
        )
        if not presentation:
            raise HTTPException(status_code=404, detail="Presentation not found")

        presentation_data = presentation.data if isinstance(presentation.data, dict) else {}
        presentation_html = presentation_data.get("html", "")
        if not presentation_html:
            raise HTTPException(status_code=400, detail="Presentation has no HTML content")
    else:
        # Generate a new presentation first
        from app.services.ppt.generator import generate_presentation
        from app.routes.utils import require_materials_text, require_material_text

        ids = request.material_ids
        if len(ids) == 1:
            text = await require_material_text(ids[0], user_id)
        else:
            text = await require_materials_text(ids, user_id)

        result = await generate_presentation(
            material_text=text,
            user_id=user_id,
        )

        # Save the generated presentation to DB
        # Prisma Python requires json.dumps() for Json fields
        create_data: dict = {
            "notebookId": request.notebook_id,
            "userId": user_id,
            "contentType": "presentation",
            "title": result.get("title", "Explainer Slides"),
            "data": json.dumps(result),
            "language": request.ppt_language,
            "materialIds": ids,
        }
        if len(ids) == 1:
            create_data["materialId"] = ids[0]

        presentation = await prisma.generatedcontent.create(data=create_data)
        presentation_data = result
        presentation_html = result.get("html", "")

    slide_count = presentation_data.get("slide_count", len(presentation_data.get("slides", [])))

    # ── Create ExplainerVideo record ──────────────────────
    explainer = await prisma.explainervideo.create(
        data={
            "userId": user_id,
            "presentationId": str(presentation.id),
            "pptLanguage": request.ppt_language,
            "narrationLanguage": request.narration_language,
            "voiceGender": request.voice_gender,
            "voiceId": voice_id,
            "status": "pending",
        }
    )

    explainer_id = str(explainer.id)

    # ── Estimate time (faster with parallel processing) ───
    estimated_minutes = max(1, slide_count * 0.5)

    # ── Launch background task ────────────────────────────
    background_tasks.add_task(
        process_explainer_video,
        explainer_id=explainer_id,
        presentation_data=presentation_data,
        presentation_html=presentation_html,
        narration_language=request.narration_language,
        voice_gender=request.voice_gender,
        voice_id=voice_id,
        user_id=user_id,
        notebook_id=request.notebook_id,
        material_ids=request.material_ids,
        slide_count=slide_count,
    )

    logger.info(
        "Explainer generation started | id=%s | user=%s | slides=%d | voice=%s | narration=%s",
        explainer_id, user_id, slide_count, voice_id, request.narration_language,
    )

    return {
        "explainer_id": explainer_id,
        "status": "pending",
        "estimated_time_minutes": round(estimated_minutes, 1),
        "slide_count": slide_count,
    }


@router.get("/explainer/{explainer_id}/status")
async def get_explainer_status(
    explainer_id: str,
    current_user=Depends(get_current_user),
):
    """Poll the status of an explainer video generation."""
    user_id = str(current_user.id)

    explainer = await prisma.explainervideo.find_first(
        where={"id": explainer_id, "userId": user_id}
    )
    if not explainer:
        raise HTTPException(status_code=404, detail="Explainer video not found")

    # Progress percentage based on status
    progress_map = {
        "pending": 0,
        "capturing_slides": 10,
        "generating_script": 30,
        "generating_audio": 55,
        "composing_video": 80,
        "completed": 100,
        "failed": 0,
    }

    return {
        "id": str(explainer.id),
        "status": explainer.status,
        "progress": progress_map.get(explainer.status, 0),
        "video_url": explainer.videoUrl,
        "duration": explainer.duration,
        "chapters": explainer.chapters,
        "error": explainer.error,
        "created_at": explainer.createdAt.isoformat() if explainer.createdAt else None,
        "completed_at": explainer.completedAt.isoformat() if explainer.completedAt else None,
    }


@router.get("/explainer/{explainer_id}/video")
async def get_explainer_video(
    explainer_id: str,
    current_user=Depends(get_current_user),
):
    """Download the finished explainer video."""
    user_id = str(current_user.id)

    explainer = await prisma.explainervideo.find_first(
        where={"id": explainer_id, "userId": user_id}
    )
    if not explainer:
        raise HTTPException(status_code=404, detail="Explainer video not found")

    if explainer.status != "completed":
        raise HTTPException(status_code=400, detail=f"Video not ready (status: {explainer.status})")

    video_path = os.path.join(EXPLAINER_OUTPUT_DIR, explainer_id, "explainer_final.mp4")
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found on disk")

    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=f"explainer_{explainer_id}.mp4",
    )
