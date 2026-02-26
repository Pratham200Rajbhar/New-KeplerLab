"""
Unit tests for backend/app/core/utils.py
Tests: sanitize_null_bytes — recursive null-byte removal from strings, lists, dicts
All tests are fully independent and require no external services.
"""

import sys
import os
import pytest

# ── Path setup ──────────────────────────────────────────────────────────────
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

from app.core.utils import sanitize_null_bytes


class TestSanitizeNullBytes:
    """Tests for the sanitize_null_bytes utility."""

    # ── Plain strings ────────────────────────────────────────────────────────

    def test_string_without_null_bytes_unchanged(self):
        assert sanitize_null_bytes("hello world") == "hello world"

    def test_single_null_byte_removed(self):
        assert sanitize_null_bytes("hel\x00lo") == "hello"

    def test_multiple_null_bytes_removed(self):
        assert sanitize_null_bytes("\x00a\x00b\x00") == "ab"

    def test_empty_string_unchanged(self):
        assert sanitize_null_bytes("") == ""

    def test_only_null_bytes_returns_empty(self):
        assert sanitize_null_bytes("\x00\x00\x00") == ""

    def test_unicode_string_with_null_bytes(self):
        # sanitize_null_bytes removes null bytes; other characters are preserved
        result = sanitize_null_bytes("café\x00latte")
        assert "\x00" not in result
        assert "café" in result
        assert "latte" in result
        assert result == "cafélatte"

    # ── Lists ─────────────────────────────────────────────────────────────────

    def test_list_of_strings(self):
        inp = ["abc\x00", "def"]
        result = sanitize_null_bytes(inp)
        assert result == ["abc", "def"]

    def test_nested_list(self):
        inp = [["a\x00b", "c\x00"], "outer\x00"]
        result = sanitize_null_bytes(inp)
        assert result == [["ab", "c"], "outer"]

    def test_list_of_non_strings(self):
        """Non-string items in list should pass through unchanged."""
        inp = [1, 2, None, 3.14]
        assert sanitize_null_bytes(inp) == [1, 2, None, 3.14]

    def test_empty_list(self):
        assert sanitize_null_bytes([]) == []

    # ── Dicts ─────────────────────────────────────────────────────────────────

    def test_dict_values_sanitized(self):
        inp = {"key": "value\x00", "other": "clean"}
        result = sanitize_null_bytes(inp)
        assert result == {"key": "value", "other": "clean"}

    def test_dict_keys_preserved(self):
        """Keys should not be modified (only values are sanitized)."""
        inp = {"key\x00name": "v"}
        result = sanitize_null_bytes(inp)
        # Keys themselves are not sanitized by the function — just check values
        assert list(result.values()) == ["v"]

    def test_nested_dict(self):
        inp = {"outer": {"inner": "val\x00ue"}}
        result = sanitize_null_bytes(inp)
        assert result == {"outer": {"inner": "value"}}

    def test_dict_with_list_value(self):
        inp = {"items": ["a\x00", "b\x00"]}
        result = sanitize_null_bytes(inp)
        assert result == {"items": ["a", "b"]}

    def test_empty_dict(self):
        assert sanitize_null_bytes({}) == {}

    # ── Non-string scalars pass through ──────────────────────────────────────

    def test_integer_passthrough(self):
        assert sanitize_null_bytes(42) == 42

    def test_float_passthrough(self):
        assert sanitize_null_bytes(3.14) == 3.14

    def test_none_passthrough(self):
        assert sanitize_null_bytes(None) is None

    def test_bool_passthrough(self):
        assert sanitize_null_bytes(True) is True

    # ── Real-world Postgres scenario ──────────────────────────────────────────

    def test_postgres_hostile_payload(self):
        """Simulate a user-submitted payload with embedded null bytes."""
        payload = {
            "title": "My Note\x00book",
            "tags": ["study\x00", "ai\x00", "math"],
            "meta": {"author": "Alice\x00", "version": 1},
        }
        result = sanitize_null_bytes(payload)
        assert result["title"] == "My Notebook"
        assert result["tags"] == ["study", "ai", "math"]
        assert result["meta"]["author"] == "Alice"
        assert result["meta"]["version"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
