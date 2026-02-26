"""
End-to-end test: LangGraph agent pipeline.
Tests intent detection (keyword rules), state management, and tool routing.
All LLM calls are mocked — no GPU or API key required.
"""

import sys
import os
import pytest
from unittest.mock import AsyncMock, patch

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

from app.services.agent.intent import (
    _keyword_classify,
    detect_intent,
    QUESTION,
    DATA_ANALYSIS,
    RESEARCH,
    CODE_EXECUTION,
    FILE_GENERATION,
    CONTENT_GENERATION,
)
from app.services.agent.state import AgentState, compress_tool_result


# ────────────────────────────────────────────────────────────────────────────
# Keyword intent classification
# ────────────────────────────────────────────────────────────────────────────

class TestKeywordIntentClassification:
    """Tests for the fast keyword-based intent classifier."""

    # ── QUESTION intent ─────────────────────────────────────

    @pytest.mark.parametrize("msg", [
        "What is machine learning?",
        "Explain the French Revolution to me",
        "Summarise chapter 3",
        "Who was Napoleon Bonaparte?",
    ])
    def test_general_question_classifies_as_question(self, msg):
        result = _keyword_classify(msg)
        assert result["intent"] == QUESTION

    # ── DATA_ANALYSIS intent ─────────────────────────────────

    @pytest.mark.parametrize("msg", [
        "Analyze this CSV file",
        "Show me a bar chart of sales by region",
        "What is the average revenue per quarter?",
        "Plot a histogram of age distribution",
        "Calculate the correlation between columns",
        "Show the trend for last year",
    ])
    def test_data_analysis_messages_classified_correctly(self, msg):
        result = _keyword_classify(msg)
        assert result["intent"] == DATA_ANALYSIS
        assert result["confidence"] >= 0.85

    # ── CODE_EXECUTION intent ─────────────────────────────────

    @pytest.mark.parametrize("msg", [
        "Run a Python script to sort a list",
        "Write code to parse JSON",
        "Execute this Python function",
        "Create a function that reverses a string",
    ])
    def test_code_execution_messages_classified_correctly(self, msg):
        result = _keyword_classify(msg)
        assert result["intent"] == CODE_EXECUTION
        assert result["confidence"] >= 0.85

    # ── RESEARCH intent ──────────────────────────────────────

    @pytest.mark.parametrize("msg", [
        "Research the latest advancements in AI",
        "Deep dive into quantum computing",
        "Search the web for climate change news",
        "Find out about current AI trends online",
    ])
    def test_research_messages_classified_correctly(self, msg):
        result = _keyword_classify(msg)
        assert result["intent"] == RESEARCH
        assert result["confidence"] >= 0.85

    # ── CONTENT_GENERATION intent ─────────────────────────────

    @pytest.mark.parametrize("msg", [
        "Create flashcards from my notes",
        "Generate a quiz on chapter 5",
        "Make me some flashcards",
        "Build a presentation on climate change",
        "Create a podcast about machine learning",
    ])
    def test_content_generation_messages_classified_correctly(self, msg):
        result = _keyword_classify(msg)
        assert result["intent"] == CONTENT_GENERATION
        assert result["confidence"] >= 0.85

    # ── FILE_GENERATION intent ────────────────────────────────

    @pytest.mark.parametrize("msg", [
        "Create a CSV file with the results",
        "Export the data as Excel",
        "Generate a Word document report",
        "Save as PDF",
        "Create a spreadsheet with this data",
    ])
    def test_file_generation_messages_classified_correctly(self, msg):
        result = _keyword_classify(msg)
        assert result["intent"] == FILE_GENERATION
        assert result["confidence"] >= 0.85

    # ── Return structure ──────────────────────────────────────

    def test_classification_always_returns_dict_with_intent_and_confidence(self):
        for msg in ["", "  ", "hello", "x" * 500]:
            result = _keyword_classify(msg)
            assert "intent" in result
            assert "confidence" in result
            assert result["intent"] in [
                QUESTION, DATA_ANALYSIS, RESEARCH,
                CODE_EXECUTION, FILE_GENERATION, CONTENT_GENERATION,
            ]
            assert 0.0 <= result["confidence"] <= 1.0

    def test_empty_message_falls_back_to_question(self):
        result = _keyword_classify("")
        assert result["intent"] == QUESTION

    def test_very_long_message_classifies_without_crash(self):
        long_msg = "What is machine learning? " * 200
        result = _keyword_classify(long_msg)
        assert result["intent"] in [QUESTION, DATA_ANALYSIS, RESEARCH,
                                     CODE_EXECUTION, FILE_GENERATION, CONTENT_GENERATION]


# ────────────────────────────────────────────────────────────────────────────
# Intent detection node (async, with state)
# ────────────────────────────────────────────────────────────────────────────

