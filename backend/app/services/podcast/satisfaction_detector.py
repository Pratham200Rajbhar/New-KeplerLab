"""Satisfaction detection for podcast Q&A.

Two-layer system:
1. Heuristic — multilingual dictionary of satisfaction phrases (fast, no LLM)
2. LLM classifier — only when Layer 1 is uncertain (~20% of responses)
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional, Tuple

from app.services.llm_service.llm import get_llm

logger = logging.getLogger(__name__)

# ── Satisfaction phrase dictionaries per language ──────────────
# Each entry: (phrase, confidence) — confidence ≥ 0.85 = auto-resume

SATISFACTION_PHRASES = {
    "en": [
        ("okay", 0.85), ("ok", 0.85), ("got it", 0.90), ("i see", 0.85),
        ("makes sense", 0.90), ("understood", 0.90), ("thank you", 0.85),
        ("thanks", 0.85), ("that's clear", 0.92), ("i understand", 0.90),
        ("perfect", 0.90), ("great", 0.85), ("alright", 0.85), ("cool", 0.80),
        ("good", 0.80), ("nice", 0.80), ("right", 0.75), ("yep", 0.85),
        ("yes", 0.75), ("sure", 0.75), ("fine", 0.80), ("no more questions", 0.95),
        ("that answers my question", 0.95), ("let's continue", 0.95),
        ("resume", 0.95), ("move on", 0.92), ("go ahead", 0.92),
    ],
    "hi": [
        ("ठीक है", 0.85), ("समझ गया", 0.90), ("समझ गयी", 0.90),
        ("अच्छा", 0.85), ("धन्यवाद", 0.85), ("शुक्रिया", 0.85),
        ("हाँ", 0.75), ("सही है", 0.85), ("ठीक", 0.80),
        ("बढ़िया", 0.85), ("आगे बढ़ो", 0.92), ("चालू करो", 0.92),
    ],
    "gu": [
        ("સમજાયું", 0.90), ("ઠીક છે", 0.85), ("બરાબર", 0.85),
        ("આભાર", 0.85), ("હા", 0.75), ("સારું", 0.85),
        ("આગળ વધો", 0.92), ("ચાલુ કરો", 0.92),
    ],
    "es": [
        ("vale", 0.85), ("entendido", 0.90), ("de acuerdo", 0.85),
        ("gracias", 0.85), ("perfecto", 0.90), ("bien", 0.80),
        ("sí", 0.75), ("claro", 0.85), ("continúa", 0.92),
    ],
    "ar": [
        ("حسنا", 0.85), ("فهمت", 0.90), ("شكرا", 0.85),
        ("تمام", 0.85), ("نعم", 0.75), ("واضح", 0.90),
        ("استمر", 0.92),
    ],
    "fr": [
        ("d'accord", 0.85), ("compris", 0.90), ("merci", 0.85),
        ("parfait", 0.90), ("bien", 0.80), ("oui", 0.75),
        ("c'est clair", 0.90), ("continue", 0.92),
    ],
    "de": [
        ("okay", 0.85), ("verstanden", 0.90), ("danke", 0.85),
        ("perfekt", 0.90), ("gut", 0.80), ("ja", 0.75),
        ("klar", 0.85), ("weiter", 0.92), ("alles klar", 0.90),
    ],
    "ja": [
        ("わかりました", 0.90), ("了解", 0.90), ("ありがとう", 0.85),
        ("はい", 0.75), ("なるほど", 0.85), ("続けて", 0.92),
        ("大丈夫", 0.85), ("ok", 0.85),
    ],
    "zh": [
        ("好的", 0.85), ("明白了", 0.90), ("谢谢", 0.85),
        ("懂了", 0.90), ("可以", 0.80), ("继续", 0.92),
        ("没问题", 0.90), ("对", 0.75),
    ],
    "pt": [
        ("entendido", 0.90), ("obrigado", 0.85), ("ok", 0.85),
        ("certo", 0.85), ("perfeito", 0.90), ("sim", 0.75),
        ("claro", 0.85), ("continue", 0.92),
    ],
}

# Phrases that indicate the user wants to ask more
FOLLOWUP_PHRASES = {
    "en": ["but", "what about", "can you explain", "why", "how", "tell me more",
           "what if", "also", "another question", "wait", "hold on", "actually"],
    "hi": ["लेकिन", "क्यों", "कैसे", "और बताओ", "एक और सवाल", "रुको"],
    "gu": ["પણ", "કેમ", "કેવી રીતે", "વધુ કહો", "એક વધુ સવાલ"],
    "es": ["pero", "por qué", "cómo", "explica más", "otra pregunta", "espera"],
    "fr": ["mais", "pourquoi", "comment", "explique plus", "une autre question"],
    "de": ["aber", "warum", "wie", "erkläre mehr", "noch eine frage", "warte"],
    "ja": ["でも", "なぜ", "どう", "もっと教えて", "もう一つ質問"],
    "zh": ["但是", "为什么", "怎么", "再解释", "还有一个问题", "等等"],
    "pt": ["mas", "por que", "como", "explique mais", "outra pergunta"],
    "ar": ["لكن", "لماذا", "كيف", "اشرح أكثر", "سؤال آخر"],
}


def detect_satisfaction_heuristic(
    message: str, language: str = "en"
) -> Tuple[Optional[bool], float]:
    """Layer 1: Heuristic satisfaction detection.
    
    Returns:
        (is_satisfied, confidence)
        - (True, ≥0.85): User is satisfied → auto-resume
        - (False, ≥0.85): User wants more → stay in Q&A
        - (None, <0.85): Uncertain → escalate to Layer 2
    """
    msg_lower = message.strip().lower()

    # Check for follow-up phrases first (higher priority)
    followup_phrases = FOLLOWUP_PHRASES.get(language, FOLLOWUP_PHRASES["en"])
    for phrase in followup_phrases:
        if phrase.lower() in msg_lower:
            return (False, 0.90)

    # Check satisfaction phrases
    phrases = SATISFACTION_PHRASES.get(language, SATISFACTION_PHRASES["en"])
    best_confidence = 0.0
    for phrase, confidence in phrases:
        if phrase.lower() in msg_lower:
            if confidence > best_confidence:
                best_confidence = confidence

    if best_confidence >= 0.85:
        return (True, best_confidence)

    # Check if the message looks like a question (uncertain)
    question_markers = ["?", "¿", "？", "吗", "か"]
    if any(m in message for m in question_markers):
        return (False, 0.90)

    # Uncertain
    return (None, best_confidence)


async def detect_satisfaction_llm(message: str, language: str = "en") -> bool:
    """Layer 2: LLM classifier for ambiguous messages.
    
    Returns True if user appears satisfied, False otherwise.
    """
    prompt = (
        "You are analyzing a listener's response during a podcast Q&A session.\n"
        f"The listener said: \"{message}\"\n\n"
        "Does this message indicate the user is satisfied with the answer and ready to "
        "continue the podcast? Respond with exactly one word: Yes or No."
    )

    try:
        llm = get_llm(mode="structured", max_tokens=10)
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: llm.invoke(prompt),
        )
        text = response.content if hasattr(response, "content") else str(response)
        return text.strip().lower().startswith("yes")
    except Exception as exc:
        logger.warning("LLM satisfaction detection failed: %s", exc)
        return False  # Default to not satisfied (safer — user stays in Q&A)


async def detect_satisfaction(
    message: str, language: str = "en"
) -> Tuple[str, float]:
    """Full two-layer satisfaction detection.
    
    Returns:
        (action, confidence)
        - ("auto_resume", confidence): Resume podcast
        - ("stay", confidence): User wants more Q&A  
        - ("prompt", confidence): Ask user what to do
    """
    # Layer 1: Heuristic
    is_satisfied, confidence = detect_satisfaction_heuristic(message, language)

    if is_satisfied is True and confidence >= 0.85:
        return ("auto_resume", confidence)
    
    if is_satisfied is False and confidence >= 0.85:
        return ("stay", confidence)

    # Layer 2: LLM (only for ambiguous ~20% of cases)
    logger.info("Satisfaction uncertain (conf=%.2f), escalating to LLM", confidence)
    llm_satisfied = await detect_satisfaction_llm(message, language)

    if llm_satisfied:
        return ("auto_resume", 0.75)

    # Still uncertain — prompt user
    return ("prompt", 0.50)
