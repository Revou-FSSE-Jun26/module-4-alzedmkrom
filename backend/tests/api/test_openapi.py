"""Swagger UI and OpenAPI document tests (BE-DOC-04, task 14.3).

The ``api_app`` fixture uses ``create_app(verify_db=False)`` with no
``FLASK_ENV`` or ``SWAGGER_ENABLED`` set, so ``swagger_enabled`` defaults to
``True`` and the docs routes are registered.
"""
import json
import os
from pathlib import Path

import pytest

from app import create_app
from app.openapi import OpenAPIError, build_openapi, document


# ---------------------------------------------------------------------------
# Helpers that use the shared api_app fixture (swagger_enabled=True).
# ---------------------------------------------------------------------------


@pytest.fixture
def docs_client(api_app):
    """Test client for the documentation routes."""
    with api_app.test_client() as client:
        with api_app.app_context():
            yield client


# ---------------------------------------------------------------------------
# GET /api/openapi.json
# ---------------------------------------------------------------------------


def test_openapi_json_returns_200_json(docs_client):
    response = docs_client.get("/api/openapi.json")
    assert response.status_code == 200
    assert "application/json" in response.content_type
    body = json.loads(response.data)
    assert body["openapi"] == "3.0.3"
    assert body["info"]["title"] == "RevoTask API"


def test_openapi_json_contains_health_path(docs_client):
    response = docs_client.get("/api/openapi.json")
    body = json.loads(response.data)
    assert "/api/health" in body["paths"]
    op = body["paths"]["/api/health"]["get"]
    assert op["summary"] == "Health check"
    assert op["tags"] == ["health"]


def test_openapi_json_contains_all_expected_paths(docs_client):
    response = docs_client.get("/api/openapi.json")
    body = json.loads(response.data)
    paths = set(body["paths"])
    expected = {
        "/api/auth/register",
        "/api/auth/login",
        "/api/users/me",
        "/api/boards",
        "/api/boards/{board_id}",
        "/api/boards/{board_id}/columns",
        "/api/boards/{board_id}/columns/reorder",
        "/api/boards/{board_id}/members",
        "/api/boards/{board_id}/members/{user_id}",
        "/api/boards/{board_id}/analytics",
        "/api/columns/{column_id}",
        "/api/columns/{column_id}/cards",
        "/api/cards",
        "/api/cards/{card_id}",
        "/api/cards/{card_id}/position",
        "/api/cards/{card_id}/comments",
        "/api/comments/{comment_id}",
        "/api/notifications",
        "/api/notifications/{notification_id}/read",
        "/api/health",
    }
    missing = expected - paths
    assert not missing, f"Missing paths in OpenAPI document: {missing}"


def test_openapi_json_excludes_docs_routes(docs_client):
    response = docs_client.get("/api/openapi.json")
    body = json.loads(response.data)
    paths = set(body["paths"])
    assert "/api/docs" not in paths
    assert "/api/openapi.json" not in paths


def test_openapi_json_has_bearer_auth_scheme(docs_client):
    response = docs_client.get("/api/openapi.json")
    body = json.loads(response.data)
    assert "bearerAuth" in body["components"]["securitySchemes"]


# ---------------------------------------------------------------------------
# GET /api/docs
# ---------------------------------------------------------------------------


def test_docs_page_returns_html(docs_client):
    response = docs_client.get("/api/docs")
    assert response.status_code == 200
    assert "text/html" in response.content_type
    assert b"swagger-ui" in response.data.lower()


# ---------------------------------------------------------------------------
# SWAGGER_ENABLED=false suppresses the docs routes
# ---------------------------------------------------------------------------


def test_swagger_disabled_in_production_by_default(monkeypatch):
    # Keep DATABASE_URL so create_app can configure the DB without error.
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.delenv("SWAGGER_ENABLED", raising=False)
    import app as app_module
    monkeypatch.setattr(app_module, "BACKEND_DIR", app_module.Path("/nonexistent"))
    app = create_app(verify_db=False)
    client = app.test_client()
    assert client.get("/api/docs").status_code == 404
    assert client.get("/api/openapi.json").status_code == 404


def test_swagger_enabled_true_overrides_production(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("SWAGGER_ENABLED", "true")
    import app as app_module
    monkeypatch.setattr(app_module, "BACKEND_DIR", app_module.Path("/nonexistent"))
    app = create_app(verify_db=False)
    client = app.test_client()
    assert client.get("/api/openapi.json").status_code == 200


# ---------------------------------------------------------------------------
# build_openapi raises OpenAPIError when a route lacks @document
# ---------------------------------------------------------------------------


def test_build_openapi_raises_for_undocumented_route():
    app = create_app(verify_db=False)
    with app.app_context():
        # Inject an undocumented route into the existing app.
        def _undocumented():
            return "", 200  # no __openapi__ attribute

        app.add_url_rule("/api/undocumented-test", "undocumented_test", _undocumented)
        with pytest.raises(OpenAPIError, match="undocumented-test"):
            build_openapi(app)
