"""Prompt template loader.

Each ``get_*_prompt`` function loads a ``.txt`` template from this
package directory and substitutes placeholders.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Dict

_DIR = os.path.dirname(__file__)


@lru_cache(maxsize=32)
def _load(filename: str) -> str:
    """Read a template file, caching the result."""
    with open(os.path.join(_DIR, filename), encoding="utf-8") as f:
        return f.read()


def _render(filename: str, subs: Dict[str, str]) -> str:
    """Load *filename* and apply all substitutions."""
    text = _load(filename)
    for key, val in subs.items():
        text = text.replace(key, val)
    return text


# ── Public helpers ────────────────────────────────────────


def get_flashcard_prompt(content_text: str, card_count: int = None, difficulty: str = "Medium", instructions: str = None) -> str:
    instructions_text = f"\nAdditional Instructions: {instructions}" if instructions else ""
    count_instruction = f"Generate {card_count} flashcards" if card_count else "Aim for 5-10 high-quality cards depending on the text length."

    return _render("flashcard_prompt.txt", {
        "{{CONTENT_TEXT}}": content_text,
        "{{CARD_COUNT_INSTRUCTION}}": count_instruction,
        "{{DIFFICULTY}}": difficulty,
        "{{INSTRUCTIONS}}": instructions_text,
    })


def get_quiz_prompt(content_text: str, mcq_count: int = None, difficulty: str = "Medium", instructions: str = None) -> str:
    instructions_text = f"\nAdditional Instructions: {instructions}" if instructions else ""
    count_instruction = f"with exactly {mcq_count} questions" if mcq_count else "with an appropriate number of questions"
    
    return _render("quiz_prompt.txt", {
        "{{CONTENT_TEXT}}": content_text,
        "{{MCQ_COUNT_INSTRUCTION}}": count_instruction,
        "{{DIFFICULTY}}": difficulty,
        "{{INSTRUCTIONS}}": instructions_text,
    })


def get_chat_prompt(context: str, chat_history: str, user_message: str) -> str:
    return _render("chat_prompt.txt", {
        "{{CONTEXT}}": context,
        "{{CHAT_HISTORY}}": chat_history,
        "{{USER_MESSAGE}}": user_message,
    })


def get_presentation_intent_prompt(
    topic: str, audience: str, purpose: str,
    theme_preference: str, material_excerpt: str,
) -> str:
    return _render("presentation_intent_prompt.txt", {
        "{{TOPIC}}": topic,
        "{{AUDIENCE}}": audience,
        "{{PURPOSE}}": purpose,
        "{{THEME_PREFERENCE}}": theme_preference or "Auto-select best theme",
        "{{MATERIAL_EXCERPT}}": material_excerpt[:3000],
    })


def get_presentation_strategy_prompt(
    intent_analysis: str, knowledge_map: str,
    material_context: str, slide_count: int,
) -> str:
    return _render("presentation_strategy_prompt.txt", {
        "{{INTENT_ANALYSIS}}": intent_analysis,
        "{{KNOWLEDGE_MAP}}": knowledge_map,
        "{{MATERIAL_CONTEXT}}": material_context[:4000],
        "{{SLIDE_COUNT}}": str(slide_count),
    })


def get_slide_content_prompt(
    slide_title: str, slide_purpose: str, layout_type: str,
    primary_component: str, supporting_components: str,
    information_density: str, narrative_position: str,
    assigned_context: str, theme_description: str,
) -> str:
    return _render("slide_content_prompt.txt", {
        "{{SLIDE_TITLE}}": slide_title,
        "{{SLIDE_PURPOSE}}": slide_purpose,
        "{{LAYOUT_TYPE}}": layout_type,
        "{{PRIMARY_COMPONENT}}": primary_component,
        "{{SUPPORTING_COMPONENTS}}": supporting_components,
        "{{INFORMATION_DENSITY}}": information_density,
        "{{NARRATIVE_POSITION}}": narrative_position,
        "{{ASSIGNED_CONTEXT}}": assigned_context[:3000],
        "{{THEME_DESCRIPTION}}": theme_description,
    })


def get_ppt_prompt(
    material_text: str,
    slide_count: int = 10,
    theme: str | None = None,
    additional_instructions: str | None = None,
) -> str:
    theme_instructions = theme or "Use a dark modern theme with gradient backgrounds, deep blues/purples/indigos, glass-morphism effects, and bright accent colors. Auto-select the best palette for the content."
    additional = additional_instructions or "No additional instructions — use your best judgment to create a polished, professional presentation."
    return _render("ppt_prompt.txt", {
        "{{MATERIAL_TEXT}}": material_text,
        "{{SLIDE_COUNT}}": str(slide_count),
        "{{THEME_INSTRUCTIONS}}": theme_instructions,
        "{{ADDITIONAL_INSTRUCTIONS}}": additional,
    })
