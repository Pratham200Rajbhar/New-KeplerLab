"""
Shared route utilities — DRY helpers used across multiple route modules.

Centralises common patterns: path validation, material fetching,
response formatting, and error handling.
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import HTTPException

from app.core.config import settings
from app.services.material_service import get_material_for_user


# ── Path Safety ───────────────────────────────────────────────


def safe_path(base_dir: str, *parts: str) -> str:
    """Resolve a path and verify it stays under *base_dir*.

    Prevents directory-traversal attacks (e.g. ``../../etc/passwd``).

    Raises:
        HTTPException(400) on traversal attempt.
    """
    full = os.path.realpath(os.path.join(base_dir, *parts))
    base = os.path.realpath(base_dir)
    if not (full == base or full.startswith(base + os.sep)):
        raise HTTPException(status_code=400, detail="Invalid file path")
    return full


# ── Material Helpers ──────────────────────────────────────────


async def require_material(material_id: str, user_id, *, require_text: bool = True):
    """Fetch a material owned by *user_id* or raise 404/400.

    Args:
        material_id: UUID string of the material.
        user_id: Current user ID (str or UUID).
        require_text: If True, also raise 400 when ``originalText`` is empty.

    Returns:
        The Prisma Material record.
    """
    material = await get_material_for_user(str(material_id), user_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    if require_text and not material.originalText:
        raise HTTPException(status_code=400, detail="Material has no text content")
    return material


async def require_material_text(material_id: str, user_id) -> str:
    """Fetch material and load its full text from storage.

    This is a convenience wrapper that combines require_material() with
    text loading from file storage.

    Args:
        material_id: UUID string of the material.
        user_id: Current user ID (str or UUID).

    Returns:
        The full text content of the material.

    Raises:
        HTTPException: 404 if material not found, 400 if no text content.
    """
    await require_material(material_id, user_id, require_text=True)
    
    from app.services.material_service import get_material_text
    text = await get_material_text(str(material_id), str(user_id))
    if not text:
        raise HTTPException(status_code=404, detail="Material text not found in storage")
    return text


async def require_materials_text(
    material_ids: list[str], user_id, *, separator: str = "\n\n---\n\n"
) -> str:
    """Fetch and combine text from multiple materials.

    Args:
        material_ids: List of material UUID strings.
        user_id: Current user ID.
        separator: Text separator between materials.

    Returns:
        Combined text from all materials.
    """
    parts: list[str] = []
    for mid in material_ids:
        text = await require_material_text(mid, user_id)
        parts.append(text)
    return separator.join(parts)


# ── File-Token Helpers ────────────────────────────────────────


async def require_file_token(token: str) -> str:
    """Validate a signed file-access token and return the user_id.

    Raises:
        HTTPException(401) if the token is invalid or expired.
    """
    from app.services.auth import validate_file_token

    user_id = await validate_file_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired file token")
    return user_id


async def require_file_token_for_user(token: str, expected_user_id: str) -> str:
    """Like ``require_file_token`` but also verifies user ownership.

    Raises:
        HTTPException(403) if the token user doesn't match *expected_user_id*.
    """
    user_id = await require_file_token(token)
    if user_id != expected_user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return user_id
