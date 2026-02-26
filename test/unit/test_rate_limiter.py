"""
Unit tests for backend/app/services/rate_limiter.py
Tests: sliding window counting, per-endpoint limits, RateLimitExceeded, clean-up,
multi-user isolation, get_rate_limit_info
Fully async, no DB or network required.
"""

import sys
import os
import asyncio
import time
import pytest
import pytest_asyncio
from unittest.mock import patch

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

import app.services.rate_limiter as _rl

from app.services.rate_limiter import (
    check_rate_limit,
    get_rate_limit_info,
    RateLimitExceeded,
    CHAT_LIMIT,
    GENERATION_LIMIT,
    AUTH_LIMIT,
    WINDOW_SECONDS,
    _request_history,
)


@pytest.fixture(autouse=True)
def clear_history():
    """Reset shared request history before every test."""
    _request_history.clear()
    yield
    _request_history.clear()


# ────────────────────────────────────────────────────────────────────────────
# Basic allow / deny
# ────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_single_request_allowed():
    """First request always passes."""
    await check_rate_limit("user-1", "chat")  # should not raise


@pytest.mark.asyncio
async def test_empty_user_id_skipped():
    """Empty user_id should not raise (no-op)."""
    await check_rate_limit("", "chat")


@pytest.mark.asyncio
async def test_chat_limit_exceeded():
    """Exceeding CHAT_LIMIT within the window raises RateLimitExceeded."""
    for _ in range(CHAT_LIMIT):
        await check_rate_limit("user-chat", "chat")
    with pytest.raises(RateLimitExceeded):
        await check_rate_limit("user-chat", "chat")


@pytest.mark.asyncio
async def test_generation_limit_exceeded():
    """Exceeding GENERATION_LIMIT raises RateLimitExceeded."""
    for _ in range(GENERATION_LIMIT):
        await check_rate_limit("user-gen", "generation")
    with pytest.raises(RateLimitExceeded):
        await check_rate_limit("user-gen", "generation")


@pytest.mark.asyncio
async def test_auth_limit_exceeded():
    """Auth brute-force limit works independently."""
    for _ in range(AUTH_LIMIT):
        await check_rate_limit("ip:1.2.3.4", "auth")
    with pytest.raises(RateLimitExceeded):
        await check_rate_limit("ip:1.2.3.4", "auth")


# ────────────────────────────────────────────────────────────────────────────
# Multi-user isolation
# ────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_different_users_isolated():
    """User A hitting limit must NOT block User B."""
    for _ in range(CHAT_LIMIT):
        await check_rate_limit("user-a", "chat")
    # user-a is now blocked
    with pytest.raises(RateLimitExceeded):
        await check_rate_limit("user-a", "chat")
    # user-b should still be fine
    await check_rate_limit("user-b", "chat")


@pytest.mark.asyncio
async def test_different_endpoint_types_isolated():
    """Hitting chat limit must NOT affect generation limit for same user."""
    for _ in range(CHAT_LIMIT):
        await check_rate_limit("user-x", "chat")
    # Generation should still work
    await check_rate_limit("user-x", "generation")


# ────────────────────────────────────────────────────────────────────────────
# Window expiry (fast mock)
# ────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_old_requests_expire():
    """Requests outside the window should not count toward the limit."""
    current = time.time()
    # Manually pre-fill with old requests (outside the window)
    old_time = current - WINDOW_SECONDS - 5
    _request_history["user-old"] = [(old_time, "chat")] * CHAT_LIMIT
    # Now the limit should not be exceeded because all are expired
    await check_rate_limit("user-old", "chat")  # should not raise


# ────────────────────────────────────────────────────────────────────────────
# RateLimitExceeded attributes
# ────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rate_limit_exceeded_has_correct_status():
    for _ in range(GENERATION_LIMIT):
        await check_rate_limit("rle-user", "generation")
    with pytest.raises(RateLimitExceeded) as exc_info:
        await check_rate_limit("rle-user", "generation")
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_exceeded_has_retry_after_header():
    for _ in range(GENERATION_LIMIT):
        await check_rate_limit("rle-user2", "generation")
    with pytest.raises(RateLimitExceeded) as exc_info:
        await check_rate_limit("rle-user2", "generation")
    assert "Retry-After" in exc_info.value.headers


# ────────────────────────────────────────────────────────────────────────────
# get_rate_limit_info
# ────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rate_limit_info_structure():
    info = await get_rate_limit_info("user-info", "chat")
    assert "limit" in info
    assert "remaining" in info
    assert "reset_in" in info


@pytest.mark.asyncio
async def test_rate_limit_info_initial_remaining():
    info = await get_rate_limit_info("fresh-user", "chat")
    assert info["remaining"] == CHAT_LIMIT


@pytest.mark.asyncio
async def test_rate_limit_info_decreases_after_request():
    await check_rate_limit("user-dec", "chat")
    info = await get_rate_limit_info("user-dec", "chat")
    assert info["remaining"] == CHAT_LIMIT - 1


@pytest.mark.asyncio
async def test_rate_limit_info_empty_user():
    info = await get_rate_limit_info("", "chat")
    assert info["remaining"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
