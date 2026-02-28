"""Export service for podcast sessions — PDF and JSON.

Both exports run as background operations; download URL is pushed via WebSocket.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Optional

from app.db.prisma_client import get_prisma
from app.services.ws_manager import ws_manager
from app.services.llm_service.llm import get_llm

logger = logging.getLogger(__name__)

_OUTPUT_BASE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "output", "podcast")
)


async def create_export(
    session_id: str,
    user_id: str,
    format: str,  # "pdf" or "json"
) -> Dict:
    """Create an export job for a podcast session."""
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
        raise ValueError("Session not found")

    export_record = await db.podcastexport.create(
        data={
            "sessionId": session_id,
            "format": format,
            "status": "processing",
        },
    )

    # Run export in background
    asyncio.create_task(
        _run_export(export_record.id, session, user_id, format),
        name=f"podcast_export_{export_record.id}",
    )

    return {
        "id": export_record.id,
        "export_id": export_record.id,
        "format": format,
        "status": "processing",
        "fileUrl": None,
    }


async def _run_export(
    export_id: str, session, user_id: str, format: str
) -> None:
    """Execute the export (background task)."""
    db = get_prisma()
    try:
        session_dir = os.path.join(_OUTPUT_BASE, session.id)
        os.makedirs(session_dir, exist_ok=True)

        if format == "json":
            file_url = await _export_json(session, session_dir)
        elif format == "pdf":
            file_url = await _export_pdf(session, session_dir)
        else:
            raise ValueError(f"Unknown format: {format}")

        await db.podcastexport.update(
            where={"id": export_id},
            data={"status": "completed", "fileUrl": file_url},
        )

        await ws_manager.send_to_user(user_id, {
            "type": "podcast_export_ready",
            "session_id": session.id,
            "export_id": export_id,
            "format": format,
            "file_url": file_url,
        })

    except Exception as exc:
        logger.exception("Export failed: %s", export_id)
        await db.podcastexport.update(
            where={"id": export_id},
            data={"status": "failed"},
        )
        await ws_manager.send_to_user(user_id, {
            "type": "podcast_export_ready",
            "session_id": session.id,
            "export_id": export_id,
            "format": format,
            "error": str(exc),
        })


async def _export_json(session, session_dir: str) -> str:
    """Export session as structured JSON."""
    filename = f"export_{uuid.uuid4().hex[:8]}.json"
    filepath = os.path.join(session_dir, filename)

    data = {
        "session_metadata": {
            "id": session.id,
            "title": session.title,
            "mode": session.mode,
            "topic": session.topic,
            "language": session.language,
            "total_duration_ms": session.totalDurationMs,
            "created_at": session.createdAt.isoformat() if session.createdAt else None,
            "completed_at": session.completedAt.isoformat() if session.completedAt else None,
        },
        "chapters": session.chapters or [],
        "segments": [
            {
                "index": seg.index,
                "speaker": seg.speaker,
                "text": seg.text,
                "duration_ms": seg.durationMs,
                "chapter": seg.chapter,
                "bookmarked": any(
                    b.segmentIndex == seg.index for b in (session.bookmarks or [])
                ),
                "annotations": [
                    {"note": a.note, "created_at": a.createdAt.isoformat()}
                    for a in (session.annotations or [])
                    if a.segmentIndex == seg.index
                ],
            }
            for seg in (session.segments or [])
        ],
        "doubts": [
            {
                "paused_at_segment": d.pausedAtSegment,
                "question": d.questionText,
                "answer": d.answerText,
                "timestamp": d.createdAt.isoformat() if d.createdAt else None,
            }
            for d in (session.doubts or [])
        ],
        "summary": session.summary,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return f"/podcast/export/file/{session.id}/{filename}"


async def _export_pdf(session, session_dir: str) -> str:
    """Export session as PDF with full transcript, doubts, and bookmarks."""
    filename = f"export_{uuid.uuid4().hex[:8]}.pdf"
    filepath = os.path.join(session_dir, filename)

    try:
        from fpdf import FPDF

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Try to use NotoSans for Unicode support
        try:
            font_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "fonts")
            noto_path = os.path.join(font_dir, "NotoSans-Regular.ttf")
            if os.path.isfile(noto_path):
                pdf.add_font("NotoSans", "", noto_path, uni=True)
                pdf.set_font("NotoSans", size=10)
            else:
                pdf.set_font("Helvetica", size=10)
        except Exception:
            pdf.set_font("Helvetica", size=10)

        # Header page
        pdf.add_page()
        pdf.set_font_size(18)
        pdf.cell(0, 10, session.title or "Podcast Transcript", ln=True, align="C")
        pdf.set_font_size(10)
        pdf.cell(0, 8, f"Language: {session.language} | Mode: {session.mode}", ln=True, align="C")
        if session.topic:
            pdf.cell(0, 8, f"Topic: {session.topic}", ln=True, align="C")
        duration_min = (session.totalDurationMs or 0) / 60000
        pdf.cell(0, 8, f"Duration: ~{duration_min:.0f} min", ln=True, align="C")
        pdf.cell(0, 8, f"Created: {session.createdAt.strftime('%Y-%m-%d') if session.createdAt else 'N/A'}", ln=True, align="C")
        pdf.ln(10)

        # Transcript
        pdf.set_font_size(14)
        pdf.cell(0, 10, "Transcript", ln=True)
        pdf.set_font_size(10)

        current_chapter = None
        for seg in (session.segments or []):
            # Chapter divider
            if seg.chapter and seg.chapter != current_chapter:
                current_chapter = seg.chapter
                pdf.ln(5)
                pdf.set_font_size(12)
                pdf.cell(0, 8, f"--- {current_chapter} ---", ln=True)
                pdf.set_font_size(10)

            speaker_label = "HOST" if seg.speaker == "host" else "GUEST"
            time_ms = sum(
                s.durationMs for s in (session.segments or []) if s.index < seg.index
            )
            timestamp = f"[{time_ms // 60000}:{(time_ms // 1000) % 60:02d}]"

            pdf.set_font_size(9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 6, f"{timestamp} {speaker_label}:", ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font_size(10)
            pdf.multi_cell(0, 5, seg.text)
            pdf.ln(2)

        # Doubts section
        if session.doubts:
            pdf.add_page()
            pdf.set_font_size(14)
            pdf.cell(0, 10, "Questions & Answers", ln=True)
            pdf.set_font_size(10)

            for d in session.doubts:
                pdf.ln(3)
                pdf.set_text_color(0, 100, 200)
                pdf.cell(0, 6, f"Q (at segment {d.pausedAtSegment}): {d.questionText}", ln=True)
                pdf.set_text_color(0, 0, 0)
                pdf.multi_cell(0, 5, f"A: {d.answerText or 'No answer'}")
                pdf.ln(2)

        # Bookmarks
        if session.bookmarks:
            pdf.ln(10)
            pdf.set_font_size(14)
            pdf.cell(0, 10, "Bookmarks", ln=True)
            pdf.set_font_size(10)
            for b in session.bookmarks:
                pdf.cell(0, 6, f"  Segment {b.segmentIndex}: {b.label or '(no label)'}", ln=True)

        pdf.output(filepath)

    except ImportError:
        # fpdf2 not installed — fallback to text file with .pdf extension
        logger.warning("fpdf2 not installed; generating plain text export as PDF fallback")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {session.title or 'Podcast Transcript'}\n\n")
            for seg in (session.segments or []):
                speaker = "HOST" if seg.speaker == "host" else "GUEST"
                f.write(f"[{speaker}] {seg.text}\n\n")

    return f"/podcast/export/file/{session.id}/{filename}"


async def get_export(export_id: str) -> Optional[Dict]:
    """Get export record."""
    db = get_prisma()
    export = await db.podcastexport.find_first(where={"id": export_id})
    if not export:
        return None
    return {
        "id": export.id,
        "session_id": export.sessionId,
        "format": export.format,
        "file_url": export.fileUrl,
        "status": export.status,
        "created_at": export.createdAt.isoformat() if export.createdAt else None,
    }


def get_export_file_path(session_id: str, filename: str) -> Optional[str]:
    """Get filesystem path for an export file."""
    path = os.path.join(_OUTPUT_BASE, session_id, filename)
    if os.path.isfile(path):
        return path
    return None


async def generate_summary(session_id: str, user_id: str) -> str:
    """Generate a summary card for a completed podcast session."""
    db = get_prisma()
    session = await db.podcastsession.find_first(
        where={"id": session_id, "userId": user_id},
        include={
            "segments": {"order_by": {"index": "asc"}},
            "doubts": {"order_by": {"createdAt": "asc"}},
        },
    )
    if not session:
        raise ValueError("Session not found")

    # Build transcript text
    transcript = "\n".join(
        f"{'HOST' if s.speaker == 'host' else 'GUEST'}: {s.text}"
        for s in (session.segments or [])
    )

    # Build doubts text
    doubts_text = ""
    if session.doubts:
        doubts_text = "\n\nQuestions asked:\n" + "\n".join(
            f"Q: {d.questionText}\nA: {d.answerText or 'N/A'}"
            for d in session.doubts
        )

    prompt = (
        "Summarize this podcast transcript in 3-5 bullet points. "
        "Include: key concepts covered, main takeaways, and any questions the listener asked.\n\n"
        f"Transcript:\n{transcript[:8000]}"
        f"{doubts_text}"
        "\n\nProvide a concise summary:"
    )

    llm = get_llm(mode="chat", max_tokens=1000)
    response = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: llm.invoke(prompt),
    )
    summary = response.content if hasattr(response, "content") else str(response)

    # Save summary
    await db.podcastsession.update(
        where={"id": session_id},
        data={"summary": summary},
    )

    return summary
