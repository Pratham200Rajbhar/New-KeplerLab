"""Rate limiting middleware for API endpoints.

Implements per-user request throttling to prevent abuse and ensure
fair resource allocation. Uses sliding window algorithm with in-memory
counters.

Limits:
- Chat endpoints: 30 requests per minute per user
- Generation endpoints (flashcard, quiz, PPT, podcast): 5 requests per minute per user
"""

from __future__ import annotations

import time
import logging
from typing import Dict, Tuple
from collections import defaultdict
from threading import Lock
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Rate limit configurations
CHAT_LIMIT = 30  # requests per minute
GENERATION_LIMIT = 5  # requests per minute
WINDOW_SECONDS = 60  # 1 minute window

# In-memory storage for request counts
# Format: {user_id: [(timestamp, endpoint_type), ...]}
_request_history: Dict[str, list] = defaultdict(list)
_lock = Lock()


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, limit: int, window: int, retry_after: int):
        """Initialize with limit details.
        
        Args:
            limit: Maximum requests allowed
            window: Time window in seconds
            retry_after: Seconds until next request allowed
        """
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "limit": limit,
                "window_seconds": window,
                "retry_after": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )


def _clean_old_requests(user_id: str, current_time: float) -> None:
    """Remove requests older than the time window.
    
    Args:
        user_id: User identifier
        current_time: Current timestamp
    """
    cutoff_time = current_time - WINDOW_SECONDS
    _request_history[user_id] = [
        (ts, endpoint) for ts, endpoint in _request_history[user_id]
        if ts > cutoff_time
    ]


def _get_request_count(user_id: str, endpoint_type: str, current_time: float) -> int:
    """Count recent requests for a specific endpoint type.
    
    Args:
        user_id: User identifier
        endpoint_type: "chat" or "generation"
        current_time: Current timestamp
    
    Returns:
        Number of requests in the current window
    """
    cutoff_time = current_time - WINDOW_SECONDS
    return sum(
        1 for ts, ep_type in _request_history[user_id]
        if ts > cutoff_time and ep_type == endpoint_type
    )


def _add_request(user_id: str, endpoint_type: str, current_time: float) -> None:
    """Record a new request.
    
    Args:
        user_id: User identifier
        endpoint_type: "chat" or "generation"
        current_time: Current timestamp
    """
    _request_history[user_id].append((current_time, endpoint_type))


def check_rate_limit(user_id: str, endpoint_type: str) -> None:
    """Check if user has exceeded rate limit for endpoint type.
    
    Args:
        user_id: User identifier
        endpoint_type: "chat" or "generation"
    
    Raises:
        RateLimitExceeded: If rate limit is exceeded
    """
    if not user_id:
        # Allow unauthenticated requests (they'll fail auth later)
        return
    
    with _lock:
        current_time = time.time()
        
        # Clean old requests
        _clean_old_requests(user_id, current_time)
        
        # Get limit for endpoint type
        limit = CHAT_LIMIT if endpoint_type == "chat" else GENERATION_LIMIT
        
        # Count recent requests
        request_count = _get_request_count(user_id, endpoint_type, current_time)
        
        if request_count >= limit:
            # Calculate retry_after (time until oldest request expires)
            oldest_request_time = min(
                ts for ts, ep_type in _request_history[user_id]
                if ep_type == endpoint_type
            )
            retry_after = int(WINDOW_SECONDS - (current_time - oldest_request_time)) + 1
            
            logger.warning(
                f"Rate limit exceeded for user {user_id}: "
                f"{request_count}/{limit} {endpoint_type} requests in {WINDOW_SECONDS}s"
            )
            raise RateLimitExceeded(limit, WINDOW_SECONDS, retry_after)
        
        # Record this request
        _add_request(user_id, endpoint_type, current_time)
        
        logger.debug(
            f"Rate limit check passed: user={user_id}, "
            f"count={request_count + 1}/{limit}, type={endpoint_type}"
        )


def get_rate_limit_info(user_id: str, endpoint_type: str) -> Dict[str, int]:
    """Get current rate limit status for a user.
    
    Args:
        user_id: User identifier
        endpoint_type: "chat" or "generation"
    
    Returns:
        Dict with limit, remaining, and reset info
    """
    if not user_id:
        return {
            "limit": 0,
            "remaining": 0,
            "reset_in": 0,
        }
    
    with _lock:
        current_time = time.time()
        _clean_old_requests(user_id, current_time)
        
        limit = CHAT_LIMIT if endpoint_type == "chat" else GENERATION_LIMIT
        request_count = _get_request_count(user_id, endpoint_type, current_time)
        remaining = max(0, limit - request_count)
        
        # Calculate reset time (when oldest request expires)
        if request_count > 0:
            oldest_request_time = min(
                ts for ts, ep_type in _request_history[user_id]
                if ep_type == endpoint_type
            )
            reset_in = int(WINDOW_SECONDS - (current_time - oldest_request_time)) + 1
        else:
            reset_in = WINDOW_SECONDS
        
        return {
            "limit": limit,
            "remaining": remaining,
            "reset_in": reset_in,
        }


async def rate_limit_middleware(request: Request, call_next):
    """FastAPI middleware for rate limiting.
    
    Automatically checks rate limits based on endpoint path.
    Adds rate limit headers to responses.
    
    Args:
        request: FastAPI request
        call_next: Next middleware/handler
    
    Returns:
        Response with rate limit headers
    """
    # Skip rate limiting for health checks and auth endpoints
    if request.url.path in ["/health", "/api/auth/login", "/api/auth/register", "/api/auth/refresh"]:
        return await call_next(request)
    
    # Determine endpoint type from path
    endpoint_type = None
    if "/chat" in request.url.path:
        endpoint_type = "chat"
    elif any(x in request.url.path for x in ["/flashcard", "/quiz", "/ppt", "/podcast"]):
        endpoint_type = "generation"
    
    # Only apply rate limiting to known endpoints
    if endpoint_type:
        # Extract user_id from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        
        if user_id:
            try:
                # Check rate limit before processing request
                check_rate_limit(user_id, endpoint_type)
            except RateLimitExceeded as e:
                return JSONResponse(
                    status_code=e.status_code,
                    content=e.detail,
                    headers=e.headers,
                )
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers to response
    if endpoint_type and hasattr(request.state, "user_id"):
        user_id = request.state.user_id
        if user_id:
            info = get_rate_limit_info(user_id, endpoint_type)
            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(info["reset_in"])
    
    return response