class TestDetectIntentNode:
    """Tests for the detect_intent LangGraph node."""

    @pytest.mark.asyncio
    async def test_intent_detected_for_question(self):
        state: AgentState = {
            "user_message": "What is supervised learning?",
            "user_id": "user-1",
            "notebook_id": "nb-1",
        }
        result = await detect_intent(state)
        assert result["intent"] == QUESTION

    @pytest.mark.asyncio
    async def test_intent_detected_for_data_analysis(self):
        state: AgentState = {
            "user_message": "Show me a bar chart of the data",
            "user_id": "user-1",
            "notebook_id": "nb-1",
        }
        result = await detect_intent(state)
        assert result["intent"] == DATA_ANALYSIS

    @pytest.mark.asyncio
    async def test_preset_intent_not_overridden(self):
        """If intent is pre-set with confidence=1.0, it should not be overridden."""
        state: AgentState = {
            "user_message": "Show me a bar chart",  # would normally → DATA_ANALYSIS
            "intent": RESEARCH,
            "intent_confidence": 1.0,
            "user_id": "user-1",
            "notebook_id": "nb-1",
        }
        result = await detect_intent(state)
        # Pre-set intent must be preserved
        assert result["intent"] == RESEARCH

    @pytest.mark.asyncio
    async def test_intent_override_respected(self):
        """intent_override field bypasses classification entirely."""
        state: AgentState = {
            "user_message": "Plot a histogram",
            "intent_override": CODE_EXECUTION,
            "user_id": "user-1",
            "notebook_id": "nb-1",
        }
        result = await detect_intent(state)
        assert result["intent"] == CODE_EXECUTION
        assert result["intent_confidence"] == 1.0

    @pytest.mark.asyncio
    async def test_result_state_includes_confidence(self):
        state: AgentState = {
            "user_message": "Research quantum computing online",
            "user_id": "user-1",
            "notebook_id": "nb-1",
        }
        result = await detect_intent(state)
        assert "intent_confidence" in result
        assert result["intent_confidence"] > 0.0

    @pytest.mark.asyncio
    async def test_state_fields_preserved(self):
        state: AgentState = {
            "user_message": "What is deep learning?",
            "user_id": "user-abc",
            "notebook_id": "nb-xyz",
            "material_ids": ["mat-1", "mat-2"],
        }
        result = await detect_intent(state)
        # Original fields must be preserved in output state
        assert result.get("user_id") == "user-abc"
        assert result.get("notebook_id") == "nb-xyz"


# ────────────────────────────────────────────────────────────────────────────
# AgentState and ToolResult utilities
# ────────────────────────────────────────────────────────────────────────────

class TestAgentStateUtilities:
    """Tests for state management helpers."""

    def test_compress_tool_result_short_output_unchanged(self):
        result = {"success": True, "output": "Short output.", "metadata": {}}
        compressed = compress_tool_result(result)
        assert compressed["output_summary"] == "Short output."

    def test_compress_tool_result_long_output_truncated(self):
        long_output = "x" * 1000
        result = {"success": True, "output": long_output, "metadata": {}}
        compressed = compress_tool_result(result)
        assert len(compressed["output_summary"]) <= 510  # 500 chars + ellipsis
        assert "…" in compressed["output_summary"]

    def test_compress_tool_result_preserves_full_output(self):
        long_output = "y" * 1000
        result = {"success": True, "output": long_output, "metadata": {}}
        compressed = compress_tool_result(result)
        assert compressed["output"] == long_output

    def test_compress_tool_result_empty_output(self):
        result = {"success": False, "output": "", "metadata": {}}
        compressed = compress_tool_result(result)
        assert compressed["output_summary"] == ""

    def test_compress_tool_result_missing_output(self):
        result = {"success": True, "metadata": {}}
        compressed = compress_tool_result(result)
        assert compressed["output_summary"] == ""


# ────────────────────────────────────────────────────────────────────────────
# Full agent routing flow (mocked LLM)
# ────────────────────────────────────────────────────────────────────────────

class TestAgentRoutingFlow:
    """Tests that correct messages route to correct intents end-to-end."""

    _ROUTING_CASES = [
        ("Explain photosynthesis", QUESTION),
        ("Analyze this CSV and plot trends", DATA_ANALYSIS),
        ("Research the latest news on AI", RESEARCH),
        ("Write Python code to sort a list", CODE_EXECUTION),
        ("Generate flashcards from my notes", CONTENT_GENERATION),
        ("Create a CSV report of the data", FILE_GENERATION),
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("message,expected_intent", _ROUTING_CASES)
    async def test_routing(self, message, expected_intent):
        state: AgentState = {"user_message": message, "user_id": "u1", "notebook_id": "nb1"}
        result = await detect_intent(state)
        assert result["intent"] == expected_intent, (
            f"'{message}' → expected {expected_intent}, got {result['intent']}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
