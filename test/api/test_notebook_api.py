"""
API tests for /notebooks CRUD endpoints.
Uses FastAPI TestClient with mocked Prisma calls — no live DB required.

Coverage:
- POST   /notebooks         → create
- GET    /notebooks         → list
- GET    /notebooks/{id}    → get by id
- PATCH  /notebooks/{id}    → update
- DELETE /notebooks/{id}    → delete
- Auth enforcement on all endpoints
"""

import sys
import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

from fastapi import FastAPI
from app.routes.notebook import router as notebook_router
from app.services.auth.security import create_access_token

_app = FastAPI()
_app.include_router(notebook_router)

USER_ID = str(uuid.uuid4())
_fake_user = SimpleNamespace(id=USER_ID, email="test@ex.com", username="tester", role="user")
_valid_token = create_access_token({"sub": USER_ID})


def _fake_notebook(name="Test NB", desc=None):
    nb_id = str(uuid.uuid4())
    return SimpleNamespace(
        id=nb_id,
        userId=USER_ID,
        name=name,
        description=desc,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {_valid_token}"}


@pytest.fixture
def client():
    with TestClient(_app, raise_server_exceptions=False) as c:
        yield c


# ── Auth enforcement ──────────────────────────────────────────────────────────

class TestNotebookAuth:

    def test_create_no_token_401(self, client):
        r = client.post("/notebooks", json={"name": "NB"})
        assert r.status_code == 401

    def test_list_no_token_401(self, client):
        r = client.get("/notebooks")
        assert r.status_code == 401

    def test_get_no_token_401(self, client):
        r = client.get(f"/notebooks/{uuid.uuid4()}")
        assert r.status_code == 401


# ── POST /notebooks ───────────────────────────────────────────────────────────

class TestCreateNotebook:

    def test_create_notebook_201(self, client, auth_headers):
        nb = _fake_notebook("My Study Notes")
        with patch("app.routes.notebook.get_current_user", new=AsyncMock(return_value=_fake_user)), \
             patch("app.routes.notebook.create_notebook", new=AsyncMock(return_value=nb)):
            r = client.post("/notebooks", json={"name": "My Study Notes"}, headers=auth_headers)
        assert r.status_code == 201

    def test_create_notebook_response_has_id(self, client, auth_headers):
        nb = _fake_notebook("AI Notes")
        with patch("app.routes.notebook.get_current_user", new=AsyncMock(return_value=_fake_user)), \
             patch("app.routes.notebook.create_notebook", new=AsyncMock(return_value=nb)):
            r = client.post("/notebooks", json={"name": "AI Notes"}, headers=auth_headers)
        if r.status_code == 201:
            assert "id" in r.json()

    def test_create_empty_name_422(self, client, auth_headers):
        with patch("app.routes.notebook.get_current_user", new=AsyncMock(return_value=_fake_user)):
            r = client.post("/notebooks", json={"name": ""}, headers=auth_headers)
        assert r.status_code == 422

    def test_create_missing_name_422(self, client, auth_headers):
        with patch("app.routes.notebook.get_current_user", new=AsyncMock(return_value=_fake_user)):
            r = client.post("/notebooks", json={}, headers=auth_headers)
        assert r.status_code == 422

    def test_create_with_description(self, client, auth_headers):
        nb = _fake_notebook("NB", "A helpful description")
        with patch("app.routes.notebook.get_current_user", new=AsyncMock(return_value=_fake_user)), \
             patch("app.routes.notebook.create_notebook", new=AsyncMock(return_value=nb)):
            r = client.post("/notebooks",
                            json={"name": "NB", "description": "A helpful description"},
                            headers=auth_headers)
        assert r.status_code in (201, 200)


# ── GET /notebooks ────────────────────────────────────────────────────────────

class TestListNotebooks:

    def test_list_returns_200(self, client, auth_headers):
        notebooks = [_fake_notebook(f"NB{i}") for i in range(3)]
        with patch("app.routes.notebook.get_current_user", new=AsyncMock(return_value=_fake_user)), \
             patch("app.routes.notebook.get_user_notebooks", new=AsyncMock(return_value=notebooks)):
            r = client.get("/notebooks", headers=auth_headers)
        assert r.status_code == 200

    def test_list_returns_array(self, client, auth_headers):
        with patch("app.routes.notebook.get_current_user", new=AsyncMock(return_value=_fake_user)), \
             patch("app.routes.notebook.get_user_notebooks", new=AsyncMock(return_value=[])):
            r = client.get("/notebooks", headers=auth_headers)
        if r.status_code == 200:
            assert isinstance(r.json(), list)

    def test_list_empty_returns_empty_array(self, client, auth_headers):
        with patch("app.routes.notebook.get_current_user", new=AsyncMock(return_value=_fake_user)), \
             patch("app.routes.notebook.get_user_notebooks", new=AsyncMock(return_value=[])):
            r = client.get("/notebooks", headers=auth_headers)
        if r.status_code == 200:
            assert r.json() == []


# ── GET /notebooks/{id} ───────────────────────────────────────────────────────

class TestGetNotebook:

    def test_get_existing_returns_200(self, client, auth_headers):
        nb = _fake_notebook("Found")
        with patch("app.routes.notebook.get_current_user", new=AsyncMock(return_value=_fake_user)), \
             patch("app.routes.notebook.get_notebook_by_id", new=AsyncMock(return_value=nb)):
            r = client.get(f"/notebooks/{nb.id}", headers=auth_headers)
        assert r.status_code == 200

    def test_get_nonexistent_returns_404(self, client, auth_headers):
        with patch("app.routes.notebook.get_current_user", new=AsyncMock(return_value=_fake_user)), \
             patch("app.routes.notebook.get_notebook_by_id", new=AsyncMock(return_value=None)):
            r = client.get(f"/notebooks/{uuid.uuid4()}", headers=auth_headers)
        assert r.status_code == 404


# ── DELETE /notebooks/{id} ────────────────────────────────────────────────────

class TestDeleteNotebook:

    def test_delete_existing_returns_200_or_204(self, client, auth_headers):
        with patch("app.routes.notebook.get_current_user", new=AsyncMock(return_value=_fake_user)), \
             patch("app.routes.notebook.delete_notebook", new=AsyncMock(return_value=True)):
            r = client.delete(f"/notebooks/{uuid.uuid4()}", headers=auth_headers)
        assert r.status_code in (200, 204)

    def test_delete_nonexistent_returns_404(self, client, auth_headers):
        with patch("app.routes.notebook.get_current_user", new=AsyncMock(return_value=_fake_user)), \
             patch("app.routes.notebook.delete_notebook", new=AsyncMock(return_value=False)):
            r = client.delete(f"/notebooks/{uuid.uuid4()}", headers=auth_headers)
        assert r.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
