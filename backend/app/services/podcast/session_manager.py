"""Podcast session management — CRUD, state transitions, and orchestration.

Manages the lifecycle of podcast sessions from creation through completion.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from prisma import Json
from app.db.prisma_client import get_prisma
from app.services.ws_manager import ws_manager
from app.services.podcast.script_generator import generate_podcast_script
from app.services.podcast.tts_service import synthesize_all_segments
from app.services.podcast.voice_map import get_default_voices, validate_voice

logger = logging.getLogger(__name__)


async def create_session(
    user_id: str,
    notebook_id: str,
    mode: str = "full",
    topic: Optional[str] = None,
    language: str = "en",
    host_voice: Optional[str] = None,
    guest_voice: Optional[str] = None,
    material_ids: Optional[List[str]] = None,
) -> Dict:
    """Create a new podcast session."""
    db = get_prisma()

    # Resolve default voices if not provided
    defaults = get_default_voices(language)
    host_v = host_voice or defaults["host"]
    guest_v = guest_voice or defaults["guest"]

    session = await db.podcastsession.create(
        data={
            "userId": user_id,
            "notebookId": notebook_id,
            "mode": mode,
            "topic": topic,
            "language": language,
            "hostVoice": host_v,
            "guestVoice": guest_v,
            "materialIds": material_ids or [],
            "status": "created",
        }
    )

    logger.info("Created podcast session %s for user %s", session.id, user_id)
    return _serialize_session(session)


async def get_session(session_id: str, user_id: str) -> Optional[Dict]:
    """Get full session state including segments."""
    db = get_prisma()

    session = await db.podcastsession.find_first(
        where={"id": session_id, "userId": user_id},
        include={
            "segments": {"order_by": {"index": "asc"}},
            "doubts": {"order_by": {"createdAt": "asc"}},
            "bookmarks": {"order_by": {"segmentIndex": "asc"}},
            "annotations": {"order_by": {"segmentIndex": "asc"}},
        },
    )

    if not session:
        return None

    return _serialize_session_full(session)


async def get_sessions_for_notebook(
    notebook_id: str, user_id: str
) -> List[Dict]:
    """List all podcast sessions for a notebook."""
    db = get_prisma()

    sessions = await db.podcastsession.find_many(
        where={"notebookId": notebook_id, "userId": user_id},
        order={"createdAt": "desc"},
    )

    return [_serialize_session(s) for s in sessions]


async def update_session_status(
    session_id: str, status: str, **extra_fields
) -> None:
    """Update session status and optional extra fields."""
    db = get_prisma()
    data = {"status": status, **extra_fields}
    if status == "completed":
        data["completedAt"] = datetime.utcnow()
    await db.podcastsession.update(where={"id": session_id}, data=data)
    logger.info("Session %s → %s", session_id, status)


async def update_current_segment(session_id: str, segment_index: int) -> None:
    """Update the current playback position."""
    db = get_prisma()
    await db.podcastsession.update(
        where={"id": session_id},
        data={"currentSegment": segment_index},
    )


async def start_generation(session_id: str, user_id: str) -> None:
    """Start the full podcast generation pipeline (script + TTS).
    
    This runs as a background task — progress is pushed via WebSocket.
    """
    db = get_prisma()
    session = await db.podcastsession.find_first(
        where={"id": session_id, "userId": user_id}
    )
    if not session:
        raise ValueError("Session not found")
    if session.status not in ("created", "failed"):
        raise ValueError(f"Cannot start generation from status: {session.status}")

    # Run generation in background
    asyncio.create_task(
        _generation_pipeline(session_id, user_id, session),
        name=f"podcast_gen_{session_id}",
    )


async def _generation_pipeline(session_id: str, user_id: str, session) -> None:
    """Full generation pipeline: script → parallel TTS (streaming) → ready.

    Key design decisions
    ─────────────────────
    • RAG retrieval + LLM are the unavoidable serial latency.
    • TTS for all segments fires concurrently (up to _TTS_CONCURRENCY=15).
    • For each segment: as soon as its audio is ready the DB row is written and
      a ``podcast_segment_ready`` WS event is pushed — the player can start
      streaming before the full batch is done.
    • Duration accumulation and final ``ready`` status happen only after every
      segment's callback has resolved, so the total duration value is accurate.
    """
    db = get_prisma()

    try:
        # ── Phase 1: Script generation ────────────────────────────────────
        await update_session_status(session_id, "script_generating")
        await ws_manager.send_to_user(user_id, {
            "type": "podcast_progress",
            "session_id": session_id,
            "phase": "script",
            "message": "Generating podcast script…",
            "progress": 0.05,
        })

        script_result = await generate_podcast_script(
            user_id=user_id,
            material_ids=session.materialIds,
            mode=session.mode,
            topic=session.topic,
            language=session.language,
            notebook_id=session.notebookId,
        )

        segments = script_result["segments"]
        # Normalise chapter keys: {name, start_segment} → {title, startSegment}
        raw_chapters = script_result.get("chapters", [])
        chapters: List[Dict] = [
            {
                "title": ch.get("title") or ch.get("name", f"Chapter {i + 1}"),
                "startSegment": ch.get("startSegment", ch.get("start_segment", 0)),
                "summary": ch.get("summary", ""),
            }
            for i, ch in enumerate(raw_chapters)
        ]
        title: str = script_result.get("title", "AI Podcast")

        # Build a fast chapter-name lookup: segment_index → chapter_title
        # (walk chapters in reverse so the first match wins)
        _sorted_chapters = sorted(chapters, key=lambda c: c["startSegment"])
        def _chapter_for(idx: int) -> Optional[str]:
            name = None
            for ch in _sorted_chapters:
                if idx >= ch["startSegment"]:
                    name = ch["title"]
                else:
                    break
            return name

        # Build segment lookup for the streaming callback
        seg_by_idx: Dict[int, Dict] = {s["segment_index"]: s for s in segments}

        # Persist title + chapters now so GET /session already shows them
        await db.podcastsession.update(
            where={"id": session_id},
            data={"title": title, "chapters": Json(chapters)},
        )

        await ws_manager.send_to_user(user_id, {
            "type": "podcast_progress",
            "session_id": session_id,
            "phase": "script",
            "message": f"Script ready — {len(segments)} segments",
            "progress": 0.25,
        })

        # ── Phase 2: Parallel TTS + streaming DB saves ────────────────────
        await update_session_status(session_id, "audio_generating")

        total_duration_ms = 0   # accumulated atomically via asyncio (single-thread)

        async def _on_segment_ready(idx: int, tts_result: Dict) -> None:
            """Called by tts_service as soon as each segment's audio is done."""
            nonlocal total_duration_ms
            seg = seg_by_idx[idx]
            duration = tts_result.get("duration_ms", 0)
            total_duration_ms += duration

            # Write DB row immediately — don't wait for the full batch
            await db.podcastsegment.create(
                data={
                    "sessionId": session_id,
                    "index": idx,
                    "speaker": seg["speaker"],
                    "text": seg["text"],
                    "audioUrl": tts_result.get("audio_url"),
                    "durationMs": duration,
                    "chapter": _chapter_for(idx),
                },
            )

            # Push per-segment WS event so frontend can begin early playback
            await ws_manager.send_to_user(user_id, {
                "type": "podcast_segment_ready",
                "session_id": session_id,
                "segment": {
                    "index": idx,
                    "speaker": seg["speaker"].upper(),
                    "text": seg["text"],
                    "audioPath": tts_result.get("audio_url"),
                    "durationMs": duration,
                    "chapter": _chapter_for(idx),
                },
            })

        async def _on_progress(completed: int, total: int) -> None:
            progress = 0.25 + 0.70 * (completed / max(total, 1))
            await ws_manager.send_to_user(user_id, {
                "type": "podcast_progress",
                "session_id": session_id,
                "phase": "audio",
                "message": f"Synthesising audio… {completed}/{total}",
                "progress": round(progress, 3),
            })

        await synthesize_all_segments(
            session_id=session_id,
            segments=segments,
            host_voice=session.hostVoice,
            guest_voice=session.guestVoice,
            on_progress=_on_progress,
            on_segment_ready=_on_segment_ready,
        )

        # ── Phase 3: Mark session ready ───────────────────────────────────
        await update_session_status(
            session_id, "ready",
            totalDurationMs=total_duration_ms,
        )

        await ws_manager.send_to_user(user_id, {
            "type": "podcast_ready",
            "session_id": session_id,
            "title": title,
            "total_segments": len(segments),
            "total_duration_ms": total_duration_ms,
            "chapters": chapters,
        })

        logger.info(
            "Podcast generation complete: session=%s segments=%d duration=%dms",
            session_id, len(segments), total_duration_ms,
        )

    except Exception as exc:
        logger.exception("Podcast generation failed: session=%s", session_id)
        await update_session_status(session_id, "failed", error=str(exc))
        await ws_manager.send_to_user(user_id, {
            "type": "podcast_progress",
            "session_id": session_id,
            "phase": "error",
            "message": f"Generation failed: {str(exc)[:300]}",
            "progress": 0,
        })


