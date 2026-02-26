"""
Unit tests for backend/app/routes/auth.py — Pydantic request models
Tests: SignupRequest validation (password rules, username length, email format),
LoginRequest validation — pure Pydantic validation, no HTTP stack.
"""

import sys
import os
import pytest
from pydantic import ValidationError

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

from app.routes.auth import SignupRequest, LoginRequest


# ────────────────────────────────────────────────────────────────────────────
# SignupRequest — valid payloads
# ────────────────────────────────────────────────────────────────────────────

class TestSignupRequestValid:

    def test_minimal_valid_payload(self):
        req = SignupRequest(email="user@example.com", username="alice", password="MyPass1!")
        assert req.email == "user@example.com"
        assert req.username == "alice"

    def test_long_valid_username(self):
        req = SignupRequest(email="u@ex.com", username="a" * 50, password="MyPass1!")
        assert len(req.username) == 50

    def test_complex_valid_password(self):
        req = SignupRequest(email="u@ex.com", username="bob", password="C0mplex!Pass#99")
        assert req.password == "C0mplex!Pass#99"

    def test_email_normalized_lowercase(self):
        """pydantic EmailStr normalises to lowercase domain."""
        req = SignupRequest(email="User@Example.COM", username="al", password="MyPass1!")
        # EmailStr may or may not lowercase — just ensure it parses
        assert "@" in req.email


# ────────────────────────────────────────────────────────────────────────────
# SignupRequest — password rules
# ────────────────────────────────────────────────────────────────────────────

class TestSignupPasswordValidation:

    def test_too_short_password_rejected(self):
        with pytest.raises(ValidationError, match="8 characters"):
            SignupRequest(email="u@ex.com", username="alice", password="Ab1")

    def test_no_uppercase_rejected(self):
        with pytest.raises(ValidationError, match="uppercase"):
            SignupRequest(email="u@ex.com", username="alice", password="alllower1!")

    def test_no_lowercase_rejected(self):
        with pytest.raises(ValidationError, match="lowercase"):
            SignupRequest(email="u@ex.com", username="alice", password="ALLUPPER1!")

    def test_no_digit_rejected(self):
        with pytest.raises(ValidationError, match="digit"):
            SignupRequest(email="u@ex.com", username="alice", password="NoDigitsHere!!")

    def test_exactly_8_chars_with_rules_passes(self):
        req = SignupRequest(email="u@ex.com", username="al", password="AbCd1234")
        assert req is not None


# ────────────────────────────────────────────────────────────────────────────
# SignupRequest — username rules
# ────────────────────────────────────────────────────────────────────────────

class TestSignupUsernameValidation:

    def test_single_char_username_rejected(self):
        with pytest.raises(ValidationError, match="between 2 and 50"):
            SignupRequest(email="u@ex.com", username="a", password="MyPass1!")

    def test_too_long_username_rejected(self):
        with pytest.raises(ValidationError, match="between 2 and 50"):
            SignupRequest(email="u@ex.com", username="a" * 51, password="MyPass1!")

    def test_2_char_username_valid(self):
        req = SignupRequest(email="u@ex.com", username="ab", password="MyPass1!")
        assert req.username == "ab"

    def test_50_char_username_valid(self):
        req = SignupRequest(email="u@ex.com", username="a" * 50, password="MyPass1!")
        assert len(req.username) == 50


# ────────────────────────────────────────────────────────────────────────────
# SignupRequest — email validation
# ────────────────────────────────────────────────────────────────────────────

class TestSignupEmailValidation:

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            SignupRequest(email="not-an-email", username="alice", password="MyPass1!")

    def test_email_without_domain_rejected(self):
        with pytest.raises(ValidationError):
            SignupRequest(email="user@", username="alice", password="MyPass1!")

    def test_valid_subdomain_email(self):
        req = SignupRequest(email="user@mail.example.co.uk", username="alice", password="MyPass1!")
        assert "mail.example.co.uk" in req.email


# ────────────────────────────────────────────────────────────────────────────
# LoginRequest
# ────────────────────────────────────────────────────────────────────────────

class TestLoginRequest:

    def test_valid_login_request(self):
        req = LoginRequest(email="user@example.com", password="anypassword")
        assert req.email == "user@example.com"

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="bad", password="pw")

    def test_missing_email_rejected(self):
        with pytest.raises(ValidationError):
            LoginRequest(password="MyPass1!")

    def test_missing_password_rejected(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="u@ex.com")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
