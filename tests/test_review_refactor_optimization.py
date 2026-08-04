from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Table

from app.main import create_app
from app.models.task import Task


def test_request_context_middleware_adds_observability_and_security_headers() -> None:
    with TestClient(create_app()) as client:
        response = client.get(
            "/api/v1/health",
            headers={"X-Request-ID": "day8-test-request"},
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "day8-test-request"
    assert float(response.headers["X-Process-Time"]) >= 0
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_invalid_request_uses_documented_error_response() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/api/v1/auth/register", json={})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"]["errors"]


def test_unexpected_error_is_hidden_behind_standard_error_response() -> None:
    app = create_app()

    @app.get("/test-only/unexpected-error")
    async def raise_unexpected_error() -> None:
        raise RuntimeError("sensitive implementation detail")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/test-only/unexpected-error")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_server_error",
            "message": "An unexpected server error occurred.",
            "details": None,
        },
    }
    assert "sensitive" not in response.text
    assert response.headers["X-Request-ID"]


def test_openapi_documents_bearer_auth_tags_and_standard_errors() -> None:
    with TestClient(create_app()) as client:
        document = client.get("/api/v1/openapi.json").json()

    assert document["info"]["description"]
    assert document["components"]["securitySchemes"]["BearerAuth"] == {
        "type": "http",
        "scheme": "bearer",
    }
    tag_names = {tag["name"] for tag in document["tags"]}
    assert {"auth", "users", "workspaces", "projects", "tasks"} <= tag_names

    operation = document["paths"]["/api/v1/projects/{project_id}/tasks"]["get"]
    assert operation["security"] == [{"BearerAuth": []}]
    for status_code in ("400", "401", "403", "404", "409", "422", "500"):
        schema = operation["responses"][status_code]["content"]["application/json"]["schema"]
        assert schema == {"$ref": "#/components/schemas/ErrorResponse"}


def test_create_app_returns_fastapi_instance() -> None:
    assert isinstance(create_app(), FastAPI)


def test_task_filter_columns_have_composite_indexes() -> None:
    task_table = cast(Table, Task.__table__)
    indexes: dict[str, tuple[str, ...]] = {
        str(index.name): tuple(column.name for column in index.columns)
        for index in task_table.indexes
    }

    assert indexes["ix_tasks_project_status"] == ("project_id", "status")
    assert indexes["ix_tasks_project_priority"] == ("project_id", "priority")
    assert indexes["ix_tasks_project_assignee"] == ("project_id", "assignee_id")
