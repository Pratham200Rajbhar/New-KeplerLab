"""Dynamic planner — multi-step execution planner with pre-checks.

Creates dynamic, multi-step plans with conditional fallbacks
and tool chaining instead of static dict lookups.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.services.agent.state import AgentState
from app.services.agent.intent import (
    QUESTION, DATA_ANALYSIS, RESEARCH, CODE_EXECUTION, CONTENT_GENERATION,
)

logger = logging.getLogger(__name__)


async def _get_completed_material_ids(material_ids: List[str]) -> List[str]:
    """Filter material_ids to only those with status='completed'.

    Returns:
        List of material IDs that are fully processed and embedded.
    """
    if not material_ids:
        return []

    try:
        from app.db.prisma_client import get_prisma
        prisma = get_prisma()
        # NOTE: Prisma Python client does not support the 'select' kwarg on find_many()
        materials = await prisma.material.find_many(
            where={
                "id": {"in": material_ids},
                "status": "completed",
            },
        )
        return [m.id for m in materials]
    except Exception as exc:
        logger.warning("[planner] Failed to check material status: %s", exc)
        # If we can't check, proceed with all IDs (graceful degradation)
        return material_ids


def _resolve_content_generation_plan(message: str) -> List[Dict[str, Any]]:
    """Determine which content generation tool to use based on message."""
    msg_lower = message.lower()

    if any(kw in msg_lower for kw in ["quiz", "test", "question"]):
        return [{"tool": "quiz_tool", "description": "Generate quiz from materials"}]

    if any(kw in msg_lower for kw in ["flashcard", "flash card", "cards"]):
        return [{"tool": "flashcard_tool", "description": "Generate flashcards from materials"}]

    if any(kw in msg_lower for kw in ["presentation", "ppt", "slides", "slide"]):
        return [{"tool": "ppt_tool", "description": "Generate presentation from materials"}]

    if any(kw in msg_lower for kw in ["summary", "summarize", "summarise", "study guide", "notes"]):
        return [{"tool": "rag_tool", "description": "Generate summary/notes from materials"}]

    # Default: use RAG for general content generation
    return [{"tool": "rag_tool", "description": "Generate requested content from materials"}]


async def plan_execution(state: AgentState) -> AgentState:
    """Dynamic planning node — creates multi-step execution plans.

    Improvements over static dict lookup:
    - Pre-checks material completion status before adding rag_tool
    - Adds conditional fallback steps (e.g. research if RAG empty)
    - Supports tool chaining (e.g. RAG context → python_tool)
    - Returns plan_error if pre-conditions fail
    """
    # ── Fast bypass: caller pre-set the plan ───────────────────────────────
    if state.get("plan"):
        logger.info(
            "[planner] Pre-set plan %s — skipping planning",
            [s["tool"] for s in state["plan"]],
        )
        return {**state, "current_step": state.get("current_step", 0)}

    intent = state.get("intent", QUESTION)
    message = state.get("user_message", "")
    material_ids = state.get("material_ids", [])

    logger.info("Planning execution for intent: %s", intent)

    # ── Pre-check: verify materials are completed before RAG ───────────────
    if intent in (QUESTION, CONTENT_GENERATION, DATA_ANALYSIS) and material_ids:
        completed = await _get_completed_material_ids(material_ids)
        if not completed:
            logger.warning(
                "[planner] No completed materials found for %s — setting plan_error",
                intent,
            )
            return {
                **state,
                "plan": [],
                "current_step": 0,
                "plan_error": "no_completed_materials",
            }
        # Update state with only completed material IDs
        material_ids = completed
        state = {**state, "material_ids": completed}

    # ── Dynamic multi-step planning ────────────────────────────────────────
    if intent == QUESTION:
        plan = [
            {"tool": "rag_tool", "description": "Search materials for answer"},
        ]
        # Add research_tool as conditional fallback if RAG returns empty
        plan.append({
            "tool": "research_tool",
            "description": "Web fallback search",
            "conditional": "if_previous_empty",
        })

    elif intent == DATA_ANALYSIS:
        plan = [
            {"tool": "rag_tool", "description": "Get data context from materials"},
            {
                "tool": "python_tool",
                "description": "Run data analysis with pandas",
                "uses_previous_output": True,  # tool chaining flag
            },
        ]

    elif intent == RESEARCH:
        plan = [
            {"tool": "research_tool", "description": "Conduct deep web research"},
        ]

    elif intent == CODE_EXECUTION:
        plan = [
            {"tool": "python_tool", "description": "Generate and execute Python code"},
        ]

    elif intent == CONTENT_GENERATION:
        plan = _resolve_content_generation_plan(message)

    else:
        plan = [
            {"tool": "rag_tool", "description": "Search materials and respond"},
        ]

    logger.info("Plan: %s", [step["tool"] for step in plan])

    return {
        **state,
        "plan": plan,
        "current_step": 0,
    }
