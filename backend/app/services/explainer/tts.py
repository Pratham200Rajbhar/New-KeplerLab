"""Text-to-speech service using edge-tts (free, multilingual).

Generates MP3 audio files from text using Microsoft Edge's TTS engine.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

import edge_tts

logger = logging.getLogger("explainer.tts")

# ── Voice mappings ────────────────────────────────────────

EDGE_TTS_VOICES: dict[str, dict[str, str]] = {
    "en": {"male": "en-US-GuyNeural", "female": "en-US-JennyNeural"},
    "hi": {"male": "hi-IN-MadhurNeural", "female": "hi-IN-SwaraNeural"},
    "gu": {"male": "gu-IN-NiranjanNeural", "female": "gu-IN-DhwaniNeural"},
    "es": {"male": "es-ES-AlvaroNeural", "female": "es-ES-ElviraNeural"},
    "fr": {"male": "fr-FR-HenriNeural", "female": "fr-FR-DeniseNeural"},
    "de": {"male": "de-DE-ConradNeural", "female": "de-DE-KatjaNeural"},
    "ta": {"male": "ta-IN-ValluvarNeural", "female": "ta-IN-PallaviNeural"},
    "te": {"male": "te-IN-MohanNeural", "female": "te-IN-ShrutiNeural"},
    "mr": {"male": "mr-IN-ManoharNeural", "female": "mr-IN-AarohiNeural"},
    "bn": {"male": "bn-IN-BashkarNeural", "female": "bn-IN-TanishaaNeural"},
}


def get_voice_id(language: str, gender: str) -> str:
    """Resolve a voice ID from language + gender."""
    lang_voices = EDGE_TTS_VOICES.get(language, EDGE_TTS_VOICES["en"])
    return lang_voices.get(gender, lang_voices["female"])


async def generate_audio_file(
    text: str,
    voice_id: str,
    output_path: str,
) -> str:
    """Generate an MP3 audio file from text using edge-tts.

    Args:
        text: The narration text to speak.
        voice_id: Edge TTS voice identifier.
        output_path: Full path for the output MP3 file.

    Returns:
        The output_path on success.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    communicate = edge_tts.Communicate(text, voice_id)
    await communicate.save(output_path)

    file_size = os.path.getsize(output_path)
    logger.info("TTS audio saved: %s (%d bytes)", output_path, file_size)
    return output_path


def get_audio_duration(filepath: str) -> float:
    """Get the duration of an audio file in seconds using pydub."""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(filepath)
        return len(audio) / 1000.0  # ms → seconds
    except Exception as exc:
        logger.warning("Could not determine audio duration for %s: %s", filepath, exc)
        return 0.0
