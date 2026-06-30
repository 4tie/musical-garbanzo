"""
Tests for Part 13 validation API endpoints.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport

from app.core.config import settings
from app.db.sqlite import transaction
from app.main import app
from app.repositories.validation import ValidationRepository
from app.schemas.validation import ValidationRunResponse


@pytest.fixture
async def client():
    """Create a test client using httpx with ASGI transport."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def clean_validation_tables():
    """Keep validation API tests isolated."""
    with transaction() as conn:
        conn.execute("DELETE FROM validation_evidence")
        conn.execute("DELETE FROM validation_runs")
    yield
    with transaction() as conn:
        conn.execute("DELETE FROM validation_evidence")
        conn.execute("DELETE FROM validation_runs")


@pytest.fixture
def sample_request():
    return {
        "source_type": "strategy",
        "strategy_name": "SampleStrategy",
        "pairs": ["BTC/USDT"],
        "timeframe": "15m",
        "exchange": "binance",
        "risk_profile": "balanced",
        "timerange": "20240101-20240601",
        "user_confirmed": True,
    }


def create_validation_fixture(tmp_path: Path, with_report: bool = True) -> dict:
    repo = ValidationRepository()
    report_path = None
    if with_report:
        report_path = "artifacts/runs/validation-run-123/validation/validation_report.json"
        full_report_path = settings.project_root / report_path
        full_report_path.parent.mkdir(parents=True, exist_ok=True)
        full_report_path.write_text(
            json.dumps(
                {
                    "final_decision": {"decision_status": "validated"},
                    "oos_result": {"status": "oos_passed"},
                    "stdout": "should not appear",
                    "api_key": "should-not-leak",
                    "no_guarantee_statement": "Validation evidence does not guarantee future performance.",
                }
            ),
            encoding="utf-8",
        )
    run = repo.create_validation_run(
        {
            "id": "validation-run-123",
            "source_type": "strategy",
            "source_run_id": None,
            "strategy_name": "SampleStrategy",
            "timeframe": "15m",
            "pairs": ["BTC/USDT"],
            "exchange": "binance",
            "risk_profile": "balanced",
            "status": "completed",
            "decision_status": "validated",
            "timerange": "20240101-20240601",
            "oos_timerange": "20240416-20240601",
            "request": {"strategy_name": "SampleStrategy", "notes": "safe"},
            "decision": {"decision_status": "validated"},
            "summary": {
                "decision_status": "validated",
                "evidence_count": 3,
                "warnings": [],
                "errors": [],
                "next_actions": ["Review validation evidence."],
            },
            "report_artifact_path": report_path,
        }
    )
    repo.create_evidence(
        {
            "validation_run_id": run["id"],
            "evidence_type": "oos",
            "status": "oos_passed",
            "timerange": "20240416-20240601",
            "metrics": {"trade_count": 40, "profit_factor": 1.4},
            "decision": {"decision_status": "oos_passed"},
            "issues": [],
            "warnings": [],
            "artifact_paths": ["artifacts/runs/oos/normalized.json"],
        }
    )
    repo.create_evidence(
        {
            "validation_run_id": run["id"],
            "evidence_type": "wfo_window",
            "status": "wfo_passed",
            "window_index": 1,
            "timerange": "20240215-20240301",
            "metrics": {"trade_count": 30, "profit_factor": 1.3},
            "decision": {"decision_status": "wfo_passed"},
            "issues": [],
            "warnings": [],
            "artifact_paths": [],
        }
    )
    repo.create_evidence(
        {
            "validation_run_id": run["id"],
            "evidence_type": "robustness",
            "status": "robustness_passed",
            "metrics": {"check": "stable"},
            "decision": {"critical_failure_count": 0},
            "issues": [],
            "warnings": [],
            "artifact_paths": [],
        }
    )
    repo.create_evidence(
        {
            "validation_run_id": run["id"],
            "evidence_type": "validation_decision",
            "status": "validated",
            "metrics": {},
            "decision": {"decision_status": "validated"},
            "issues": [],
            "warnings": [],
            "artifact_paths": [],
        }
    )
    return run


