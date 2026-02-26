"""
Unit tests for backend/app/services/storage_service.py
Tests: save/load/delete material text, UUID validation, path safety,
storage stats, filename sanitization
Uses a temporary directory — no live DB or ChromaDB needed.
"""

import sys
import os
import uuid
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

import app.services.storage_service as _svc


@pytest.fixture(autouse=True)
def temp_storage_dir(tmp_path):
    """Redirect all storage operations to a temp dir for isolation."""
    with patch.object(_svc, "MATERIAL_TEXT_DIR", tmp_path):
        yield tmp_path


from app.services.storage_service import (
    save_material_text,
    load_material_text,
    delete_material_text,
    get_material_summary,
    get_storage_stats,
)


# ────────────────────────────────────────────────────────────────────────────
# save_material_text
# ────────────────────────────────────────────────────────────────────────────

class TestSaveMaterialText:

    def test_save_returns_true(self):
        mid = str(uuid.uuid4())
        result = save_material_text(mid, "Hello world content")
        assert result is True

    def test_save_creates_file(self, temp_storage_dir):
        mid = str(uuid.uuid4())
        save_material_text(mid, "Test content")
        assert (temp_storage_dir / f"{mid}.txt").exists()

    def test_save_writes_correct_content(self, temp_storage_dir):
        mid = str(uuid.uuid4())
        text = "The quick brown fox jumps over the lazy dog."
        save_material_text(mid, text)
        written = (temp_storage_dir / f"{mid}.txt").read_text(encoding="utf-8")
        assert written == text

    def test_save_unicode_content(self):
        mid = str(uuid.uuid4())
        text = "日本語テスト\nкирилица\n한국어"
        assert save_material_text(mid, text) is True

    def test_save_empty_content(self):
        mid = str(uuid.uuid4())
        result = save_material_text(mid, "")
        assert result is True

    def test_save_invalid_uuid_returns_false(self):
        result = save_material_text("not-a-uuid", "content")
        assert result is False

    def test_save_path_traversal_rejected(self):
        result = save_material_text("../../etc/passwd", "evil")
        assert result is False


# ────────────────────────────────────────────────────────────────────────────
# load_material_text
# ────────────────────────────────────────────────────────────────────────────

class TestLoadMaterialText:

    def test_load_returns_saved_content(self):
        mid = str(uuid.uuid4())
        text = "Saved content for loading"
        save_material_text(mid, text)
        loaded = load_material_text(mid)
        assert loaded == text

    def test_load_nonexistent_returns_none(self):
        mid = str(uuid.uuid4())
        assert load_material_text(mid) is None

    def test_load_invalid_uuid_returns_none(self):
        assert load_material_text("not-a-uuid") is None

    def test_load_after_delete_returns_none(self):
        mid = str(uuid.uuid4())
        save_material_text(mid, "temporary")
        delete_material_text(mid)
        assert load_material_text(mid) is None

    def test_load_large_content(self):
        mid = str(uuid.uuid4())
        text = "A" * 100_000
        save_material_text(mid, text)
        loaded = load_material_text(mid)
        assert len(loaded) == 100_000


# ────────────────────────────────────────────────────────────────────────────
# delete_material_text
# ────────────────────────────────────────────────────────────────────────────

class TestDeleteMaterialText:

    def test_delete_existing_returns_true(self):
        mid = str(uuid.uuid4())
        save_material_text(mid, "to be deleted")
        assert delete_material_text(mid) is True

    def test_delete_removes_file(self, temp_storage_dir):
        mid = str(uuid.uuid4())
        save_material_text(mid, "content")
        delete_material_text(mid)
        assert not (temp_storage_dir / f"{mid}.txt").exists()

    def test_delete_nonexistent_returns_false(self):
        mid = str(uuid.uuid4())
        assert delete_material_text(mid) is False

    def test_delete_invalid_uuid_returns_false(self):
        assert delete_material_text("../../evil") is False

    def test_double_delete_second_returns_false(self):
        mid = str(uuid.uuid4())
        save_material_text(mid, "content")
        delete_material_text(mid)
        assert delete_material_text(mid) is False


# ────────────────────────────────────────────────────────────────────────────
# get_material_summary
# ────────────────────────────────────────────────────────────────────────────

class TestGetMaterialSummary:

    def test_short_text_returned_as_is(self):
        text = "Short text."
        result = get_material_summary(text, max_chars=1000)
        assert result == text

    def test_long_text_truncated(self):
        text = "word " * 500
        result = get_material_summary(text, max_chars=100)
        assert len(result) <= 120  # allow small overrun for sentence boundary

    def test_truncated_ends_with_ellipsis(self):
        text = "Hello world. " * 100
        result = get_material_summary(text, max_chars=50)
        assert result.endswith("...")

    def test_empty_text_returns_empty(self):
        assert get_material_summary("") == ""

    def test_none_like_empty(self):
        assert get_material_summary("") == ""


# ────────────────────────────────────────────────────────────────────────────
# get_storage_stats
# ────────────────────────────────────────────────────────────────────────────

class TestGetStorageStats:

    def test_empty_dir_returns_zero_count(self, temp_storage_dir):
        stats = get_storage_stats()
        assert stats["file_count"] == 0

    def test_count_matches_saved_files(self):
        for _ in range(3):
            save_material_text(str(uuid.uuid4()), "content")
        stats = get_storage_stats()
        assert stats["file_count"] == 3

    def test_stats_has_required_keys(self):
        stats = get_storage_stats()
        assert "file_count" in stats
        assert "total_size_mb" in stats

    def test_total_size_increases(self):
        save_material_text(str(uuid.uuid4()), "A" * 10_000)
        stats = get_storage_stats()
        assert stats["total_size_mb"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
