"""Citation validation for RAG responses.

This module enforces strict citation requirements in LLM responses,
ensuring all claims are grounded in provided sources.
"""

from __future__ import annotations

import re
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Minimum citation density: at least 1 citation per N words
MIN_CITATION_DENSITY = 100  # 1 citation per 100 words

# Minimum citations required for non-trivial responses
MIN_CITATIONS_REQUIRED = 1


def validate_citations(
    response: str,
    num_sources: int,
    strict: bool = True,
) -> Dict:
    """Validate that LLM response properly cites sources.
    
    Checks for:
    1. Presence of [SOURCE N] citations
    2. Valid source numbers (within range)
    3. Sufficient citation density
    4. No hallucinated sources
    
    Args:
        response: LLM response text
        num_sources: Number of sources provided in context
        strict: If True, enforce minimum citation requirements
    
    Returns:
        Dict with:
        - is_valid: bool
        - cited_sources: List[int] (1-indexed source numbers)
        - missing_citations: bool
        - invalid_sources: List[int] (out-of-range citations)
        - citation_density: float (citations per 100 words)
        - error_message: Optional[str]
    """
    result = {
        "is_valid": False,
        "cited_sources": [],
        "missing_citations": False,
        "invalid_sources": [],
        "citation_density": 0.0,
        "error_message": None,
    }
    
    # Special case: "I could not find..." responses are valid
    if _is_not_found_response(response):
        result["is_valid"] = True
        logger.info("Response is a valid 'not found' answer")
        return result
    
    # Extract all [SOURCE N] patterns
    citation_pattern = r'\[SOURCE\s+(\d+)\]'
    matches = re.findall(citation_pattern, response)
    
    if not matches:
        result["missing_citations"] = True
        result["error_message"] = "No source citations found in response"
        logger.warning("Response has no citations")
        return result
    
    # Parse and validate source numbers
    cited_sources = []
    invalid_sources = []
    
    for match in matches:
        source_num = int(match)
        if source_num < 1 or source_num > num_sources:
            invalid_sources.append(source_num)
        elif source_num not in cited_sources:
            cited_sources.append(source_num)
    
    result["cited_sources"] = sorted(cited_sources)
    result["invalid_sources"] = invalid_sources
    
    # Check for invalid source numbers
    if invalid_sources:
        result["error_message"] = (
            f"Response cites invalid sources: {invalid_sources}. "
            f"Valid range: 1-{num_sources}"
        )
        logger.error(f"Invalid source citations: {invalid_sources}")
        return result
    
    # Calculate citation density (citations per 100 words)
    word_count = len(response.split())
    result["citation_density"] = (len(matches) / max(word_count, 1)) * 100
    
    # Check citation requirements (only in strict mode)
    if strict:
        # Require at least one citation for non-trivial responses
        if word_count > 20 and len(cited_sources) < MIN_CITATIONS_REQUIRED:
            result["missing_citations"] = True
            result["error_message"] = (
                f"Insufficient citations: found {len(cited_sources)}, "
                f"required at least {MIN_CITATIONS_REQUIRED}"
            )
            logger.warning(
                f"Insufficient citations: {len(cited_sources)}/{MIN_CITATIONS_REQUIRED}"
            )
            return result
        
        # Check citation density for longer responses
        if word_count > 50 and result["citation_density"] < (100 / MIN_CITATION_DENSITY):
            result["error_message"] = (
                f"Low citation density: {result['citation_density']:.2f} "
                f"citations per 100 words (minimum: {100/MIN_CITATION_DENSITY:.2f})"
            )
            logger.warning(
                f"Low citation density: {result['citation_density']:.2f}"
            )
            return result
    
    # All checks passed
    result["is_valid"] = True
    logger.info(
        f"Citations validated: {len(cited_sources)} sources, "
        f"density={result['citation_density']:.2f}"
    )
    
    return result


def _is_not_found_response(response: str) -> bool:
    """Check if response is a valid 'information not found' answer.
    
    Returns True if response indicates the answer is not in the sources.
    """
    response_lower = response.lower().strip()
    
    not_found_patterns = [
        "i could not find",
        "i couldn't find",
        "not found in the provided",
        "not available in the sources",
        "the sources do not contain",
        "there is no information",
        "the provided materials do not",
    ]
    
    return any(pattern in response_lower for pattern in not_found_patterns)


def extract_uncited_text(response: str) -> List[str]:
    """Extract sentences that appear between citations.
    
    Useful for debugging citation gaps in responses.
    
    Args:
        response: LLM response text
    
    Returns:
        List of text segments without nearby citations
    """
    # Split by citation markers
    citation_pattern = r'\[SOURCE\s+\d+\]'
    segments = re.split(citation_pattern, response)
    
    # Filter out very short segments (< 50 chars)
    uncited = [seg.strip() for seg in segments if len(seg.strip()) > 50]
    
    logger.debug(f"Found {len(uncited)} potentially uncited text segments")
    return uncited


def suggest_citation_placement(response: str, num_sources: int) -> str:
    """Suggest where citations might be needed (for debugging).
    
    Args:
        response: LLM response text
        num_sources: Number of available sources
    
    Returns:
        Annotated response with [CITATION NEEDED?] markers
    """
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', response)
    
    annotated = []
    for sentence in sentences:
        # Check if sentence has a citation
        if not re.search(r'\[SOURCE\s+\d+\]', sentence):
            # Sentence lacks citation - annotate it
            annotated.append(f"{sentence} [CITATION NEEDED?]")
        else:
            annotated.append(sentence)
    
    return " ".join(annotated)


def check_citation_coverage(
    cited_sources: List[int],
    num_sources: int,
    min_coverage: float = 0.5,
) -> Tuple[bool, float]:
    """Check if response uses a sufficient variety of sources.
    
    Helps detect over-reliance on a single source.
    
    Args:
        cited_sources: List of cited source numbers
        num_sources: Total number of sources provided
        min_coverage: Minimum fraction of sources that should be cited
    
    Returns:
        Tuple of (is_sufficient, coverage_ratio)
    """
    unique_cited = len(set(cited_sources))
    coverage = unique_cited / max(num_sources, 1)
    
    is_sufficient = coverage >= min_coverage or num_sources < 3
    
    logger.debug(
        f"Citation coverage: {unique_cited}/{num_sources} "
        f"({coverage:.1%}) - sufficient={is_sufficient}"
    )
    
    return is_sufficient, coverage


def build_validation_error_message(validation_result: Dict) -> str:
    """Build a user-friendly error message from validation results.
    
    Args:
        validation_result: Dict from validate_citations()
    
    Returns:
        Human-readable error message
    """
    if validation_result["is_valid"]:
        return "Citations are valid"
    
    error = validation_result.get("error_message", "Unknown validation error")
    
    # Add suggestions
    suggestions = []
    
    if validation_result["missing_citations"]:
        suggestions.append(
            "Please cite sources using [SOURCE 1], [SOURCE 2], etc."
        )
    
    if validation_result["invalid_sources"]:
        suggestions.append(
            "Ensure all citations reference valid source numbers"
        )
    
    if validation_result["citation_density"] < 1.0:
        suggestions.append(
            "Add more citations to support your claims"
        )
    
    if suggestions:
        error += "\n\nSuggestions:\n- " + "\n- ".join(suggestions)
    
    return error
