"""
Unit tests for backend/app/services/token_counter.py
Source reference: "4. IaaS.pdf" — Infrastructure as a Service lecture notes.
Tests: estimate_token_count, truncate_context, token limits
No database or network required.
"""

import sys
import os
import pytest

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

from app.services.token_counter import (
    estimate_token_count,
    truncate_context_intelligently,
    get_model_token_limit,
    TOKEN_LIMITS,
)


# ── Reference passage from "4. IaaS.pdf" ──────────────────────────────────────────
# This excerpt covers IaaS metering, dynamic scaling, and service characteristics.
_IAAS_PASSAGE = (
    "Infrastructure as a Service provides access to virtualized hardware resources including "
    "virtual machines, virtual storage, virtual local area networks, load balancers, IP addresses, "
    "and software bundles delivered over a public connection such as the internet. "
    "Dynamic scaling is one of the major benefits of IaaS because resources can be automatically "
    "scaled up or down based on application demand without manual intervention. "
    "IaaS providers use metering to charge customers based on the CPU power, memory, and storage "
    "consumed per instance per hour, with costs ranging from two cents for a small instance to "
    "2.60 dollars per hour for a large Windows Server instance. "
    "Service-level agreements guarantee resources will be available 99.999 percent of the time "
    "and that additional capacity will be provisioned dynamically when usage exceeds 80 percent. "
    "Self-service provisioning allows customers to deploy virtual machines and configure networks "
    "without filing tickets or waiting for the provider's operations team to act. "
)


class TestEstimateTokenCount:
    """Token counting — accuracy and edge cases."""

    def test_empty_string_is_zero(self):
        assert estimate_token_count("") == 0

    def test_none_like_empty(self):
        assert estimate_token_count("") == 0

    def test_short_text_positive(self):
        # Simple IaaS sentence
        count = estimate_token_count("IaaS provides virtual machines over the internet.")
        assert count > 0

    def test_longer_text_has_more_tokens(self):
        short = "IaaS provides virtual infrastructure."
        long = short * 100
        assert estimate_token_count(long) > estimate_token_count(short)

    def test_rough_estimate_reasonable(self):
        """The IaaS passage (~160 words) should be in the range 100-600 tokens."""
        # _IAAS_PASSAGE is approximately 160 words / ~1 050 characters
        count = estimate_token_count(_IAAS_PASSAGE)
        assert 100 <= count <= 600

    def test_unicode_text(self):
        """Unicode text should still produce a positive count."""
        count = estimate_token_count("日本語テスト文字列")
        assert count > 0

    def test_whitespace_only(self):
        count = estimate_token_count("   \t\n  ")
        # May be 0 or very small — just ensure non-negative
        assert count >= 0

    def test_single_character(self):
        count = estimate_token_count("a")
        # tiktoken: 1 token; fallback: max(1, 1//4) = 1
        assert count >= 1

    def test_model_parameter_accepted(self):
        """Passing model name should not raise."""
        count = estimate_token_count(_IAAS_PASSAGE, model="llama3")
        assert count > 0


class TestTokenLimitsDict:
    """Verify TOKEN_LIMITS dictionary integrity."""

    def test_default_limit_exists(self):
        assert "default" in TOKEN_LIMITS
        assert TOKEN_LIMITS["default"] > 0

    def test_llama3_limit(self):
        assert TOKEN_LIMITS.get("llama3", 0) >= 4096

    def test_gemini_flash_large_limit(self):
        assert TOKEN_LIMITS.get("gemini-2.5-flash", 0) >= 100000

    def test_all_limits_positive(self):
        for model, limit in TOKEN_LIMITS.items():
            assert limit > 0, f"Token limit for {model!r} must be positive"


class TestGetModelTokenLimit:
    """Verify get_model_token_limit returns sensible values."""

    def test_default_model(self):
        assert get_model_token_limit("default") == TOKEN_LIMITS["default"]

    def test_known_model_exact_match(self):
        assert get_model_token_limit("llama3") == TOKEN_LIMITS["llama3"]

    def test_unknown_model_returns_default(self):
        limit = get_model_token_limit("some-unknown-model-xyz")
        assert limit == TOKEN_LIMITS["default"]

    def test_gemini_partial_match(self):
        """Partial name matching should find a reasonable limit."""
        limit = get_model_token_limit("gemini-2.5-flash-latest")
        assert limit >= 100000


class TestTruncateContextIntelligently:
    """Context truncation via truncate_context_intelligently."""

    def _chunks(self, n, words_each=50):
        return [(f"Chunk {i}: " + "word " * words_each, float(n - i)) for i in range(n)]

    def test_no_truncation_when_below_limit(self):
        chunks = self._chunks(2, words_each=20)
        selected, truncated = truncate_context_intelligently(chunks, max_tokens=10000)
        assert truncated is False

    def test_truncation_when_above_limit(self):
        # 20 chunks of 50 words each ≈ 20*50/4 = 250 tokens each → try 100-token limit
        chunks = self._chunks(20, words_each=200)
        selected, truncated = truncate_context_intelligently(chunks, max_tokens=100)
        assert truncated is True
        assert len(selected) < 20

    def test_high_score_chunks_preferred(self):
        """Chunks with higher scores should be selected first."""
        chunks = [("High-priority content " * 10, 10.0), ("Low-priority content " * 10, 1.0)]
        selected, _ = truncate_context_intelligently(chunks, max_tokens=50)
        if selected:
            # First selected chunk should be the higher-scoring one
            assert "High-priority" in selected[0][0]

    def test_empty_chunks_not_truncated(self):
        selected, truncated = truncate_context_intelligently([], max_tokens=1000)
        assert selected == []
        assert truncated is False

    def test_returns_tuple(self):
        result = truncate_context_intelligently(self._chunks(3), max_tokens=10000)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_selected_chunks_are_subset_of_input(self):
        chunks = self._chunks(5)
        selected, _ = truncate_context_intelligently(chunks, max_tokens=10000)
        for chunk in selected:
            assert chunk in chunks


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
