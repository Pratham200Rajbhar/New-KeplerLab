"""Playwright-based screenshot service for HTML presentations.

Takes 16:9 widescreen screenshots (1920×1080) of each slide in the
generated HTML presentation and saves them as PNG images.

Slide detection strategy:
  1. Try to find `.slide` elements and screenshot each one via clip.
  2. Fall back to scroll-based capture if no `.slide` elements found.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import time
from typing import List, Dict, Tuple

from playwright.async_api import async_playwright
from app.core.config import settings

logger = logging.getLogger("ppt.screenshots")

# Fixed 16:9 widescreen dimensions
SLIDE_WIDTH = 1920
SLIDE_HEIGHT = 1080


class ScreenshotService:
    """Service for taking 16:9 screenshots of HTML presentation slides."""

    def __init__(self):
        self.output_dir = settings.PRESENTATIONS_OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    async def capture_slides(
        self,
        html_content: str,
        user_id: str,
        presentation_id: str,
        slide_count: int,
    ) -> List[Dict[str, str]]:
        """Take 1920×1080 screenshots of each slide and return metadata.

        Args:
            html_content: Complete HTML presentation (fixed 1920×1080 slides).
            user_id: User ID for folder organization.
            presentation_id: Unique ID for this presentation.
            slide_count: Number of slides to capture.

        Returns:
            List of slide metadata dicts with file paths and URLs.
        """
        t0 = time.time()
        logger.info(
            "Starting slide capture | user=%s | presentation_id=%s | expected_slides=%d",
            user_id,
            presentation_id,
            slide_count,
        )

        # Create output directories
        ppt_dir = os.path.join(self.output_dir, user_id, presentation_id)
        os.makedirs(ppt_dir, exist_ok=True)

        slides_data: List[Dict[str, str]] = []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor",
                        "--no-sandbox",
                        "--disable-gpu",
                        "--font-render-hinting=none",
                    ],
                )
                logger.debug("Browser launched successfully")

                # Viewport MUST match our slide dimensions exactly
                context = await browser.new_context(
                    viewport={"width": SLIDE_WIDTH, "height": SLIDE_HEIGHT},
                    device_scale_factor=1,
                )

                page = await context.new_page()

                # Write HTML to temp file and load it
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".html", delete=False, encoding="utf-8"
                ) as f:
                    f.write(html_content)
                    temp_html_path = f.name

                try:
                    await page.goto(
                        f"file://{temp_html_path}",
                        wait_until="networkidle",
                        timeout=30000,
                    )
                    logger.debug("Page loaded successfully")

                    # Wait for CSS rendering (gradients, blur, fonts)
                    await page.wait_for_timeout(3000)

                    # ── Detect actual slide elements ──────────────
                    actual_slide_count = await page.evaluate(
                        "document.querySelectorAll('.slide').length"
                    )
                    target_count = actual_slide_count if actual_slide_count > 0 else slide_count
                    logger.info(
                        "Detected %d .slide elements (expected %d), capturing %d",
                        actual_slide_count,
                        slide_count,
                        target_count,
                    )

                    # ── Capture each slide ────────────────────────
                    for slide_num in range(1, target_count + 1):
                        slide_filename = f"slide_{slide_num}.png"
                        slide_path = os.path.join(ppt_dir, slide_filename)

                        try:
                            if actual_slide_count > 0:
                                # Strategy A: clip-based capture using element position
                                # This is more reliable than scroll-based capture
                                bbox = await page.evaluate(
                                    f"""
                                    (() => {{
                                        const el = document.querySelectorAll('.slide')[{slide_num - 1}];
                                        if (!el) return null;
                                        const r = el.getBoundingClientRect();
                                        return {{ x: r.x, y: r.y + window.scrollY, width: r.width, height: r.height }};
                                    }})()
                                    """
                                )

                                if bbox:
                                    # Scroll the slide into view first
                                    await page.evaluate(
                                        f"document.querySelectorAll('.slide')[{slide_num - 1}].scrollIntoView({{behavior: 'instant', block: 'start'}})"
                                    )
                                    await page.wait_for_timeout(400)

                                    # Capture the viewport (which should show exactly this slide)
                                    await page.screenshot(
                                        path=slide_path,
                                        full_page=False,
                                        type="png",
                                        clip={
                                            "x": 0,
                                            "y": 0,
                                            "width": SLIDE_WIDTH,
                                            "height": SLIDE_HEIGHT,
                                        },
                                    )
                                else:
                                    # Element not found — fall back to scroll
                                    await self._scroll_and_capture(
                                        page, slide_num, slide_path
                                    )
                            else:
                                # Strategy B: scroll-based capture (fallback)
                                await self._scroll_and_capture(
                                    page, slide_num, slide_path
                                )

                            # Verify screenshot
                            if os.path.exists(slide_path):
                                file_size = os.path.getsize(slide_path)
                                if file_size < 1000:
                                    logger.warning(
                                        "Slide %d screenshot unusually small: %d bytes",
                                        slide_num,
                                        file_size,
                                    )
                            else:
                                raise FileNotFoundError(
                                    f"Screenshot not created: {slide_path}"
                                )

                            relative_path = (
                                f"{user_id}/{presentation_id}/{slide_filename}"
                            )
                            slides_data.append(
                                {
                                    "slide_number": slide_num,
                                    "filename": slide_filename,
                                    "file_path": slide_path,
                                    "url": f"/presentation/slides/{relative_path}",
                                    "width": SLIDE_WIDTH,
                                    "height": SLIDE_HEIGHT,
                                    "file_size": os.path.getsize(slide_path),
                                }
                            )

                            logger.debug(
                                "Captured slide %d/%d (size: %d bytes)",
                                slide_num,
                                target_count,
                                os.path.getsize(slide_path),
                            )

                        except Exception as slide_error:
                            logger.error(
                                "Failed to capture slide %d: %s",
                                slide_num,
                                str(slide_error),
                            )
                            continue

                finally:
                    if os.path.exists(temp_html_path):
                        os.unlink(temp_html_path)

                await browser.close()

        except Exception as exc:
            logger.error(
                "Screenshot capture FAILED | user=%s | presentation_id=%s | error=%s",
                user_id,
                presentation_id,
                str(exc),
            )
            raise

        elapsed = time.time() - t0
        logger.info(
            "Slide capture COMPLETED | user=%s | presentation_id=%s | captured=%d/%d slides | time=%.2fs",
            user_id,
            presentation_id,
            len(slides_data),
            target_count,
            elapsed,
        )

        return slides_data

    async def _scroll_and_capture(
        self,
        page,
        slide_num: int,
        slide_path: str,
    ) -> None:
        """Fallback: scroll to Nth slide position and take a viewport screenshot."""
        scroll_position = (slide_num - 1) * SLIDE_HEIGHT
        await page.evaluate(f"window.scrollTo(0, {scroll_position})")
        await page.wait_for_timeout(600)
        await page.screenshot(
            path=slide_path,
            full_page=False,
            type="png",
            clip={
                "x": 0,
                "y": 0,
                "width": SLIDE_WIDTH,
                "height": SLIDE_HEIGHT,
            },
        )


async def capture_presentation_slides(
    html_content: str,
    user_id: str,
    presentation_id: str,
    slide_count: int,
) -> List[Dict[str, str]]:
    """Convenience function to capture slides using the ScreenshotService.

    Args:
        html_content: Complete HTML presentation (1920×1080 slides).
        user_id: User ID for organization.
        presentation_id: Unique presentation identifier.
        slide_count: Number of slides expected.

    Returns:
        List of slide metadata.
    """
    service = ScreenshotService()
    return await service.capture_slides(
        html_content, user_id, presentation_id, slide_count
    )