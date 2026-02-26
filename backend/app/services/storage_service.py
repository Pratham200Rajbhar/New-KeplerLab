"""File storage abstraction layer.

Provides unified interface for storing/loading material text files.
Prepares for future S3/MinIO migration.

Current implementation: Local filesystem
Future: S3, MinIO, Azure Blob, etc.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Storage directory for material text files — absolute path from settings
MATERIAL_TEXT_DIR = Path(settings.UPLOAD_DIR).parent / "material_text"

# UUID v4 pattern for material_id validation
_UUID_RE = re.compile(r"^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$", re.I)


def _validate_material_id(material_id: str) -> None:
    """Validate material_id is a safe UUID to prevent path traversal."""
    if not material_id or not _UUID_RE.match(material_id):
        raise ValueError(f"Invalid material_id format: {material_id!r}")


def _ensure_storage_dir() -> None:
    """Ensure storage directory exists."""
    MATERIAL_TEXT_DIR.mkdir(parents=True, exist_ok=True)


def save_material_text(material_id: str, text: str) -> bool:
    """Save full material text to file storage.
    
    Args:
        material_id: Unique material identifier (UUID)
        text: Full extracted text content
    
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        _validate_material_id(material_id)
        _ensure_storage_dir()
        
        file_path = MATERIAL_TEXT_DIR / f"{material_id}.txt"
        
        with open(file_path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        
        logger.info(f"Saved material text: {material_id} ({len(text)} chars)")
        return True
        
    except ValueError as e:
        logger.error(f"Invalid material_id: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to save material text {material_id}: {e}")
        return False


def load_material_text(material_id: str) -> Optional[str]:
    """Load full material text from file storage.
    
    Args:
        material_id: Unique material identifier (UUID)
    
    Returns:
        Full text content, or None if not found
    """
    try:
        _validate_material_id(material_id)
        file_path = MATERIAL_TEXT_DIR / f"{material_id}.txt"
        
        if not file_path.exists():
            logger.warning(f"Material text not found: {material_id}")
            return None
        
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            text = f.read()
        
        logger.debug(f"Loaded material text: {material_id} ({len(text)} chars)")
        return text
        
    except ValueError as e:
        logger.error(f"Invalid material_id: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to load material text {material_id}: {e}")
        return None


def delete_material_text(material_id: str) -> bool:
    """Delete material text from file storage.
    
    Args:
        material_id: Unique material identifier (UUID)
    
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        _validate_material_id(material_id)
        file_path = MATERIAL_TEXT_DIR / f"{material_id}.txt"
        
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted material text: {material_id}")
            return True
        else:
            logger.warning(f"Material text not found for deletion: {material_id}")
            return False
        
    except ValueError as e:
        logger.error(f"Invalid material_id: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to delete material text {material_id}: {e}")
        return False


def get_material_summary(text: str, max_chars: int = 1000) -> str:
    """Extract summary from full text for database storage.
    
    Args:
        text: Full text content
        max_chars: Maximum characters for summary
    
    Returns:
        Summary text (first N characters)
    """
    if not text:
        return ""
    
    summary = text[:max_chars]
    
    # Try to break at sentence boundary if possible
    if len(text) > max_chars:
        last_period = summary.rfind(". ")
        if last_period > max_chars // 2:
            summary = summary[:last_period + 1]
        summary += "..."
    
    return summary


def get_storage_stats() -> dict:
    """Get storage statistics.
    
    Returns:
        Dict with file count and total size
    """
    try:
        if not MATERIAL_TEXT_DIR.exists():
            return {"file_count": 0, "total_size_mb": 0.0}
        
        files = list(MATERIAL_TEXT_DIR.glob("*.txt"))
        total_size = sum(f.stat().st_size for f in files)
        
        return {
            "file_count": len(files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }
        
    except Exception as e:
        logger.error(f"Failed to get storage stats: {e}")
        return {"file_count": 0, "total_size_mb": 0.0, "error": str(e)}


def delete_uploaded_file(file_path: str) -> bool:
    """Delete an uploaded file from disk.

    Args:
        file_path: Absolute path to the file.

    Returns:
        True if deleted, False otherwise.
    """
    try:
        p = Path(file_path)
        if p.exists() and p.is_file():
            p.unlink()
            logger.info("Deleted uploaded file: %s", file_path)
            return True
        return False
    except Exception as e:
        logger.error("Failed to delete uploaded file %s: %s", file_path, e)
        return False
