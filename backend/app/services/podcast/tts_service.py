"""TTS service for podcast — parallel per-segment synthesis via edge-tts.

Each dialogue turn is synthesized into its own MP3 file independently.
All segments are synthesized in parallel with streaming callbacks so the
generation pipeline can persist + broadcast each segment the moment its
audio is ready — enabling early playback without waiting for the full batch.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Callable, Dict, List, Optional

import edge_tts
from mutagen.mp3 import MP3

logger = logging.getLogger(__name__)

# Output base directory
_OUTPUT_BASE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "output", "podcast")
)

# How many edge-tts connections to open simultaneously.
# edge-tts is pure-async/network so we can push concurrency high.
_TTS_CONCURRENCY = 15
# Retry attempts for transient network errors
_TTS_MAX_RETRIES = 3


def _get_session_dir(session_id: str) -> str:
    """Return and create the output directory for a session."""
    path = os.path.join(_OUTPUT_BASE, session_id)
    os.makedirs(path, exist_ok=True)
    return path


def _segment_filename(index: int, speaker: str) -> str:
    """Return the filename for a segment audio file."""
    return f"seg_{index:04d}_{speaker}.mp3"


async def _duration_from_file(output_path: str, text: str) -> int:
    """Read MP3 duration; fallback to word-count estimate."""
    try:
        audio = await asyncio.to_thread(MP3, output_path)
        return int(audio.info.length * 1000)
    except Exception:
        word_count = len(text.split())
        return max(500, int((word_count / 150) * 60 * 1000))


async def synthesize_segment(
    text: str,
    voice_id: str,
    output_path: str,
    rate: str = "+0%",
) -> int:
    """Synthesize a single text segment to MP3 with retry.

    Returns duration in milliseconds.
    """
    last_exc: Exception | None = None
    for attempt in range(_TTS_MAX_RETRIES):
        try:
            communicate = edge_tts.Communicate(text, voice_id, rate=rate)
            await communicate.save(output_path)
            return await _duration_from_file(output_path, text)
        except Exception as exc:
            last_exc = exc
            wait = 0.5 * (attempt + 1)
            logger.warning(
                "TTS attempt %d/%d failed for voice=%s: %s — retrying in %.1fs",
                attempt + 1, _TTS_MAX_RETRIES, voice_id, exc, wait,
            )
            await asyncio.sleep(wait)

    raise RuntimeError(f"TTS failed after {_TTS_MAX_RETRIES} attempts: {last_exc}") from last_exc


async def synthesize_all_segments(
    session_id: str,
    segments: List[Dict],
    host_voice: str,
    guest_voice: str,
    on_progress: Optional[Callable] = None,
    on_segment_ready: Optional[Callable] = None,
) -> List[Dict]:
    """Synthesize all segments with high concurrency and streaming callbacks.

    Args:
        session_id:        Session identifier — sets the audio output directory.
        segments:          List of ``{speaker, text, segment_index}``.
        host_voice:        edge-tts voice ID for the host speaker.
        guest_voice:       edge-tts voice ID for the guest speaker.
        on_progress:       ``async (completed: int, total: int)`` — overall progress.
        on_segment_ready:  ``async (segment_index: int, result: dict)`` — called the
                           instant a segment's audio is synthesised.  Use this to
                           persist the segment to the DB and push a WS event WITHOUT
                           waiting for the whole batch to finish.  Exceptions raised
                           inside the callback are logged but do not abort synthesis.

    Returns:
        Ordered list of ``{segment_index, audio_url, duration_ms, filename}``.
    """
    session_dir = _get_session_dir(session_id)
    total = len(segments)
    completed_count = 0
    sem = asyncio.Semaphore(_TTS_CONCURRENCY)

    # Build a fast index: segment_index → seg dict
    seg_by_idx = {s["segment_index"]: s for s in segments}

    async def _synth_one(seg: Dict) -> Dict:
        nonlocal completed_count
        idx = seg["segment_index"]
        speaker = seg["speaker"].lower()
        voice = host_voice if speaker == "host" else guest_voice
        filename = _segment_filename(idx, speaker)
        output_path = os.path.join(session_dir, filename)

        result: Dict
        try:
            async with sem:
                duration_ms = await synthesize_segment(
                    text=seg["text"],
                    voice_id=voice,
                    output_path=output_path,
                )
            result = {
                "segment_index": idx,
                "audio_url": f"/podcast/session/{session_id}/segment/{idx}/audio",
                "duration_ms": duration_ms,
                "filename": filename,
            }
        except Exception as exc:
            logger.error("TTS permanently failed for segment %d: %s", idx, exc)
            result = {
                "segment_index": idx,
                "audio_url": None,
                "duration_ms": 0,
                "filename": None,
                "error": str(exc),
            }

        # Increment before callbacks so progress is accurate
        completed_count += 1

        # Streaming callback — fire-and-forget on exception so one bad segment
        # never blocks the rest of the batch.
        if on_segment_ready:
            try:
                await on_segment_ready(idx, result)
            except Exception as cb_exc:
                logger.error(
                    "on_segment_ready callback failed for segment %d: %s",
                    idx, cb_exc,
                )

        if on_progress:
            try:
                await on_progress(completed_count, total)
            except Exception:
                pass

        return result

    # Launch all concurrently — semaphore controls actual parallelism
    raw_results = await asyncio.gather(*(_synth_one(seg) for seg in segments))

    # Return sorted by index regardless of completion order
    raw_results = sorted(raw_results, key=lambda r: r["segment_index"])

    success_count = sum(1 for r in raw_results if r.get("audio_url"))
    logger.info(
        "TTS batch complete: %d/%d segments synthesised for session %s",
        success_count, total, session_id,
    )
    return raw_results


async def synthesize_single(
    session_id: str,
    text: str,
    voice_id: str,
    filename: str,
) -> Dict:
    """Synthesize a single piece of text (e.g., Q&A answer).

    Returns {audio_url, duration_ms}.
    """
    session_dir = _get_session_dir(session_id)
    output_path = os.path.join(session_dir, filename)

    duration_ms = await synthesize_segment(text, voice_id, output_path)

    return {
        "audio_url": f"/podcast/session/{session_id}/audio/{filename}",
        "duration_ms": duration_ms,
        "filename": filename,
    }


def get_segment_audio_path(session_id: str, segment_index: int) -> Optional[str]:
    """Return the file path for a segment's audio, or None if not found."""
    session_dir = os.path.join(_OUTPUT_BASE, session_id)
    if not os.path.isdir(session_dir):
        return None

    # Try both speaker types
    for speaker in ("host", "guest"):
        filename = _segment_filename(segment_index, speaker)
        path = os.path.join(session_dir, filename)
        if os.path.isfile(path):
            return path

    return None


def get_audio_file_path(session_id: str, filename: str) -> Optional[str]:
    """Return the file path for any audio file in a session directory."""
    path = os.path.join(_OUTPUT_BASE, session_id, filename)
    if os.path.isfile(path):
        return path
    return None


async def generate_voice_preview(voice_id: str, text: str) -> bytes:
    """Generate a short voice preview and return raw MP3 bytes."""
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        communicate = edge_tts.Communicate(text, voice_id)
        await communicate.save(tmp_path)

        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
