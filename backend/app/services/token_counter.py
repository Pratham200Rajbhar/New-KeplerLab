"""Token counting and usage tracking.

Features:
- Estimate token count before LLM calls
- Truncate context intelligently if exceeds limits
- Track daily per-user token usage
- Return truncation warnings
"""

from __future__ import annotations

import logging
from datetime import datetime, date
from typing import Optional, Tuple

import tiktoken

from app.db.prisma_client import prisma
from app.core.config import settings

logger = logging.getLogger(__name__)

# Token limits by model
TOKEN_LIMITS = {
    "default": 4096,
    "gpt-3.5-turbo": 4096,
    "gpt-4": 8192,
    "gpt-4-32k": 32768,
    "claude-2": 100000,
    "llama3": 8192,
    "llama3.1": 128000,
    "gemini-2.5-flash": 1000000,
    "qwen3.5": 32768,
}

# Default encoding for token counting
DEFAULT_ENCODING = "cl100k_base"  # GPT-3.5/GPT-4 encoding


# Cached tokenizer instance — avoid re-creating on every call
_cached_tokenizer = None


def _get_tokenizer(model_name: str = "default"):
    """Get tokenizer for model (cached)."""
    global _cached_tokenizer
    if _cached_tokenizer is not None:
        return _cached_tokenizer
    try:
        # Use tiktoken for accurate counting (OpenAI-compatible)
        _cached_tokenizer = tiktoken.get_encoding(DEFAULT_ENCODING)
        return _cached_tokenizer
    except Exception as e:
        logger.warning(f"Failed to load tokenizer: {e}, using fallback")
        return None


