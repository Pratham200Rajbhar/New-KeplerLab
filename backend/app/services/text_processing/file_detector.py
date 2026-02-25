"""File type detection using content sniffing + extension fallback.

Supports any file the extractor can handle.  Unknown types are returned with
category='unknown' so the extractor can attempt a generic text fallback rather
than hard-failing.
"""

from __future__ import annotations

import mimetypes
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class FileTypeDetector:
    """Detect file types using python-magic (content) with extension fallback."""

    # ── Canonical MIME → extension map ────────────────────────────────────────
    # This maps every MIME type we know how to extract to its canonical extension.
    # It is also used by upload.py to expose the supported-formats endpoint.
    SUPPORTED_TYPES: Dict[str, str] = {
        # ── Documents ──────────────────────────────────────────────────────────
        "application/pdf":                                                          "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/msword":                                                       "doc",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation":"pptx",
        "application/vnd.ms-powerpoint":                                            "ppt",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":       "xlsx",
        "application/vnd.ms-excel":                                                 "xls",
        "text/plain":                                                               "txt",
        "text/markdown":                                                            "md",
        "text/csv":                                                                 "csv",
        "text/html":                                                                "html",
        "application/rtf":                                                          "rtf",
        "text/rtf":                                                                 "rtf",
        "application/epub+zip":                                                     "epub",
        "application/vnd.oasis.opendocument.text":                                  "odt",
        "application/vnd.oasis.opendocument.spreadsheet":                           "ods",
        "application/vnd.oasis.opendocument.presentation":                          "odp",
        # ── Images (OCR) ───────────────────────────────────────────────────────
        "image/jpeg":                                                               "jpg",
        "image/jpg":                                                                "jpg",
        "image/png":                                                                "png",
        "image/gif":                                                                "gif",
        "image/bmp":                                                                "bmp",
        "image/tiff":                                                               "tiff",
        "image/webp":                                                               "webp",
        "image/svg+xml":                                                            "svg",
        # ── Audio (Whisper transcription) ──────────────────────────────────────
        "audio/mpeg":                                                               "mp3",
        "audio/mp3":                                                                "mp3",
        "audio/wav":                                                                "wav",
        "audio/x-wav":                                                              "wav",
        "audio/mp4":                                                                "m4a",
        "audio/x-m4a":                                                              "m4a",
        "audio/aac":                                                                "aac",
        "audio/x-aac":                                                              "aac",
        "audio/ogg":                                                                "ogg",
        "audio/flac":                                                               "flac",
        "audio/x-flac":                                                             "flac",
        "audio/webm":                                                               "webm",
        # ── Video (Whisper transcription) ──────────────────────────────────────
        "video/mp4":                                                                "mp4",
        "video/mpeg":                                                               "mpeg",
        "video/avi":                                                                "avi",
        "video/x-msvideo":                                                          "avi",
        "video/quicktime":                                                          "mov",
        "video/x-matroska":                                                         "mkv",
        "video/mkv":                                                                "mkv",
        "video/webm":                                                               "webm",
        "video/x-ms-wmv":                                                           "wmv",
        "video/3gpp":                                                               "3gp",
        # ── Email / messaging ──────────────────────────────────────────────────
        "message/rfc822":                                                           "eml",
        "application/vnd.ms-outlook":                                               "msg",
    }

    # Extension → canonical extension (for URL / filename extension fallback)
    _EXT_MAP: Dict[str, str] = {
        ".pdf": "pdf", ".docx": "docx", ".doc": "doc", ".pptx": "pptx",
        ".ppt": "ppt", ".xlsx": "xlsx", ".xls": "xls", ".txt": "txt",
        ".md": "md", ".csv": "csv", ".html": "html", ".htm": "html",
        ".rtf": "rtf", ".epub": "epub", ".odt": "odt", ".ods": "ods",
        ".odp": "odp",
        # Images
        ".jpg": "jpg", ".jpeg": "jpg", ".png": "png", ".gif": "gif",
        ".bmp": "bmp", ".tiff": "tiff", ".tif": "tiff", ".webp": "webp",
        ".svg": "svg",
        # Audio
        ".mp3": "mp3", ".wav": "wav", ".m4a": "m4a", ".aac": "aac",
        ".ogg": "ogg", ".flac": "flac",
        # Video
        ".mp4": "mp4", ".avi": "avi", ".mov": "mov", ".mkv": "mkv",
        ".webm": "webm", ".wmv": "wmv", ".mpeg": "mpeg", ".mpg": "mpeg",
        ".3gp": "3gp",
        # Email
        ".eml": "eml", ".msg": "msg",
    }

    # ── Category helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _mime_to_category(mime: str) -> str:
        if not mime:
            return "unknown"
        if mime.startswith("image/"):
            return "image"
        if mime.startswith("audio/"):
            return "audio"
        if mime.startswith("video/"):
            return "video"
        if mime.startswith("text/") or mime in {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
            "application/rtf",
            "application/epub+zip",
            "application/vnd.oasis.opendocument.text",
            "application/vnd.oasis.opendocument.spreadsheet",
            "application/vnd.oasis.opendocument.presentation",
            "message/rfc822",
            "application/vnd.ms-outlook",
        }:
            return "document"
        return "unknown"

    @staticmethod
    def _ext_to_category(ext: str) -> str:
        """Fallback category from extension when MIME is unavailable."""
        images   = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".svg"}
        audio    = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
        video    = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".wmv", ".mpeg", ".mpg", ".3gp"}
        if ext in images:   return "image"
        if ext in audio:    return "audio"
        if ext in video:    return "video"
        return "document"

    # ── Public API ──────────────────────────────────────────────────────────────

    @staticmethod
    def detect_file_type(file_path: str) -> Dict[str, Optional[str]]:
        """Detect file type; always returns a usable dict (never raises)."""
        path = Path(file_path)
        file_ext = path.suffix.lower()

        # 1. Content-based MIME sniff (python-magic)
        mime_type: Optional[str] = None
        try:
            import magic as _magic
            mime_type = _magic.from_file(str(path), mime=True)
        except Exception:
            pass

        # 2. Extension fallback if sniff failed or gave generic octet-stream
        if not mime_type or mime_type == "application/octet-stream":
            guessed, _ = mimetypes.guess_type(str(path))
            if guessed:
                mime_type = guessed
            elif not mime_type:
                mime_type = "application/octet-stream"

        # Normalised extension: prefer SUPPORTED_TYPES lookup, then _EXT_MAP
        ext = FileTypeDetector.SUPPORTED_TYPES.get(mime_type)
        if not ext:
            ext = FileTypeDetector._EXT_MAP.get(file_ext, file_ext.lstrip(".") or "bin")

        # Category
        category = FileTypeDetector._mime_to_category(mime_type)
        if category == "unknown" and file_ext:
            category = FileTypeDetector._ext_to_category(file_ext)

        is_supported = mime_type in FileTypeDetector.SUPPORTED_TYPES or file_ext in FileTypeDetector._EXT_MAP

        return {
            "mime_type":    mime_type,
            "extension":    ext,
            "category":     category,
            "is_supported": is_supported,
        }

    @staticmethod
    def detect_from_extension(url_or_path: str) -> Optional[str]:
        """Return a type indicator (extension or 'image') inferred ONLY from the extension.

        Returns None if the extension is unrecognised.
        Used as fallback when HTTP header detection fails for remote URLs.
        """
        ext = Path(url_or_path.split("?")[0]).suffix.lower()
        if not ext:
            return None

        # Use the canonical map
        canonical = FileTypeDetector._EXT_MAP.get(ext)
        if not canonical:
            return None
            
        # For historical consistency in the extractor's _DOWNLOAD_CATS, 
        # we return the extension for documents/audio/video, but "image" for images.
        cat = FileTypeDetector._ext_to_category(ext)
        if cat == "image":
            return "image"
        return canonical

    @staticmethod
    def is_supported(file_path: str) -> bool:
        info = FileTypeDetector.detect_file_type(file_path)
        return info["is_supported"]

    @staticmethod
    def get_supported_extensions() -> list:
        exts = list({v for v in FileTypeDetector.SUPPORTED_TYPES.values()})
        return sorted(exts)