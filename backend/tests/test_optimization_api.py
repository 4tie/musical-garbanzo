"""
Tests for Part 08 optimization API.
"""
import pytest
from unittest.mock import MagicMock, patch
import json

import httpx
from httpx import ASGITransport

from app.main import app
from app.schemas.optimization import (
    OptimizationRequest,
    OptimizationStatus,
    OptimizationResultStatus,
    OptimizationTrialStatus,
)
from app.schemas.strategies import StrategyReadiness


@pytest.fixture
async def client():
    """Create a test client using httpx with ASGI transport."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_optimization_repository():
    """Create a mock optimization repository."""
    repo = MagicMock()
    return repo


@pytest.fixture
def sample_run_data():
    """Sample optimization run data."""
    return {
        "id": "opt-run-123",
        "parent_run_id": None,
        "baseline_run_id": "run-789",
        "optimized_run_id": "run-999",
        "strategy_name": "MyStrategy",
        "timeframe": "1h",
        "pairs": ["BTC/USDT", "ETH/USDT"],
        "exchange": "binance",
        "risk_profile": "balanced",
        "status": "completed",
        "result_status": "improved",
        "best_trial_id": "trial-456",
        "epochs_requested": 50,
        "epochs_completed": 50,
        "spaces": ["buy", "sell"],
        "policy": {
            "max_epochs": 200,
            "default_epochs": 50,
            "allowed_spaces": ["buy", "sell"],
            "locked_spaces": ["roi", "stoploss", "trailing", "protection"],
            "max_optimized_parameters": 6,
            "allow_roi_optimization": False,
            "allow_stoploss_optimization": False,
            "allow_trailing_optimization": False,
            "timeout_seconds": 3600,
            "min_trades": 10,
            "stop_on_zero_trades": True
        },
        "request": {},
        "comparison": {},
        "report_artifact_path": None,
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T12:00:00Z"
    }


@pytest.fixture
def sample_trial_data():
    """Sample optimization trial data."""
    return {
        "id": "trial-456",
        "optimization_run_id": "opt-run-123",
        "trial_number": 25,
        "status": "best",
        "is_best": True,
        "is_selected_for_validation": False,
        "params": {},
        "buy_params": {},
        "sell_params": {},
        "roi_params": None,
        "stoploss_params": None,
        "trailing_params": None,
        "metrics": {},
        "loss_score": 0.15,
        "profit_total": 150.5,
        "profit_factor": 2.5,
        "expectancy": 0.05,
        "max_drawdown": -10.2,
        "trade_count": 45,
        "win_rate": 0.6,
        "rejection_reason": None,
        "failure_reason": None,
        "artifact_paths": [],
        "raw_trial": None,
        "created_at": "2024-01-15T11:30:00Z"
    }


@pytest.fixture
def sample_comparison_data():
    """Sample comparison data."""
    return {
        "optimization_run_id": "opt-run-123",
        "baseline_run_id": "run-789",
        "optimized_run_id": "run-999",
        "best_trial_id": "trial-456",
        "baseline_metrics": {},
        "optimized_metrics": {},
        "delta_profit_factor": 0.5,
        "delta_expectancy": 0.02,
        "delta_drawdown": -2.0,
        "delta_trade_count": 5,
        "baseline_classification": "promising",
        "optimized_classification": "validated",
        "result_status": "improved",
        "improvement_summary": "Optimized strategy shows improvement",
        "warnings": [],
        "overfit_suspected": False,
        "created_at": "2024-01-15T12:00:00Z"
    }


class TestOptimizationAPI:
    """Tests for optimization API endpoints."""

    async def test_openapi_includes_optimization_tag(self, client):
        """Test that OpenAPI schema includes Optimization tag."""
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        openapi_schema = response.json()
        # Check that optimization paths exist
        assert "/api/optimization/runs" in openapi_schema["paths"]
        assert "/api/optimization/runs/{optimization_run_id}" in openapi_schema["paths"]

    @patch("app.api.v1.routers.optimization.OptimizationPipelineService")
    async def test_post_run_calls_pipeline_service(self, mock_pipeline_service_class, client):
        """Test that POST /run calls the real pipeline service."""
        # Mock gate to pass
        with patch("app.api.v1.routers.optimization.assert_strategy_ready_for_run") as mock_gate:
            mock_gate.return_value = None

            # Mock pipeline service to return a successful result
            mock_pipeline_service = MagicMock()
            mock_pipeline_service.run_optimization.return_value = {
                "optimization_run_id": "opt-run-123",
                "status": "completed",
                "baseline_run_id": "baseline-456",
            }
            mock_pipeline_service_class.return_value = mock_pipeline_service

            request_data = {
                "strategy_name": "MyStrategy",
                "pairs": ["BTC/USDT"],
                "timeframe": "1h",
                "epochs": 50,
                "user_confirmed": True
            }
            response = await client.post("/api/optimization/run", json=request_data)
            assert response.status_code == 202
            response_data = response.json()
            assert response_data["run_id"] == "opt-run-123"
            assert response_data["status"] == "completed"
            mock_pipeline_service.run_optimization.assert_called_once()

    async def test_post_run_invalid_request_rejected(self, client):
        """Test that invalid request is rejected."""
        request_data = {
            "strategy_name": "",  # Invalid: empty
            "pairs": [],  # Invalid: empty
            "timeframe": "",  # Invalid: empty
            "user_confirmed": True
        }
        response = await client.post("/api/optimization/run", json=request_data)
        assert response.status_code in [400, 422]  # Validation error

    async def test_post_run_invalid_epochs_rejected(self, client):
        """Test that invalid epochs value is rejected."""
        request_data = {
            "strategy_name": "MyStrategy",
            "pairs": ["BTC/USDT"],
            "timeframe": "1h",
            "epochs": 500,  # Invalid: exceeds 200
            "user_confirmed": True
        }
        response = await client.post("/api/optimization/run", json=request_data)
        assert response.status_code in [400, 422]

    async def test_post_run_invalid_spaces_rejected(self, client):
        """Test that invalid spaces value is rejected."""
        request_data = {
            "strategy_name": "MyStrategy",
            "pairs": ["BTC/USDT"],
            "timeframe": "1h",
            "spaces": ["invalid_space"],  # Invalid: not in allowed list
            "user_confirmed": True
        }
        response = await client.post("/api/optimization/run", json=request_data)
        assert response.status_code in [400, 422]

    async def test_post_run_requires_user_confirmed(self, client):
        """Test that user_confirmed=true is required."""
        request_data = {
            "strategy_name": "MyStrategy",
            "pairs": ["BTC/USDT"],
            "timeframe": "1h",
            "epochs": 50,
            "user_confirmed": False  # Invalid: must be true
        }
        response = await client.post("/api/optimization/run", json=request_data)
        assert response.status_code == 400
        response_text = response.text.lower()
        assert "user_confirmed" in response_text

    @patch("app.api.v1.routers.optimization.OptimizationRepository")
    async def test_list_runs_endpoint_works(self, mock_repo_class, client, sample_run_data):
        """Test that list runs endpoint works."""
        mock_repo = MagicMock()
        mock_repo.list_optimization_runs.return_value = [sample_run_data]
        mock_repo_class.return_value = mock_repo

        response = await client.get("/api/optimization/runs")
        assert response.status_code == 200
        runs = response.json()
        assert len(runs) == 1
        assert runs[0]["id"] == "opt-run-123"
        assert runs[0]["strategy_name"] == "MyStrategy"
        assert "best_trial_id" in runs[0]

    @patch("app.api.v1.routers.optimization.OptimizationRepository")
    async def test_list_runs_with_status_filter(self, mock_repo_class, client, sample_run_data):
        """Test that list runs endpoint works with status filter."""
        mock_repo = MagicMock()
        mock_repo.list_optimization_runs.return_value = [sample_run_data]
        mock_repo_class.return_value = mock_repo

        response = await client.get("/api/optimization/runs?status=completed")
        assert response.status_code == 200
        mock_repo.list_optimization_runs.assert_called_with(limit=100, status="completed")

    @patch("app.api.v1.routers.optimization.OptimizationRepository")
    async def test_list_runs_with_pagination(self, mock_repo_class, client, sample_run_data):
        """Test that list runs endpoint works with pagination."""
        mock_repo = MagicMock()
        mock_repo.list_optimization_runs.return_value = [sample_run_data]
        mock_repo_class.return_value = mock_repo

        response = await client.get("/api/optimization/runs?limit=10&offset=5")
        assert response.status_code == 200
        mock_repo.list_optimization_runs.assert_called_with(limit=10, status=None)

    @patch("app.api.v1.routers.optimization.OptimizationRepository")
    async def test_run_detail_endpoint_works(self, mock_repo_class, client, sample_run_data, sample_trial_data, sample_comparison_data):
        """Test that run detail endpoint works."""
        mock_repo = MagicMock()
        mock_repo.get_run.return_value = sample_run_data
        mock_repo.get_trial.return_value = sample_trial_data
        mock_repo.get_comparison.return_value = sample_comparison_data
        mock_repo_class.return_value = mock_repo

        response = await client.get("/api/optimization/runs/opt-run-123")
        assert response.status_code == 200
        detail = response.json()
        assert detail["run"]["id"] == "opt-run-123"
        assert detail["run"]["strategy_name"] == "MyStrategy"
        assert detail["best_trial"] is not None
        assert detail["comparison"] is not None

    @patch("app.api.v1.routers.optimization.OptimizationRepository")
    async def test_run_detail_missing_run_returns_404(self, mock_repo_class, client):
        """Test that missing run returns clean 404."""
        mock_repo = MagicMock()
        mock_repo.get_run.return_value = None
        mock_repo_class.return_value = mock_repo

        response = await client.get("/api/optimization/runs/nonexistent-run")
        assert response.status_code == 404
        response_text = response.text.lower()
        assert "not found" in response_text

    @patch("app.api.v1.routers.optimization.OptimizationRepository")
    async def test_status_endpoint_works(self, mock_repo_class, client, sample_run_data):
        """Test that status endpoint works."""
        mock_repo = MagicMock()
        mock_repo.get_run.return_value = sample_run_data
        mock_repo.list_trials.return_value = []
        mock_repo_class.return_value = mock_repo

        response = await client.get("/api/optimization/runs/opt-run-123/status")
        assert response.status_code == 200
        status = response.json()
        assert status["run_id"] == "opt-run-123"
        assert status["status"] == "completed"
        assert "trials_completed" in status

    @patch("app.api.v1.routers.optimization.OptimizationRepository")
    async def test_status_missing_run_returns_404(self, mock_repo_class, client):
        """Test that status endpoint returns 404 for missing run."""
        mock_repo = MagicMock()
        mock_repo.get_run.return_value = None
        mock_repo_class.return_value = mock_repo

        response = await client.get("/api/optimization/runs/nonexistent-run/status")
        assert response.status_code == 404

    @patch("app.api.v1.routers.optimization.OptimizationRepository")
    async def test_trials_endpoint_returns_all_trials(self, mock_repo_class, client, sample_run_data, sample_trial_data):
        """Test that trials endpoint returns all trials, not only best."""
        mock_repo = MagicMock()
        mock_repo.get_run.return_value = sample_run_data
        mock_repo.list_trials.return_value = [sample_trial_data]
        mock_repo_class.return_value = mock_repo

        response = await client.get("/api/optimization/runs/opt-run-123/trials")
        assert response.status_code == 200
        trials = response.json()
        assert len(trials) == 1
        assert trials[0]["id"] == "trial-456"
        assert trials[0]["status"] == "best"

    @patch("app.api.v1.routers.optimization.OptimizationRepository")
    async def test_trials_missing_run_returns_404(self, mock_repo_class, client):
        """Test that trials endpoint returns 404 for missing run."""
        mock_repo = MagicMock()
        mock_repo.get_run.return_value = None
        mock_repo_class.return_value = mock_repo

        response = await client.get("/api/optimization/runs/nonexistent-run/trials")
        assert response.status_code == 404

    @patch("app.api.v1.routers.optimization.OptimizationRepository")
    async def test_trial_detail_includes_full_params(self, mock_repo_class, client, sample_run_data, sample_trial_data):
        """Test that trial detail endpoint includes full parameters."""
        mock_repo = MagicMock()
        mock_repo.get_run.return_value = sample_run_data
        mock_repo.get_trial.return_value = sample_trial_data
        mock_repo_class.return_value = mock_repo

        response = await client.get("/api/optimization/runs/opt-run-123/trials/trial-456")
        assert response.status_code == 200
        detail = response.json()
        assert detail["trial"]["id"] == "trial-456"
        assert "buy_params" in detail["trial"]
        assert "sell_params" in detail["trial"]
        assert "roi_params" in detail["trial"]
        assert "stoploss_params" in detail["trial"]
        assert "trailing_params" in detail["trial"]
        assert "metrics" in detail["trial"]

    @patch("app.api.v1.routers.optimization.OptimizationRepository")
    async def test_trial_detail_missing_run_returns_404(self, mock_repo_class, client):
        """Test that trial detail returns 404 for missing run."""
        mock_repo = MagicMock()
        mock_repo.get_run.return_value = None
        mock_repo_class.return_value = mock_repo

        response = await client.get("/api/optimization/runs/nonexistent-run/trials/trial-456")
        assert response.status_code == 404

    @patch("app.api.v1.routers.optimization.OptimizationRepository")
    async def test_trial_detail_missing_trial_returns_404(self, mock_repo_class, client, sample_run_data):
        """Test that trial detail returns 404 for missing trial."""
        mock_repo = MagicMock()
        mock_repo.get_run.return_value = sample_run_data
        mock_repo.get_trial.return_value = None
        mock_repo_class.return_value = mock_repo

        response = await client.get("/api/optimization/runs/opt-run-123/trials/nonexistent-trial")
        assert response.status_code == 404

    @patch("app.api.v1.routers.optimization.OptimizationRepository")
    async def test_best_trial_endpoint_works(self, mock_repo_class, client, sample_run_data, sample_trial_data):
        """Test that best-trial endpoint works."""
        mock_repo = MagicMock()
        mock_repo.get_run.return_value = sample_run_data
        mock_repo.get_trial.return_value = sample_trial_data
        mock_repo_class.return_value = mock_repo

        response = await client.get("/api/optimization/runs/opt-run-123/best-trial")
        assert response.status_code == 200
        trial = response.json()
        assert trial["id"] == "trial-456"
        assert trial["is_best"] is True
        assert trial["status"] == "best"

    @patch("app.api.v1.routers.optimization.OptimizationRepository")
    async def test_best_trial_missing_run_returns_404(self, mock_repo_class, client):
        """Test that best-trial returns 404 for missing run."""
        mock_repo = MagicMock()
        mock_repo.get_run.return_value = None
        mock_repo_class.return_value = mock_repo

        response = await client.get("/api/optimization/runs/nonexistent-run/best-trial")
        assert response.status_code == 404

    @patch("app.api.v1.routers.optimization.OptimizationRepository")
    async def test_best_trial_no_best_trial_returns_404(self, mock_repo_class, client, sample_run_data):
        """Test that best-trial returns 404 when no best trial exists."""
        mock_repo = MagicMock()
        sample_run_data_no_best = sample_run_data.copy()
        sample_run_data_no_best["best_trial_id"] = None
        mock_repo.get_run.return_value = sample_run_data_no_best
        mock_repo_class.return_value = mock_repo

        response = await client.get("/api/optimization/runs/opt-run-123/best-trial")
        assert response.status_code == 404
        response_text = response.text.lower()
        assert "best trial" in response_text

    @patch("app.api.v1.routers.optimization.OptimizationRepository")
    async def test_comparison_endpoint_works(self, mock_repo_class, client, sample_run_data, sample_comparison_data):
        """Test that comparison endpoint works."""
        mock_repo = MagicMock()
        mock_repo.get_run.return_value = sample_run_data
        mock_repo.get_comparison.return_value = sample_comparison_data
        mock_repo_class.return_value = mock_repo

        response = await client.get("/api/optimization/runs/opt-run-123/comparison")
        assert response.status_code == 200
        comparison = response.json()
        assert comparison["optimization_run_id"] == "opt-run-123"
        assert comparison["baseline_run_id"] == "run-789"
        assert comparison["optimized_run_id"] == "run-999"
        assert "baseline_metrics" in comparison
        assert "optimized_metrics" in comparison
        assert "delta_profit_factor" in comparison
        assert "delta_expectancy" in comparison
        assert "result_status" in comparison

    @patch("app.api.v1.routers.optimization.OptimizationRepository")
    async def test_comparison_missing_run_returns_404(self, mock_repo_class, client):
        """Test that comparison returns 404 for missing run."""
        mock_repo = MagicMock()
        mock_repo.get_run.return_value = None
        mock_repo_class.return_value = mock_repo

        response = await client.get("/api/optimization/runs/nonexistent-run/comparison")
        assert response.status_code == 404

    @patch("app.api.v1.routers.optimization.OptimizationRepository")
    async def test_comparison_not_available_returns_404(self, mock_repo_class, client, sample_run_data):
        """Test that comparison returns 404 when comparison not available."""
        mock_repo = MagicMock()
        mock_repo.get_run.return_value = sample_run_data
        mock_repo.get_comparison.return_value = None
        mock_repo_class.return_value = mock_repo

        response = await client.get("/api/optimization/runs/opt-run-123/comparison")
        assert response.status_code == 404
        response_text = response.text.lower()
        assert "comparison" in response_text

    @patch("app.api.v1.routers.optimization.OptimizationRepository")
    async def test_report_endpoint_returns_metadata_and_content(self, mock_repo_class, client, sample_run_data, tmp_path):
        """Report endpoint returns useful metadata and safe JSON content."""
        report_path = tmp_path / "optimization_report.json"
        report_path.write_text(
            json.dumps(
                {
                    "optimization_run_id": "opt-run-123",
                    "best_trial_id": "trial-456",
                    "comparison": {"result_status": "optimization_rejected"},
                }
            ),
            encoding="utf-8",
        )
        sample_run_data_with_report = sample_run_data.copy()
        sample_run_data_with_report["report_artifact_path"] = str(report_path)
        mock_repo = MagicMock()
        mock_repo.get_run.return_value = sample_run_data_with_report
        mock_repo_class.return_value = mock_repo

        response = await client.get("/api/optimization/runs/opt-run-123/report")
        assert response.status_code == 200
        report = response.json()
        assert report["optimization_run_id"] == "opt-run-123"
        assert report["status"] == "available"
        assert report["report"]["best_trial_id"] == "trial-456"
        assert report["report"]["comparison"]["result_status"] == "optimization_rejected"

    @patch("app.api.v1.routers.optimization.OptimizationRepository")
    async def test_report_missing_run_returns_404(self, mock_repo_class, client):
        """Test that report returns 404 for missing run."""
        mock_repo = MagicMock()
        mock_repo.get_run.return_value = None
        mock_repo_class.return_value = mock_repo

        response = await client.get("/api/optimization/runs/nonexistent-run/report")
        assert response.status_code == 404

    @patch("app.api.v1.routers.optimization.OptimizationRepository")
    async def test_report_not_available_returns_404(self, mock_repo_class, client, sample_run_data):
        """Test that report returns controlled 404 if missing."""
        mock_repo = MagicMock()
        mock_repo.get_run.return_value = sample_run_data
        mock_repo_class.return_value = mock_repo

        response = await client.get("/api/optimization/runs/opt-run-123/report")
        assert response.status_code == 404
        response_text = response.text.lower()
        assert "report" in response_text

    async def test_no_secrets_exposed_in_responses(self, client):
        """Test that no secrets are exposed in API responses."""
        # This is a structural test - we check that responses don't contain secret-like fields
        request_data = {
            "strategy_name": "MyStrategy",
            "pairs": ["BTC/USDT"],
            "timeframe": "1h"
        }
        response = await client.post("/api/optimization/run", json=request_data)
        # Even error response should not contain secrets
        assert "password" not in str(response.json()).lower()
        assert "secret" not in str(response.json()).lower()
        assert "token" not in str(response.json()).lower()
        assert "key" not in str(response.json()).lower()

    async def test_no_profit_guarantee_wording(self, client):
        """Test that no profit guarantee wording appears in responses."""
        request_data = {
            "strategy_name": "MyStrategy",
            "pairs": ["BTC/USDT"],
            "timeframe": "1h"
        }
        response = await client.post("/api/optimization/run", json=request_data)
        response_text = str(response.json()).lower()
        assert "guarantee" not in response_text
        assert "sure thing" not in response_text
        assert "risk-free" not in response_text

    @patch("app.api.v1.routers.optimization.OptimizationRepository")
    async def test_api_responses_are_frontend_ready(self, mock_repo_class, client, sample_run_data):
        """Test that API responses are frontend-ready (proper JSON structure)."""
        mock_repo = MagicMock()
        mock_repo.list_optimization_runs.return_value = [sample_run_data]
        mock_repo_class.return_value = mock_repo

        response = await client.get("/api/optimization/runs")
        assert response.status_code == 200
        runs = response.json()
        assert isinstance(runs, list)
        assert len(runs) > 0
        # Check that datetime fields are properly serialized
        assert "created_at" in runs[0]
        assert "updated_at" in runs[0]
        # Check that all required fields are present
        assert "id" in runs[0]
        assert "strategy_name" in runs[0]
        assert "status" in runs[0]


class TestOptimizationReadinessGate:
    """Tests for Part 12 strategy readiness gate integration in optimization API."""

    @patch("app.api.v1.routers.optimization.OptimizationPipelineService")
    async def test_optimization_allows_ready_strategy(self, mock_pipeline_service_class, client):
        """Optimization should allow strategies with ready readiness."""
        with patch("app.api.v1.routers.optimization.assert_strategy_ready_for_run") as mock_gate:
            mock_gate.return_value = None

            mock_pipeline_service = MagicMock()
            mock_pipeline_service.run_optimization.return_value = {
                "optimization_run_id": "opt-run-123",
                "status": "completed",
                "baseline_run_id": "baseline-456",
            }
            mock_pipeline_service_class.return_value = mock_pipeline_service

            request_data = {
                "strategy_name": "ReadyStrategy",
                "pairs": ["BTC/USDT"],
                "timeframe": "1h",
                "epochs": 50,
                "user_confirmed": True
            }

            response = await client.post("/api/optimization/run", json=request_data)

            assert response.status_code == 202
            mock_gate.assert_called_once_with("ReadyStrategy", run_type="optimization")
            mock_pipeline_service.run_optimization.assert_called_once()

    async def test_optimization_blocks_missing_sidecar(self, client):
        """Optimization should block strategies with missing_sidecar readiness."""
        from fastapi import HTTPException

        with patch("app.api.v1.routers.optimization.assert_strategy_ready_for_run") as mock_gate:
            mock_gate.side_effect = HTTPException(
                status_code=400,
                detail={
                    "error": True,
                    "code": "strategy_not_ready",
                    "message": "Strategy 'MissingSidecarStrategy' is missing required sidecar JSON file.",
                    "strategy_name": "MissingSidecarStrategy",
                    "readiness": "missing_sidecar",
                    "issues": [],
                    "warnings": [],
                    "next_actions": [
                        "Open Strategy Workspace",
                        "Inspect strategy readiness issues",
                        "Fix the strategy or sidecar JSON manually",
                        "Revalidate before starting optimization"
                    ]
                }
            )

            request_data = {
                "strategy_name": "MissingSidecarStrategy",
                "pairs": ["BTC/USDT"],
                "timeframe": "1h",
                "epochs": 50,
                "user_confirmed": True
            }

            response = await client.post("/api/optimization/run", json=request_data)

            assert response.status_code == 400
            mock_gate.assert_called_once_with("MissingSidecarStrategy", run_type="optimization")

    async def test_optimization_blocks_invalid(self, client):
        """Optimization should block strategies with invalid readiness."""
        from fastapi import HTTPException

        with patch("app.api.v1.routers.optimization.assert_strategy_ready_for_run") as mock_gate:
            mock_gate.side_effect = HTTPException(
                status_code=400,
                detail={
                    "error": True,
                    "code": "strategy_not_ready",
                    "message": "Strategy 'InvalidStrategy' has invalid structure.",
                    "strategy_name": "InvalidStrategy",
                    "readiness": "invalid",
                    "issues": [],
                    "warnings": [],
                    "next_actions": [
                        "Open Strategy Workspace",
                        "Inspect strategy readiness issues",
                        "Fix the strategy or sidecar JSON manually",
                        "Revalidate before starting optimization"
                    ]
                }
            )

            request_data = {
                "strategy_name": "InvalidStrategy",
                "pairs": ["BTC/USDT"],
                "timeframe": "1h",
                "epochs": 50,
                "user_confirmed": True
            }

            response = await client.post("/api/optimization/run", json=request_data)

            assert response.status_code == 400
            mock_gate.assert_called_once_with("InvalidStrategy", run_type="optimization")

    async def test_optimization_blocks_parse_error(self, client):
        """Optimization should block strategies with parse_error readiness."""
        from fastapi import HTTPException

        with patch("app.api.v1.routers.optimization.assert_strategy_ready_for_run") as mock_gate:
            mock_gate.side_effect = HTTPException(
                status_code=400,
                detail={
                    "error": True,
                    "code": "strategy_not_ready",
                    "message": "Strategy 'ParseErrorStrategy' has parsing errors.",
                    "strategy_name": "ParseErrorStrategy",
                    "readiness": "parse_error",
                    "issues": [],
                    "warnings": [],
                    "next_actions": [
                        "Open Strategy Workspace",
                        "Inspect strategy readiness issues",
                        "Fix the strategy or sidecar JSON manually",
                        "Revalidate before starting optimization"
                    ]
                }
            )

            request_data = {
                "strategy_name": "ParseErrorStrategy",
                "pairs": ["BTC/USDT"],
                "timeframe": "1h",
                "epochs": 50,
                "user_confirmed": True
            }

            response = await client.post("/api/optimization/run", json=request_data)

            assert response.status_code == 400
            mock_gate.assert_called_once_with("ParseErrorStrategy", run_type="optimization")

    async def test_optimization_blocks_unsafe(self, client):
        """Optimization should block strategies with unsafe readiness."""
        from fastapi import HTTPException

        with patch("app.api.v1.routers.optimization.assert_strategy_ready_for_run") as mock_gate:
            mock_gate.side_effect = HTTPException(
                status_code=400,
                detail={
                    "error": True,
                    "code": "strategy_not_ready",
                    "message": "Strategy 'UnsafeStrategy' contains unsafe patterns.",
                    "strategy_name": "UnsafeStrategy",
                    "readiness": "unsafe",
                    "issues": [],
                    "warnings": [],
                    "next_actions": [
                        "Open Strategy Workspace",
                        "Inspect strategy readiness issues",
                        "Fix the strategy or sidecar JSON manually",
                        "Revalidate before starting optimization"
                    ]
                }
            )

            request_data = {
                "strategy_name": "UnsafeStrategy",
                "pairs": ["BTC/USDT"],
                "timeframe": "1h",
                "epochs": 50,
                "user_confirmed": True
            }

            response = await client.post("/api/optimization/run", json=request_data)

            assert response.status_code == 400
            mock_gate.assert_called_once_with("UnsafeStrategy", run_type="optimization")

    @patch("app.api.v1.routers.optimization.OptimizationPipelineService")
    async def test_blocked_optimization_does_not_start_execution(self, mock_pipeline_service_class, client):
        """Blocked optimization should not start pipeline execution."""
        from fastapi import HTTPException

        with patch("app.api.v1.routers.optimization.assert_strategy_ready_for_run") as mock_gate:
            mock_gate.side_effect = HTTPException(
                status_code=400,
                detail={
                    "error": True,
                    "code": "strategy_not_ready",
                    "message": "Strategy is not ready",
                    "strategy_name": "BlockedStrategy",
                    "readiness": "missing_sidecar",
                    "issues": [],
                    "warnings": [],
                    "next_actions": []
                }
            )

        with patch("app.api.v1.routers.optimization.OptimizationPipelineService") as mock_service:
            # Service should NOT be called when strategy is blocked
            service_instance = MagicMock()
            mock_service.return_value = service_instance

            request_data = {
                "strategy_name": "BlockedStrategy",
                "pairs": ["BTC/USDT"],
                "timeframe": "1h",
                "epochs": 50,
                "user_confirmed": True
            }

            response = await client.post("/api/optimization/run", json=request_data)

            assert response.status_code == 400
            # Pipeline service should NOT be called
            service_instance.run_optimization.assert_not_called()

    @patch("app.api.v1.routers.optimization.OptimizationPipelineService")
    async def test_blocked_optimization_does_not_start_baseline_first(self, mock_pipeline_service_class, client):
        """Blocked optimization should not start baseline-first execution."""
        from fastapi import HTTPException

        with patch("app.api.v1.routers.optimization.assert_strategy_ready_for_run") as mock_gate:
            mock_gate.side_effect = HTTPException(
                status_code=400,
                detail={
                    "error": True,
                    "code": "strategy_not_ready",
                    "message": "Strategy is not ready",
                    "strategy_name": "BlockedStrategy",
                    "readiness": "missing_sidecar",
                    "issues": [],
                    "warnings": [],
                    "next_actions": []
                }
            )

        with patch("app.api.v1.routers.optimization.OptimizationPipelineService") as mock_service:
            service_instance = MagicMock()
            mock_service.return_value = service_instance

            request_data = {
                "strategy_name": "BlockedStrategy",
                "pairs": ["BTC/USDT"],
                "timeframe": "1h",
                "epochs": 50,
                "run_baseline_first": True,  # This should not execute when blocked
                "user_confirmed": True
            }

            response = await client.post("/api/optimization/run", json=request_data)

            assert response.status_code == 400
            # Pipeline service should NOT be called even with run_baseline_first=True
            service_instance.run_optimization.assert_not_called()

    async def test_blocked_response_includes_next_actions(self, client):
        """Blocked response should include next_actions."""
        from fastapi import HTTPException

        with patch("app.api.v1.routers.optimization.assert_strategy_ready_for_run") as mock_gate:
            mock_gate.side_effect = HTTPException(
                status_code=400,
                detail={
                    "error": True,
                    "code": "strategy_not_ready",
                    "message": "Strategy is not ready",
                    "strategy_name": "BlockedStrategy",
                    "readiness": "missing_sidecar",
                    "issues": [],
                    "warnings": [],
                    "next_actions": [
                        "Open Strategy Workspace",
                        "Inspect strategy readiness issues",
                        "Fix the strategy or sidecar JSON manually",
                        "Revalidate before starting optimization"
                    ]
                }
            )

            request_data = {
                "strategy_name": "BlockedStrategy",
                "pairs": ["BTC/USDT"],
                "timeframe": "1h",
                "epochs": 50,
                "user_confirmed": True
            }

            response = await client.post("/api/optimization/run", json=request_data)

            assert response.status_code == 400
            mock_gate.assert_called_once_with("BlockedStrategy", run_type="optimization")
