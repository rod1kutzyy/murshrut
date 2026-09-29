from pathlib import Path

import pytest
import yaml
from httpx import ASGITransport, AsyncClient

from app.main import app

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
async def test_swagger_ui_and_openapi_are_public():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        docs = await client.get("/api/docs")
        schema_response = await client.get("/api/openapi.json")

    assert docs.status_code == 200
    assert "/api/openapi.json" in docs.text
    assert schema_response.status_code == 200
    schema = schema_response.json()
    assert schema["openapi"].startswith("3.1.")
    assert schema["info"]["version"] == "1.0.0"
    assert [tag["name"] for tag in schema["tags"]] == [
        "system",
        "auth",
        "profile",
        "events",
        "evenings",
        "admin",
    ]


def test_openapi_documents_paths_security_and_errors():
    schema = app.openapi()
    assert set(schema["paths"]) == {
        "/api/health",
        "/api/v1/config",
        "/api/v1/categories",
        "/api/v1/auth/max",
        "/api/v1/auth/demo",
        "/api/v1/users/me",
        "/api/v1/users/me/preferences",
        "/api/v1/recommendations",
        "/api/v1/events/catalog",
        "/api/v1/events/favorites",
        "/api/v1/events/{event_id}",
        "/api/v1/events/{event_id}/reaction",
        "/api/v1/evenings/generate",
        "/api/v1/evenings",
        "/api/v1/evenings/{plan_id}",
        "/api/v1/evenings/{plan_id}/save",
        "/api/admin/events/sync",
    }
    schemes = schema["components"]["securitySchemes"]
    assert schemes["BearerAuth"]["scheme"] == "bearer"
    assert schemes["AdminToken"] == {
        "type": "apiKey",
        "description": "Секрет ручной синхронизации событий.",
        "in": "header",
        "name": "X-Admin-Token",
    }
    assert schema["paths"]["/api/v1/recommendations"]["get"]["security"] == [
        {"BearerAuth": []}
    ]
    assert schema["paths"]["/api/admin/events/sync"]["post"]["security"] == [
        {"AdminToken": []}
    ]
    responses = schema["paths"]["/api/v1/events/catalog"]["get"]["responses"]
    assert {"401", "409", "422", "502"} <= set(responses)


def test_openapi_yaml_snapshot_is_current():
    snapshot = yaml.safe_load((ROOT / "docs" / "openapi.yaml").read_text())
    assert snapshot == app.openapi()
