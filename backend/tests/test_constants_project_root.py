"""
Tests for PROJECT_ROOT derivation in constants.py.
"""
from pathlib import Path
from app.core.constants import PROJECT_ROOT


def test_project_root_is_derived_from_file_location():
    """PROJECT_ROOT should be derived from the constants file location, not hardcoded."""
    # PROJECT_ROOT should be the parent of the backend directory
    constants_file = Path(__file__).resolve()
    backend_dir = constants_file.parent
    project_root = backend_dir.parent.parent  # Go up from backend to project root
    
    assert PROJECT_ROOT == str(project_root)
    assert "her" in PROJECT_ROOT.lower()  # Should contain project name


def test_project_root_is_absolute_path():
    """PROJECT_ROOT should be an absolute path."""
    project_root_path = Path(PROJECT_ROOT)
    assert project_root_path.is_absolute()


def test_project_root_paths_are_derived():
    """All derived paths should be based on PROJECT_ROOT."""
    from app.core.constants import (
        FREQTRADE_WORKSPACE,
        FREQTRADE_USER_DATA,
        FREQTRADE_HYPEROPT_RESULTS,
        HER_ARTIFACTS,
        HER_ARTIFACTS_RUNS,
    )
    
    assert FREQTRADE_WORKSPACE.startswith(PROJECT_ROOT)
    assert FREQTRADE_USER_DATA.startswith(PROJECT_ROOT)
    assert FREQTRADE_HYPEROPT_RESULTS.startswith(PROJECT_ROOT)
    assert HER_ARTIFACTS.startswith(PROJECT_ROOT)
    assert HER_ARTIFACTS_RUNS.startswith(PROJECT_ROOT)
