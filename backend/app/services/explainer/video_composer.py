"""Video composition service using ffmpeg.

Combines slide PNG images with audio MP3 files into per-slide MP4 videos,
then concatenates them into a single final video.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile

logger = logging.getLogger("explainer.video")


def compose_slide_video(
    image_path: str,
    audio_path: str,
    output_path: str,
) -> str:
    """Create an MP4 video from a single slide image + audio.

    Uses ffmpeg to loop the image for the duration of the audio,
    encoding at 1920×1080 with H.264 video and AAC audio.

    Args:
        image_path: Path to the slide PNG image.
        audio_path: Path to the narration MP3 audio.
        output_path: Path for the output MP4 file.

    Returns:
        The output_path on success.

    Raises:
        RuntimeError: If ffmpeg fails.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:-1:-1:color=black",
        output_path,
    ]

    logger.info("Composing slide video: %s + %s → %s", image_path, audio_path, output_path)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        logger.error("ffmpeg slide composition failed: %s", result.stderr)
        raise RuntimeError(f"ffmpeg failed: {result.stderr[:500]}")

    logger.info("Slide video created: %s (%d bytes)", output_path, os.path.getsize(output_path))
    return output_path


def concatenate_videos(
    video_paths: list[str],
    output_path: str,
) -> str:
    """Concatenate multiple MP4 videos into a single final video.

    Uses ffmpeg's concat demuxer for fast, lossless concatenation
    (all input videos must share the same codec/resolution).

    Args:
        video_paths: Ordered list of MP4 file paths.
        output_path: Path for the final concatenated MP4.

    Returns:
        The output_path on success.

    Raises:
        RuntimeError: If ffmpeg fails.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Write the concat file list
    concat_file = output_path + ".concat.txt"
    with open(concat_file, "w") as f:
        for vp in video_paths:
            f.write(f"file '{vp}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        output_path,
    ]

    logger.info("Concatenating %d videos → %s", len(video_paths), output_path)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    # Clean up concat file
    try:
        os.remove(concat_file)
    except OSError:
        pass

    if result.returncode != 0:
        logger.error("ffmpeg concatenation failed: %s", result.stderr)
        raise RuntimeError(f"ffmpeg concat failed: {result.stderr[:500]}")

    file_size = os.path.getsize(output_path)
    logger.info("Final video created: %s (%.1f MB)", output_path, file_size / 1024 / 1024)
    return output_path
