import asyncio
import logging
from typing import Optional

from app.db.prisma_client import prisma

logger = logging.getLogger(__name__)


async def create_notebook(user_id: str, name: str, description: Optional[str]):
    notebook = await prisma.notebook.create(
        data={
            "userId": user_id if isinstance(user_id, str) else str(user_id),
            "name": name,
            "description": description,
        }
    )
    logger.info(f"Created notebook: {notebook.id} for user: {user_id}")
    return notebook


async def get_user_notebooks(user_id: str, skip: int = 0, take: int = 50) -> list:
    return await prisma.notebook.find_many(
        where={"userId": user_id if isinstance(user_id, str) else str(user_id)},
        order={"createdAt": "desc"},
        skip=skip,
        take=take,
    )


async def get_notebook_by_id(notebook_id: str, user_id: str):
    return await prisma.notebook.find_first(
        where={
            "id": str(notebook_id),
            "userId": str(user_id),
        }
    )


async def update_notebook(
    notebook_id: str,
    user_id: str,
    name: Optional[str],
    description: Optional[str],
):
    notebook = await get_notebook_by_id(notebook_id, user_id)
    if not notebook:
        return None

    data = {}
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description

    if data:
        notebook = await prisma.notebook.update(
            where={"id": str(notebook_id)},
            data=data,
        )
    return notebook


async def delete_notebook(notebook_id: str, user_id: str) -> bool:
    notebook = await get_notebook_by_id(notebook_id, user_id)
    if not notebook:
        return False

    # Clean up related data before deleting notebook
    try:
        # Delete generated content
        await prisma.generatedcontent.delete_many(
            where={"notebookId": str(notebook_id), "userId": str(user_id)}
        )
    except Exception as e:
        logger.warning(f"Failed to delete generated content for notebook {notebook_id}: {e}")

    try:
        # Delete associated materials and their text files
        materials = await prisma.material.find_many(
            where={"notebookId": str(notebook_id), "userId": str(user_id)}
        )
        for mat in materials:
            # Delete material text file from storage (sync I/O → thread pool)
            try:
                from app.services.storage_service import delete_material_text
                await asyncio.to_thread(delete_material_text, str(mat.id))
            except Exception:
                pass
            # Delete embeddings from ChromaDB (run sync call in thread pool)
            try:
                from app.db.chroma import get_collection
                collection = get_collection()
                await asyncio.to_thread(
                    collection.delete, where={"material_id": str(mat.id)}
                )
            except Exception as chroma_exc:
                logger.warning("Failed to delete ChromaDB embeddings for material %s: %s", mat.id, chroma_exc)
        # Delete material records
        await prisma.material.delete_many(
            where={"notebookId": str(notebook_id), "userId": str(user_id)}
        )
    except Exception as e:
        logger.warning(f"Failed to delete materials for notebook {notebook_id}: {e}")

    await prisma.notebook.delete(where={"id": str(notebook_id)})
    logger.info(f"Deleted notebook and associated data: {notebook_id}")
    return True


# ── Generated Content ─────────────────────────────────────────


async def save_notebook_content(
    notebook_id: str,
    user_id: str,
    content_type: str,
    title: Optional[str],
    data: dict,
    material_id: Optional[str],
):
    """Persist a new GeneratedContent record."""
    import json

    create_data: dict = {
        "notebookId": notebook_id,
        "userId": user_id,
        "contentType": content_type,
        "title": title,
        # Prisma Python 0.15 requires json.dumps() for Json fields
        "data": json.dumps(data),
    }
    if material_id and material_id.strip():
        create_data["materialId"] = material_id

    content = await prisma.generatedcontent.create(data=create_data)
    logger.info("Saved %s content for notebook %s (id=%s)", content_type, notebook_id, content.id)
    return content


async def get_notebook_content(notebook_id: str, user_id: str) -> list:
    """Return all GeneratedContent records for *notebook_id* newest-first."""
    return await prisma.generatedcontent.find_many(
        where={"notebookId": notebook_id, "userId": user_id},
        order={"createdAt": "desc"},
    )


async def delete_notebook_content(
    notebook_id: str, user_id: str, content_id: str
) -> bool:
    """Delete a GeneratedContent record.  Returns False if not found."""
    content = await prisma.generatedcontent.find_first(
        where={"id": content_id, "notebookId": notebook_id, "userId": user_id}
    )
    if not content:
        return False
    await prisma.generatedcontent.delete(where={"id": content_id})
    return True


async def update_notebook_content_title(
    notebook_id: str, user_id: str, content_id: str, title: str
):
    """Update title of a GeneratedContent record.  Returns None if not found."""
    content = await prisma.generatedcontent.find_first(
        where={"id": content_id, "notebookId": notebook_id, "userId": user_id}
    )
    if not content:
        return None
    return await prisma.generatedcontent.update(
        where={"id": content_id},
        data={"title": title},
    )
