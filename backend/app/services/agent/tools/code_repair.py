"""Code repair — self-healing code execution via LLM-based fix.

Takes broken code and stderr, asks the LLM to fix the specific error,
and returns the corrected code string.
"""

from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger(__name__)

_PROMPT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "prompts", "code_repair_prompt.txt"
)


def _load_repair_prompt() -> str:
    """Load the code repair prompt template."""
    try:
        with open(_PROMPT_PATH, "r") as f:
            return f.read()
    except FileNotFoundError:
        logger.warning("[code_repair] Prompt file not found, using inline fallback")
        return (
            "You are a Python debugger. Your ONLY job is to fix the error below.\n\n"
            "=== ORIGINAL CODE ===\n{broken_code}\n\n"
            "=== ERROR MESSAGE ===\n{stderr}\n\n"
            "=== SANDBOX SECURITY RULES ===\n"
            "NEVER use: subprocess, shutil, socket, requests, urllib, httpx, aiohttp\n"
            "NEVER use: os.system(), os.popen(), os.exec*(), os.spawn*(), os.kill()\n"
            "NEVER use: os.environ, os.getenv(), os.listdir(), os.walk(), os.makedirs()\n"
            "NEVER use: eval(), exec(), __import__(), compile()\n"
            "NEVER use: multiprocessing, threading, signal, ctypes, pickle\n"
            "NEVER use: plt.show() — use plt.savefig() instead\n"
            "You CAN use: os.path.join(), os.path.exists(), os.path.basename()\n"
            "If the error mentions a forbidden import, REMOVE it and find an alternative.\n"
            "If the error is OpenBLAS/pthread, it is transient — return code as-is.\n\n"
            "=== INSTRUCTIONS ===\n"
            "- Return ONLY the corrected Python code\n"
            "- Do NOT add any explanation or comments\n"
            "- Do NOT wrap in markdown fences\n"
            "- Fix ONLY the specific error — do not change anything else\n"
            "- If the error is a missing import, add an ALLOWED import at the top\n"
            "- If the error is a wrong variable name, fix just that variable\n\n"
            "=== FIXED CODE ===\n"
        )


def _extract_code(response_text: str) -> str:
    """Extract code from LLM response, stripping markdown fences if present."""
    text = response_text.strip()

    # Try to extract from ```python ... ``` or ``` ... ``` blocks
    pattern = r"```(?:python)?\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # If no fences, return as-is (LLM followed instructions)
    return text


async def repair_code(broken_code: str, stderr: str, llm) -> str:
    """Attempt to fix broken Python code using the LLM.

    Args:
        broken_code: The code that produced an error.
        stderr: The error output from execution.
        llm: An LLM instance with .ainvoke() method.

    Returns:
        The fixed code string.
    """
    template = _load_repair_prompt()
    repair_prompt = template.format(broken_code=broken_code, stderr=stderr)

    logger.info("[code_repair] Requesting fix for error: %s", stderr[:200])

    response = await llm.ainvoke(repair_prompt)
    raw = getattr(response, "content", None) or str(response)

    fixed_code = _extract_code(raw)

    logger.info(
        "[code_repair] Got fix (%d chars, original was %d chars)",
        len(fixed_code),
        len(broken_code),
    )

    return fixed_code