async def delete_session(session_id: str, user_id: str) -> bool:
    """Delete a podcast session and its files."""
    db = get_prisma()
    session = await db.podcastsession.find_first(
        where={"id": session_id, "userId": user_id}
    )
    if not session:
        return False

    # Delete audio files
    output_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "output", "podcast", session_id
    )
    if os.path.isdir(output_dir):
        import shutil
        shutil.rmtree(output_dir, ignore_errors=True)

    # Delete DB records (cascades handle segments, doubts, etc.)
    await db.podcastsession.delete(where={"id": session_id})
    logger.info("Deleted podcast session %s", session_id)
    return True


async def update_session_title(
    session_id: str, user_id: str, title: str
) -> Optional[Dict]:
    """Rename a podcast session."""
    db = get_prisma()
    session = await db.podcastsession.find_first(
        where={"id": session_id, "userId": user_id}
    )
    if not session:
        return None

    updated = await db.podcastsession.update(
        where={"id": session_id}, data={"title": title}
    )
    return _serialize_session(updated)


async def update_session_tags(
    session_id: str, user_id: str, tags: List[str]
) -> Optional[Dict]:
    """Update tags for a podcast session."""
    db = get_prisma()
    session = await db.podcastsession.find_first(
        where={"id": session_id, "userId": user_id}
    )
    if not session:
        return None

    updated = await db.podcastsession.update(
        where={"id": session_id}, data={"tags": tags}
    )
    return _serialize_session(updated)


