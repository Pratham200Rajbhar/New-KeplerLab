"""Podcast script generation with Pydantic validation."""

import asyncio
import logging
from functools import partial
from io import BytesIO
from app.services.llm_service.structured_invoker import invoke_structured
from app.services.llm_service.llm_schemas import PodcastScriptOutput
from app.services.text_to_speech.tts import generate_dialogue_audio
from app.prompts import get_podcast_prompt

logger = logging.getLogger(__name__)


def generate_podcast_script(material_text: str) -> dict:
    """Generate podcast script from material text using structured LLM invocation.
    
    Args:
        material_text: Source material (truncated to 8000 chars)
    
    Returns:
        dict: Validated podcast script with title and dialogue
    """
    prompt = get_podcast_prompt(material_text[:8000])
    result = invoke_structured(prompt, PodcastScriptOutput, max_retries=2)
    return result.model_dump()


def generate_podcast_audio(material_text: str) -> tuple[BytesIO, str, list]:
    """
    Generate podcast audio with dialogue timing information (sync).

    Returns:
        tuple: (audio_buffer, title, dialogue_with_timing)
    """
    script = generate_podcast_script(material_text)
    dialogue = [(d["speaker"], d["text"]) for d in script.get("dialogue", [])]
    audio_buffer, timing_data = generate_dialogue_audio(dialogue)
    title = script.get("title", "Podcast")
    return audio_buffer, title, timing_data


async def generate_podcast_audio_async(material_text: str) -> tuple[BytesIO, str, list]:
    """Async wrapper — offloads blocking TTS + numpy concatenation to thread pool.

    Use this from async route handlers instead of the sync version.

    Returns:
        tuple: (audio_buffer, title, dialogue_with_timing)
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        partial(generate_podcast_audio, material_text),
    )
