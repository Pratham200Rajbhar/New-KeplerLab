"""
Unit tests for backend/app/services/file_validator.py
Tests: file size validation, executable detection, filename sanitization,
path traversal prevention, MIME type blocking
No network or DB required.
"""

import sys
import os
import tempfile
import pytest
from pathlib import Path

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

from app.services.file_validator import (
    validate_file_size,
    sanitize_filename,
    generate_internal_filename,
    FileValidationError,
    BLOCKED_EXTENSIONS,
    BLOCKED_MIME_TYPES,
    MAX_FILE_SIZE,
)


# ────────────────────────────────────────────────────────────────────────────
# File size validation
# ────────────────────────────────────────────────────────────────────────────

class TestFileSizeValidation:

    def test_normal_size_passes(self):
        """1 MB should pass (default limit is 25 MB)."""
        validate_file_size(1 * 1024 * 1024)  # no exception

    def test_zero_size_rejected(self):
        with pytest.raises(FileValidationError, match="empty"):
            validate_file_size(0)

    def test_exceeds_limit_rejected(self):
        too_large = MAX_FILE_SIZE + 1
        with pytest.raises(FileValidationError, match="too large|exceeds"):
            validate_file_size(too_large)

    def test_exactly_at_limit_passes(self):
        """Exactly at the limit should pass (boundary condition)."""
        validate_file_size(MAX_FILE_SIZE)  # no exception

    def test_one_byte_passes(self):
        validate_file_size(1)  # no exception


# ────────────────────────────────────────────────────────────────────────────
# Filename sanitization
# ────────────────────────────────────────────────────────────────────────────

class TestSanitizeFilename:

    def test_normal_filename_unchanged_structure(self):
        result = sanitize_filename("document.pdf")
        assert "document" in result
        assert ".pdf" in result

    def test_path_traversal_stripped(self):
        """Path components must be stripped."""
        result = sanitize_filename("../../etc/passwd")
        assert "/" not in result
        assert ".." not in result

    def test_null_bytes_removed(self):
        result = sanitize_filename("file\x00name.pdf")
        assert "\x00" not in result

    def test_double_dot_rejected(self):
        # Path.name strips the '../' prefix, so '../secret.txt' becomes 'secret.txt'
        # — the traversal is neutralised by design. The result must be safe.
        result = sanitize_filename("../secret.txt")
        assert ".." not in result
        assert "/" not in result

    def test_backslash_path_traversal(self):
        with pytest.raises(FileValidationError):
            sanitize_filename("..\\secret.txt")

    def test_long_filename_truncated(self):
        long_name = "a" * 300 + ".pdf"
        result = sanitize_filename(long_name)
        assert len(result) <= 255

    def test_special_chars_replaced(self):
        """Special characters should be replaced with underscores."""
        result = sanitize_filename("my file (v2)!.pdf")
        assert "(" not in result
        assert "!" not in result

    def test_empty_filename_rejected(self):
        with pytest.raises(FileValidationError):
            sanitize_filename("")

    def test_windows_path_with_backslash_raises(self):
        # On Linux, 'C:\Users\admin\secret.pdf' is treated as a single filename
        # containing '\\' which triggers path traversal detection.
        with pytest.raises(FileValidationError):
            sanitize_filename("C:\\Users\\admin\\secret.pdf")

    def test_unicode_filename_sanitized(self):
        """Unicode filenames should not crash the sanitizer."""
        result = sanitize_filename("文件名.pdf")
        assert isinstance(result, str)
        assert len(result) > 0


# ────────────────────────────────────────────────────────────────────────────
# Internal filename generation
# ────────────────────────────────────────────────────────────────────────────

class TestGenerateInternalFilename:

    def test_returns_tuple(self):
        name, ext = generate_internal_filename("report.pdf")
        assert isinstance(name, str)
        assert isinstance(ext, str)

    def test_extension_preserved(self):
        _, ext = generate_internal_filename("report.pdf")
        assert ext == ".pdf"

    def test_internal_name_unique(self):
        """Two calls must produce different internal names."""
        n1, _ = generate_internal_filename("file.pdf")
        n2, _ = generate_internal_filename("file.pdf")
        assert n1 != n2

    def test_internal_name_has_extension(self):
        name, ext = generate_internal_filename("doc.docx")
        assert name.endswith(".docx")

    def test_original_name_not_exposed(self):
        """Internal filename should not contain the original filename."""
        name, _ = generate_internal_filename("mysecretfile.pdf")
        assert "mysecretfile" not in name


# ────────────────────────────────────────────────────────────────────────────
# Blocked extensions set
# ────────────────────────────────────────────────────────────────────────────

class TestBlockedSets:

    def test_exe_in_blocked_extensions(self):
        assert ".exe" in BLOCKED_EXTENSIONS

    def test_sh_in_blocked_extensions(self):
        assert ".sh" in BLOCKED_EXTENSIONS

    def test_pdf_not_blocked(self):
        assert ".pdf" not in BLOCKED_EXTENSIONS

    def test_docx_not_blocked(self):
        assert ".docx" not in BLOCKED_EXTENSIONS

    def test_dll_in_blocked_extensions(self):
        assert ".dll" in BLOCKED_EXTENSIONS

    def test_executable_mime_blocked(self):
        assert "application/x-executable" in BLOCKED_MIME_TYPES

    def test_pe_exe_mime_blocked(self):
        assert "application/x-dosexec" in BLOCKED_MIME_TYPES

    def test_jar_mime_blocked(self):
        assert "application/java-archive" in BLOCKED_MIME_TYPES

    def test_pdf_mime_not_blocked(self):
        assert "application/pdf" not in BLOCKED_MIME_TYPES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
