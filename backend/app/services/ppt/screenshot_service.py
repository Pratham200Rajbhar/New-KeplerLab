"""Playwright-based screenshot service for HTML presentations.

Takes full-page screenshots of each slide in the generated presentation
and saves them as PNG images with proper naming and organization.
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


class ScreenshotService:
    """Service for taking screenshots of HTML presentation slides."""
    
    def __init__(self):
        self.output_dir = settings.PRESENTATIONS_OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)
    
    async def capture_slides(
        self, 
        html_content: str, 
        user_id: str,
        presentation_id: str,
        slide_count: int
    ) -> List[Dict[str, str]]:
        """
        Take screenshots of each slide and return metadata.
        
        Args:
            html_content: Complete HTML presentation
            user_id: User ID for folder organization
            presentation_id: Unique ID for this presentation
            slide_count: Number of slides to capture
            
        Returns:
            List of slide metadata with file paths and URLs
        """
        logger.info(
            "Starting slide capture | user=%s | presentation_id=%s | slides=%d",
            user_id, presentation_id, slide_count
        )
        
        # Create user directory
        user_dir = os.path.join(self.output_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)
        
        # Create presentation directory
        ppt_dir = os.path.join(user_dir, presentation_id)
        os.makedirs(ppt_dir, exist_ok=True)
        
        slides_data = []
        
        try:
            async with async_playwright() as p:
                # Launch browser with error handling
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor'
                    ]
                )
                logger.debug("Browser launched successfully")
                
                # Create context with proper viewport
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    device_scale_factor=1
                )
                
                page = await context.new_page()
                
                # Write HTML to temp file and load it
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                    f.write(html_content)
                    temp_html_path = f.name
                
                try:
                    await page.goto(f"file://{temp_html_path}", wait_until="networkidle")
                    logger.debug("Page loaded successfully")
                    
                    # Wait for any CSS animations to settle
                    await page.wait_for_timeout(2000)
                    
                    # Take screenshots of each slide
                    for slide_num in range(1, slide_count + 1):
                        slide_filename = f"slide_{slide_num}.png"
                        slide_path = os.path.join(ppt_dir, slide_filename)
                        
                        try:
                            # Scroll to the specific slide
                            # Each slide is 100vh, so slide N starts at (N-1) * viewport_height
                            scroll_position = (slide_num - 1) * 1080
                            await page.evaluate(f"window.scrollTo(0, {scroll_position})")
                            
                            # Wait for scroll to complete
                            await page.wait_for_timeout(500)
                            
                            # Take screenshot of the current viewport (should show the slide)
                            # Fixed: Removed quality parameter for PNG format
                            await page.screenshot(
                                path=slide_path,
                                full_page=False,  # Just the viewport
                                type='png'
                                # Note: quality parameter is not supported for PNG format in Playwright
                                # Use type='jpeg' with quality parameter if compression is needed
                            )
                            
                            # Verify screenshot was created and has reasonable size
                            if os.path.exists(slide_path):
                                file_size = os.path.getsize(slide_path)
                                if file_size < 1000:  # Less than 1KB is probably an error
                                    logger.warning("Screenshot file is unusually small: %d bytes", file_size)
                            else:
                                raise Exception(f"Screenshot file was not created: {slide_path}")
                            
                            # Generate URL for the screenshot
                            relative_path = f"{user_id}/{presentation_id}/{slide_filename}"
                            slide_url = f"/presentation/slides/{relative_path}"
                            
                            slides_data.append({
                                "slide_number": slide_num,
                                "filename": slide_filename,
                                "file_path": slide_path,
                                "url": slide_url,
                                "width": 1920,
                                "height": 1080,
                                "file_size": os.path.getsize(slide_path)
                            })
                            
                            logger.debug("Captured slide %d/%d (size: %d bytes)", 
                                       slide_num, slide_count, os.path.getsize(slide_path))
                            
                        except Exception as slide_error:
                            logger.error("Failed to capture slide %d: %s", slide_num, str(slide_error))
                            # Continue with other slides even if one fails
                            continue
                    
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_html_path):
                        os.unlink(temp_html_path)
                
                await browser.close()
                
        except Exception as exc:
            logger.error(
                "Screenshot capture FAILED | user=%s | presentation_id=%s | error=%s",
                user_id, presentation_id, str(exc)
            )
            raise
        
        logger.info(
            "Slide capture COMPLETED | user=%s | presentation_id=%s | captured=%d slides",
            user_id, presentation_id, len(slides_data)
        )
        
        return slides_data


async def capture_presentation_slides(
    html_content: str,
    user_id: str, 
    presentation_id: str,
    slide_count: int
) -> List[Dict[str, str]]:
    """
    Convenience function to capture slides using the ScreenshotService.
    
    Args:
        html_content: Complete HTML presentation
        user_id: User ID for organization
        presentation_id: Unique presentation identifier
        slide_count: Number of slides expected
        
    Returns:
        List of slide metadata
    """
    service = ScreenshotService()
    return await service.capture_slides(html_content, user_id, presentation_id, slide_count)