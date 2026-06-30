"""
Regression tests for pytest database isolation.
"""
from pathlib import Path

from app.core.config import settings
from app.db.sqlite import get_database_path


def test_pytest_database_path_is_not_runtime_database():
    project_root = Path(__file__).resolve().parents[2]
    runtime_db = (project_root / "data" / "her.db").resolve()

    assert get_database_path().resolve() != runtime_db
    assert settings.DATABASE_URL != "sqlite:///./data/her.db"


def test_pytest_database_path_uses_ignored_runtime_directory():
    project_root = Path(__file__).resolve().parents[2]
    db_path = get_database_path().resolve()

    assert db_path.parent == project_root / ".pytest_runtime"
    assert db_path.name.startswith("her-test-")
