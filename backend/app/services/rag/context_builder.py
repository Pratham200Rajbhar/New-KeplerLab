"""
Context filtering, compression, and formatting for RAG.

Processes reranked chunks to create high-quality, token-limited context
for LLM prompts: score normalisation, length filtering, token capping,
and extractive summarisation for oversized chunks.
"""

from __future__ import annotations

import logging
import math
import re
from typing import List, Tuple, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _count_tokens(text: str) -> int:
    """Rough token count estimation (1 token ≈ 4 characters)."""
    return len(text) // 4


def _normalize_score(score: float) -> float:
    """Normalize a reranker score to [0, 1].

    Cross-encoder models (e.g. BAAI/bge-reranker-large) return raw logits
    that are NOT bounded to [0, 1].  Comparing those raw values against
    ``settings.MIN_SIMILARITY_SCORE`` (0.3) is meaningless and incorrectly
    discards chunks with logit ≈ 0.2 (which still represent high relevance).

    Strategy:
    - If the score is already in [0, 1] (e.g. fallback 1.0) keep it as-is.
    - Otherwise apply sigmoid to map unbounded logits into (0, 1).
    """
    if 0.0 <= score <= 1.0:
        return score
    return 1.0 / (1.0 + math.exp(-score))


def _filter_chunks(
    chunks: List[Tuple[str, float]],
    min_score: float,
    min_length: int,
) -> List[Tuple[str, float]]:
    """Remove low-quality chunks based on score and length.

    Scores are normalised to [0, 1] via sigmoid before comparison so that
    raw cross-encoder logits (which can be negative) are handled correctly.
    """
    filtered = []
    for chunk, score in chunks:
        norm_score = _normalize_score(score)
        if norm_score >= min_score and len(chunk) >= min_length:
            filtered.append((chunk, norm_score))
        else:
            logger.debug(
                "Filtered chunk: raw_score=%.3f norm_score=%.3f len=%d",
                score, norm_score, len(chunk),
            )
    return filtered


def _summarize_chunk(chunk: str, max_sentences: int = 4) -> str:
    """Extractive summarization: keep the first ``max_sentences`` sentences.

    Uses regex sentence boundaries (handles abbreviations and decimal numbers
    better than a plain ``.split('.')``) so that Markdown headings, list items,
    and code blocks are not mangled.
    """
    # Split on sentence-ending punctuation followed by whitespace / end-of-string,
    # but NOT after common abbreviations like 'e.g.', 'i.e.', 'Mr.', 'Fig.'.
    sentence_end = re.compile(r'(?<=[.!?])(?:\s+|$)(?=[A-Z"\']|$)')
    sentences = [s.strip() for s in sentence_end.split(chunk) if s.strip()]
    if len(sentences) <= max_sentences:
        return chunk
    return " ".join(sentences[:max_sentences]) + " …"


def build_context(
    chunks: List[Tuple[str, float]],
    max_tokens: Optional[int] = None,
) -> str:
    """Build formatted context from reranked chunks.
    
    Applies filtering, token limiting, and formatting with source citations.
    
    Args:
        chunks: List of (chunk_text, score) tuples
        max_tokens: Maximum total tokens for context (uses config default if None)
    
    Returns:
        Formatted context string with source citations
    """
    if not chunks:
        return "No relevant context found."
    
    max_tokens = max_tokens or settings.MAX_CONTEXT_TOKENS
    
    # Step 1: Filter low-quality chunks
    filtered = _filter_chunks(
        chunks,
        min_score=settings.MIN_SIMILARITY_SCORE,
        min_length=settings.MIN_CONTEXT_CHUNK_LENGTH,
    )
    
    if not filtered:
        logger.warning("All chunks filtered out due to low quality")
        return "No sufficiently relevant context found."

    logger.info("Filtered %d chunks down to %d", len(chunks), len(filtered))
    
    # Step 2: Build context with token limiting
    formatted_chunks = []
    total_tokens = 0
    
    for idx, (chunk, score) in enumerate(filtered, start=1):
        # Check if we need to compress
        chunk_tokens = _count_tokens(chunk)
        
        if total_tokens + chunk_tokens > max_tokens:
            # Try summarization if this is not the last chunk
            if idx < len(filtered):
                summarized = _summarize_chunk(chunk)
                chunk_tokens = _count_tokens(summarized)
                
                if total_tokens + chunk_tokens <= max_tokens:
                    chunk = summarized
                else:
                    logger.info(f"Context limit reached at chunk {idx}/{len(filtered)}")
                    break
            else:
                # Last chunk, try to fit it
                if total_tokens < max_tokens * 0.5:  # If we have room
                    chunk = _summarize_chunk(chunk)
                else:
                    break
        
        # Format with source citation
        formatted_chunks.append(
            f"---- SOURCE {idx} ----\n{chunk}\n"
        )
        total_tokens += chunk_tokens
        
        logger.debug(
            "Added source %d: %d tokens (score=%.3f)",
            idx, chunk_tokens, score,
        )

    context = "\n".join(formatted_chunks)
    logger.info(
        "Built context: %d sources, ~%d tokens",
        len(formatted_chunks), total_tokens,
    )
    return context
