from fastapi.testclient import TestClient

from app.main import create_app


def test_health_check_returns_application_status() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "TaskHub API",
        "environment": "local",
        "version": "0.1.0",
    }


def test_unknown_route_uses_standard_error_shape() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/unknown")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"
