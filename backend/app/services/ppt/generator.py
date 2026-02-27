"""PPT (HTML presentation) generation service.

Single-prompt pipeline:
  1. Collect ALL material text (no RAG — full context)
  2. Build prompt with user preferences (slide count, theme, extra instructions)
  3. Invoke LLM → get structured JSON with embedded HTML
  4. Validate via PresentationHTMLOutput schema
  5. Extract individual slide HTML docs using BeautifulSoup (no Playwright)
  6. Return the result with full HTML + per-slide HTML docs

Slides are delivered as standalone HTML strings; the frontend renders them
in scaled iframes — pixel-perfect, instant, no browser automation needed.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from typing import Optional

from app.prompts import get_ppt_prompt
from app.services.llm_service.llm_schemas import PresentationHTMLOutput
from app.services.llm_service.structured_invoker import invoke_structured
from app.services.ppt.slide_extractor import extract_slides

logger = logging.getLogger("ppt.generator")


async def generate_presentation(
    material_text: str,
    user_id: str,
    *,
    max_slides: Optional[int] = None,
    theme: Optional[str] = None,
    additional_instructions: Optional[str] = None,
) -> dict:
    """Generate a full HTML presentation with per-slide HTML from raw material text.

    Args:
        material_text: The complete source text from the uploaded material.
        user_id: User ID (kept for API compatibility).
        max_slides: Desired slide count (default: AI decides, ~10).
        theme: CSS theme description (default: AI decides).
        additional_instructions: Extra user guidance for the AI.

    Returns:
        dict with keys: title, slide_count, theme, html, slides, presentation_id
        where slides is a list of per-slide HTML dicts (no screenshots)
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

    # ── Step 4: Extract per-slide HTML docs (no Playwright) ──
    t2 = time.time()
    try:
        # Run CPU-bound HTML parsing in a thread to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        slides_data = await loop.run_in_executor(None, extract_slides, html)
    except Exception as exc:
        logger.error("PPT slide extraction FAILED: %s", exc)
        slides_data = []

    extract_time = time.time() - t2
    effective_slide_count = len(slides_data) if slides_data else result.slide_count

    if slides_data and len(slides_data) != result.slide_count:
        logger.warning(
            "PPT slide count mismatch: LLM reported %d but HTML contains %d .slide elements",
            result.slide_count,
            len(slides_data),
        )

    total_time = time.time() - t0

    logger.info(
        "PPT generation COMPLETE | user=%s | presentation_id=%s | total_time=%.2fs"
        " | extract_time=%.3fs | title=%s | slide_count=%d | html_length=%d | format=16:9@1920x1080",
        user_id,
        presentation_id,
        total_time,
        extract_time,
        result.title,
        effective_slide_count,
        len(html),
    )

    return {
        "presentation_id": presentation_id,
        "title": result.title,
        "slide_count": effective_slide_count,
        "theme": result.theme,
        "html": html,
        "slides": slides_data,  # [{slide_number, slide_id, html}, ...]
    }


# ── Fixed dimensions for 16:9 widescreen presentation ─────────
SLIDE_WIDTH = 1920
SLIDE_HEIGHT = 1080


def _post_process_html(html: str) -> str:
    """Clean up and enhance the generated HTML for 16:9 fixed-size rendering.

    Ensures:
    - Proper DOCTYPE
    - Viewport meta tag for fixed 1920px width
    - Safety CSS that enforces 1920×1080 slide dimensions
    - No JavaScript execution
    - Proper overflow handling
    """
    stripped = html.strip()

    # ── 1. Ensure proper doctype ──────────────────────────────
    if not stripped.lower().startswith("<!doctype"):
        stripped = "<!DOCTYPE html>\n" + stripped

    # ── 2. Inject / fix viewport meta tag ─────────────────────
    viewport_meta = '<meta name="viewport" content="width=1920">'
    if '<meta name="viewport"' not in stripped.lower():
        # Add viewport meta after <head> or after charset meta
        if "<head>" in stripped.lower():
            stripped = stripped.replace("<head>", f"<head>\n  {viewport_meta}", 1)
            stripped = stripped.replace("<HEAD>", f"<HEAD>\n  {viewport_meta}", 1)
    else:
        # Replace existing viewport meta with our fixed-width version
        stripped = re.sub(
            r'<meta\s+name=["\']viewport["\'][^>]*>',
            viewport_meta,
            stripped,
            count=1,
            flags=re.IGNORECASE,
        )

    # ── 3. Inject safety CSS ──────────────────────────────────
    safety_style = f"""
<style data-ppt-safety>
/* === PPT Safety Overrides (16:9 @ {SLIDE_WIDTH}x{SLIDE_HEIGHT}) === */
script {{ display: none !important; }}
html {{
    scroll-snap-type: y mandatory;
    scroll-behavior: smooth;
    overflow-x: hidden;
}}
body {{
    margin: 0;
    padding: 0;
    overflow-x: hidden;
    width: {SLIDE_WIDTH}px;
}}
*, *::before, *::after {{
    box-sizing: border-box;
}}
/* Enforce fixed 16:9 slide dimensions */
.slide {{
    width: {SLIDE_WIDTH}px;
    height: {SLIDE_HEIGHT}px;
    overflow: hidden;
    scroll-snap-align: start;
    position: relative;
}}
/* Prevent any rogue 100vh usage from breaking layout */
.slide {{
    min-height: {SLIDE_HEIGHT}px !important;
    max-height: {SLIDE_HEIGHT}px !important;
}}
/* Typography safety — prevent absurdly large/small text */
.slide h1 {{ max-font-size: 3.2rem; }}
.slide h2 {{ max-font-size: 2.4rem; }}
.slide p, .slide li {{ line-height: 1.5; }}
/* Ensure images don't overflow slides */
.slide img {{
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
}}
</style>
"""
    if "</head>" in stripped:
        stripped = stripped.replace("</head>", safety_style + "\n</head>", 1)
    elif "</HEAD>" in stripped:
        stripped = stripped.replace("</HEAD>", safety_style + "\n</HEAD>", 1)

    # ── 4. Remove any <script> tags the LLM may have included ─
    stripped = re.sub(
        r"<script[^>]*>.*?</script>",
        "",
        stripped,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # ── 5. Fix any 100vh references in inline styles ──────────
    stripped = stripped.replace("height: 100vh", f"height: {SLIDE_HEIGHT}px")
    stripped = stripped.replace("height:100vh", f"height:{SLIDE_HEIGHT}px")
    stripped = stripped.replace("min-height: 100vh", f"min-height: {SLIDE_HEIGHT}px")
    stripped = stripped.replace("min-height:100vh", f"min-height:{SLIDE_HEIGHT}px")

    logger.debug("PPT HTML post-processed | length=%d", len(stripped))
    return stripped
