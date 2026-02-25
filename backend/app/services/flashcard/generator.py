"""Flashcard generation with Pydantic validation."""

from app.services.llm_service.structured_invoker import invoke_structured
from app.services.llm_service.llm_schemas import FlashcardOutput
from app.prompts import get_flashcard_prompt
import logging

logger = logging.getLogger(__name__)


def generate_flashcards(material_text: str, card_count: int = None, difficulty: str = "Medium", instructions: str = None) -> dict:
    """Generate flashcards from material text using structured LLM invocation.
    
    Args:
        material_text: Source material for flashcard generation
        card_count: Number of cards to generate
        difficulty: Difficulty level (Easy/Medium/Hard)
        instructions: Additional instructions for card generation
    
    Returns:
        dict: Validated flashcard data with title and cards
    """
    prompt = get_flashcard_prompt(material_text, card_count, difficulty, instructions)
    result = invoke_structured(prompt, FlashcardOutput, max_retries=2)
    return result.model_dump()
