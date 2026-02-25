"""Structured LLM invocation with robust JSON parsing, auto-repair, and failsafe.

This module provides production-grade structured output parsing with:
- Deterministic generation parameters
- Automatic JSON extraction and repair
- Retry logic with correction prompts
- Comprehensive error handling and logging
- Timeout protection
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.services.llm_service.llm import get_llm_structured

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# ── JSON Extraction Patterns ──────────────────────────────────

_CODE_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*\n?|```\s*", re.DOTALL)
_THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


# ── JSON Auto-Repair ──────────────────────────────────────────


def _clean_json_text(text: str) -> str:
    """Remove markdown fences, reasoning tags, and explanatory text."""
    # Remove reasoning tags
    text = _THINK_TAG_RE.sub("", text).strip()
    
    # Remove markdown code fences
    text = _CODE_FENCE_RE.sub("", text).strip()
    
    # Remove common prefixes/suffixes
    text = re.sub(r"^(Here's|Here is|The JSON|Output:|Response:)\s*:?\s*", "", text, flags=re.IGNORECASE)
    
    return text.strip()


def _extract_json_block(text: str) -> str:
    """Extract the first {...} or [...] block from text."""
    # Find first opening brace/bracket
    start_brace = text.find("{")
    start_bracket = text.find("[")
    
    # Determine which comes first
    if start_brace == -1 and start_bracket == -1:
        raise ValueError("No JSON block found")
    
    if start_bracket == -1 or (start_brace != -1 and start_brace < start_bracket):
        # Object
        start = start_brace
        end = text.rfind("}")
        if end > start:
            return text[start:end + 1]
    else:
        # Array
        start = start_bracket
        end = text.rfind("]")
        if end > start:
            return text[start:end + 1]
    
    raise ValueError("Could not extract complete JSON block")


def _repair_json(text: str) -> str:
    """Apply common JSON repair heuristics.
    
    - Fix missing commas
    - Remove trailing commas
    - Replace single quotes with double quotes
    - Ensure proper closing
    """
    # Replace single quotes with double quotes (carefully)
    # Only if they appear to be JSON string delimiters
    text = re.sub(r"'([^']*)'(?=\s*[:,\}\]])", r'"\1"', text)
    
    # Fix missing commas between object properties
    text = re.sub(r'"\s*\n\s*"', '",\n"', text)
    
    # Remove trailing commas before closing brackets
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    
    # Fix common escaping issues
    text = text.replace('\\"', '"').replace('\\n', '\n')
    
    return text


def parse_json_robust(text: str) -> dict:
    """Extract and parse JSON from LLM output with aggressive repair.
    
    Attempts:
    1. Direct JSON parse
    2. Clean and parse
    3. Extract block and parse
    4. Apply repair heuristics
    5. Use json_repair library
    
    Args:
        text: Raw LLM output text
    
    Returns:
        Parsed JSON object
    
    Raises:
        ValueError: If JSON cannot be extracted after all attempts
    """
    # Quick path: valid JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Clean markdown/tags
    cleaned = _clean_json_text(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    # Extract JSON block
    try:
        extracted = _extract_json_block(cleaned)
        return json.loads(extracted)
    except (ValueError, json.JSONDecodeError):
        pass
    
    # Apply repair heuristics
    try:
        repaired = _repair_json(extracted if 'extracted' in locals() else cleaned)
        return json.loads(repaired)
    except (json.JSONDecodeError, NameError):
        pass
    
    # Last resort: use json_repair library
    try:
        import json_repair
        return json_repair.loads(cleaned)
    except Exception as e:
        logger.error(f"All JSON parsing attempts failed: {e}")
        raise ValueError(
            f"Cannot extract valid JSON from LLM response. "
            f"First 500 chars: {text[:500]}"
        )


# ── Structured Invocation with Retry ──────────────────────────


def invoke_structured(
    prompt: str,
    schema: Type[T],
    max_retries: int = 2,
    timeout: Optional[int] = None,
) -> T:
    """Invoke LLM for structured output with robust parsing and retry.
    
    Pipeline:
    1. Call LLM with deterministic generation parameters
    2. Extract raw response text
    3. Parse JSON with auto-repair
    4. Validate against Pydantic schema
    5. Retry with correction prompt if failed
    6. Return validated object or error dict
    
    Args:
        prompt: Input prompt with JSON schema instructions
        schema: Pydantic model class for validation
        max_retries: Number of retry attempts (default: 2)
        timeout: Override default LLM timeout
    
    Returns:
        Validated Pydantic model instance
    
    Raises:
        ValueError: If parsing/validation fails after all retries
    """
    llm = get_llm_structured()
    
    last_error: Optional[Exception] = None
    last_response: str = ""
    
    start_time = time.time()
    effective_timeout = timeout or settings.LLM_TIMEOUT
    
    for attempt in range(1 + max_retries):
        try:
            # Check timeout
            if time.time() - start_time > effective_timeout:
                logger.error(f"Structured invocation timeout after {effective_timeout}s")
                raise TimeoutError(f"LLM invocation exceeded {effective_timeout}s timeout")
            
            # Build prompt
            if attempt > 0:
                effective_prompt = _build_retry_prompt(prompt, last_response, last_error)
                logger.info(f"Retry attempt {attempt}/{max_retries} for structured output")
            else:
                effective_prompt = prompt
            
            # Invoke LLM
            logger.debug(f"Invoking LLM (attempt {attempt + 1})")
            response = llm.invoke(effective_prompt)
            
            # Extract text
            text = getattr(response, "content", str(response)).strip()
            last_response = text
            
            # Parse JSON
            logger.debug("Parsing JSON from LLM response")
            data = parse_json_robust(text)
            
            # Validate with schema
            logger.debug(f"Validating against schema: {schema.__name__}")
            validated = schema.model_validate(data)
            
            logger.info(f"Structured output validated successfully (attempt {attempt + 1})")
            return validated
        
        except (json.JSONDecodeError, ValueError, ValidationError) as exc:
            last_error = exc
            logger.warning(
                f"Structured output failed (attempt {attempt + 1}/{max_retries + 1}): "
                f"{type(exc).__name__}: {str(exc)[:200]}"
            )
            
            # Log raw response for debugging
            if attempt == max_retries:
                logger.error(
                    f"Final attempt failed. Raw response: {last_response[:1000]}"
                )
    
    # All attempts failed - raise error
    error_msg = (
        f"Failed to produce valid structured output after {max_retries + 1} attempts. "
        f"Last error: {type(last_error).__name__}: {str(last_error)}"
    )
    logger.error(error_msg)
    raise ValueError(error_msg)


def invoke_structured_safe(
    prompt: str,
    schema: Type[T],
    max_retries: int = 2,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    """Safe wrapper that returns error dict instead of raising exception.
    
    Returns:
        On success: {"success": True, "data": validated_object.model_dump()}
        On failure: {"success": False, "error": "ERROR_CODE", "details": "message"}
    """
    try:
        result = invoke_structured(prompt, schema, max_retries, timeout)
        return {
            "success": True,
            "data": result.model_dump()
        }
    
    except TimeoutError as e:
        logger.error(f"LLM timeout: {e}")
        return {
            "success": False,
            "error": "LLM_TIMEOUT",
            "details": str(e)
        }
    
    except ValueError as e:
        logger.error(f"LLM output invalid: {e}")
        return {
            "success": False,
            "error": "LLM_OUTPUT_INVALID",
            "details": str(e)
        }
    
    except Exception as e:
        logger.error(f"Unexpected error in structured invocation: {e}", exc_info=True)
        return {
            "success": False,
            "error": "LLM_INVOCATION_ERROR",
            "details": str(e)
        }


# ── Async Variants ────────────────────────────────────────────


async def async_invoke_structured(
    prompt: str,
    schema: Type[T],
    max_retries: int = 2,
    timeout: Optional[int] = None,
) -> T:
    """Async version of invoke_structured using ainvoke."""
    llm = get_llm_structured()
    
    last_error: Optional[Exception] = None
    last_response: str = ""
    
    start_time = time.time()
    effective_timeout = timeout or settings.LLM_TIMEOUT
    
    for attempt in range(1 + max_retries):
        try:
            if time.time() - start_time > effective_timeout:
                logger.error(f"Async structured invocation timeout after {effective_timeout}s")
                raise TimeoutError(f"LLM invocation exceeded {effective_timeout}s timeout")
            
            if attempt > 0:
                effective_prompt = _build_retry_prompt(prompt, last_response, last_error)
                logger.info(f"Async retry attempt {attempt}/{max_retries}")
            else:
                effective_prompt = prompt
            
            logger.debug(f"Async invoking LLM (attempt {attempt + 1})")
            response = await llm.ainvoke(effective_prompt)
            
            text = getattr(response, "content", str(response)).strip()
            last_response = text
            
            data = parse_json_robust(text)
            validated = schema.model_validate(data)
            
            logger.info(f"Async structured output validated (attempt {attempt + 1})")
            return validated
        
        except (json.JSONDecodeError, ValueError, ValidationError) as exc:
            last_error = exc
            logger.warning(
                f"Async structured output failed (attempt {attempt + 1}): "
                f"{type(exc).__name__}: {str(exc)[:200]}"
            )
    
    error_msg = f"Async failed after {max_retries + 1} attempts. Last error: {last_error}"
    logger.error(error_msg)
    raise ValueError(error_msg)


async def async_invoke_structured_safe(
    prompt: str,
    schema: Type[T],
    max_retries: int = 2,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    """Async safe wrapper returning error dict."""
    try:
        result = await async_invoke_structured(prompt, schema, max_retries, timeout)
        return {"success": True, "data": result.model_dump()}
    
    except TimeoutError as e:
        return {"success": False, "error": "LLM_TIMEOUT", "details": str(e)}
    
    except ValueError as e:
        return {"success": False, "error": "LLM_OUTPUT_INVALID", "details": str(e)}
    
    except Exception as e:
        logger.error(f"Async unexpected error: {e}", exc_info=True)
        return {"success": False, "error": "LLM_INVOCATION_ERROR", "details": str(e)}


# ── Retry Prompt Builder ──────────────────────────────────────


def _build_retry_prompt(
    original_prompt: str,
    previous_response: str,
    error: Optional[Exception],
) -> str:
    """Build a delta correction prompt — sends ONLY the broken JSON + fix instruction.

    Does NOT re-send the full original prompt. This saves tokens on retries.
    """
    error_desc = f"{type(error).__name__}: {str(error)[:200]}" if error else "invalid format"

    return f"""The following JSON output is invalid or truncated. Fix ONLY the JSON — do not change values or structure, just repair syntax issues.

Error: {error_desc}

Broken JSON:
```
{previous_response[:2000]}
```

Rules:
- Return ONLY valid JSON — no markdown fences, no explanatory text
- Complete all fields in the schema
- Ensure proper JSON syntax (commas, quotes, brackets)
- Keep output compact to avoid truncation

YOUR FIXED JSON OUTPUT:
"""
