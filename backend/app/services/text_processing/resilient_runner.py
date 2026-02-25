"""Resilient runner — timeout + retry wrapper for heavy processing tasks.

Provides :func:`run_with_timeout` for CPU-bound work (OCR, Whisper,
LibreOffice) and :func:`run_with_retry` for combining retries with
timeouts.  All functions are synchronous (they spawn threads/processes
internally) so they integrate cleanly with the existing sync service layer.

Usage::

    from app.services.text_processing.resilient_runner import run_with_retry

    result = run_with_retry(
        lambda: ocr_service.extract_text_from_image(path),
        timeout=settings.OCR_TIMEOUT_SECONDS,
        max_retries=settings.PROCESSING_MAX_RETRIES,
        task_name="OCR",
    )
"""

from __future__ import annotations

import logging
import signal
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ProcessingTimeoutError(Exception):
    """Raised when a processing task exceeds its timeout."""


class ProcessingRetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted."""

    def __init__(self, task_name: str, attempts: int, last_error: Exception):
        self.task_name = task_name
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"{task_name} failed after {attempts} attempt(s): {last_error}"
        )


# ── Core primitives ──────────────────────────────────────────


def run_with_timeout(
    fn: Callable[[], T],
    timeout: int,
    *,
    task_name: str = "task",
) -> T:
    """Execute *fn* in a thread with a hard timeout.

    Args:
        fn: Zero-argument callable (use ``functools.partial`` or a lambda
            to capture arguments).
        timeout: Maximum wall-clock seconds before aborting.
        task_name: Human-readable label for log messages.

    Returns:
        The return value of *fn*.

    Raises:
        ProcessingTimeoutError: If *fn* does not finish in time.
        Exception: Any exception raised by *fn* is re-raised as-is.
    """
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fn)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeout:
            logger.error(
                "%s timed out after %d seconds", task_name, timeout
            )
            future.cancel()
            raise ProcessingTimeoutError(
                f"{task_name} timed out after {timeout} seconds"
            )


def run_with_retry(
    fn: Callable[[], T],
    timeout: int,
    *,
    max_retries: int = 2,
    task_name: str = "task",
    backoff_base: float = 1.0,
) -> T:
    """Execute *fn* with timeout protection and automatic retries.

    On each attempt *fn* is wrapped in :func:`run_with_timeout`.  If it
    fails (timeout **or** exception), the next attempt is made after a
    short exponential back-off sleep.

    Args:
        fn: Zero-argument callable.
        timeout: Per-attempt timeout in seconds.
        max_retries: Total number of **attempts** (including the first).
        task_name: Human-readable label for log messages.
        backoff_base: Multiplier for exponential back-off between retries.

    Returns:
        The return value of *fn* on the first successful attempt.

    Raises:
        ProcessingRetryExhaustedError: When all attempts fail.
    """
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "%s attempt %d/%d (timeout=%ds)",
                task_name, attempt, max_retries, timeout,
            )
            return run_with_timeout(fn, timeout, task_name=task_name)

        except Exception as exc:
            last_error = exc
            logger.warning(
                "%s attempt %d/%d failed: %s",
                task_name, attempt, max_retries, exc,
            )
            if attempt < max_retries:
                sleep_secs = backoff_base * (2 ** (attempt - 1))
                logger.info(
                    "Retrying %s in %.1f seconds…", task_name, sleep_secs
                )
                time.sleep(sleep_secs)

    raise ProcessingRetryExhaustedError(task_name, max_retries, last_error)  # type: ignore[arg-type]
