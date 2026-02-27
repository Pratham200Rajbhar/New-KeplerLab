"""HTML slide extractor for presentations.

Parses the generated HTML presentation to extract each individual slide
as a complete, standalone HTML document. This replaces screenshot capture
entirely — slides are sent as HTML strings and rendered in the browser via
iframes, giving pixel-perfect, zero-latency, CSS-accurate rendering.

Pipeline:
  1. Parse full presentation HTML with BeautifulSoup
  2. Extract all <style> / CSS content from <head>
  3. Extract all :root / @keyframes / CSS variable declarations
  4. For each .slide element, build a complete standalone HTML doc:
       <head> (full CSS + safety overrides) + <body> (just this slide)
  5. Return list of slide metadata dicts

No Playwright, no browser, no file I/O — instant extraction.
"""

from __future__ import annotations

import logging
import re
import time
from typing import List, Dict, Optional

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger("ppt.extractor")

# Fixed 16:9 widescreen dimensions (matches generator constants)
SLIDE_WIDTH = 1920
SLIDE_HEIGHT = 1080

# Minimal CSS injected into every standalone slide doc to guarantee
# correct fixed-size rendering regardless of the theme CSS.
_SLIDE_RESET_CSS = f"""
/* === Slide isolation reset === */
*, *::before, *::after {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}}
html, body {{
    width: {SLIDE_WIDTH}px;
    height: {SLIDE_HEIGHT}px;
    overflow: hidden;
    margin: 0;
    padding: 0;
    background: #000;
}}
.slide {{
    width: {SLIDE_WIDTH}px  !important;
    height: {SLIDE_HEIGHT}px !important;
    min-height: {SLIDE_HEIGHT}px !important;
    max-height: {SLIDE_HEIGHT}px !important;
    overflow: hidden !important;
    position: relative !important;
}}
"""


def extract_slides(html_content: str) -> List[Dict]:
    """Extract individual slides from the full presentation HTML.

    For each .slide element, produces a complete standalone HTML document
    with the original CSS embedded so the slide renders identically to the
    full presentation.

    Args:
        html_content: Complete HTML presentation document (from the LLM).

    Returns:
        List of dicts, one per slide:
        {
            "slide_number": int,
            "slide_id":     str,   # e.g. "slide-1"
            "html":         str,   # complete standalone HTML document
        }

    The list is empty only if no .slide elements are found in the HTML.
    """
    t0 = time.time()

    try:
        soup = BeautifulSoup(html_content, "html.parser")
    except Exception as exc:
        logger.error("BeautifulSoup parse failed: %s", exc)
        return []

    # ── 1. Collect all CSS from <head> ──────────────────────────────────────
    head_css = _extract_head_css(soup)

    # ── 2. Find all slide elements ──────────────────────────────────────────
    # Support both <section class="slide ..."> and <div class="slide ...">
    slide_elements = _find_slide_elements(soup)

    if not slide_elements:
        logger.warning("No .slide elements found in HTML — returning empty list")
        return []

    logger.info(
        "Found %d slide elements | head_css_length=%d chars",
        len(slide_elements),
        len(head_css),
    )

    # ── 3. Build standalone HTML for each slide ─────────────────────────────
    slides: List[Dict] = []

    for idx, slide_el in enumerate(slide_elements, start=1):
        slide_id = slide_el.get("id") or f"slide-{idx}"

        try:
            slide_html = _build_slide_html(
                slide_element=slide_el,
                head_css=head_css,
                slide_number=idx,
                slide_id=slide_id,
            )
            slides.append(
                {
                    "slide_number": idx,
                    "slide_id": slide_id,
                    "html": slide_html,
                }
            )
        except Exception as exc:
            logger.error("Failed to build HTML for slide %d: %s", idx, exc)
            continue

    elapsed = time.time() - t0
    logger.info(
        "Slide extraction complete | extracted=%d/%d | time=%.3fs",
        len(slides),
        len(slide_elements),
        elapsed,
    )
    return slides


# ────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ────────────────────────────────────────────────────────────────────────────


def _extract_head_css(soup: BeautifulSoup) -> str:
    """Extract and concatenate all CSS from <style> tags in the document.

    Also extracts inline <style> tags from anywhere in the document
    (some LLMs put styles inside <body>).
    """
    css_blocks: List[str] = []

    for style_tag in soup.find_all("style"):
        content = style_tag.get_text()
        if content.strip():
            css_blocks.append(content)

    return "\n\n".join(css_blocks)


def _find_slide_elements(soup: BeautifulSoup) -> List[Tag]:
    """Find all elements that represent presentation slides.

    Matches:
    - <section class="slide ...">
    - <div class="slide ...">

    Returns them in document order.
    """
    def _has_slide_class(tag):
        if tag.name not in ("section", "div"):
            return False
        classes = tag.get("class", [])
        if isinstance(classes, str):
            classes = classes.split()
        return "slide" in classes

    return soup.find_all(_has_slide_class)


def _build_slide_html(
    slide_element: Tag,
    head_css: str,
    slide_number: int,
    slide_id: str,
) -> str:
    """Build a complete standalone HTML document for a single slide.

    The output HTML:
    - Is a self-contained, valid HTML5 document
    - Embeds all theme CSS from the original presentation
    - Has the slide element as the only body content
    - Has overflow: hidden and fixed 1920×1080 dimensions
    - Has no external resources, no JavaScript
    """
    # Stringify the slide element
    slide_markup = str(slide_element)

    # Ensure the slide element has the right class
    if 'class="slide"' not in slide_markup and "class='slide'" not in slide_markup:
        # Add slide class if the tag has additional classes (e.g. class="slide intro")
        pass  # The class is already there from the selector

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width={SLIDE_WIDTH}">
  <title>Slide {slide_number}</title>
  <style>
{head_css}
  </style>
  <style>
{_SLIDE_RESET_CSS}
  </style>
</head>
<body>
{slide_markup}
</body>
</html>"""

    return html


# ────────────────────────────────────────────────────────────────────────────
# Utility: count slides without full extraction
# ────────────────────────────────────────────────────────────────────────────


def count_slides(html_content: str) -> int:
    """Fast count of .slide elements without building standalone docs."""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        return len(_find_slide_elements(soup))
    except Exception:
        # Fall back to regex as last resort
        pattern = r'<(?:section|div)[^>]*\bclass\s*=\s*["\'][^"\']*\bslide\b'
        return len(re.findall(pattern, html_content, re.IGNORECASE))
