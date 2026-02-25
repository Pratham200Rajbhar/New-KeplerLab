import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID

from app.services.auth import get_current_user
from app.services.notebook_service import (
    create_notebook,
    get_user_notebooks,
    get_notebook_by_id,
    update_notebook,
    delete_notebook,
    save_notebook_content,
    get_notebook_content,
    delete_notebook_content,
    update_notebook_content_title,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notebooks")


class NotebookCreate(BaseModel):
    name: str
    description: Optional[str] = None


class NotebookUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class NotebookResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.post("", response_model=NotebookResponse, status_code=status.HTTP_201_CREATED)
async def create_notebook_endpoint(
    request: NotebookCreate,
    current_user=Depends(get_current_user),
):
    notebook = await create_notebook(str(current_user.id), request.name, request.description)
    return NotebookResponse(
        id=str(notebook.id),
        name=notebook.name,
        description=notebook.description,
        created_at=notebook.createdAt.isoformat(),
        updated_at=notebook.updatedAt.isoformat()
    )


@router.get("", response_model=List[NotebookResponse])
async def list_notebooks(
    current_user=Depends(get_current_user),
):
    notebooks = await get_user_notebooks(str(current_user.id))
    return [
        NotebookResponse(
            id=str(n.id),
            name=n.name,
            description=n.description,
            created_at=n.createdAt.isoformat(),
            updated_at=n.updatedAt.isoformat()
        )
        for n in notebooks
    ]


@router.get("/{notebook_id}", response_model=NotebookResponse)
async def get_notebook(
    notebook_id: UUID,
    current_user=Depends(get_current_user),
):
    notebook = await get_notebook_by_id(str(notebook_id), str(current_user.id))
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return NotebookResponse(
        id=str(notebook.id),
        name=notebook.name,
        description=notebook.description,
        created_at=notebook.createdAt.isoformat(),
        updated_at=notebook.updatedAt.isoformat()
    )


@router.put("/{notebook_id}", response_model=NotebookResponse)
async def update_notebook_endpoint(
    notebook_id: UUID,
    request: NotebookUpdate,
    current_user=Depends(get_current_user),
):
    notebook = await update_notebook(str(notebook_id), str(current_user.id), request.name, request.description)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return NotebookResponse(
        id=str(notebook.id),
        name=notebook.name,
        description=notebook.description,
        created_at=notebook.createdAt.isoformat(),
        updated_at=notebook.updatedAt.isoformat()
    )


@router.delete("/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notebook_endpoint(
    notebook_id: UUID,
    current_user=Depends(get_current_user),
):
    deleted = await delete_notebook(str(notebook_id), str(current_user.id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return None


# ===== Generated Content Endpoints =====


class SaveContentRequest(BaseModel):
    content_type: str  # flashcards, quiz, audio
    title: Optional[str] = None
    data: dict
    material_id: Optional[str] = None


@router.post("/{notebook_id}/content")
async def save_generated_content(
    notebook_id: UUID,
    request: SaveContentRequest,
    current_user=Depends(get_current_user),
):
    """Save generated content (flashcards, quiz, etc.) to a notebook.
    Each generation is stored as a new record — previous items are never deleted.
    """
    notebook = await get_notebook_by_id(str(notebook_id), str(current_user.id))
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    content = await save_notebook_content(
        notebook_id=str(notebook_id),
        user_id=str(current_user.id),
        content_type=request.content_type,
        title=request.title,
        data=request.data,
        material_id=request.material_id,
    )

    return {
        "id": str(content.id),
        "content_type": content.contentType,
        "title": content.title,
        "created_at": content.createdAt.isoformat()
    }


@router.get("/{notebook_id}/content")
async def get_notebook_content_endpoint(
    notebook_id: UUID,
    current_user=Depends(get_current_user),
):
    """Get all generated content for a notebook."""
    notebook = await get_notebook_by_id(str(notebook_id), str(current_user.id))
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    contents = await get_notebook_content(str(notebook_id), str(current_user.id))

    return [
        {
            "id": str(c.id),
            "content_type": c.contentType,
            "title": c.title,
            "data": c.data,
            "material_id": c.materialId,
            "created_at": c.createdAt.isoformat()
        }
        for c in contents
    ]


@router.delete("/{notebook_id}/content/{content_id}")
async def delete_generated_content(
    notebook_id: UUID,
    content_id: UUID,
    current_user=Depends(get_current_user),
):
    """Delete a specific generated content item."""
    deleted = await delete_notebook_content(
        str(notebook_id), str(current_user.id), str(content_id)
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Content not found")
    return {"deleted": True}


class UpdateContentRequest(BaseModel):
    title: str

@router.put("/{notebook_id}/content/{content_id}")
async def update_generated_content_title_endpoint(
    notebook_id: UUID,
    content_id: UUID,
    request: UpdateContentRequest,
    current_user=Depends(get_current_user),
):
    """Update title for a specific generated content item."""
    updated = await update_notebook_content_title(
        str(notebook_id), str(current_user.id), str(content_id), request.title
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Content not found")
    return {
        "id": str(updated.id),
        "content_type": updated.contentType,
        "title": updated.title,
        "created_at": updated.createdAt.isoformat()
    }

