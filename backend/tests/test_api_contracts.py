"""
Tests for unified API contracts and OpenAPI-safe responses.
"""
import json
import pytest
import httpx
from httpx import ASGITransport

from app.db.sqlite import get_connection
from app.main import app


@pytest.fixture
async def client():
    """Create a test client using httpx with ASGI transport."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _clean_runs():
    conn = get_connection()
    try:
        conn.execute("DELETE FROM run_stages")
        conn.execute("DELETE FROM runs")
        conn.commit()
    finally:
        conn.close()


async def test_openapi_json_loads_and_contains_tags(client):
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema

    operation_tags = set()
    for path_item in schema["paths"].values():
        for operation in path_item.values():
            if isinstance(operation, dict):
                operation_tags.update(operation.get("tags", []))

    assert {
        "System",
        "Runs",
        "Run Stages",
        "Strategies",
        "Artifacts",
        "Metrics",
        "Logs",
        "Retry History",
        "Audit Logs",
    }.issubset(operation_tags)


async def test_health_still_works(client):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["backend"] == "healthy"


async def test_invalid_run_id_returns_clean_404(client):
    response = await client.get("/api/runs/not-a-real-run")

    assert response.status_code == 404
    data = response.json()
    assert data == {
        "error": True,
        "type": "not_found",
        "message": "Run not-a-real-run not found",
        "details": {},
    }


async def test_invalid_status_returns_clean_400(client):
    _clean_runs()
    create_response = await client.post(
        "/api/runs",
        json={"name": "Contract Run", "mode": "generate_strategy"},
    )
    run_id = create_response.json()["id"]

    response = await client.post(
        f"/api/runs/{run_id}/status",
        json={"status": "not_a_status"},
    )

    assert response.status_code == 400
    data = response.json()
    assert data["error"] is True
    assert data["type"] == "validation_error"
    assert "Invalid status" in data["message"]
    assert data["details"] == {}


async def test_error_response_does_not_contain_traceback(client):
    response = await client.get("/api/runs/not-a-real-run")
    body = json.dumps(response.json()).lower()

    assert "traceback" not in body
    assert "stack" not in body


async def test_public_settings_does_not_expose_secrets(client):
    response = await client.get("/api/settings/public")

    assert response.status_code == 200
    body = json.dumps(response.json()).lower()
    assert "discord_bot_token" not in body
    assert "app_secret_key" not in body
    assert "change-me" not in body
    assert "***masked***" in response.json()["database_url"]
