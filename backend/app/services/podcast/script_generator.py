"""Podcast script generation via LLM.

Generates a structured two-persona dialogue from source material.

Optimisations vs. the original:
• Multi-angle RAG — fires 2–3 query variants in parallel so the LLM gets a
  richer, more diverse context window without extra latency.
• asyncio.to_thread() instead of run_in_executor(lambda:…) — avoids closure
  capture bugs and is cleaner under Python 3.11.
• Larger max_tokens budget (12 000) so longer scripts aren't truncated.
• Robust JSON extraction with a second-pass repair attempt.
• Per-mode query strategy so "debate", "deep-dive", etc. get relevant chunks.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Dict, List, Optional

from app.services.llm_service.llm import get_llm
from app.services.rag.secure_retriever import secure_similarity_search_enhanced
from app.services.podcast.voice_map import LANGUAGE_NAMES

logger = logging.getLogger(__name__)

_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "prompts")

# Queries per mode: primary query + optional supplementary angles
_MODE_QUERIES: Dict[str, List[str]] = {
    "overview": [
        "Comprehensive overview of all key topics, concepts, and findings",
        "Summary of main conclusions and takeaways",
    ],
    "deep-dive": [
        "Detailed technical explanation of core concepts and mechanisms",
        "Advanced details, edge cases, and nuanced analysis",
    ],
    "debate": [
        "Arguments for and against the main claims",
        "Counterarguments, criticisms, and alternative perspectives",
    ],
    "q-and-a": [
        "Frequently asked questions and their answers",
        "Common misconceptions and clarifications",
    ],
    "full": [
        "Comprehensive overview of all key topics, concepts, and findings",
        "Detailed analysis and supporting evidence",
    ],
    "topic": [],  # filled dynamically from req.topic
}


def _load_prompt() -> str:
    path = os.path.join(_PROMPT_DIR, "podcast_script_prompt.txt")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _extract_json(text: str) -> dict:
    """Extract JSON object from LLM response.  Tries progressively looser strategies."""
    text = text.strip()

    # Strategy 1 — direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2 — strip markdown fences
    for pattern in (
        r"```json\s*\n?([\s\S]*?)\n?```",
        r"```\s*\n?([\s\S]*?)\n?```",
    ):
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                pass

    # Strategy 3 — grab outermost {...}
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    # Strategy 4 — fix common trailing-comma issues and retry
    candidate = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    raise ValueError(
        f"Could not extract valid JSON from LLM response "
        f"({len(text)} chars): {text[:300]}…"
    )


def _rag_search(
    user_id: str,
    query: str,
    material_ids: List[str],
    notebook_id: Optional[str],
    use_mmr: bool = True,
    use_reranker: bool = True,
) -> str:
    """Synchronous wrapper — run in a thread via asyncio.to_thread."""
    return secure_similarity_search_enhanced(
        user_id=user_id,
        query=query,
        material_ids=material_ids,
        notebook_id=notebook_id,
        use_mmr=use_mmr,
        use_reranker=use_reranker,
        return_formatted=True,
    )


async def _gather_context(
    user_id: str,
    queries: List[str],
    material_ids: List[str],
    notebook_filter: Optional[str],
) -> str:
    """Fire multiple RAG queries in parallel and merge unique chunks."""
    if not queries:
        return ""

    results = await asyncio.gather(
        *[
            asyncio.to_thread(
                _rag_search,
                user_id, q, material_ids, notebook_filter,
                True, True,
            )
            for q in queries
        ],
        return_exceptions=True,
    )

    # Deduplicate chunks (split on double-newline, preserve order)
    seen: set[str] = set()
    merged: List[str] = []
    for res in results:
        if isinstance(res, Exception):
            logger.warning("RAG query failed: %s", res)
            continue
        if not res or res == "No relevant context found.":
            continue
        for chunk in res.split("\n\n"):
            chunk = chunk.strip()
            if chunk and chunk not in seen:
                seen.add(chunk)
                merged.append(chunk)

    return "\n\n".join(merged)


async def generate_podcast_script(
    user_id: str,
    material_ids: List[str],
    mode: str = "full",
    topic: Optional[str] = None,
    language: str = "en",
    notebook_id: Optional[str] = None,
) -> Dict:
    """Generate a two-persona podcast script from source material.

    Returns:
        {
            "segments": [{speaker, text, segment_index}],
            "chapters": [{title, startSegment, summary}],
            "title": str
        }
    """
    logger.info(
        "Generating podcast script: mode=%s language=%s materials=%d",
        mode, language, len(material_ids),
    )

    # ── Build query list ──────────────────────────────────────────────────
    if mode == "topic" and topic:
        queries = [
            f'Detailed information about: "{topic}"',
            f'Background context and supporting details for: "{topic}"',
        ]
    else:
        queries = _MODE_QUERIES.get(mode, _MODE_QUERIES["overview"])

    # When material_ids are given, skip notebook filter — material may not be
    # linked to this notebook yet (e.g. just uploaded).
    notebook_filter = notebook_id if not material_ids else None

    # ── Phase A: Parallel multi-angle RAG ────────────────────────────────
    context = await _gather_context(user_id, queries, material_ids, notebook_filter)

    if not context:
        # Fallback: single broad query without MMR/reranker
        logger.warning("Multi-angle RAG returned no context; falling back to basic search")
        context = await asyncio.to_thread(
            _rag_search,
            user_id,
            "All content and key information",
            material_ids,
            None,      # no notebook filter
            False,     # no MMR
            False,     # no reranker
        )

    if not context or context == "No relevant context found.":
        raise ValueError("No relevant content found in the selected materials.")

    logger.info("Context gathered: %d chars from %d query angles", len(context), len(queries))

    # ── Phase B: LLM script generation ───────────────────────────────────
    language_name = LANGUAGE_NAMES.get(language, "English")
    mode_instruction = (
        f'Focus specifically on: "{topic}". Only cover content related to this topic.'
        if mode == "topic" and topic
        else {
            "overview":  "Cover all major topics and concepts comprehensively but accessibly.",
            "deep-dive": "Provide in-depth technical analysis; do not oversimplify.",
            "debate":    "Present contrasting viewpoints; host challenges, guest defends.",
            "q-and-a":   "Host asks questions, guest answers clearly and precisely.",
            "full":      "Cover everything — breadth and depth — in a long-form episode.",
        }.get(mode, "Cover all major topics and concepts from the source material comprehensively.")
    )

    prompt = _load_prompt().format(
        language=language_name,
        mode_instruction=mode_instruction,
        context=context,
    )

    llm = get_llm(mode="creative", max_tokens=12000)
    response = await asyncio.to_thread(llm.invoke, prompt)

    response_text = response.content if hasattr(response, "content") else str(response)
    logger.info("Script LLM response: %d chars", len(response_text))

    # ── Phase C: Parse + validate ─────────────────────────────────────────
    result = _extract_json(response_text)

    segments: List[Dict] = result.get("segments", [])
    if not segments:
        raise ValueError("LLM returned empty segments list")

    # Ensure sequential indices and valid speaker values
    for i, seg in enumerate(segments):
        seg["segment_index"] = i
        if seg.get("speaker", "").lower() not in ("host", "guest"):
            seg["speaker"] = "host" if i % 2 == 0 else "guest"

    # Normalise chapters from either key convention
    raw_chapters: List[Dict] = result.get("chapters", [{"name": "Full Episode", "start_segment": 0}])
    chapters: List[Dict] = [
        {
            "title": ch.get("title") or ch.get("name", f"Chapter {i + 1}"),
            "startSegment": ch.get("startSegment", ch.get("start_segment", 0)),
            "summary": ch.get("summary", ""),
        }
        for i, ch in enumerate(raw_chapters)
    ]
    title: str = result.get("title", "AI Podcast")

    logger.info(
        "Script generated: %d segments, %d chapters, title=%r",
        len(segments), len(chapters), title,
    )

    return {"segments": segments, "chapters": chapters, "title": title}
