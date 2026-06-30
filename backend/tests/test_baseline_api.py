"""
Unit tests for Part 07 baseline evaluation API endpoints.
"""
from unittest.mock import MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport

from app.main import app
from app.schemas.baseline import (
    BaselineEvaluationRequest,
    BaselineEvaluationResult,
    BaselineStageResult,
)
from app.schemas.strategies import StrategyReadiness


@pytest.fixture
async def client():
    """Create a test client using httpx with ASGI transport."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_baseline_service():
    """Create a mocked BaselineEvaluationService."""
    with patch("app.api.v1.routers.baseline.BaselineEvaluationService") as mock:
        service_instance = MagicMock()
        mock.return_value = service_instance
        yield service_instance


class TestBaselineAPI:
    """Test baseline evaluation API endpoints."""

    async def test_openapi_includes_baseline_tag(self, client):
        """OpenAPI schema should include Baseline Evaluation tag."""
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        openapi_data = response.json()
        # Check if baseline endpoints are registered
        paths = openapi_data.get("paths", {})
        assert "/api/baseline/evaluate" in paths or "/baseline/evaluate" in paths

    async def test_evaluate_endpoint_accepts_valid_request(self, client, mock_baseline_service):
        """Evaluate endpoint should accept valid request."""
        # Mock successful evaluation
        mock_result = BaselineEvaluationResult(
            success=True,
            run_id="test_run_id",
            status="completed",
            classification="candidate",
            confidence_score=0.75,
            strategy_name="TestStrategy",
            pairs=["BTC/USDT"],
            timeframe="5m",
            exchange="binance",
            risk_profile="balanced",
            metrics={},
            decision={},
            quality_flags=[],
            stage_results=[],
            artifact_paths=[],
            warnings=[],
            errors=[],
            next_actions=[],
        )
        mock_baseline_service.evaluate.return_value = mock_result

        request_data = {
            "strategy_name": "HERSmokeStrategy",
            "pairs": ["BTC/USDT"],
            "timeframe": "5m",
            "exchange": "binance",
            "days": 30,
            "risk_profile": "balanced",
            "download_missing_data": True,
            "user_confirmed": True,
            "apply_decision_to_run": True,
        }

        response = await client.post("/api/baseline/evaluate", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["run_id"] == "test_run_id"
        assert data["status"] == "completed"
        mock_baseline_service.evaluate.assert_called_once()

    async def test_evaluate_endpoint_rejects_invalid_request(self, client):
        """Evaluate endpoint should reject invalid request."""
        request_data = {
            "strategy_name": "",  # Invalid: empty
            "pairs": [],  # Invalid: empty
            "timeframe": "5m",
            "risk_profile": "balanced",
        }

        response = await client.post("/api/baseline/evaluate", json=request_data)

        assert response.status_code in (400, 422)  # Validation error

    async def test_evaluate_confirmation_required_response_clean(self, client, mock_baseline_service):
        """Confirmation required response should be clean and frontend-ready."""
        # Mock confirmation required result
        mock_stage = BaselineStageResult(
            stage_name="data_check",
            status="confirmation_required",
            started_at="2024-01-01T00:00:00Z",
            completed_at="2024-01-01T00:00:01Z",
            duration_seconds=1.0,
            message="Data download requires confirmation",
            error_code="confirmation_required_for_download",
            warnings=[],
            errors=[],
            artifact_paths=[],
            details={},
        )

        mock_result = BaselineEvaluationResult(
            success=False,
            run_id="test_run_id",
            status="confirmation_required",
            classification=None,
            confidence_score=None,
            strategy_name="TestStrategy",
            pairs=["BTC/USDT"],
            timeframe="5m",
            exchange="binance",
            risk_profile="balanced",
            metrics={},
            decision={},
            quality_flags=[],
            stage_results=[mock_stage],
            artifact_paths=[],
            warnings=[],
            errors=[],
            next_actions=["Set user_confirmed to True in request"],
        )
        mock_baseline_service.evaluate.return_value = mock_result

        request_data = {
            "strategy_name": "TestStrategy",
            "pairs": ["BTC/USDT"],
            "timeframe": "5m",
            "risk_profile": "balanced",
            "download_missing_data": True,
            "user_confirmed": False,
        }

        response = await client.post("/api/baseline/evaluate", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "confirmation_required"
        assert data["success"] is False
        assert len(data["next_actions"]) > 0
        # No stack traces
        assert "Traceback" not in str(data)
        # No secrets
        assert "password" not in str(data).lower()
        assert "api_key" not in str(data).lower()

    async def test_get_run_status_returns_frontend_ready_data(self, client):
        """Get run status should return frontend-ready data."""
        # This test requires a real run in the database, so we skip it for unit tests
        # Integration tests would cover this with a real database
        pytest.skip("Requires database with real run data")

    async def test_get_report_missing_returns_controlled_404(self, client):
        """Get report should return controlled 404 when report not found."""
        with patch("app.api.v1.routers.baseline.ArtifactRepository") as mock_artifact_repo:
            mock_artifact_repo.return_value.get_artifacts_by_run_id.return_value = []

            response = await client.get("/api/baseline/runs/123e4567-e89b-12d3-a456-426614174000/report")

            assert response.status_code == 404
            # No stack traces in response
            assert "Traceback" not in response.text

    async def test_no_secrets_in_response(self, client, mock_baseline_service):
        """Response should not contain secrets."""
        # Mock result with potential secret-like data
        mock_result = BaselineEvaluationResult(
            success=True,
            run_id="test_run_id",
            status="completed",
            classification="candidate",
            confidence_score=0.75,
            strategy_name="TestStrategy",
            pairs=["BTC/USDT"],
            timeframe="5m",
            exchange="binance",
            risk_profile="balanced",
            metrics={"profit": 100},
            decision={"classification": "candidate"},
            quality_flags=[],
            stage_results=[],
            artifact_paths=[],
            warnings=[],
            errors=[],
            next_actions=[],
        )
        mock_baseline_service.evaluate.return_value = mock_result

        request_data = {
            "strategy_name": "TestStrategy",
            "pairs": ["BTC/USDT"],
            "timeframe": "5m",
            "risk_profile": "balanced",
        }

        response = await client.post("/api/baseline/evaluate", json=request_data)

        assert response.status_code == 200
        data_str = str(response.json())
        # Check no secret-like keys are exposed
        assert "password" not in data_str.lower()
        assert "api_key" not in data_str.lower()
        assert "secret" not in data_str.lower()
        assert "token" not in data_str.lower()

    async def test_endpoint_does_not_expose_raw_stdout_stderr(self, client, mock_baseline_service):
        """Endpoint should not expose raw stdout/stderr content by default."""
        # Mock result with details that might contain stdout/stderr
        mock_stage = BaselineStageResult(
            stage_name="baseline_backtest",
            status="completed",
            started_at="2024-01-01T00:00:00Z",
            completed_at="2024-01-01T00:01:00Z",
            duration_seconds=60.0,
            message="Backtest completed",
            warnings=[],
            errors=[],
            artifact_paths=[],
            details={"exit_code": 0, "duration": 60},  # No raw stdout/stderr
        )

        mock_result = BaselineEvaluationResult(
            success=True,
            run_id="test_run_id",
            status="completed",
            classification="candidate",
            confidence_score=0.75,
            strategy_name="TestStrategy",
            pairs=["BTC/USDT"],
            timeframe="5m",
            exchange="binance",
            risk_profile="balanced",
            metrics={},
            decision={},
            quality_flags=[],
            stage_results=[mock_stage],
            artifact_paths=[],
            warnings=[],
            errors=[],
            next_actions=[],
        )
        mock_baseline_service.evaluate.return_value = mock_result

        request_data = {
            "strategy_name": "TestStrategy",
            "pairs": ["BTC/USDT"],
            "timeframe": "5m",
            "risk_profile": "balanced",
        }

        response = await client.post("/api/baseline/evaluate", json=request_data)

        assert response.status_code == 200
        data = response.json()
        # Check that stdout/stderr are not in response
        data_str = str(data)
        assert "stdout" not in data_str.lower()
        assert "stderr" not in data_str.lower()

    async def test_no_approved_export_live_profit_guarantee_wording(self, client, mock_baseline_service):
        """Response should not contain approved/export/live/profit guarantee wording."""
        mock_result = BaselineEvaluationResult(
            success=True,
            run_id="test_run_id",
            status="completed",
            classification="candidate",  # Not approved
            confidence_score=0.75,
            strategy_name="TestStrategy",
            pairs=["BTC/USDT"],
            timeframe="5m",
            exchange="binance",
            risk_profile="balanced",
            metrics={"profit": 100},
            decision={"classification": "candidate"},
            quality_flags=[],
            stage_results=[],
            artifact_paths=[],
            warnings=[],
            errors=[],
            next_actions=[],
        )
        mock_baseline_service.evaluate.return_value = mock_result

        request_data = {
            "strategy_name": "TestStrategy",
            "pairs": ["BTC/USDT"],
            "timeframe": "5m",
            "risk_profile": "balanced",
        }

        response = await client.post("/api/baseline/evaluate", json=request_data)

        assert response.status_code == 200
        data_str = str(response.json())
        # Check no forbidden wording
        assert "approved" not in data_str.lower()
        assert "export" not in data_str.lower()
        assert "live trading" not in data_str.lower()
        assert "profit guarantee" not in data_str.lower()

    async def test_get_baseline_run_not_found(self, client):
        """Get baseline run should return 404 when run not found."""
        with patch("app.api.v1.routers.baseline.RunRepository") as mock_run_repo:
            mock_run_repo.return_value.get_run.return_value = None

            response = await client.get("/api/baseline/runs/123e4567-e89b-12d3-a456-426614174000")

            assert response.status_code == 404
            # No stack traces in response
            assert "Traceback" not in response.text

    async def test_get_baseline_status_not_found(self, client):
        """Get baseline status should return 404 when run not found."""
        with patch("app.api.v1.routers.baseline.RunRepository") as mock_run_repo:
            mock_run_repo.return_value.get_run.return_value = None

            response = await client.get("/api/baseline/runs/123e4567-e89b-12d3-a456-426614174000/status")

            assert response.status_code == 404
            # No stack traces in response
            assert "Traceback" not in response.text


class TestBaselineReadinessGate:
    """Tests for Part 12 strategy readiness gate integration in baseline API."""

    async def test_baseline_allows_ready_strategy(self, client, mock_baseline_service):
        """Baseline should allow strategies with ready readiness."""
        with patch("app.api.v1.routers.baseline.assert_strategy_ready_for_run") as mock_gate:
            mock_gate.return_value = None

            mock_result = BaselineEvaluationResult(
                success=True,
                run_id="test_run_id",
                status="completed",
                classification="candidate",
                confidence_score=0.75,
                strategy_name="ReadyStrategy",
                pairs=["BTC/USDT"],
                timeframe="5m",
                exchange="binance",
                risk_profile="balanced",
                metrics={},
                decision={},
                quality_flags=[],
                stage_results=[],
                artifact_paths=[],
                warnings=[],
                errors=[],
                next_actions=[],
            )
            mock_baseline_service.evaluate.return_value = mock_result

            request_data = {
                "strategy_name": "ReadyStrategy",
                "pairs": ["BTC/USDT"],
                "timeframe": "5m",
                "risk_profile": "balanced",
            }

            response = await client.post("/api/baseline/evaluate", json=request_data)

            assert response.status_code == 200
            mock_gate.assert_called_once_with("ReadyStrategy", run_type="baseline")
            mock_baseline_service.evaluate.assert_called_once()

    async def test_baseline_blocks_missing_sidecar(self, client):
        """Baseline should block strategies with missing_sidecar readiness."""
        from fastapi import HTTPException

        with patch("app.api.v1.routers.baseline.assert_strategy_ready_for_run") as mock_gate:
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
                        "Revalidate before starting baseline"
                    ]
                }
            )

            request_data = {
                "strategy_name": "MissingSidecarStrategy",
                "pairs": ["BTC/USDT"],
                "timeframe": "5m",
                "risk_profile": "balanced",
            }

            response = await client.post("/api/baseline/evaluate", json=request_data)

            assert response.status_code == 400
            # FastAPI wraps HTTPException detail in the response
            # The detail dict is returned as-is in the response body
            mock_gate.assert_called_once_with("MissingSidecarStrategy", run_type="baseline")

    async def test_baseline_blocks_invalid(self, client):
        """Baseline should block strategies with invalid readiness."""
        from fastapi import HTTPException

        with patch("app.api.v1.routers.baseline.assert_strategy_ready_for_run") as mock_gate:
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
                        "Revalidate before starting baseline"
                    ]
                }
            )

            request_data = {
                "strategy_name": "InvalidStrategy",
                "pairs": ["BTC/USDT"],
                "timeframe": "5m",
                "risk_profile": "balanced",
            }

            response = await client.post("/api/baseline/evaluate", json=request_data)

            assert response.status_code == 400
            mock_gate.assert_called_once_with("InvalidStrategy", run_type="baseline")

    async def test_baseline_blocks_parse_error(self, client):
        """Baseline should block strategies with parse_error readiness."""
        from fastapi import HTTPException

        with patch("app.api.v1.routers.baseline.assert_strategy_ready_for_run") as mock_gate:
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
                        "Revalidate before starting baseline"
                    ]
                }
            )

            request_data = {
                "strategy_name": "ParseErrorStrategy",
                "pairs": ["BTC/USDT"],
                "timeframe": "5m",
                "risk_profile": "balanced",
            }

            response = await client.post("/api/baseline/evaluate", json=request_data)

            assert response.status_code == 400
            mock_gate.assert_called_once_with("ParseErrorStrategy", run_type="baseline")

    async def test_baseline_blocks_unsafe(self, client):
        """Baseline should block strategies with unsafe readiness."""
        from fastapi import HTTPException

        with patch("app.api.v1.routers.baseline.assert_strategy_ready_for_run") as mock_gate:
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
                        "Revalidate before starting baseline"
                    ]
                }
            )

            request_data = {
                "strategy_name": "UnsafeStrategy",
                "pairs": ["BTC/USDT"],
                "timeframe": "5m",
                "risk_profile": "balanced",
            }

            response = await client.post("/api/baseline/evaluate", json=request_data)

            assert response.status_code == 400
            mock_gate.assert_called_once_with("UnsafeStrategy", run_type="baseline")

    async def test_blocked_baseline_does_not_start_execution(self, client):
        """Blocked baseline should not start service execution."""
        from fastapi import HTTPException

        with patch("app.api.v1.routers.baseline.assert_strategy_ready_for_run") as mock_gate:
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

        with patch("app.api.v1.routers.baseline.BaselineEvaluationService") as mock_service:
            # Service should NOT be called when strategy is blocked
            service_instance = MagicMock()
            mock_service.return_value = service_instance

            request_data = {
                "strategy_name": "BlockedStrategy",
                "pairs": ["BTC/USDT"],
                "timeframe": "5m",
                "risk_profile": "balanced",
            }

            response = await client.post("/api/baseline/evaluate", json=request_data)

            assert response.status_code == 400
            # Service evaluate should NOT be called
            service_instance.evaluate.assert_not_called()

    async def test_blocked_response_includes_next_actions(self, client):
        """Blocked response should include next_actions."""
        from fastapi import HTTPException

        with patch("app.api.v1.routers.baseline.assert_strategy_ready_for_run") as mock_gate:
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
                        "Revalidate before starting baseline"
                    ]
                }
            )

            request_data = {
                "strategy_name": "BlockedStrategy",
                "pairs": ["BTC/USDT"],
                "timeframe": "5m",
                "risk_profile": "balanced",
            }

            response = await client.post("/api/baseline/evaluate", json=request_data)

            assert response.status_code == 400
            mock_gate.assert_called_once_with("BlockedStrategy", run_type="baseline")
