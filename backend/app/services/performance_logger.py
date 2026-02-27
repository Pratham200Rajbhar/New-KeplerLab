"""Performance monitoring middleware for API endpoints.

Tracks and logs performance metrics for all requests:
- Total request time (end-to-end)
- Retrieval time (vector search + MMR)
- Reranking time (cross-encoder scoring)
- LLM latency (generation time)

Metrics are logged in structured format for analysis and alerting.
"""

from __future__ import annotations

import time
import logging
from typing import Optional, Dict
from contextvars import ContextVar
from fastapi import Request
from fastapi.responses import Response

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("performance")

# Context variables for tracking timings across async operations
_request_start_time: ContextVar[float] = ContextVar("request_start_time")
_retrieval_time: ContextVar[float] = ContextVar("retrieval_time", default=0.0)
_reranking_time: ContextVar[float] = ContextVar("reranking_time", default=0.0)
_llm_time: ContextVar[float] = ContextVar("llm_time", default=0.0)


def set_request_start_time() -> None:
    """Mark the start of request processing."""
    _request_start_time.set(time.time())


def get_request_elapsed_time() -> float:
    """Get elapsed time since request start.
    
    Returns:
        Elapsed seconds, or 0.0 if not set
    """
    try:
        start = _request_start_time.get()
        return time.time() - start
    except LookupError:
        return 0.0


def record_retrieval_time(seconds: float) -> None:
    """Record time spent in retrieval (vector search + MMR).
    
    Args:
        seconds: Elapsed time in seconds
    """
    _retrieval_time.set(seconds)
    logger.debug(f"Retrieval completed in {seconds:.3f}s")


def record_reranking_time(seconds: float) -> None:
    """Record time spent in reranking (cross-encoder).
    
    Args:
        seconds: Elapsed time in seconds
    """
    _reranking_time.set(seconds)
    logger.debug(f"Reranking completed in {seconds:.3f}s")


def record_llm_time(seconds: float) -> None:
    """Record time spent in LLM generation.
    
    Args:
        seconds: Elapsed time in seconds
    """
    _llm_time.set(seconds)
    logger.debug(f"LLM generation completed in {seconds:.3f}s")


def get_performance_metrics() -> Dict[str, float]:
    """Get all recorded performance metrics.
    
    Returns:
        Dict with retrieval_time, reranking_time, llm_time, total_time
    """
    try:
        total_time = get_request_elapsed_time()
        retrieval = _retrieval_time.get()
        reranking = _reranking_time.get()
        llm = _llm_time.get()
    except LookupError:
        return {
            "retrieval_time": 0.0,
            "reranking_time": 0.0,
            "llm_time": 0.0,
            "total_time": 0.0,
        }
    
    return {
        "retrieval_time": retrieval,
        "reranking_time": reranking,
        "llm_time": llm,
        "total_time": total_time,
    }


def log_performance_metrics(
    endpoint: str,
    method: str,
    status_code: int,
    user_id: Optional[str] = None,
) -> None:
    """Log performance metrics in structured format.
    
    Args:
        endpoint: Request path
        method: HTTP method
        status_code: Response status code
        user_id: Optional user identifier
    """
    metrics = get_performance_metrics()
    
    # Calculate other time (total - known components)
    known_time = (
        metrics["retrieval_time"] +
        metrics["reranking_time"] +
        metrics["llm_time"]
    )
    other_time = max(0.0, metrics["total_time"] - known_time)
    
    # Log structured performance data
    perf_logger.info(
        "request_performance",
        extra={
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "user_id": user_id or "anonymous",
            "total_time": round(metrics["total_time"], 3),
            "retrieval_time": round(metrics["retrieval_time"], 3),
            "reranking_time": round(metrics["reranking_time"], 3),
            "llm_time": round(metrics["llm_time"], 3),
            "other_time": round(other_time, 3),
        }
    )


async def performance_monitoring_middleware(request: Request, call_next):
    """FastAPI middleware for performance monitoring.
    
    Records request start time, processes request, then logs all metrics.
    Adds performance headers to response for debugging.
    
    Args:
        request: FastAPI request
        call_next: Next middleware/handler
    
    Returns:
        Response with performance headers
    """
    # Start timing
    set_request_start_time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate total time
    total_time = get_request_elapsed_time()
    
    # Extract user_id if available
    user_id = getattr(request.state, "user_id", None)
    
    # Log metrics for monitored endpoints
    if any(x in request.url.path for x in ["/chat", "/flashcard", "/quiz", "/ppt", "/notebook"]):
        log_performance_metrics(
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            user_id=user_id,
        )
    
    # Only add performance headers in development (avoid leaking internals in prod)
    from app.core.config import settings
    if settings.ENVIRONMENT == "development":
        metrics = get_performance_metrics()
        response.headers["X-Response-Time"] = f"{total_time:.3f}s"
        if metrics["retrieval_time"] > 0:
            response.headers["X-Retrieval-Time"] = f"{metrics['retrieval_time']:.3f}s"
        if metrics["reranking_time"] > 0:
            response.headers["X-Reranking-Time"] = f"{metrics['reranking_time']:.3f}s"
        if metrics["llm_time"] > 0:
            response.headers["X-LLM-Time"] = f"{metrics['llm_time']:.3f}s"
    
    return response


# Helper functions for instrumentation in service code
class PerformanceTimer:
    """Context manager for timing code blocks.
    
    Example:
        with PerformanceTimer() as timer:
            # ... do work ...
        record_retrieval_time(timer.elapsed)
    """
    
    def __init__(self):
        self.start_time: float = 0.0
        self.elapsed: float = 0.0
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.time() - self.start_time
        return False
