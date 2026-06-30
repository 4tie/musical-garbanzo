"""
Pytest-wide safety guard for SQLite database isolation.

Tests create and delete many rows. They must never point at the local runtime
database used by scripts and manual validation.
"""
from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DB_PATH = (PROJECT_ROOT / "data" / "her.db").resolve()
DEFAULT_TEST_DB_PATH = (
    PROJECT_ROOT / ".pytest_runtime" / f"her-test-{os.getpid()}.db"
).resolve()


def _sqlite_path_from_url(database_url: str) -> Path:
    """Return the filesystem path represented by a SQLite database URL."""
    db_path = database_url.replace("sqlite:///", "", 1)
    path = Path(db_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def _test_database_url() -> str:
    """Return the isolated pytest database URL."""
    return f"sqlite:///{DEFAULT_TEST_DB_PATH}"


TEST_DATABASE_URL = _test_database_url()
TEST_DB_PATH = _sqlite_path_from_url(TEST_DATABASE_URL)

if TEST_DB_PATH == RUNTIME_DB_PATH:
    raise RuntimeError("pytest DATABASE_URL must not point at data/her.db")

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


def pytest_configure(config):
    """Apply the test database to already-imported settings, if any."""
    TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    try:
        from app.core.config import settings
    except Exception:
        return

    settings.APP_ENV = "test"
    settings.DATABASE_URL = TEST_DATABASE_URL

    from app.db.sqlite import initialize_database

    initialize_database()


def pytest_sessionfinish(session, exitstatus):
    """Remove only the isolated pytest database created for this session."""
    if TEST_DB_PATH != RUNTIME_DB_PATH and TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
