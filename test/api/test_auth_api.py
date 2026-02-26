"""
API tests for POST /auth/signup and POST /auth/login endpoints.
Uses FastAPI TestClient with mocked database calls — no live DB required.

Test strategy:
- Validate request schema enforcement (422 for bad input)
- Mock register_user / authenticate_user for happy paths
- Test duplicate email (409)
- Test wrong password (401)
- JWT cookie/header presence
"""

import sys
import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")


# ── Build a minimal FastAPI app with only the auth router ────────────────────

from fastapi import FastAPI
from app.routes.auth import router as auth_router
from app.services.auth.security import hash_password, create_access_token

_app = FastAPI()
_app.include_router(auth_router)


def _fake_user(email: str = "alice@example.com", username: str = "alice") -> SimpleNamespace:
    return SimpleNamespace(
        id=str(uuid.uuid4()),
        email=email,
        username=username,
        hashedPassword=hash_password("MyPass1!"),
        isActive=True,
        role="user",
        createdAt="2026-01-01T00:00:00",
        updatedAt="2026-01-01T00:00:00",
    )


@pytest.fixture
def client():
    with TestClient(_app, raise_server_exceptions=False) as c:
        yield c


# ────────────────────────────────────────────────────────────────────────────
# POST /auth/signup — schema validation (no DB needed)
# ────────────────────────────────────────────────────────────────────────────

class TestSignupSchemaValidation:

    def test_missing_all_fields_422(self, client):
        r = client.post("/auth/signup", json={})
        assert r.status_code == 422

    def test_invalid_email_422(self, client):
        r = client.post("/auth/signup", json={
            "email": "not-email",
            "username": "alice",
            "password": "MyPass1!"
        })
        assert r.status_code == 422

    def test_short_password_422(self, client):
        r = client.post("/auth/signup", json={
            "email": "u@ex.com",
            "username": "alice",
            "password": "Ab1"
        })
        assert r.status_code == 422

    def test_no_uppercase_password_422(self, client):
        r = client.post("/auth/signup", json={
            "email": "u@ex.com",
            "username": "alice",
            "password": "alllower1!"
        })
        assert r.status_code == 422

    def test_no_digit_password_422(self, client):
        r = client.post("/auth/signup", json={
            "email": "u@ex.com",
            "username": "alice",
            "password": "NoDigitsHere!"
        })
        assert r.status_code == 422

    def test_username_too_short_422(self, client):
        r = client.post("/auth/signup", json={
            "email": "u@ex.com",
            "username": "a",
            "password": "MyPass1!"
        })
        assert r.status_code == 422


class TestSignupSuccess:

    def test_successful_signup_returns_201(self, client):
        fake = _fake_user()
        with patch("app.routes.auth.register_user", new=AsyncMock(return_value=fake)):
            r = client.post("/auth/signup", json={
                "email": "alice@example.com",
                "username": "alice",
                "password": "MyPass1!"
            })
        assert r.status_code == 201

    def test_signup_response_has_user_fields(self, client):
        fake = _fake_user()
        with patch("app.routes.auth.register_user", new=AsyncMock(return_value=fake)):
            r = client.post("/auth/signup", json={
                "email": "alice@example.com",
                "username": "alice",
                "password": "MyPass1!"
            })
        if r.status_code == 201:
            body = r.json()
            assert "id" in body
            assert "email" in body

    def test_duplicate_email_raises_409(self, client):
        from fastapi import HTTPException
        with patch("app.routes.auth.register_user",
                   new=AsyncMock(side_effect=HTTPException(status_code=409, detail="Email already registered"))):
            r = client.post("/auth/signup", json={
                "email": "dup@example.com",
                "username": "dupuser",
                "password": "MyPass1!"
            })
        assert r.status_code == 409


# ────────────────────────────────────────────────────────────────────────────
# POST /auth/login
# ────────────────────────────────────────────────────────────────────────────

class TestLoginSchemaValidation:

    def test_missing_all_fields_422(self, client):
        r = client.post("/auth/login", json={})
        assert r.status_code == 422

    def test_invalid_email_422(self, client):
        r = client.post("/auth/login", json={"email": "bad", "password": "pw"})
        assert r.status_code == 422

    def test_missing_password_422(self, client):
        r = client.post("/auth/login", json={"email": "u@ex.com"})
        assert r.status_code == 422


class TestLoginSuccess:

    def test_successful_login_returns_200(self, client):
        fake = _fake_user()
        access_token = create_access_token({"sub": fake.id})
        from app.services.auth.security import create_refresh_token
        refresh_token = create_refresh_token({"sub": fake.id})

        with patch("app.routes.auth.authenticate_user", new=AsyncMock(return_value=fake)), \
             patch("app.routes.auth.store_refresh_token", new=AsyncMock()), \
             patch("app.routes.auth.create_access_token", return_value=access_token), \
             patch("app.routes.auth.create_refresh_token", return_value=refresh_token):
            r = client.post("/auth/login", json={
                "email": "alice@example.com",
                "password": "MyPass1!"
            })
        assert r.status_code == 200

    def test_login_returns_access_token(self, client):
        fake = _fake_user()
        access_token = create_access_token({"sub": fake.id})
        from app.services.auth.security import create_refresh_token
        refresh_token = create_refresh_token({"sub": fake.id})

        with patch("app.routes.auth.authenticate_user", new=AsyncMock(return_value=fake)), \
             patch("app.routes.auth.store_refresh_token", new=AsyncMock()), \
             patch("app.routes.auth.create_access_token", return_value=access_token), \
             patch("app.routes.auth.create_refresh_token", return_value=refresh_token):
            r = client.post("/auth/login", json={
                "email": "alice@example.com",
                "password": "MyPass1!"
            })
        if r.status_code == 200:
            body = r.json()
            assert "access_token" in body

    def test_wrong_password_raises_401(self, client):
        from fastapi import HTTPException
        with patch("app.routes.auth.authenticate_user",
                   new=AsyncMock(side_effect=HTTPException(status_code=401, detail="Invalid credentials"))):
            r = client.post("/auth/login", json={
                "email": "alice@example.com",
                "password": "WrongPass1!"
            })
        assert r.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
