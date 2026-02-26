"""
Shared pytest fixtures and configuration for the entire test suite.
Applies to all subdirectories: unit/, integration/, api/, e2e/
"""

import sys
import os
import uuid
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# ── Ensure backend is importable from every pytest session ──────────────────
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Minimal env so that Pydantic Settings can validate on import
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")


# ── pytest-asyncio mode ──────────────────────────────────────────────────────
# Set asyncio_mode to "auto" so all async tests get a loop automatically.
# This can also be set in pytest.ini; here it is set programmatically.


# ── Fake user fixture ────────────────────────────────────────────────────────

@pytest.fixture
def fake_user():
    """Return a mock user object suitable for dependency injection in API tests."""
    from types import SimpleNamespace
    return SimpleNamespace(
        id="test-user-id-" + str(uuid.uuid4())[:8],
        username="testuser",
        email="test@example.com",
        role="user",
    )


# ── Temporary storage fixture ────────────────────────────────────────────────

@pytest.fixture
def temp_storage_dir(tmp_path):
    """Patch MATERIAL_TEXT_DIR to a temporary directory for storage tests."""
    import app.services.storage_service as _svc
    with patch.object(_svc, "MATERIAL_TEXT_DIR", tmp_path):
        yield tmp_path


# ── Rate limiter cleanup ──────────────────────────────────────────────────────

@pytest.fixture(autouse=False)
def clear_rate_limiter():
    """Clear rate-limiter history before each test to prevent bleed-through."""
    try:
        import app.services.rate_limiter as _rl
        _rl._request_history.clear()
    except Exception:
        pass
    yield
    try:
        import app.services.rate_limiter as _rl
        _rl._request_history.clear()
    except Exception:
        pass


# ── FastAPI TestClient fixture ────────────────────────────────────────────────

@pytest.fixture(scope="session")
def app_client():
    """Return a FastAPI TestClient for the full application."""
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


# ── Mocked Prisma client fixture ──────────────────────────────────────────────

@pytest.fixture
def mock_prisma(monkeypatch):
    """Provide a pre-configured async mock Prisma client."""
    mock_db = MagicMock()
    mock_db.user = MagicMock()
    mock_db.notebook = MagicMock()
    mock_db.material = MagicMock()
    mock_db.chatsession = MagicMock()
    mock_db.chatmessage = MagicMock()
    mock_db.backgroundjob = MagicMock()
    mock_db.generatedcontent = MagicMock()
    mock_db.refreshtoken = MagicMock()
    mock_db.apiusagelog = MagicMock()
    # All DB calls are async by default
    for attr in ["create", "find_unique", "find_many", "update", "delete", "upsert", "count"]:
        setattr(mock_db.user, attr, AsyncMock(return_value=None))
        setattr(mock_db.notebook, attr, AsyncMock(return_value=None))
        setattr(mock_db.material, attr, AsyncMock(return_value=None))
    return mock_db


# ── Output directory fixture ──────────────────────────────────────────────────

@pytest.fixture(scope="session")
def output_dir():
    """Ensure the output/test_artifacts directory exists and return its path."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    out = os.path.join(project_root, "output", "test_artifacts")
    os.makedirs(out, exist_ok=True)
    return out
