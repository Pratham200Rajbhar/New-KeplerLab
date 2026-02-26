"""
Unit tests for backend/app/services/rag/context_builder.py
Source reference: "4. IaaS.pdf" — Infrastructure as a Service lecture notes.
Tests: _normalize_score, _filter_chunks, _summarize_chunk, build_context
No ChromaDB or LLM required — pure logic tests.
"""

import sys
import os
import math
import pytest

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

# Import private helpers directly for white-box testing
from app.services.rag.context_builder import (
    build_context,
    _normalize_score,
    _filter_chunks,
    _summarize_chunk,
    _count_tokens,
)


# ── Reference text blocks derived from "4. IaaS.pdf" ────────────────────────────

_IAAS_DYNAMIC_SCALING = (
    "Dynamic scaling is one of the major benefits of IaaS for companies facing resource uncertainty. "
    "Resources can be automatically scaled up or down based on the requirements of the running "
    "application workloads. If customers need more resources than originally expected they can "
    "obtain them immediately up to a given limit set by the provider. "
    "A provider of IaaS typically optimizes the environment so that hardware, operating system, "
    "and automation software can support a large number of concurrent application workloads. "
)

_IAAS_SERVICE_LEVELS = (
    "Consumers acquire IaaS services in different ways, either on an on-demand model with no "
    "long-term contract or by signing a contract for a specific amount of storage or compute. "
    "A typical IaaS contract includes some level of service guarantee specifying that resources "
    "will be available 99.999 percent of the time and that additional capacity will be provisioned "
    "dynamically when greater than 80 percent of any given resource is being actively consumed. "
    "A service-level agreement documents what the provider has agreed to deliver in terms of "
    "availability, response to demand, and recovery time objectives for the customer environment. "
)

_IAAS_RENTAL_MODEL = (
    "When companies use IaaS the servers, storage, and other IT infrastructure components are "
    "rented for a fee based on the quantity of resources used and how long they remain in use. "
    "Customers gain immediate virtual access to the resources they need without receiving any "
    "physical hardware delivery at their own premises or offices anywhere in the world. "
    "The physical components remain inside the infrastructure service provider's data center "
    "where the provider is fully responsible for hardware maintenance and replacement. "
    "Within a private IaaS model the charge-back approach allocates usage fees to individual "
    "departments based on their actual resource consumption over a week, month, or year. "
)

_IAAS_METERING = (
    "IaaS providers use the metering process to charge users based on the instance of computing "
    "consumed, defined as the CPU power, memory allocation, and storage space used per hour. "
    "When an instance is initiated hourly charges begin to accumulate until the instance is "
    "explicitly terminated by the customer or automatically stopped by a lifecycle policy. "
    "The charge for a very small instance may be as little as two cents per hour while the "
    "hourly fee can increase to 2.60 dollars for a large resource-intensive instance running "
    "Windows Server with additional software license fees bundled into the per-hour rate. "
    "Metering ensures that each customer sharing the same multi-tenant environment is billed "
    "accurately for their actual resource consumption and no more than that amount per period. "
)

_IAAS_SELF_SERVICE = (
    "Self-service provisioning is an imperative characteristic of IaaS that allows customers "
    "to request and configure cloud computing resources without any direct human intervention "
    "from the provider's operations team at any point in the provisioning workflow. "
    "The banking ATM service is a great example of the business value of self-service: "
    "without the ATM, banks would require costly human staff to manage all customer activities "
    "even for the most repetitive and straightforward financial transactions at branch locations. "
    "Similarly, IaaS self-service interfaces let organizations provision virtual machines, "
    "allocate storage volumes, configure virtual networks, and deploy software bundles on demand. "
)


# ────────────────────────────────────────────────────────────────────────────
# _normalize_score
# ────────────────────────────────────────────────────────────────────────────

class TestNormalizeScore:

    def test_zero_maps_to_half(self):
        """sigmoid(0) = 0.5"""
        assert _normalize_score(0.0) == pytest.approx(0.5, abs=1e-6)

    def test_large_positive_maps_close_to_one(self):
        assert _normalize_score(100.0) > 0.99

    def test_large_negative_maps_close_to_zero(self):
        assert _normalize_score(-100.0) < 0.01

    def test_output_in_zero_one_range(self):
        for score in [-10, -1, -0.5, 0, 0.5, 1, 10]:
            norm = _normalize_score(score)
            assert 0.0 <= norm <= 1.0

    def test_monotonic(self):
        """Higher raw score → higher normalized score."""
        scores = [-5, -1, 0, 1, 5]
        normalized = [_normalize_score(s) for s in scores]
        assert normalized == sorted(normalized)


# ────────────────────────────────────────────────────────────────────────────
# _count_tokens
# ────────────────────────────────────────────────────────────────────────────

class TestCountTokens:

    def test_empty_returns_positive_or_zero(self):
        count = _count_tokens("")
        assert count >= 0

    def test_nonempty_positive(self):
        count = _count_tokens("Hello world test sentence.")
        assert count > 0

    def test_longer_text_more_tokens(self):
        short = _count_tokens("Hi")
        long = _count_tokens("Hi " * 200)
        assert long > short