class TestValidationAPI:
    async def test_openapi_includes_validation_tag(self, client):
        response = await client.get("/openapi.json")

        assert response.status_code == 200
        paths = response.json()["paths"]
        assert "/api/validation/run" in paths
        assert "/api/v1/validation/run" in paths

    @patch("app.api.v1.routers.validation.ValidationExecutionService")
    async def test_run_endpoint_accepts_valid_request(
        self,
        mock_service_class,
        client,
        sample_request,
    ):
        service = MagicMock()
        service.run_validation.return_value = ValidationRunResponse(
            validation_run_id="validation-run-123",
            status="completed",
            decision_status="validated",
            strategy_name="SampleStrategy",
            pairs=["BTC/USDT"],
            timeframe="15m",
            exchange="binance",
            risk_profile="balanced",
        )
        mock_service_class.return_value = service

        response = await client.post("/api/validation/run", json=sample_request)

        assert response.status_code == 200
        data = response.json()
        assert data["validation_run_id"] == "validation-run-123"
        assert data["decision_status"] == "validated"
        service.run_validation.assert_called_once()

    async def test_run_endpoint_rejects_invalid_request(self, client):
        response = await client.post(
            "/api/validation/run",
            json={"source_type": "strategy", "strategy_name": "", "pairs": []},
        )

        assert response.status_code in {400, 422}

    @patch("app.api.v1.routers.validation.ValidationExecutionService")
    async def test_blocked_strategy_returns_controlled_response(
        self,
        mock_service_class,
        client,
        sample_request,
    ):
        service = MagicMock()
        service.run_validation.return_value = ValidationRunResponse(
            validation_run_id="validation-run-123",
            status="failed_controlled",
            decision_status="validation_error",
            strategy_name="SampleStrategy",
            pairs=["BTC/USDT"],
            timeframe="15m",
            exchange="binance",
            risk_profile="balanced",
            errors=["strategy_not_ready: Strategy is not ready."],
            next_actions=["Open Strategy Workspace."],
        )
        mock_service_class.return_value = service

        response = await client.post("/api/validation/run", json=sample_request)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed_controlled"
        assert "strategy_not_ready" in data["errors"][0]

    async def test_list_runs_endpoint(self, client, tmp_path):
        create_validation_fixture(tmp_path)

        response = await client.get("/api/validation/runs")

        assert response.status_code == 200
        data = response.json()
        assert data[0]["validation_run_id"] == "validation-run-123"
        assert data[0]["summary"]["evidence_count"] == 3

    async def test_run_detail_endpoint(self, client, tmp_path):
        create_validation_fixture(tmp_path)

        response = await client.get("/api/validation/runs/validation-run-123")

        assert response.status_code == 200
        data = response.json()
        assert data["run"]["validation_run_id"] == "validation-run-123"
        assert data["oos_summary"]["evidence_type"] == "oos"
        assert data["robustness_summary"]["count"] == 1
        assert data["final_decision"]["decision_status"] == "validated"

    async def test_status_endpoint(self, client, tmp_path):
        create_validation_fixture(tmp_path)

        response = await client.get("/api/validation/runs/validation-run-123/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["decision_status"] == "validated"
        assert "oos_decision" in data["completed_stages"]

    async def test_evidence_endpoint(self, client, tmp_path):
        create_validation_fixture(tmp_path)

        response = await client.get("/api/validation/runs/validation-run-123/evidence")

        assert response.status_code == 200
        data = response.json()
        assert len(data["evidence"]) == 4
        assert data["oos"][0]["evidence_type"] == "oos"
        assert data["wfo_windows"][0]["window_index"] == 1
        assert data["robustness"][0]["evidence_type"] == "robustness"

    async def test_report_endpoint(self, client, tmp_path):
        create_validation_fixture(tmp_path)

        response = await client.get("/api/validation/runs/validation-run-123/report")

        assert response.status_code == 200
        data = response.json()
        encoded = json.dumps(data).lower()
        assert data["report"]["final_decision"]["decision_status"] == "validated"
        assert "stdout" not in encoded
        assert "should-not-leak" not in encoded

    async def test_missing_run_returns_clean_404(self, client):
        response = await client.get("/api/validation/runs/missing-run")

        assert response.status_code == 404
        assert "not_found" in response.text or "not found" in response.text.lower()
        assert "traceback" not in response.text.lower()

    async def test_report_missing_returns_clean_404(self, client, tmp_path):
        create_validation_fixture(tmp_path, with_report=False)

        response = await client.get("/api/validation/runs/validation-run-123/report")

        assert response.status_code == 404
        assert "not_found" in response.text or "not found" in response.text.lower()

    @patch("app.api.v1.routers.validation.ValidationExecutionService")
    async def test_backend_exception_returns_controlled_failure(
        self,
        mock_service_class,
        client,
        sample_request,
    ):
        service = MagicMock()
        service.run_validation.side_effect = RuntimeError(
            "api_key=SHOULD_NOT_LEAK traceback details"
        )
        mock_service_class.return_value = service

        response = await client.post("/api/validation/run", json=sample_request)

        assert response.status_code == 200
        encoded = response.text.lower()
        assert "failed_controlled" in encoded
        assert "should_not_leak" not in encoded
        assert "api_key" not in encoded
        assert "traceback" not in encoded

    async def test_no_secrets_or_action_wording_exposed(self, client, tmp_path):
        create_validation_fixture(tmp_path)

        responses = [
            await client.get("/api/validation/runs"),
            await client.get("/api/validation/runs/validation-run-123"),
            await client.get("/api/validation/runs/validation-run-123/status"),
            await client.get("/api/validation/runs/validation-run-123/evidence"),
        ]
        encoded = " ".join(response.text.lower() for response in responses)

        assert "api_key" not in encoded
        assert "should-not-leak" not in encoded
        assert "approved for live" not in encoded
        assert "profit guarantee" not in encoded

    async def test_frontend_ready_response_shape(self, client, tmp_path):
        create_validation_fixture(tmp_path)

        list_response = await client.get("/api/validation/runs")
        detail_response = await client.get("/api/validation/runs/validation-run-123")

        list_item = list_response.json()[0]
        detail = detail_response.json()
        assert {"validation_run_id", "strategy_name", "status", "decision_status"} <= set(list_item)
        assert {"run", "request", "oos_summary", "wfo_summary", "robustness_summary"} <= set(detail)
