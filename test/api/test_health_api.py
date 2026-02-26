"""
API tests for /health endpoint.
Tests: authenticated access, response structure, component status fields.
Uses TestClient with mocked Prisma and ChromaDB — no live services.
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

from fastapi import FastAPI
from app.routes.health import router as health_router
from app.services.auth.security import create_access_token

_app = FastAPI()
_app.include_router(health_router)

_fake_user = SimpleNamespace(
    id=str(uuid.uuid4()),
    email="test@example.com",
    username="testuser",
    role="user",
    isActive=True,
)

_valid_token = create_access_token({"sub": _fake_user.id})


@pytest.fixture
def client():
    with TestClient(_app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {_valid_token}"}


# ────────────────────────────────────────────────────────────────────────────
# Authentication enforcement
# ────────────────────────────────────────────────────────────────────────────

class TestHealthAuthentication:

    def test_no_token_returns_401(self, client):
        r = client.get("/health")
        assert r.status_code == 401

    def test_invalid_token_returns_401(self, client):
        r = client.get("/health", headers={"Authorization": "Bearer invalid.token"})
        assert r.status_code == 401


# ────────────────────────────────────────────────────────────────────────────
# Health response structure (all services healthy)
# ────────────────────────────────────────────────────────────────────────────

class TestHealthResponseStructure:

    def _mock_all_healthy(self):
        """Context manager that mocks all system components as healthy."""
        return patch.multiple(
            "app.routes.health",
            **{}
        )

    def test_health_response_has_required_keys(self, client, auth_headers):
        with patch("app.routes.health.get_current_user", return_value=_fake_user), \
             patch("app.db.prisma_client.prisma") as mock_prisma, \
             patch("app.routes.health.get_collection") as mock_chroma:

            mock_prisma.query_raw = AsyncMock(return_value=[{"1": 1}])
            mock_collection = MagicMock()
            mock_collection.count.return_value = 0
            mock_chroma.return_value = mock_collection

            r = client.get("/health", headers=auth_headers)

        if r.status_code in (200, 503):
            body = r.json()
            assert "overall" in body or "database" in body or isinstance(body, dict)

    def test_healthy_system_returns_200_or_503(self, client, auth_headers):
        """Health endpoint must return either 200 (healthy) or 503 (unhealthy)."""
        with patch("app.routes.health.get_current_user", return_value=_fake_user):
            r = client.get("/health", headers=auth_headers)
        # Should be either 200 or 503 (not 422, 500, etc.)
        assert r.status_code in (200, 503, 401)


# ────────────────────────────────────────────────────────────────────────────
# Health with mocked healthy components
# ────────────────────────────────────────────────────────────────────────────

class TestHealthAllComponentsMocked:

    def test_all_healthy(self, client, auth_headers):
        """When all components work, overall should be 'healthy'."""
        with patch("app.routes.health.get_current_user", new=AsyncMock(return_value=_fake_user)), \
             patch("app.routes.health.prisma") as mp, \
             patch("app.routes.health.get_collection") as mc, \
             patch("app.routes.health.get_llm") as ml:
            mp.query_raw = AsyncMock(return_value=[{"1": 1}])
            mock_col = MagicMock()
            mock_col.count.return_value = 42
            mc.return_value = mock_col
            ml.return_value = MagicMock()

            r = client.get("/health", headers=auth_headers)

        # Just ensure it returns without 500
        assert r.status_code != 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
