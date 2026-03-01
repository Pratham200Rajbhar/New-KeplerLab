"""Mind map generation route."""

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.models.mindmap_schemas import MindMapRequest, MindMapResponse
from app.services.mindmap.generator import generate_mindmap
from app.services.auth import get_current_user
from app.db.prisma_client import get_prisma

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/mindmap")
async def create_mindmap(
    request: MindMapRequest,
    current_user=Depends(get_current_user),
):
    """Generate a mind map from selected materials."""
    if not request.material_ids:
        raise HTTPException(status_code=400, detail="No materials selected")

    # Verify notebook belongs to user
    prisma = get_prisma()
    notebook = await prisma.notebook.find_first(
        where={"id": request.notebook_id, "userId": str(current_user.id)}
    )
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    try:
        result = await generate_mindmap(
            material_ids=request.material_ids,
            notebook_id=request.notebook_id,
            user_id=str(current_user.id),
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Mind map generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate mind map")


@router.get("/mindmap/{notebook_id}")
async def get_mindmap(
    notebook_id: str,
    current_user=Depends(get_current_user),
):
    """Retrieve saved mind map for a notebook."""
    prisma = get_prisma()
    content = await prisma.generatedcontent.find_first(
        where={
            "notebookId": notebook_id,
            "contentType": "mindmap",
            "userId": str(current_user.id),
        }
    )
    if not content:
        raise HTTPException(status_code=404, detail="Mind map not found")

    data = content.data if isinstance(content.data, dict) else (json.loads(content.data) if content.data else {})
    return JSONResponse(content=data)


@router.delete("/mindmap/{id}")
async def delete_mindmap(
    id: str,
    current_user=Depends(get_current_user),
):
    """Delete a mind map."""
    prisma = get_prisma()
    content = await prisma.generatedcontent.find_first(
        where={
            "id": id,
            "contentType": "mindmap",
            "userId": str(current_user.id),
        }
    )
    if not content:
        raise HTTPException(status_code=404, detail="Mind map not found")

    await prisma.generatedcontent.delete(where={"id": id})
    return {"success": True}
