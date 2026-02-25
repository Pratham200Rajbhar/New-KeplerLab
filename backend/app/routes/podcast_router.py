"""Podcast generation and audio serving route."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
import logging
import os
import uuid

from app.services.podcast.generator import generate_podcast_audio_async
from app.services.auth import get_current_user, create_file_token
from app.core.config import settings
from .utils import safe_path, require_material_text, require_file_token_for_user

logger = logging.getLogger(__name__)
router = APIRouter()


class PodcastRequest(BaseModel):
    material_id: str


def _save_audio(audio_buffer, title: str, user_id: str) -> tuple[str, str]:
    """Save audio buffer to disk, return (filename, filepath)."""
    user_dir = os.path.join(settings.PODCAST_OUTPUT_DIR, user_id)
    os.makedirs(user_dir, exist_ok=True)

    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)
    filename = f"{safe_title.replace(' ', '_')[:50] or 'podcast'}_{uuid.uuid4().hex[:6]}.wav"
    filepath = os.path.join(user_dir, filename)

    with open(filepath, "wb") as f:
        f.write(audio_buffer.read())
    return filename, filepath


@router.post("/podcast")
async def generate_podcast(
    request: PodcastRequest,
    current_user=Depends(get_current_user),
):
    """Generate podcast and return metadata for preview."""
    text = await require_material_text(request.material_id, current_user.id)

    logger.info(f"Generating podcast for material: {request.material_id}")
    audio_buffer, title, dialogue_timing = await generate_podcast_audio_async(text)

    filename, _ = _save_audio(audio_buffer, title, str(current_user.id))
    logger.info(f"Podcast saved: {filename}")

    return {
        "title": title,
        "audio_filename": filename,
        "material_id": request.material_id,
        "dialogue": dialogue_timing,
        "file_token": create_file_token(str(current_user.id)),
    }


@router.get("/podcast/audio/{user_id}/{filename}")
async def get_podcast_audio(
    user_id: str,
    filename: str,
    token: str = Query(..., description="Signed file access token"),
):
    """Serve the generated podcast audio file. Requires signed file token."""
    await require_file_token_for_user(token, user_id)

    audio_path = safe_path(settings.PODCAST_OUTPUT_DIR, user_id, filename)
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(path=audio_path, media_type="audio/wav", headers={"Cache-Control": "no-cache"})


@router.post("/podcast/download")
async def download_podcast(
    request: PodcastRequest,
    current_user=Depends(get_current_user),
):
    """Generate and download podcast directly."""
    text = await require_material_text(request.material_id, current_user.id)

    audio_buffer, title, _ = await generate_podcast_audio_async(text)
    filename, filepath = _save_audio(audio_buffer, title, str(current_user.id))

    return FileResponse(path=filepath, media_type="audio/wav", filename=filename)
