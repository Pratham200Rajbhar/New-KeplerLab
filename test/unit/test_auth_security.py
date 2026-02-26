"""
Unit tests for backend/app/services/auth/security.py
Tests: password hashing, JWT token creation/decoding, token types, expiry
All tests are fully independent and use no database or network.
"""

import sys
import os
import time
import pytest
from datetime import timedelta, datetime, timezone

# ── Path setup ──────────────────────────────────────────────────────────────
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

# Provide minimal env vars so Settings validation passes without a real .env
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

from app.services.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_file_token,
    decode_token,
    hash_token,
)


# ────────────────────────────────────────────────────────────────────────────
# Password hashing
# ────────────────────────────────────────────────────────────────────────────

class TestPasswordHashing:
    """Verify bcrypt hash/verify round-trips."""

    def test_hash_returns_nonempty_string(self):
        """hash_password must return a non-empty string."""
        h = hash_password("MySecret1")
        assert isinstance(h, str)
        assert len(h) > 0

    def test_hash_differs_from_plaintext(self):
        """Hash must NOT equal the original password."""
        pw = "MySecret1"
        assert hash_password(pw) != pw

    def test_verify_correct_password(self):
        """Correct password must verify as True."""
        pw = "CorrectPassword9"
        assert verify_password(pw, hash_password(pw)) is True

    def test_verify_wrong_password(self):
        """Wrong password must verify as False."""
        h = hash_password("RightPassword1")
        assert verify_password("WrongPassword1", h) is False

    def test_same_password_different_hashes(self):
        """bcrypt uses random salt — same password → different hashes."""
        pw = "SamePassword1"
        h1 = hash_password(pw)
        h2 = hash_password(pw)
        assert h1 != h2  # different salts

    def test_empty_password_not_verified_against_wrong_hash(self):
        """Empty password should not verify against a real hash."""
        h = hash_password("RealPassword1")
        assert verify_password("", h) is False

    def test_unicode_password(self):
        """Unicode passwords should hash and verify correctly."""
        pw = "Pässwörд1"
        assert verify_password(pw, hash_password(pw)) is True


# ────────────────────────────────────────────────────────────────────────────
# Access token
# ────────────────────────────────────────────────────────────────────────────

class TestAccessToken:
    """JWT access token creation and decoding."""

    def test_creates_access_token(self):
        token = create_access_token({"sub": "user-123"})
        assert isinstance(token, str)
        assert len(token) > 10

    def test_access_token_has_correct_type(self):
        token = create_access_token({"sub": "user-abc"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["type"] == "access"

    def test_access_token_has_sub(self):
        token = create_access_token({"sub": "user-xyz"})
        payload = decode_token(token)
        assert payload["sub"] == "user-xyz"

    def test_access_token_has_jti(self):
        """Each token must have a unique jti (JWT ID)."""
        t1 = create_access_token({"sub": "u1"})
        t2 = create_access_token({"sub": "u1"})
        p1 = decode_token(t1)
        p2 = decode_token(t2)
        assert p1["jti"] != p2["jti"]

    def test_access_token_custom_expiry(self):
        """Token with 1 second expiry should still decode immediately."""
        token = create_access_token({"sub": "u1"}, expires_delta=timedelta(seconds=5))
        payload = decode_token(token)
        assert payload is not None

    def test_expired_access_token_returns_none(self):
        """Token with negative expiry (already expired) should decode to None."""
        token = create_access_token({"sub": "u1"}, expires_delta=timedelta(seconds=-1))
        result = decode_token(token)
        assert result is None


# ────────────────────────────────────────────────────────────────────────────
# Refresh token
# ────────────────────────────────────────────────────────────────────────────

class TestRefreshToken:
    """JWT refresh token creation and decoding."""

    def test_creates_refresh_token(self):
        token = create_refresh_token({"sub": "user-123"})
        assert isinstance(token, str)

    def test_refresh_token_has_correct_type(self):
        token = create_refresh_token({"sub": "user-abc"})
        payload = decode_token(token)
        assert payload["type"] == "refresh"

    def test_refresh_token_has_family(self):
        """Refresh token must include family for rotation tracking."""
        token = create_refresh_token({"sub": "user-abc"}, family="family-1")
        payload = decode_token(token)
        assert payload["family"] == "family-1"

    def test_refresh_token_family_defaults_to_sub(self):
        """If no family given, family defaults to sub."""
        token = create_refresh_token({"sub": "user-test"})
        payload = decode_token(token)
        assert payload["family"] == "user-test"


# ────────────────────────────────────────────────────────────────────────────
# File token
# ────────────────────────────────────────────────────────────────────────────

class TestFileToken:
    """Short-lived file access token tests."""

    def test_creates_file_token(self):
        token = create_file_token("user-123")
        assert isinstance(token, str)

    def test_file_token_has_correct_type(self):
        token = create_file_token("user-123")
        payload = decode_token(token)
        assert payload["type"] == "file"

    def test_file_token_sub_matches_user(self):
        token = create_file_token("user-abc")
        payload = decode_token(token)
        assert payload["sub"] == "user-abc"

    def test_file_token_custom_expiry(self):
        """Token with custom expiry should decode."""
        token = create_file_token("u1", expires_minutes=10)
        payload = decode_token(token)
        assert payload is not None


# ────────────────────────────────────────────────────────────────────────────
# decode_token
# ────────────────────────────────────────────────────────────────────────────

class TestDecodeToken:
    """Edge cases for decode_token."""

    def test_invalid_token_returns_none(self):
        assert decode_token("not.a.token") is None

    def test_empty_string_returns_none(self):
        assert decode_token("") is None

    def test_tampered_token_returns_none(self):
        """Changing one character invalidates the signature."""
        token = create_access_token({"sub": "u1"})
        tampered = token[:-3] + "XXX"
        assert decode_token(tampered) is None

    def test_wrong_secret_returns_none(self):
        """Token signed with different secret should fail."""
        from jose import jwt
        from app.core.config import settings
        token = jwt.encode({"sub": "u1", "exp": 9999999999}, "wrong-secret", algorithm=settings.JWT_ALGORITHM)
        assert decode_token(token) is None


# ────────────────────────────────────────────────────────────────────────────
# hash_token
# ────────────────────────────────────────────────────────────────────────────

class TestHashToken:
    """Deterministic SHA-256 token hash for secure storage."""

    def test_hash_token_is_deterministic(self):
        t = "my-refresh-token-string"
        assert hash_token(t) == hash_token(t)

    def test_hash_token_different_inputs(self):
        assert hash_token("token-a") != hash_token("token-b")

    def test_hash_token_returns_hex_string(self):
        h = hash_token("any-token")
        assert isinstance(h, str)
        # SHA-256 hexdigest = 64 hex chars
        assert len(h) == 64


# ────────────────────────────────────────────────────────────────────────────
# Run directly
# ────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
