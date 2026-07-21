import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.routes.dispatch import verify_jwt_token

@pytest.fixture
def client():
    app.dependency_overrides[verify_jwt_token] = lambda: "mock_token"
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_preview_template_success(client):
    """
    Assert successful preview behavior remains unchanged.
    """
    with patch("app.routes.templates.render_preview") as mock_render:
        mock_render.return_value = {
            "title": "Rendered Title",
            "body": "Rendered Body"
        }
        
        response = client.post(
            "/templates/preview",
            json={
                "title_template": "Hello {{ name }}",
                "body_template": "Welcome!",
                "mock_context": {"name": "Test"}
            }
        )
        
        assert response.status_code == 200
        assert response.json() == {
            "rendered_title": "Rendered Title",
            "rendered_body": "Rendered Body"
        }

def test_preview_template_failure_sanitized(client):
    """
    On rendering failure, return HTTP 400 with a fixed message.
    Sensitive exception details must be hidden.
    """
    with patch("app.routes.templates.render_preview") as mock_render:
        sensitive_marker = "SUPER_SECRET_JINJA_INTERNAL_ERROR_12345"
        mock_render.side_effect = Exception(f"Failed because {sensitive_marker}")
        
        response = client.post(
            "/templates/preview",
            json={
                "title_template": "Hello {{ name }}",
                "body_template": "Welcome!",
                "mock_context": {"name": "Test"}
            }
        )
        
        assert response.status_code == 400
        
        # Assert response detail equals exactly "Template render failed."
        assert response.json()["detail"] == "Template render failed."
        
        # Assert the sensitive marker is absent from the complete response.
        assert sensitive_marker not in response.text

def test_preview_template_auth_validation_unchanged():
    """
    Assert authentication and request validation behavior remain unchanged.
    """
    client = TestClient(app)
    response = client.post(
        "/templates/preview",
        json={
            "title_template": "Hello {{ name }}",
            "body_template": "Welcome!",
            "mock_context": {"name": "Test"}
        }
    )
    
    # Expect 403 Forbidden or 401 Unauthorized because of missing token
    assert response.status_code in (401, 403)


def test_template_routes_registered_once() -> None:
    """
    Verify that the /templates router is not duplicated.
    """
    from app.main import app as main_app
    
    # We expect a few specific template endpoints, like POST /templates and GET /templates
    template_routes = [
        route for route in main_app.routes 
        if hasattr(route, "path") and route.path.startswith("/templates")
    ]
    
    # Check uniqueness based on (path, method) combination
    seen_endpoints = set()
    for route in template_routes:
        # A route might have multiple methods, typically one for APIRoute
        methods = getattr(route, "methods", set())
        for method in methods:
            endpoint_signature = (route.path, method)
            assert endpoint_signature not in seen_endpoints, (
                f"Duplicate route detected: {route.path} [{method}]"
            )
            seen_endpoints.add(endpoint_signature)
