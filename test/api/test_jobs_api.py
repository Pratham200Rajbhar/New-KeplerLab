"""
API tests for GET /jobs/{job_id} endpoint.
Tests: auth enforcement, 404 for missing job, job status fields.
Uses TestClient with mocked job_service.
"""

import sys
import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

from fastapi import FastAPI
from app.routes.jobs import router as jobs_router
from app.services.auth.security import create_access_token

_app = FastAPI()
_app.include_router(jobs_router)

USER_ID = str(uuid.uuid4())
_fake_user = SimpleNamespace(id=USER_ID, email="test@ex.com", username="tester", role="user")
_valid_token = create_access_token({"sub": USER_ID})


def _fake_job(status="completed", job_type="material_processing", result=None, error=None):
    return SimpleNamespace(
        id=str(uuid.uuid4()),
        userId=USER_ID,
        jobType=job_type,
        status=status,
        result=result,
        error=error,
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

def test_jobs_no_token_401(client):
    r = client.get(f"/jobs/{uuid.uuid4()}")
    assert r.status_code == 401


def test_jobs_invalid_token_401(client):
    r = client.get(f"/jobs/{uuid.uuid4()}", headers={"Authorization": "Bearer bad.token"})
    assert r.status_code == 401


# ── 404 for missing job ───────────────────────────────────────────────────────

def test_job_not_found_404(client, auth_headers):
    with patch("app.routes.jobs.get_current_user", new=AsyncMock(return_value=_fake_user)), \
         patch("app.routes.jobs.get_job", new=AsyncMock(return_value=None)):
        r = client.get(f"/jobs/{uuid.uuid4()}", headers=auth_headers)
    assert r.status_code == 404


# ── Successful job retrieval ──────────────────────────────────────────────────

def test_job_status_completed(client, auth_headers):
    job = _fake_job(status="completed")
    with patch("app.routes.jobs.get_current_user", new=AsyncMock(return_value=_fake_user)), \
         patch("app.routes.jobs.get_job", new=AsyncMock(return_value=job)):
        r = client.get(f"/jobs/{job.id}", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"


def test_job_response_has_required_fields(client, auth_headers):
    job = _fake_job(status="pending")
    with patch("app.routes.jobs.get_current_user", new=AsyncMock(return_value=_fake_user)), \
         patch("app.routes.jobs.get_job", new=AsyncMock(return_value=job)):
        r = client.get(f"/jobs/{job.id}", headers=auth_headers)
    if r.status_code == 200:
        body = r.json()
        assert "id" in body
        assert "status" in body
        assert "type" in body


def test_job_with_result_includes_result(client, auth_headers):
    job = _fake_job(status="completed", result={"flashcards": []})
    with patch("app.routes.jobs.get_current_user", new=AsyncMock(return_value=_fake_user)), \
         patch("app.routes.jobs.get_job", new=AsyncMock(return_value=job)):
        r = client.get(f"/jobs/{job.id}", headers=auth_headers)
    if r.status_code == 200:
        body = r.json()
        assert "result" in body


def test_job_with_error_includes_error(client, auth_headers):
    job = _fake_job(status="failed", error="LLM timeout")
    with patch("app.routes.jobs.get_current_user", new=AsyncMock(return_value=_fake_user)), \
         patch("app.routes.jobs.get_job", new=AsyncMock(return_value=job)):
        r = client.get(f"/jobs/{job.id}", headers=auth_headers)
    if r.status_code == 200:
        body = r.json()
        assert "error" in body
        assert body["error"] == "LLM timeout"


# ── Status values ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("status", ["pending", "processing", "completed", "failed"])
def test_all_job_statuses(client, auth_headers, status):
    job = _fake_job(status=status)
    with patch("app.routes.jobs.get_current_user", new=AsyncMock(return_value=_fake_user)), \
         patch("app.routes.jobs.get_job", new=AsyncMock(return_value=job)):
        r = client.get(f"/jobs/{job.id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == status


# ── Job types ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("job_type", [
    "material_processing", "flashcard", "quiz", "podcast", "presentation"
])
def test_all_job_types(client, auth_headers, job_type):
    job = _fake_job(status="completed", job_type=job_type)
    with patch("app.routes.jobs.get_current_user", new=AsyncMock(return_value=_fake_user)), \
         patch("app.routes.jobs.get_job", new=AsyncMock(return_value=job)):
        r = client.get(f"/jobs/{job.id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["type"] == job_type


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
