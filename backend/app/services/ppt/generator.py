"""PPT (HTML presentation) generation service.

Single-prompt pipeline:
  1. Collect ALL material text (no RAG — full context)
  2. Build prompt with user preferences (slide count, theme, extra instructions)
  3. Invoke LLM → get structured JSON with embedded HTML
  4. Validate via PresentationHTMLOutput schema
  5. Take screenshots of each slide using Playwright
  6. Return the result with HTML and slide images

All steps are logged for easy debugging.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Optional

from app.prompts import get_ppt_prompt
from app.services.llm_service.llm_schemas import PresentationHTMLOutput
from app.services.llm_service.structured_invoker import invoke_structured
from app.services.ppt.screenshot_service import capture_presentation_slides

logger = logging.getLogger("ppt.generator")


async def generate_presentation(
    material_text: str,
    user_id: str,
    *,
    max_slides: Optional[int] = None,
    theme: Optional[str] = None,
    additional_instructions: Optional[str] = None,
) -> dict:
    """Generate a full HTML presentation with slide screenshots from raw material text.

    Args:
        material_text: The complete source text from the uploaded material.
        user_id: User ID for organizing screenshot files.
        max_slides: Desired slide count (default: AI decides, ~10).
        theme: CSS theme description (default: AI decides).
        additional_instructions: Extra user guidance for the AI.

    Returns:
        dict with keys: title, slide_count, theme, html, slides, presentation_id
        where slides is a list of slide image metadata
    """
    slide_count = max_slides if max_slides and 1 <= max_slides <= 60 else 10
    text_len = len(material_text)
    presentation_id = uuid.uuid4().hex[:12]  # Unique ID for this presentation

    logger.info(
        "PPT generation started | user=%s | presentation_id=%s | text_length=%d | target_slides=%d | theme=%s | has_extra_instructions=%s",
        user_id,
        presentation_id,
        text_len,
        slide_count,
        theme or "auto",
        bool(additional_instructions),
    )

    # ── Step 1: Build prompt ──────────────────────────────
    t0 = time.time()
    prompt = get_ppt_prompt(
        material_text=material_text,
        slide_count=slide_count,
        theme=theme,
        additional_instructions=additional_instructions,
    )
    prompt_time = time.time() - t0
    logger.info(
        "PPT prompt built | prompt_length=%d | build_time=%.3fs",
        len(prompt),
        prompt_time,
    )
    logger.debug("PPT prompt preview (first 500 chars): %s", prompt[:500])

    # ── Step 2: Invoke LLM with validation ────────────────
    t1 = time.time()
    try:
        result: PresentationHTMLOutput = invoke_structured(
            prompt, PresentationHTMLOutput, max_retries=2
        )
    except Exception as exc:
        llm_time = time.time() - t1
        logger.error(
            "PPT LLM invocation FAILED after %.2fs: %s",
            llm_time,
            exc,
        )
        raise
    llm_time = time.time() - t1
    logger.info(
        "PPT LLM invocation succeeded | llm_time=%.2fs | title=%s | slides=%d | html_length=%d",
        llm_time,
        result.title,
        result.slide_count,
        len(result.html),
    )

    # ── Step 3: Post-process HTML ─────────────────────────
    html = _post_process_html(result.html)
    
    # ── Step 4: Capture slide screenshots ────────────────
    t2 = time.time()
    try:
        # Await screenshot capture directly since we're already in async context
        slides_data = await capture_presentation_slides(
            html_content=html,
            user_id=user_id,
            presentation_id=presentation_id,
            slide_count=result.slide_count
        )
        
    except Exception as exc:
        screenshot_time = time.time() - t2
        logger.error(
            "PPT screenshot capture FAILED after %.2fs: %s",
            screenshot_time,
            exc,
        )
        # Continue without screenshots rather than failing completely
        slides_data = []
    
    screenshot_time = time.time() - t2
    total_time = time.time() - t0
    
    logger.info(
        "PPT generation COMPLETE | user=%s | presentation_id=%s | total_time=%.2fs | screenshot_time=%.2fs | title=%s | slide_count=%d | final_html_length=%d | captured_slides=%d",
        user_id,
        presentation_id,
        total_time,
        screenshot_time,
        result.title,
        result.slide_count,
        len(html),
        len(slides_data),
    )

    return {
        "presentation_id": presentation_id,
        "title": result.title,
        "slide_count": result.slide_count,
        "theme": result.theme,
        "html": html,
        "slides": slides_data,  # List of slide image metadata
    }


def _post_process_html(html: str) -> str:
    """Clean up and enhance the generated HTML."""
    # Ensure proper doctype
    stripped = html.strip()
    if not stripped.lower().startswith("<!doctype"):
        stripped = "<!DOCTYPE html>\n" + stripped

    # Inject override to prevent any JS that the LLM might have snuck in
    # (the prompt says no JS, but be safe)
    safety_style = """
<style>
/* Safety overrides */
script { display: none !important; }
html { scroll-snap-type: y mandatory; scroll-behavior: smooth; overflow-x: hidden; }
body { overflow-x: hidden; margin: 0; padding: 0; }
* { box-sizing: border-box; }
/* Compact slide layout overrides */
.slide {
    width: 100%; height: 100vh; overflow: hidden;
    padding: 40px 60px !important;
    display: flex; flex-direction: column; justify-content: center;
}
.slide h1 { font-size: clamp(1.8rem, 3vw, 2.5rem) !important; margin-bottom: 12px !important; }
.slide h2 { font-size: clamp(1.3rem, 2.2vw, 1.8rem) !important; margin-bottom: 10px !important; }
.slide h3 { font-size: clamp(1.1rem, 1.8vw, 1.4rem) !important; margin-bottom: 8px !important; }
.slide p, .slide li { font-size: clamp(0.9rem, 1.3vw, 1.1rem) !important; line-height: 1.5 !important; }
</style>
"""
    if "</head>" in stripped:
        stripped = stripped.replace("</head>", safety_style + "</head>", 1)

    logger.debug("PPT HTML post-processed | length=%d", len(stripped))
    return stripped