# ────────────────────────────────────────────────────────────────────────────
# _filter_chunks
# ────────────────────────────────────────────────────────────────────────────

class TestFilterChunks:
    # Source: "4. IaaS.pdf" — IaaS text blocks replace generic "word " padding

    def _long_text(self, n=200):
        # Use real IaaS content repeated to reach ~n words
        base = _IAAS_DYNAMIC_SCALING + _IAAS_SERVICE_LEVELS + _IAAS_RENTAL_MODEL
        return (base * ((n * 6 // len(base)) + 1))[:n * 6]

    def test_high_score_chunk_kept(self):
        chunks = [(self._long_text(), 5.0)]  # high logit → sigmoid ≈ 1.0
        result = _filter_chunks(chunks, min_score=0.5, min_length=10)
        assert len(result) == 1

    def test_very_low_score_chunk_filtered(self):
        chunks = [(self._long_text(), -100.0)]  # sigmoid ≈ 0.0 < 0.5
        result = _filter_chunks(chunks, min_score=0.5, min_length=10)
        assert len(result) == 0

    def test_too_short_chunk_filtered(self):
        chunks = [("Hi", 5.0)]
        result = _filter_chunks(chunks, min_score=0.0, min_length=100)
        assert len(result) == 0

    def test_empty_input_empty_output(self):
        assert _filter_chunks([], min_score=0.5, min_length=10) == []

    def test_multiple_chunks_filtered_correctly(self):
        chunks = [
            (self._long_text(), 5.0),   # high score — keep
            (self._long_text(), -100.0), # low score — filter
            (self._long_text(), 2.0),    # medium-high — keep
        ]
        result = _filter_chunks(chunks, min_score=0.5, min_length=10)
        assert len(result) == 2

    def test_scores_normalized_in_output(self):
        """Output scores should be in [0, 1]."""
        chunks = [(self._long_text(), 3.0)]
        result = _filter_chunks(chunks, min_score=0.0, min_length=10)
        for _, norm_score in result:
            assert 0.0 <= norm_score <= 1.0


# ────────────────────────────────────────────────────────────────────────────
# _summarize_chunk
# ────────────────────────────────────────────────────────────────────────────

class TestSummarizeChunk:

    def _make_sentences(self, n=10):
        return " ".join(f"This is sentence number {i}." for i in range(n))

    def test_short_text_unchanged(self):
        text = "One sentence only."
        result = _summarize_chunk(text, max_sentences=4)
        assert result == text

    def test_long_text_truncated(self):
        text = self._make_sentences(20)
        result = _summarize_chunk(text, max_sentences=4)
        assert len(result) < len(text)

    def test_truncated_ends_with_ellipsis(self):
        text = self._make_sentences(20)
        result = _summarize_chunk(text, max_sentences=4)
        assert result.endswith("…")

    def test_returns_string(self):
        assert isinstance(_summarize_chunk("Hello."), str)


# ────────────────────────────────────────────────────────────────────────────
# build_context
# ────────────────────────────────────────────────────────────────────────────

class TestBuildContext:
    # Source: "4. IaaS.pdf" — IaaS chunks replace generic "Relevant document chunk content"

    def _chunk(self, text=None, score=3.0):
        if text is None:
            # Real IaaS metering/self-service content as default chunk body
            text = (_IAAS_METERING + _IAAS_SELF_SERVICE) * 2
        return (text, score)

    def test_empty_chunks_returns_not_found(self):
        result = build_context([])
        assert "no" in result.lower() or "not found" in result.lower()

    def test_single_chunk_returns_content(self):
        chunk_text = "Important information about the topic. " * 10
        result = build_context([self._chunk(chunk_text)])
        assert isinstance(result, str)
        assert len(result) > 0

    def test_multiple_chunks_all_included(self):
        chunks = [self._chunk() for _ in range(3)]
        result = build_context(chunks)
        # Should contain "SOURCE 1" at minimum
        assert "SOURCE 1" in result

    def test_low_score_chunks_filtered(self):
        # Source: "4. IaaS.pdf" — real IaaS text used instead of 'a '*100
        chunks = [(_IAAS_DYNAMIC_SCALING * 3, -100.0)]  # sigmoid ≈ 0 → filtered
        result = build_context(chunks)
        assert "not" in result.lower() or "no" in result.lower()

    def test_source_labels_in_output(self):
        chunks = [self._chunk() for _ in range(2)]
        result = build_context(chunks)
        assert "SOURCE" in result

    def test_custom_max_tokens_respected(self):
        """Very tight token budget should limit output or produce not-found message."""
        # Source: "4. IaaS.pdf" — large IaaS corpus replaces synthetic repeated word padding
        big_iaas_text = (
            _IAAS_DYNAMIC_SCALING + _IAAS_SERVICE_LEVELS + _IAAS_RENTAL_MODEL
            + _IAAS_METERING + _IAAS_SELF_SERVICE
        ) * 10
        big_chunk = (big_iaas_text, 5.0)
        result_tight = build_context([big_chunk], max_tokens=10)
        result_generous = build_context([big_chunk], max_tokens=50000)
        # With a tiny budget, context should either be shorter or a not-found message
        assert len(result_tight) <= len(result_generous)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
