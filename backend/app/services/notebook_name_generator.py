"""Generate a concise notebook name from content using the LLM."""

from __future__ import annotations

import logging

from app.services.llm_service.llm import get_llm

logger = logging.getLogger(__name__)

_PROMPT = """Based on this document content, generate a short, descriptive notebook name (2-5 words max).
The name should capture the main topic or subject matter.
Do NOT include words like "Notebook", "Notes", "Document", or file extensions.
Just return the name, nothing else.

Content preview:
{preview}

Notebook name:"""

_PROMPT_MATERIAL = """Based on this document content, generate a short, descriptive title for this specific material (3-8 words max).
The title should capture the specific subject matter or main topic of this individual document or webpage.
Do NOT include generic words like "Document", "File", "Page", or file extensions.
Just return the title, nothing else.

Content preview:
{preview}

Material title:"""


def generate_notebook_name(content: str, filename: str | None = None) -> str:
    """Return a 2-5 word notebook name derived from *content*."""
    preview = content[:2000]
    # Retry logic for robustness
    for attempt in range(3):
        try:
            response = get_llm().invoke(_PROMPT.format(preview=preview))
            # Works for both chat models (response.content) and plain-string LLMs
            name = (getattr(response, "content", None) or str(response)).strip().strip("\"'")[:50]
            if name and len(name) >= 3:
                return name
        except Exception as e:
            if attempt == 2:
                logger.error(f"Failed to generate notebook name after 3 attempts: {e}")
            else:
                logger.warning(f"Notebook name generation attempt {attempt + 1} failed: {e}")

    # Fallback
    if filename:
        return filename.rsplit(".", 1)[0][:40]
    return "New Notebook"

def generate_material_title(content: str, filename: str | None = None) -> str:
    """Return a 3-8 word title for a material derived from *content*."""
    preview = content[:2000]
    # Retry logic for robustness
    for attempt in range(3):
        try:
            response = get_llm().invoke(_PROMPT_MATERIAL.format(preview=preview))
            # Works for both chat models (response.content) and plain-string LLMs
            title = (getattr(response, "content", None) or str(response)).strip().strip("\"'")[:100]
            if title and len(title) >= 3:
                return title
        except Exception as e:
            if attempt == 2:
                logger.error(f"Failed to generate material title after 3 attempts: {e}")
            else:
                logger.warning(f"Material title generation attempt {attempt + 1} failed: {e}")

    # Fallback
    if filename:
        return filename.rsplit(".", 1)[0][:60]
    return "Untitled Material"
