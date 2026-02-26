"""
Unit tests for backend/app/services/text_processing/file_detector.py
Tests: SUPPORTED_TYPES coverage, MIME-to-extension mapping, category assignments
No file system or network required.
"""

import sys
import os
import pytest

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

from app.services.text_processing.file_detector import FileTypeDetector


DETECTOR = FileTypeDetector()


class TestSupportedTypesMapping:
    """Verify the SUPPORTED_TYPES coverage and correctness."""

    def test_pdf_supported(self):
        assert "application/pdf" in FileTypeDetector.SUPPORTED_TYPES

    def test_pdf_maps_to_pdf(self):
        assert FileTypeDetector.SUPPORTED_TYPES["application/pdf"] == "pdf"

    def test_docx_supported(self):
        assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in FileTypeDetector.SUPPORTED_TYPES

    def test_xlsx_supported(self):
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in FileTypeDetector.SUPPORTED_TYPES

    def test_pptx_supported(self):
        assert "application/vnd.openxmlformats-officedocument.presentationml.presentation" in FileTypeDetector.SUPPORTED_TYPES

    def test_plain_text_supported(self):
        assert "text/plain" in FileTypeDetector.SUPPORTED_TYPES

    def test_csv_supported(self):
        assert "text/csv" in FileTypeDetector.SUPPORTED_TYPES

    def test_mp3_supported(self):
        assert "audio/mpeg" in FileTypeDetector.SUPPORTED_TYPES

    def test_mp4_supported(self):
        assert "video/mp4" in FileTypeDetector.SUPPORTED_TYPES

    def test_jpg_supported(self):
        assert "image/jpeg" in FileTypeDetector.SUPPORTED_TYPES

    def test_png_supported(self):
        assert "image/png" in FileTypeDetector.SUPPORTED_TYPES

    def test_epub_supported(self):
        assert "application/epub+zip" in FileTypeDetector.SUPPORTED_TYPES

    def test_markdown_supported(self):
        assert "text/markdown" in FileTypeDetector.SUPPORTED_TYPES

    def test_all_extensions_lowercase(self):
        """All extension values should be lowercase (no '.PDF')."""
        for mime, ext in FileTypeDetector.SUPPORTED_TYPES.items():
            assert ext == ext.lower(), f"Extension for {mime!r} is not lowercase: {ext!r}"

    def test_all_extension_nonempty(self):
        for mime, ext in FileTypeDetector.SUPPORTED_TYPES.items():
            assert len(ext) > 0, f"Empty extension for MIME: {mime!r}"

    def test_no_dot_prefix_in_extensions(self):
        """Extensions should NOT include a leading dot."""
        for mime, ext in FileTypeDetector.SUPPORTED_TYPES.items():
            assert not ext.startswith("."), f"Extension has leading dot: {ext!r}"

    def test_unique_mimes(self):
        """All MIME keys should be unique (dict guarantees this but let's be explicit)."""
        mimes = list(FileTypeDetector.SUPPORTED_TYPES.keys())
        assert len(mimes) == len(set(mimes))


class TestFileTypeDetectorInstantiation:

    def test_detector_instantiates(self):
        d = FileTypeDetector()
        assert d is not None

    def test_supported_types_is_dict(self):
        assert isinstance(FileTypeDetector.SUPPORTED_TYPES, dict)

    def test_supported_types_nonempty(self):
        assert len(FileTypeDetector.SUPPORTED_TYPES) > 20


class TestCategoryGroupings:
    """Check that each media category is represented."""

    def test_documents_present(self):
        doc_mimes = [m for m in FileTypeDetector.SUPPORTED_TYPES if "pdf" in m or "word" in m]
        assert len(doc_mimes) >= 1

    def test_audio_present(self):
        audio_mimes = [m for m in FileTypeDetector.SUPPORTED_TYPES if m.startswith("audio/")]
        assert len(audio_mimes) >= 3

    def test_video_present(self):
        video_mimes = [m for m in FileTypeDetector.SUPPORTED_TYPES if m.startswith("video/")]
        assert len(video_mimes) >= 3

    def test_images_present(self):
        image_mimes = [m for m in FileTypeDetector.SUPPORTED_TYPES if m.startswith("image/")]
        assert len(image_mimes) >= 4

    def test_spreadsheets_present(self):
        sheet_mimes = [m for m in FileTypeDetector.SUPPORTED_TYPES if "spreadsheet" in m or "excel" in m or m == "text/csv"]
        assert len(sheet_mimes) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
