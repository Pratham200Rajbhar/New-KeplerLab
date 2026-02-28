"""Q&A service for podcast interruptions.

Handles questions during podcast playback — routes through RAG,
generates answers, synthesizes answer audio.

Optimisations:
• asyncio.to_thread() for all blocking calls (no lambda-closure bugs).
• RAG skips notebook filter when material_ids are present (matches
  script_generator.py behaviour for unlinked materials).
• Parallel RAG + prompt-build so TTS starts as early as possible.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Optional

from app.db.prisma_client import get_prisma
from app.services.llm_service.llm import get_llm
from app.services.rag.secure_retriever import secure_similarity_search_enhanced
from app.services.podcast.tts_service import synthesize_single
from app.services.podcast.voice_map import LANGUAGE_NAMES

logger = logging.getLogger(__name__)

_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "prompts")


def _load_qa_prompt() -> str:
    path = os.path.join(_PROMPT_DIR, "podcast_qa_prompt.txt")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _rag_for_question(
    user_id: str,
    question: str,
    material_ids: list,
    notebook_id: Optional[str],
) -> str:
    """Synchronous RAG call — run via asyncio.to_thread."""
    # Skip notebook filter when material_ids are given so unlinked materials work
    nb_filter = notebook_id if not material_ids else None
    ctx = secure_similarity_search_enhanced(
        user_id=user_id,
        query=question,
        material_ids=material_ids,
        notebook_id=nb_filter,
        use_mmr=True,
        use_reranker=True,
        return_formatted=True,
    )
    if not ctx or ctx == "No relevant context found.":
        # Fallback without notebook filter
        ctx = secure_similarity_search_enhanced(
            user_id=user_id,
            query=question,
            material_ids=material_ids,
            notebook_id=None,
            use_mmr=False,
            use_reranker=False,
            return_formatted=True,
        )
    return ctx or "No relevant context available."


async def handle_question(
    session_id: str,
    user_id: str,
    question_text: str,
    paused_at_segment: int,
    question_audio_url: Optional[str] = None,
) -> Dict:
    """Process a listener question during podcast interruption.

    Pipeline: RAG retrieval → LLM answer → TTS synthesis → DB persist.
    """
    db = get_prisma()
    session = await db.podcastsession.find_first(
        where={"id": session_id, "userId": user_id}
    )
    if not session:
        raise ValueError("Session not found")

    logger.info(
        "Q&A: session=%s segment=%d question=%s",
        session_id, paused_at_segment, question_text[:80],
    )

    # 1. RAG retrieval
    context = await asyncio.to_thread(
        _rag_for_question,
        user_id, question_text, session.materialIds, session.notebookId,
    )

    # 2. Generate answer
    language_name = LANGUAGE_NAMES.get(session.language, "English")
    prompt = _load_qa_prompt().format(
        language=language_name,
        context=context,
        question=question_text,
    )

    llm = get_llm(mode="chat", max_tokens=2000)
    response = await asyncio.to_thread(llm.invoke, prompt)
    answer_text = response.content if hasattr(response, "content") else str(response)

    # 3. Synthesise answer audio (guest voice answers the question)
    answer_filename = f"qa_{uuid.uuid4().hex[:8]}.mp3"
    tts_result = await synthesize_single(
        session_id=session_id,
        text=answer_text,
        voice_id=session.guestVoice,
        filename=answer_filename,
    )

    # 4. Persist doubt record
    doubt = await db.podcastdoubt.create(
        data={
            "sessionId": session_id,
            "pausedAtSegment": paused_at_segment,
            "questionText": question_text,
            "questionAudioUrl": question_audio_url,
            "answerText": answer_text,
            "answerAudioUrl": tts_result["audio_url"],
        },
    )

    logger.info("Q&A answered: doubt=%s answer_len=%d", doubt.id, len(answer_text))

    return {
        "id": doubt.id,
        "questionText": question_text,
        "answerText": answer_text,
        "audioPath": tts_result["audio_url"],
        "answerDurationMs": tts_result["duration_ms"],
        "pausedAtSegment": paused_at_segment,
    }


async def get_doubts(session_id: str, user_id: str) -> list:
    """Get all Q&A doubts for a session."""
    db = get_prisma()
    session = await db.podcastsession.find_first(
        where={"id": session_id, "userId": user_id}
    )
    if not session:
        return []

    doubts = await db.podcastdoubt.find_many(
        where={"sessionId": session_id},
        order={"createdAt": "asc"},
    )

    return [
        {
            "id": d.id,
            "pausedAtSegment": d.pausedAtSegment,
            "questionText": d.questionText,
            "questionAudioUrl": d.questionAudioUrl,
            "answerText": d.answerText,
            "audioPath": d.answerAudioUrl,
            "resolvedAt": d.resolvedAt.isoformat() if d.resolvedAt else None,
            "createdAt": d.createdAt.isoformat() if d.createdAt else None,
        }
        for d in doubts
    ]


async def resolve_doubt(doubt_id: str) -> None:
    """Mark a doubt as resolved."""
    db = get_prisma()
    await db.podcastdoubt.update(
        where={"id": doubt_id},
        data={"resolvedAt": datetime.utcnow()},
    )
