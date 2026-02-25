"""Flashcard generation route."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional

from app.services.flashcard.generator import generate_flashcards
from app.services.auth import get_current_user
from .utils import require_material_text, require_materials_text

logger = logging.getLogger(__name__)
router = APIRouter()


class FlashcardRequest(BaseModel):
    material_id: Optional[str] = None
    material_ids: Optional[List[str]] = None
    topic: Optional[str] = None
    card_count: Optional[int] = None
    difficulty: Optional[str] = "Medium"
    additional_instructions: Optional[str] = None


@router.post("/flashcard")
async def create_flashcards(
    request: FlashcardRequest,
    current_user=Depends(get_current_user),
):
    ids = request.material_ids or ([request.material_id] if request.material_id else [])
    if not ids:
        raise HTTPException(status_code=400, detail="No material selected")

    if len(ids) == 1:
        text = await require_material_text(ids[0], current_user.id)
    else:
        text = await require_materials_text(ids, current_user.id)
    
    if request.topic and request.topic.strip():
        text = f"Focus on the topic: {request.topic}\n\nContent:\n{text}"

    try:
        flashcards = generate_flashcards(
            text,
            card_count=request.card_count,
            difficulty=request.difficulty,
            instructions=request.additional_instructions
        )
        return JSONResponse(content=flashcards)
    except Exception as e:
        logger.error(f"Flashcard generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate flashcards")

