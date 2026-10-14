import os
import sys
from pathlib import Path
import tempfile

import pytest

os.environ.setdefault("GEMINI_API_KEY", "pytest-validation-key")
os.environ.setdefault("INITIAL_RECRUITER_EMAIL", "recruiter@example.test")
os.environ.setdefault("INITIAL_RECRUITER_PASSWORD", "Test-Only-Password-2026!")
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "unit-test-secret-key-with-at-least-thirty-two-bytes-123",
)
os.environ.setdefault(
    "AUTH_DATABASE_PATH",
    str(Path(tempfile.gettempdir()) / f"cv_match_auth_{os.getpid()}.sqlite3"),
)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.auth_dependencies import get_current_active_user
from app.main import app
from app.services.auth_service import ActiveUser, auth_service

_TEST_USER = ActiveUser(
    id=auth_service.bootstrap_user_id,
    email=auth_service.bootstrap_email,
)
app.dependency_overrides[get_current_active_user] = lambda: _TEST_USER


@pytest.fixture(scope="session", autouse=True)
def clean_test_auth_database():
    yield
    database_path = auth_service.database_path
    for path in (
        database_path,
        Path(f"{database_path}-shm"),
        Path(f"{database_path}-wal"),
    ):
        if path.exists():
            path.unlink()
