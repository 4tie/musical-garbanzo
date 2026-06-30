"""
Tests for optimization report endpoint.
"""
import pytest
import json
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.api.v1.routers.optimization import get_optimization_report


@pytest.fixture
def mock_optimization_repo():
    """Mock optimization repository."""
    repo = MagicMock()
    return repo


def test_report_endpoint_returns_report_content(tmp_path, mock_optimization_repo):
    """Report endpoint should return actual report content when available."""
    # Create a temporary report file
    report_file = tmp_path / "optimization_report.json"
    report_content = {
        "optimization_run_id": "opt-run-123",
        "summary": "Test report",
        "metrics": {"profit_total": 0.15},
    }
    report_file.write_text(json.dumps(report_content), encoding="utf-8")
    
    # Mock repository to return run with report path
    mock_optimization_repo.get_run.return_value = {
        "id": "opt-run-123",
        "report_artifact_path": str(report_file),
    }
    
    with patch("app.api.v1.routers.optimization.OptimizationRepository", return_value=mock_optimization_repo):
        result = asyncio.run(get_optimization_report("opt-run-123"))
    
    assert result["optimization_run_id"] == "opt-run-123"
    assert result["status"] == "available"
    assert "report" in result
    assert result["report"]["summary"] == "Test report"
    assert result["report"]["metrics"]["profit_total"] == 0.15


def test_report_endpoint_404_when_run_not_found(mock_optimization_repo):
    """Report endpoint should return 404 when run not found."""
    mock_optimization_repo.get_run.return_value = None
    
    with patch("app.api.v1.routers.optimization.OptimizationRepository", return_value=mock_optimization_repo):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_optimization_report("opt-run-123"))
    
    assert exc_info.value.status_code == 404
    assert "not found" in str(exc_info.value.detail).lower()


def test_report_endpoint_404_when_report_path_missing(mock_optimization_repo):
    """Report endpoint should return 404 when report path is not set."""
    mock_optimization_repo.get_run.return_value = {
        "id": "opt-run-123",
        "report_artifact_path": None,
    }
    
    with patch("app.api.v1.routers.optimization.OptimizationRepository", return_value=mock_optimization_repo):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_optimization_report("opt-run-123"))
    
    assert exc_info.value.status_code == 404
    assert "not available" in str(exc_info.value.detail).lower()


def test_report_endpoint_404_when_report_file_missing(tmp_path, mock_optimization_repo):
    """Report endpoint should return 404 when report file doesn't exist."""
    # Report path exists but file doesn't
    report_path = tmp_path / "missing_report.json"
    
    mock_optimization_repo.get_run.return_value = {
        "id": "opt-run-123",
        "report_artifact_path": str(report_path),
    }
    
    with patch("app.api.v1.routers.optimization.OptimizationRepository", return_value=mock_optimization_repo):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_optimization_report("opt-run-123"))
    
    assert exc_info.value.status_code == 404
    assert "not found" in str(exc_info.value.detail).lower()


def test_report_endpoint_500_when_report_invalid_json(tmp_path, mock_optimization_repo):
    """Report endpoint should return 500 when report file is invalid JSON."""
    # Create a file with invalid JSON
    report_file = tmp_path / "invalid_report.json"
    report_file.write_text("{ invalid json }", encoding="utf-8")
    
    mock_optimization_repo.get_run.return_value = {
        "id": "opt-run-123",
        "report_artifact_path": str(report_file),
    }
    
    with patch("app.api.v1.routers.optimization.OptimizationRepository", return_value=mock_optimization_repo):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_optimization_report("opt-run-123"))
    
    assert exc_info.value.status_code == 500
    assert "could not be parsed" in str(exc_info.value.detail).lower()
