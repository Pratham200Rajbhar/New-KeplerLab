"""Pydantic schemas for validating structured LLM outputs."""

from pydantic import BaseModel, Field, model_validator
from typing import Any, List, Optional


# ── Quiz ──────────────────────────────────────────────────

class QuizQuestion(BaseModel):
    question: str
    options: List[str] = Field(min_length=2, max_length=6)
    correct_answer: int
    explanation: Optional[str] = None


class QuizOutput(BaseModel):
    title: str
    questions: List[Any]  # raw dicts accepted; validated + filtered below

    @model_validator(mode="after")
    def _drop_incomplete_questions(self) -> "QuizOutput":
        """Discard incomplete/truncated question objects, keep valid ones.

        This makes truncated LLM responses (where the last 1-2 questions are
        cut off mid-JSON) still produce a usable quiz instead of failing.
        """
        valid = []
        for item in self.questions:
            try:
                valid.append(QuizQuestion.model_validate(item))
            except Exception:
                pass  # truncated item — skip
        if not valid:
            raise ValueError("No valid quiz questions found in LLM output")
        self.questions = valid  # type: ignore[assignment]
        return self


# ── Flashcards ────────────────────────────────────────────

class Flashcard(BaseModel):
    question: str
    answer: str


class FlashcardOutput(BaseModel):
    title: str
    flashcards: List[Any]  # raw dicts accepted; validated + filtered below

    @model_validator(mode="after")
    def _drop_incomplete_cards(self) -> "FlashcardOutput":
        """Discard incomplete/truncated flashcard objects, keep valid ones."""
        valid = []
        for item in self.flashcards:
            try:
                valid.append(Flashcard.model_validate(item))
            except Exception:
                pass
        if not valid:
            raise ValueError("No valid flashcards found in LLM output")
        self.flashcards = valid  # type: ignore[assignment]
        return self


# ── Podcast ───────────────────────────────────────────────

class PodcastDialogueLine(BaseModel):
    speaker: str
    text: str


class PodcastScriptOutput(BaseModel):
    title: str
    dialogue: List[PodcastDialogueLine] = Field(min_length=1)


# ── Presentation ─────────────────────────────────────────


class IntentAnalysis(BaseModel):
    """Phase 1 output — audience/topic analysis for presentation planning."""
    technical_depth: str = Field(description="low / medium / high / expert")
    persuasion_vs_explanation: str = Field(description="e.g. '30/70' or '70/30'")
    estimated_duration_minutes: int = Field(ge=1, le=120)
    expected_slide_density: str = Field(description="sparse / moderate / dense")
    visual_emphasis: str = Field(description="low / medium / high")
    formality_level: str = Field(description="casual / professional / academic / executive")
    recommended_slide_count: int = Field(ge=3, le=60)
    theme_suggestion: Optional[str] = None


class SlidePlan(BaseModel):
    """A single slide in the presentation strategy."""
    slide_number: int
    title: str
    purpose: str = Field(description="e.g. title, introduction, content, comparison, summary, q_and_a")
    layout_type: str = Field(description="e.g. title_slide, bullets, two_column, chart, table, diagram, image_focus, blank")
    primary_component: str = Field(description="e.g. bullets, table, chart, diagram, image, text_block, kpi_highlight")
    supporting_components: List[str] = Field(default_factory=list)
    information_density: str = Field(description="light / moderate / heavy")
    narrative_position: str = Field(description="opening / rising / climax / falling / conclusion")


class PresentationStrategy(BaseModel):
    """Phase 3 output — dynamic presentation structure."""
    presentation_title: str
    total_slides: int = Field(ge=3, le=60)
    narrative_summary: str
    slides: List[Any]  # raw dicts; validated below

    @model_validator(mode="after")
    def _validate_slides(self) -> "PresentationStrategy":
        valid = []
        for item in self.slides:
            try:
                valid.append(SlidePlan.model_validate(item))
            except Exception:
                pass
        if not valid:
            raise ValueError("No valid slide plans found in LLM output")
        self.slides = valid  # type: ignore[assignment]
        self.total_slides = len(valid)
        return self


class SlideContent(BaseModel):
    """Phase 5 output — generated content for a single slide."""
    title: str
    subtitle: Optional[str] = None
    bullets: Optional[List[str]] = None
    paragraph: Optional[str] = None
    table_data: Optional[dict] = None  # {"headers": [...], "rows": [[...], ...]}
    chart_data: Optional[dict] = None  # {"type": "bar|pie|line", "labels": [...], "values": [...]}
    diagram_structure: Optional[dict] = None  # {"nodes": [...], "connections": [...]}
    image_prompt: Optional[str] = None
    speaker_notes: Optional[str] = None
    key_metric: Optional[dict] = None  # {"value": "...", "label": "...", "trend": "up|down|flat"}


# ── Presentation HTML (single-prompt pipeline) ───────────


class PresentationHTMLOutput(BaseModel):
    """Single-prompt HTML presentation output."""
    title: str
    slide_count: int = Field(ge=1, le=60)
    theme: str = Field(default="dark-modern")
    html: str = Field(min_length=100, description="Complete standalone HTML document")

    @model_validator(mode="after")
    def _validate_html(self) -> "PresentationHTMLOutput":
        """Sanity check and auto-repair HTML output."""
        h = self.html.strip()
        if "<html" not in h.lower():
            raise ValueError("HTML output must contain an <html> tag")
        # Auto-repair: if </html> is missing the LLM truncated slightly — append it
        if "</html>" not in h.lower():
            # Check if </body> is also missing and add both
            if "</body>" not in h.lower():
                self.html = h + "\n</body>\n</html>"
            else:
                self.html = h + "\n</html>"
        return self
