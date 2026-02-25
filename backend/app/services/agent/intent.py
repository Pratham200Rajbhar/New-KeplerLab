"""High-speed intent detector using MYOPENLM for fast keyword-based classification.

Detects user intent from their message to route to the correct tool.
Uses fast keyword rules with MYOPENLM fallback for complex cases.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Tuple

from app.services.agent.state import AgentState
from app.services.llm_service.llm import get_llm

logger = logging.getLogger(__name__)

# ── Intent Constants ──────────────────────────────────────────
QUESTION = "QUESTION"
DATA_ANALYSIS = "DATA_ANALYSIS"
RESEARCH = "RESEARCH"
CODE_EXECUTION = "CODE_EXECUTION"
CONTENT_GENERATION = "CONTENT_GENERATION"

# ── Intent Hierarchy — order matters, checked top to bottom ──

_INTENT_RULES = [
    # DATA_ANALYSIS — must come before QUESTION to catch data queries
    (DATA_ANALYSIS, [
        r"\b(csv|excel|xlsx|spreadsheet|dataframe|df\b|column|row|average|mean|sum|count|aggregate|trend|chart|plot|graph|visuali[sz]e|pandas|numpy|calculate|compute)\b",
        r"\bwhat (is|are|was|were) the (total|average|max|min|count|sum)\b",
        r"\bhow many\b.*(row|record|entry|entries)\b",
        r"\bshow me (a |the )?(chart|graph|plot|table)\b",
        r"\b(analyze|analyse)\s+(this|the|my)?\s*(data|csv|file|table|spreadsheet)\b",
        r"\b(explain|describe|tell me about)\s+(the\s+)?(data|table|spreadsheet|columns?)\b",
    ], 0.90),
    # CODE_EXECUTION — explicit code requests
    (CODE_EXECUTION, [
        r"\b(run|execute|write|create)\s+(a\s+)?(python|script|code|program|function)\b",
        r"\b(python|bash|shell)\b.*\b(run|execute|do)\b",
        r"\b(code|script)\s+(for|to|that)\b",
    ], 0.90),
    # RESEARCH — deep research requests
    (RESEARCH, [
        r"\b(research|investigate|deep\s*dive|find\s*out\s*about|search\s+the\s+web|look\s+up\s+online|latest|current|news\s+about)\b",
        r"\b(comprehensive|thorough|detailed)\s+(analysis|research|study|report)\b",
    ], 0.90),
    # CONTENT_GENERATION — explicit creation requests only
    (CONTENT_GENERATION, [
        r"\b(make|create|generate|build|produce)\s+(me\s+)?(a\s+|some\s+)?(quiz|flashcard|flash\s*card|presentation|slides|ppt|podcast)\b",
        r"\b(quiz|flashcard|flash\s*card)\s+(me|from|on|about)\b",
    ], 0.92),
    # QUESTION — default fallback (always matches)
    (QUESTION, [r".*"], 0.50),
]


async def _llm_classify(message: str) -> Dict[str, Any]:
    """LLM-based intent classification via MYOPENLM (fast model).

    Only called when keyword rules are ambiguous.  Returns same shape as
    ``_keyword_classify``.
    """
    _INTENT_LIST = ", ".join([QUESTION, DATA_ANALYSIS, RESEARCH, CODE_EXECUTION, CONTENT_GENERATION])
    prompt = (
        f"Classify the following user message into exactly one intent.\n"
        f"Intents: {_INTENT_LIST}\n"
        f"Rules:\n"
        f"- QUESTION: general question or information request about uploaded content\n"
        f"- DATA_ANALYSIS: asks to analyze, chart, or compute over data/tables/CSV\n"
        f"- RESEARCH: asks to search the web or research external topics\n"
        f"- CODE_EXECUTION: asks to write or run code\n"
        f"- CONTENT_GENERATION: asks to create quiz, flashcards, presentation, or podcast\n"
        f"\nMessage: \"{message}\"\n"
        f"Reply with ONLY the intent name, nothing else."
    )
    llm = get_llm(temperature=0.0, max_tokens=20)
    response = await llm.ainvoke(prompt)
    raw = (getattr(response, "content", None) or str(response)).strip().upper()
    # Normalise — pick whichever known intent appears first in the response
    for intent in [DATA_ANALYSIS, CODE_EXECUTION, RESEARCH, CONTENT_GENERATION, QUESTION]:
        if intent in raw:
            return {"intent": intent, "confidence": 0.80}
    return {"intent": QUESTION, "confidence": 0.60}


def _keyword_classify(message: str) -> Dict[str, Any]:
    """Fast keyword-based classification using ordered priority rules.

    Returns dict with intent, confidence, requires_planning.
    Always returns a result (QUESTION as fallback).
    """
    msg_lower = message.lower()

    for intent, patterns, confidence in _INTENT_RULES:
        for pattern in patterns:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                return {
                    "intent": intent,
                    "confidence": confidence,
                }

    # Should never reach here due to QUESTION catch-all, but just in case
    return {"intent": QUESTION, "confidence": 0.5}


async def detect_intent(state: AgentState) -> AgentState:
    """Intent detection node for the agent graph.

    If intent is already set with confidence == 1.0 (pre-set by a route handler
    such as /agent/analyze or /agent/research, or via intent_override), the
    detection step is skipped to avoid overriding the caller's explicit intent.

    Otherwise tries keyword rules (fast path).
    """
    # ── Fast bypass: caller pre-set the intent or intent_override ──────────
    if state.get("intent_override"):
        logger.info(
            "[intent] intent_override=%s — using directly",
            state["intent_override"],
        )
        return {
            **state,
            "intent": state["intent_override"],
            "intent_confidence": 1.0,
        }

    if state.get("intent") and state.get("intent_confidence", 0.0) >= 1.0:
        logger.info(
            "[intent] Pre-set intent=%s (confidence=1.0) — skipping detection",
            state["intent"],
        )
        return state

    message = state.get("user_message", "")
    logger.info("Detecting intent for message: %s...", message[:100])

    # Fast path: keyword rules (always returns a result)
    result = _keyword_classify(message)
    logger.info(
        "Keyword intent: %s (confidence=%.2f)", result["intent"], result["confidence"]
    )

    # LLM fallback via MYOPENLM — only when keyword rules are ambiguous
    # (i.e. fell through to the QUESTION catch-all with low confidence)
    if result["intent"] == QUESTION and result["confidence"] <= 0.55:
        try:
            llm_result = await _llm_classify(message)
            logger.info(
                "[intent] LLM fallback: %s (confidence=%.2f)",
                llm_result["intent"], llm_result["confidence"],
            )
            result = llm_result
        except Exception as exc:
            logger.warning("[intent] LLM fallback failed, keeping keyword result: %s", exc)

    return {
        **state,
        "intent": result["intent"],
        "intent_confidence": result["confidence"],
    }
