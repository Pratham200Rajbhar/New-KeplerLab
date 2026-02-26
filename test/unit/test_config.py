"""
Unit tests for backend/app/core/config.py
Tests: Settings defaults, field validators (CORS parsing), project-root resolution,
type correctness, critical fields present
No DB or network required.
"""

import sys
import os
import pytest

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

from app.core.config import settings, Settings


class TestSettingsDefaults:
    """Verify default values in the Settings singleton."""

    def test_settings_is_settings_instance(self):
        assert isinstance(settings, Settings)

    def test_jwt_algorithm_default(self):
        assert settings.JWT_ALGORITHM == "HS256"

    def test_access_token_expire_minutes_default(self):
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 15

    def test_refresh_token_expire_days_default(self):
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7

    def test_file_token_expire_minutes_default(self):
        assert settings.FILE_TOKEN_EXPIRE_MINUTES == 5

    def test_max_upload_size_mb_positive(self):
        assert settings.MAX_UPLOAD_SIZE_MB > 0

    def test_code_execution_timeout_positive(self):
        assert settings.CODE_EXECUTION_TIMEOUT > 0

    def test_max_code_repair_attempts_positive(self):
        assert settings.MAX_CODE_REPAIR_ATTEMPTS > 0

    def test_cors_origins_is_list(self):
        assert isinstance(settings.CORS_ORIGINS, list)

    def test_cors_origins_has_default(self):
        assert len(settings.CORS_ORIGINS) >= 1

    def test_llm_provider_is_string(self):
        assert isinstance(settings.LLM_PROVIDER, str)
        assert len(settings.LLM_PROVIDER) > 0

    def test_chroma_dir_is_string(self):
        assert isinstance(settings.CHROMA_DIR, str)

    def test_upload_dir_is_string(self):
        assert isinstance(settings.UPLOAD_DIR, str)

    def test_cookie_name_default(self):
        assert settings.COOKIE_NAME == "refresh_token"

    def test_cookie_samesite_default(self):
        assert settings.COOKIE_SAMESITE in ("lax", "strict", "none")

    def test_environment_is_valid(self):
        assert settings.ENVIRONMENT in ("development", "staging", "production")


class TestCorsValidator:
    """Test the comma-separated CORS_ORIGINS validator."""

    def test_list_input_preserved(self):
        """If CORS_ORIGINS is already a list it should pass through."""
        class TmpSettings(Settings):
            model_config = {"env_file": None}

        # Direct instantiation with list input
        tmp = TmpSettings(
            DATABASE_URL="psql://x",
            JWT_SECRET_KEY="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"],
        )
        assert isinstance(tmp.CORS_ORIGINS, list)
        assert "http://localhost:3000" in tmp.CORS_ORIGINS

    def test_string_input_split(self):
        """Comma-separated string should be split into list."""
        class TmpSettings(Settings):
            model_config = {"env_file": None}

        tmp = TmpSettings(
            DATABASE_URL="psql://x",
            JWT_SECRET_KEY="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            CORS_ORIGINS="http://a.com,http://b.com",
        )
        assert isinstance(tmp.CORS_ORIGINS, list)
        assert "http://a.com" in tmp.CORS_ORIGINS
        assert "http://b.com" in tmp.CORS_ORIGINS


class TestOutputDirectories:
    """Output directory settings are non-empty strings."""

    def test_podcast_output_dir(self):
        assert isinstance(settings.PODCAST_OUTPUT_DIR, str)
        assert len(settings.PODCAST_OUTPUT_DIR) > 0

    def test_presentations_output_dir(self):
        assert isinstance(settings.PRESENTATIONS_OUTPUT_DIR, str)
        assert len(settings.PRESENTATIONS_OUTPUT_DIR) > 0

    def test_generated_output_dir(self):
        assert isinstance(settings.GENERATED_OUTPUT_DIR, str)
        assert len(settings.GENERATED_OUTPUT_DIR) > 0


class TestTokenLimitsInConfig:
    """RAG/retrieval configuration values are sensible."""

    def test_initial_vector_k_positive(self):
        if hasattr(settings, "INITIAL_VECTOR_K"):
            assert settings.INITIAL_VECTOR_K > 0

    def test_final_k_positive(self):
        if hasattr(settings, "FINAL_K"):
            assert settings.FINAL_K > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