# ── Serialization helpers ─────────────────────────────────────


def _serialize_session(s) -> Dict:
    """Serialize a session record to a dict (camelCase for JS clients)."""
    return {
        "id": s.id,
        "notebookId": s.notebookId,
        "userId": s.userId,
        "mode": s.mode,
        "topic": s.topic,
        "language": s.language,
        "status": s.status,
        "currentSegment": s.currentSegment,
        "hostVoice": s.hostVoice,
        "guestVoice": s.guestVoice,
        "title": s.title,
        "tags": s.tags or [],
        "chapters": s.chapters or [],
        "totalDurationMs": s.totalDurationMs or 0,
        "materialIds": s.materialIds or [],
        "summary": s.summary,
        "error": s.error,
        "createdAt": s.createdAt.isoformat() if s.createdAt else None,
        "completedAt": s.completedAt.isoformat() if s.completedAt else None,
    }


def _serialize_session_full(s) -> Dict:
    """Serialize a session with included relations."""
    data = _serialize_session(s)

    data["segments"] = [
        {
            "id": seg.id,
            "index": seg.index,
            "speaker": seg.speaker.upper(),
            "text": seg.text,
            "audioPath": seg.audioUrl,  # frontend checks seg.audioPath
            "durationMs": seg.durationMs or 0,
            "chapter": seg.chapter,
        }
        for seg in (s.segments or [])
    ]

    data["doubts"] = [
        {
            "id": d.id,
            "pausedAtSegment": d.pausedAtSegment,
            "questionText": d.questionText,
            "questionAudioUrl": d.questionAudioUrl,
            "answerText": d.answerText,
            "audioPath": d.answerAudioUrl,  # frontend checks doubt.audioPath
            "resolvedAt": d.resolvedAt.isoformat() if d.resolvedAt else None,
            "createdAt": d.createdAt.isoformat() if d.createdAt else None,
        }
        for d in (s.doubts or [])
    ]

    data["bookmarks"] = [
        {
            "id": b.id,
            "segmentIndex": b.segmentIndex,
            "label": b.label,
            "createdAt": b.createdAt.isoformat() if b.createdAt else None,
        }
        for b in (s.bookmarks or [])
    ]

    data["annotations"] = [
        {
            "id": a.id,
            "segmentIndex": a.segmentIndex,
            "note": a.note,
            "createdAt": a.createdAt.isoformat() if a.createdAt else None,
        }
        for a in (s.annotations or [])
    ]

    return data
