"""
Integration tests for the storage service + file system
Tests: save/load/delete material text, concurrent operations, large files,
storage stats accuracy — uses real temp filesystem
"""

import sys
import os
import uuid
import threading
import tempfile
import shutil
import pytest
from unittest.mock import patch

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

import app.services.storage_service as _svc
from app.services.storage_service import (
    save_material_text,
    load_material_text,
    delete_material_text,
    get_storage_stats,
    get_material_summary,
)


@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    with patch.object(_svc, "MATERIAL_TEXT_DIR", tmp_path):
        yield tmp_path


# ── Save → Load round-trip ────────────────────────────────────────────────────

class TestSaveLoadRoundTrip:

    def test_utf8_round_trip(self):
        mid = str(uuid.uuid4())
        text = "Hello\n日本語\nCafé\n\tTabbed content"
        save_material_text(mid, text)
        assert load_material_text(mid) == text

    def test_large_text_round_trip(self):
        mid = str(uuid.uuid4())
        text = "A" * 500_000
        save_material_text(mid, text)
        loaded = load_material_text(mid)
        assert len(loaded) == 500_000

    def test_overwrite_text(self):
        """Saving twice with same ID should overwrite the previous content."""
        mid = str(uuid.uuid4())
        save_material_text(mid, "Version 1")
        save_material_text(mid, "Version 2")
        assert load_material_text(mid) == "Version 2"

    def test_binary_safe_text(self):
        """Text with special escape sequences should survive."""
        mid = str(uuid.uuid4())
        text = "Line1\n\rLine2\r\nLine3\x0bLine4"
        save_material_text(mid, text)
        loaded = load_material_text(mid)
        assert loaded == text

    def test_newlines_preserved(self):
        mid = str(uuid.uuid4())
        text = "para1\n\npara2\n\npara3"
        save_material_text(mid, text)
        assert load_material_text(mid) == text


# ── Concurrent access ─────────────────────────────────────────────────────────

class TestConcurrentAccess:

    def test_concurrent_saves_different_ids(self):
        """Multiple threads should be able to save different materials concurrently."""
        errors = []
        ids = [str(uuid.uuid4()) for _ in range(10)]

        def save(mid):
            try:
                save_material_text(mid, f"Content for {mid}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=save, args=(mid,)) for mid in ids]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Concurrent save errors: {errors}"
        # Verify all were saved
        for mid in ids:
            assert load_material_text(mid) is not None

    def test_concurrent_reads(self):
        """Multiple threads reading same material should all succeed."""
        mid = str(uuid.uuid4())
        text = "Shared content " * 1000
        save_material_text(mid, text)

        results = []
        errors = []

        def read():
            try:
                results.append(load_material_text(mid))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=read) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert all(r == text for r in results)


# ── Storage stats ─────────────────────────────────────────────────────────────

class TestStorageStatsAccuracy:

    def test_stats_count_exact(self):
        n = 5
        for _ in range(n):
            save_material_text(str(uuid.uuid4()), "Some content here" * 100)
        stats = get_storage_stats()
        assert stats["file_count"] == n

    def test_stats_size_increases(self):
        mid = str(uuid.uuid4())
        large_text = "X" * 100_000
        save_material_text(mid, large_text)
        stats = get_storage_stats()
        assert stats["total_size_mb"] > 0.09  # > 90 KB

    def test_stats_after_delete_decreases(self):
        mid = str(uuid.uuid4())
        save_material_text(mid, "temp content")
        before = get_storage_stats()["file_count"]
        delete_material_text(mid)
        after = get_storage_stats()["file_count"]
        assert after == before - 1


# ── Material summary integration ──────────────────────────────────────────────

class TestMaterialSummaryIntegration:

    def test_summary_fits_limit(self):
        text = "Important sentence. " * 500
        summary = get_material_summary(text, max_chars=200)
        # Allow for ellipsis and sentence boundary adjustments
        assert len(summary) <= 250

    def test_summary_of_academic_text(self):
        text = (
            "This paper presents a novel approach to transformer-based neural networks. "
            "We demonstrate state-of-the-art performance on multiple benchmarks. "
            "Our method achieves 95% accuracy on the test set. " * 20
        )
        summary = get_material_summary(text, max_chars=500)
        assert len(summary) > 0
        assert "transformer" in summary.lower() or "neural" in summary.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
