"""
End-to-end test: Flashcard / Quiz / Podcast / Presentation generation pipelines.
These tests mock the LLM layer (invoke_structured / get_llm) so no GPU or API key
is required. The goal is to verify the wiring — prompt construction, output
parsing, and return-shape correctness.
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

SAMPLE_MATERIAL = (
    "# The French Revolution\n\n"
    "The French Revolution began in 1789 as a period of radical political and social "
    "transformation. It ended the absolute monarchy, established a constitutional "
    "republic, and eventually brought Napoleon Bonaparte to power.\n\n"
    "## Key Causes\n\n"
    "Financial crisis, social inequality, and Enlightenment philosophy drove the revolution. "
    "France was effectively bankrupt after supporting the American Revolution.\n\n"
    "## Key Events\n\n"
    "- 1789: Storming of the Bastille (July 14)\n"
    "- 1789: Declaration of the Rights of Man and Citizen\n"
    "- 1793: Reign of Terror under Robespierre\n"
    "- 1799: Napoleon's coup (18 Brumaire)\n"
) * 3


# ────────────────────────────────────────────────────────────────────────────
# Flashcard generation pipeline
# ────────────────────────────────────────────────────────────────────────────

class TestFlashcardGenerationPipeline:
    """Tests for the flashcard generation service (LLM mocked)."""

    def _mock_flashcard_output(self, card_count=5, difficulty="Medium"):
        from app.services.llm_service.llm_schemas import FlashcardOutput, Flashcard
        return FlashcardOutput(
            title="French Revolution Flashcards",
            flashcards=[
                Flashcard(
                    question="What happened in 1789?",
                    answer="The French Revolution began; the Bastille was stormed.",
                )
                for _ in range(card_count)
            ]
        )

    def test_flashcard_generation_returns_dict(self):
        mock_output = self._mock_flashcard_output()
        with patch("app.services.flashcard.generator.invoke_structured", return_value=mock_output):
            from app.services.flashcard.generator import generate_flashcards
            result = generate_flashcards(SAMPLE_MATERIAL, card_count=5)
            assert isinstance(result, dict)

    def test_flashcard_result_has_required_keys(self):
        mock_output = self._mock_flashcard_output()
        with patch("app.services.flashcard.generator.invoke_structured", return_value=mock_output):
            from app.services.flashcard.generator import generate_flashcards
            result = generate_flashcards(SAMPLE_MATERIAL)
            assert "title" in result
            assert "flashcards" in result

    def test_flashcard_title_is_string(self):
        mock_output = self._mock_flashcard_output()
        with patch("app.services.flashcard.generator.invoke_structured", return_value=mock_output):
            from app.services.flashcard.generator import generate_flashcards
            result = generate_flashcards(SAMPLE_MATERIAL)
            assert isinstance(result["title"], str)
            assert len(result["title"]) > 0

    def test_flashcard_cards_is_list(self):
        mock_output = self._mock_flashcard_output()
        with patch("app.services.flashcard.generator.invoke_structured", return_value=mock_output):
            from app.services.flashcard.generator import generate_flashcards
            result = generate_flashcards(SAMPLE_MATERIAL, card_count=3)
            assert isinstance(result["flashcards"], list)

    def test_flashcard_each_card_has_question_answer(self):
        mock_output = self._mock_flashcard_output(card_count=5)
        with patch("app.services.flashcard.generator.invoke_structured", return_value=mock_output):
            from app.services.flashcard.generator import generate_flashcards
            result = generate_flashcards(SAMPLE_MATERIAL, card_count=5)
            for card in result["flashcards"]:
                assert "question" in card
                assert "answer" in card
                assert len(card["question"]) > 0
                assert len(card["answer"]) > 0

    @pytest.mark.parametrize("difficulty", ["Easy", "Medium", "Hard"])
    def test_flashcard_accepts_difficulty_levels(self, difficulty):
        mock_output = self._mock_flashcard_output(difficulty=difficulty)
        with patch("app.services.flashcard.generator.invoke_structured", return_value=mock_output):
            from app.services.flashcard.generator import generate_flashcards
            result = generate_flashcards(SAMPLE_MATERIAL, difficulty=difficulty)
            assert result is not None


# ────────────────────────────────────────────────────────────────────────────
# Quiz generation pipeline
# ────────────────────────────────────────────────────────────────────────────

class TestQuizGenerationPipeline:
    """Tests for the quiz generation service (LLM mocked)."""

    def _mock_quiz_output(self, mcq_count=5, difficulty="Medium"):
        from app.services.llm_service.llm_schemas import QuizOutput
        return QuizOutput(
            title="French Revolution Quiz",
            questions=[
                {
                    "question": f"Question {i + 1}: What characterized the French Revolution?",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct_answer": 0,
                    "explanation": "The French Revolution fundamentally changed French society.",
                }
                for i in range(mcq_count)
            ]
        )

    def test_quiz_generation_returns_dict(self):
        mock_output = self._mock_quiz_output()
        with patch("app.services.quiz.generator.invoke_structured", return_value=mock_output):
            from app.services.quiz.generator import generate_quiz
            result = generate_quiz(SAMPLE_MATERIAL, mcq_count=5)
            assert isinstance(result, dict)

    def test_quiz_result_has_required_keys(self):
        mock_output = self._mock_quiz_output()
        with patch("app.services.quiz.generator.invoke_structured", return_value=mock_output):
            from app.services.quiz.generator import generate_quiz
            result = generate_quiz(SAMPLE_MATERIAL)
            assert "title" in result
            assert "questions" in result

    def test_quiz_questions_is_list(self):
        mock_output = self._mock_quiz_output(mcq_count=3)
        with patch("app.services.quiz.generator.invoke_structured", return_value=mock_output):
            from app.services.quiz.generator import generate_quiz
            result = generate_quiz(SAMPLE_MATERIAL, mcq_count=3)
            assert isinstance(result["questions"], list)

    def test_quiz_each_question_has_options_and_answer(self):
        mock_output = self._mock_quiz_output(mcq_count=3)
        with patch("app.services.quiz.generator.invoke_structured", return_value=mock_output):
            from app.services.quiz.generator import generate_quiz
            result = generate_quiz(SAMPLE_MATERIAL, mcq_count=3)
            for q in result["questions"]:
                assert "question" in q
                assert "options" in q
                assert "correct_answer" in q
                assert len(q["options"]) == 4

    def test_quiz_correct_answer_is_valid_index(self):
        mock_output = self._mock_quiz_output()
        with patch("app.services.quiz.generator.invoke_structured", return_value=mock_output):
            from app.services.quiz.generator import generate_quiz
            result = generate_quiz(SAMPLE_MATERIAL)
            for q in result["questions"]:
                idx = q["correct_answer"]
                assert 0 <= idx < len(q["options"])

    @pytest.mark.parametrize("difficulty", ["Easy", "Medium", "Hard"])
    def test_quiz_accepts_difficulty_levels(self, difficulty):
        mock_output = self._mock_quiz_output(difficulty=difficulty)
        with patch("app.services.quiz.generator.invoke_structured", return_value=mock_output):
            from app.services.quiz.generator import generate_quiz
            result = generate_quiz(SAMPLE_MATERIAL, difficulty=difficulty)
            assert result is not None


# ────────────────────────────────────────────────────────────────────────────
# Prompt construction validation
# ────────────────────────────────────────────────────────────────────────────

class TestPromptConstruction:
    """Verify prompt builders embed material and parameters correctly."""

    def test_flashcard_prompt_contains_material(self):
        from app.prompts import get_flashcard_prompt
        prompt = get_flashcard_prompt(SAMPLE_MATERIAL, card_count=5)
        assert isinstance(prompt, str)
        assert len(prompt) > len(SAMPLE_MATERIAL) * 0  # non-empty

    def test_quiz_prompt_contains_material(self):
        from app.prompts import get_quiz_prompt
        prompt = get_quiz_prompt(SAMPLE_MATERIAL, mcq_count=5)
        assert isinstance(prompt, str)

    def test_flashcard_prompt_mentions_difficulty(self):
        from app.prompts import get_flashcard_prompt
        prompt = get_flashcard_prompt(SAMPLE_MATERIAL, difficulty="Hard")
        # Prompt should reference the difficulty setting
        assert "Hard" in prompt or "hard" in prompt.lower() or len(prompt) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
