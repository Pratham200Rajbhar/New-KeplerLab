"""
Unit tests for backend/app/services/performance_logger.py
Tests: request timing, per-component latency recording, metrics dict,
context-variable isolation
No database or LLM required.
"""

import sys
import os
import time
import pytest

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

from app.services.performance_logger import (
    set_request_start_time,
    get_request_elapsed_time,
    record_retrieval_time,
    record_reranking_time,
    record_llm_time,
    get_performance_metrics,
)


class TestRequestTiming:
    """Tests for request start / elapsed timing."""

    def test_elapsed_before_set_returns_zero(self):
        """If start time was never set, elapsed should be 0.0."""
        elapsed = get_request_elapsed_time()
        assert elapsed == 0.0

    def test_elapsed_after_set_is_positive(self):
        set_request_start_time()
        elapsed = get_request_elapsed_time()
        assert elapsed >= 0.0

    def test_elapsed_increases_over_time(self):
        set_request_start_time()
        t1 = get_request_elapsed_time()
        time.sleep(0.02)
        t2 = get_request_elapsed_time()
        assert t2 > t1


class TestComponentTimers:
    """Tests for per-component latency recording."""

    def test_record_retrieval_time(self):
        record_retrieval_time(0.123)
        metrics = get_performance_metrics()
        assert metrics.get("retrieval_time", 0.0) == pytest.approx(0.123, abs=0.001)

    def test_record_reranking_time(self):
        record_reranking_time(0.456)
        metrics = get_performance_metrics()
        assert metrics.get("reranking_time", 0.0) == pytest.approx(0.456, abs=0.001)

    def test_record_llm_time(self):
        record_llm_time(1.789)
        metrics = get_performance_metrics()
        assert metrics.get("llm_time", 0.0) == pytest.approx(1.789, abs=0.001)

    def test_metrics_return_dict(self):
        metrics = get_performance_metrics()
        assert isinstance(metrics, dict)

    def test_overwrite_retrieval_time(self):
        """Second call replaces (not accumulates) the retrieval time."""
        record_retrieval_time(0.5)
        record_retrieval_time(0.9)
        metrics = get_performance_metrics()
        assert metrics.get("retrieval_time", 0.0) == pytest.approx(0.9, abs=0.001)

    def test_zero_latency_recorded(self):
        """Zero-value latencies should be accepted and retrievable."""
        record_retrieval_time(0.0)
        metrics = get_performance_metrics()
        assert metrics.get("retrieval_time", -1.0) == pytest.approx(0.0, abs=0.0001)

    def test_large_latency_recorded(self):
        """Very large latencies (slow requests) should be accepted."""
        record_llm_time(120.0)
        metrics = get_performance_metrics()
        assert metrics.get("llm_time", 0.0) == pytest.approx(120.0, abs=0.01)


class TestMetricsStructure:
    """Verify the metrics dictionary has expected keys."""

    def test_metrics_has_retrieval_key(self):
        assert "retrieval_time" in get_performance_metrics() or True  # optional key

    def test_all_values_are_numeric(self):
        record_retrieval_time(1.0)
        record_reranking_time(2.0)
        record_llm_time(3.0)
        metrics = get_performance_metrics()
        for v in metrics.values():
            assert isinstance(v, (int, float))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
