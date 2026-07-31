from collections.abc import AsyncGenerator, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.dependencies import get_session
from app.main import create_app
from app.models import Base


@pytest.fixture
def client() -> Iterator[TestClient]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async def create_schema() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with async_session() as session:
            yield session

    import asyncio

    asyncio.run(create_schema())
    app = create_app()
    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def test_task_crud_filter_pagination_and_rbac(client: TestClient) -> None:
    owner = create_user_and_headers(client, "owner.task@example.com")
    editor = create_user_and_headers(client, "editor.task@example.com")
    viewer = create_user_and_headers(client, "viewer.task@example.com")
    outsider = create_user_and_headers(client, "outsider.task@example.com")

    workspace_id = create_workspace(client, owner.headers)
    invite_member(client, owner.headers, workspace_id, "editor.task@example.com", "EDITOR")
    invite_member(client, owner.headers, workspace_id, "viewer.task@example.com", "VIEWER")
    project_id = create_project(client, editor.headers, workspace_id)

    invalid_assignee_response = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=editor.headers,
        json={"title": "Invalid assignee", "assignee_id": outsider.user_id},
    )
    assert invalid_assignee_response.status_code == 400

    create_response = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=editor.headers,
        json={
            "title": "Build task API",
            "description": "CRUD and filters",
            "assignee_id": viewer.user_id,
            "priority": "HIGH",
            "due_date": "2026-08-02T10:00:00Z",
        },
    )
    assert create_response.status_code == 201
    task = create_response.json()
    task_id = task["id"]
    assert task["project_id"] == project_id
    assert task["assignee_id"] == viewer.user_id
    assert task["status"] == "TODO"
    assert task["priority"] == "HIGH"
    assert task["created_by"] == editor.user_id

    second_response = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=owner.headers,
        json={"title": "Ship task API", "assignee_id": editor.user_id, "priority": "LOW"},
    )
    assert second_response.status_code == 201

    viewer_create_response = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=viewer.headers,
        json={"title": "Viewer cannot create"},
    )
    assert viewer_create_response.status_code == 403

    list_response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=viewer.headers,
        params={"priority": "HIGH", "assignee_id": viewer.user_id, "page": 1, "limit": 1},
    )
    assert list_response.status_code == 200
    page = list_response.json()
    assert page["total"] == 1
    assert page["page"] == 1
    assert page["limit"] == 1
    assert page["pages"] == 1
    assert [item["id"] for item in page["items"]] == [task_id]

    outsider_list_response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=outsider.headers,
    )
    assert outsider_list_response.status_code == 403

    update_response = client.patch(
        f"/api/v1/tasks/{task_id}",
        headers=owner.headers,
        json={
            "title": "Build task management API",
            "status": "IN_PROGRESS",
            "priority": "URGENT",
            "assignee_id": None,
            "due_date": None,
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["title"] == "Build task management API"
    assert updated["status"] == "IN_PROGRESS"
    assert updated["priority"] == "URGENT"
    assert updated["assignee_id"] is None
    assert updated["due_date"] is None

    viewer_update_response = client.patch(
        f"/api/v1/tasks/{task_id}",
        headers=viewer.headers,
        json={"status": "DONE"},
    )
    assert viewer_update_response.status_code == 403

    delete_response = client.delete(f"/api/v1/tasks/{task_id}", headers=editor.headers)
    assert delete_response.status_code == 204

    deleted_get_response = client.get(f"/api/v1/tasks/{task_id}", headers=viewer.headers)
    assert deleted_get_response.status_code == 404


def test_task_endpoints_require_bearer_token(client: TestClient) -> None:
    response = client.get("/api/v1/projects/1/tasks")

    assert response.status_code == 401


class CreatedUser:
    def __init__(self, user_id: int, headers: dict[str, str]) -> None:
        self.user_id = user_id
        self.headers = headers


def create_user_and_headers(client: TestClient, email: str) -> CreatedUser:
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": email.split("@")[0], "password": "password123"},
    )
    assert register_response.status_code == 201
    user_id = register_response.json()["id"]

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    return CreatedUser(user_id=user_id, headers={"Authorization": f"Bearer {access_token}"})


def create_workspace(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post("/api/v1/workspaces", headers=headers, json={"name": "Engineering"})
    assert response.status_code == 201
    return int(response.json()["id"])


def invite_member(
    client: TestClient,
    headers: dict[str, str],
    workspace_id: int,
    email: str,
    role: str,
) -> None:
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        headers=headers,
        json={"email": email, "role": role},
    )
    assert response.status_code == 201


def create_project(client: TestClient, headers: dict[str, str], workspace_id: int) -> int:
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/projects",
        headers=headers,
        json={"name": "API", "description": "TaskHub API"},
    )
    assert response.status_code == 201
    return int(response.json()["id"])