def estimate_token_count(text: str, model: str = "default") -> int:
    """Estimate token count for text.
    
    Args:
        text: Input text
        model: Model name for tokenizer selection
    
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    
    try:
        tokenizer = _get_tokenizer(model)
        if tokenizer:
            return len(tokenizer.encode(text))
    except Exception as e:
        logger.debug(f"Tokenization failed: {e}, using rough estimate")
    
    # Fallback: rough estimate (1 token ≈ 4 characters)
    return len(text) // 4


def get_model_token_limit(model: str) -> int:
    """Get token limit for model.
    
    Args:
        model: Model name
    
    Returns:
        Maximum tokens for model
    """
    # Try exact match
    if model in TOKEN_LIMITS:
        return TOKEN_LIMITS[model]
    
    # Try partial match
    for key in TOKEN_LIMITS:
        if key in model.lower():
            return TOKEN_LIMITS[key]
    
    return TOKEN_LIMITS["default"]


def truncate_context_intelligently(
    chunks_with_scores: list,
    max_tokens: int,
    question: str = "",
    model: str = "default"
) -> Tuple[list, bool]:
    """Truncate context to fit token limit, prioritizing high-scoring chunks.
    
    Args:
        chunks_with_scores: List of (chunk_text, score) tuples
        max_tokens: Maximum tokens allowed
        question: User question
        model: Model name
    
    Returns:
        Tuple of (truncated_chunks, was_truncated)
    """
    question_tokens = estimate_token_count(question, model)
    available_tokens = max_tokens - question_tokens - 200  # Reserve for response
    
    if available_tokens <= 0:
        logger.warning("Question too long, no space for context")
        return [], True
    
    # Sort chunks by score (highest first)
    sorted_chunks = sorted(chunks_with_scores, key=lambda x: x[1], reverse=True)
    
    selected_chunks = []
    total_tokens = 0
    was_truncated = False
    
    for chunk_text, score in sorted_chunks:
        chunk_tokens = estimate_token_count(chunk_text, model)
        
        if total_tokens + chunk_tokens <= available_tokens:
            selected_chunks.append((chunk_text, score))
            total_tokens += chunk_tokens
        else:
            was_truncated = True
            logger.info(f"Context truncated: {len(sorted_chunks) - len(selected_chunks)} chunks dropped")
            break
    
    return selected_chunks, was_truncated


async def track_token_usage(
    user_id: str,
    tokens_used: int,
    usage_date: Optional[date] = None
) -> None:
    """Track daily token usage for user.
    
    Args:
        user_id: User identifier
        tokens_used: Number of tokens used
        usage_date: Date (default: today)
    """
    if not user_id or tokens_used <= 0:
        return
    
    if usage_date is None:
        usage_date = date.today()
    
    try:
        # Atomic upsert via raw SQL to prevent race conditions
        # ON CONFLICT DO UPDATE adds tokens atomically without read-then-write
        await prisma.execute_raw(
            'INSERT INTO "UserTokenUsage" ("id", "userId", "date", "tokensUsed") '
            "VALUES (gen_random_uuid(), $1, $2, $3) "
            'ON CONFLICT ("userId", "date") '
            'DO UPDATE SET "tokensUsed" = "UserTokenUsage"."tokensUsed" + $3',
            user_id,
            usage_date,
            tokens_used,
        )
        
        logger.debug(f"Tracked {tokens_used} tokens for user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to track token usage: {e}")
        # Don't raise - tracking is non-critical


async def get_user_daily_usage(user_id: str, usage_date: Optional[date] = None) -> int:
    """Get user's token usage for a specific date.
    
    Args:
        user_id: User identifier
        usage_date: Date (default: today)
    
    Returns:
        Total tokens used on that date
    """
    if usage_date is None:
        usage_date = date.today()
    
    try:
        record = await prisma.usertokenusage.find_first(
            where={
                "userId": user_id,
                "date": usage_date,
            }
        )
        
        return record.tokensUsed if record else 0
        
    except Exception as e:
        logger.error(f"Failed to get token usage: {e}")
        return 0


async def get_user_monthly_usage(user_id: str, year: int, month: int) -> int:
    """Get user's total token usage for a month.
    
    Args:
        user_id: User identifier
        year: Year
        month: Month (1-12)
    
    Returns:
        Total tokens used in that month
    """
    try:
        # Query records for the month
        from datetime import datetime
        start_date = datetime(year, month, 1).date()
        
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date()
        else:
            end_date = datetime(year, month + 1, 1).date()
        
        records = await prisma.usertokenusage.find_many(
            where={
                "userId": user_id,
                "date": {
                    "gte": start_date,
                    "lt": end_date,
                }
            }
        )
        
        return sum(r.tokensUsed for r in records)
        
    except Exception as e:
        logger.error(f"Failed to get monthly usage: {e}")
        return 0


def prepare_context_with_token_limit(
    chunks_with_metadata: list,
    query: str,
    model: str = "default",
    safety_margin: int = 500
) -> dict:
    """Prepare context with token limit enforcement.
    
    Args:
        chunks_with_metadata: List of chunk dicts with text and scores
        query: User query
        model: Model name
        safety_margin: Extra tokens to reserve
    
    Returns:
        Dict with context, token counts, and truncation flag
    """
    max_tokens = get_model_token_limit(model)
    
    # Extract chunks with scores
    chunks_with_scores = [
        (chunk.get("text", ""), chunk.get("score", 1.0))
        for chunk in chunks_with_metadata
    ]
    
    # Truncate if needed
    selected_chunks, was_truncated = truncate_context_intelligently(
        chunks_with_scores,
        max_tokens - safety_margin,
        query,
        model
    )
    
    # Build context string
    context_parts = [chunk[0] for chunk in selected_chunks]
    context_str = "\n\n".join(context_parts)
    
    # Calculate final tokens
    context_tokens = estimate_token_count(context_str, model)
    query_tokens = estimate_token_count(query, model)
    total_tokens = context_tokens + query_tokens
    
    return {
        "context": context_str,
        "context_tokens": context_tokens,
        "query_tokens": query_tokens,
        "total_tokens": total_tokens,
        "model_max_tokens": max_tokens,
        "truncated": was_truncated,
        "chunks_included": len(selected_chunks),
        "chunks_dropped": len(chunks_with_scores) - len(selected_chunks),
    }
