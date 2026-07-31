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


def test_project_crud_archive_and_rbac(client: TestClient) -> None:
    owner = create_user_and_headers(client, "owner.project@example.com")
    editor = create_user_and_headers(client, "editor.project@example.com")
    viewer = create_user_and_headers(client, "viewer.project@example.com")
    outsider = create_user_and_headers(client, "outsider.project@example.com")

    workspace_response = client.post(
        "/api/v1/workspaces",
        headers=owner.headers,
        json={"name": "Engineering"},
    )
    assert workspace_response.status_code == 201
    workspace_id = workspace_response.json()["id"]

    invite_editor_response = client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        headers=owner.headers,
        json={"email": "editor.project@example.com", "role": "EDITOR"},
    )
    assert invite_editor_response.status_code == 201

    invite_viewer_response = client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        headers=owner.headers,
        json={"email": "viewer.project@example.com", "role": "VIEWER"},
    )
    assert invite_viewer_response.status_code == 201

    create_response = client.post(
        f"/api/v1/workspaces/{workspace_id}/projects",
        headers=editor.headers,
        json={"name": "API", "description": "TaskHub API"},
    )
    assert create_response.status_code == 201
    project = create_response.json()
    project_id = project["id"]
    assert project["workspace_id"] == workspace_id
    assert project["status"] == "ACTIVE"

    list_response = client.get(
        f"/api/v1/workspaces/{workspace_id}/projects",
        headers=viewer.headers,
    )
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [project_id]

    outsider_list_response = client.get(
        f"/api/v1/workspaces/{workspace_id}/projects",
        headers=outsider.headers,
    )
    assert outsider_list_response.status_code == 403

    viewer_update_response = client.patch(
        f"/api/v1/projects/{project_id}",
        headers=viewer.headers,
        json={"name": "Viewer Rename"},
    )
    assert viewer_update_response.status_code == 403

    update_response = client.patch(
        f"/api/v1/projects/{project_id}",
        headers=owner.headers,
        json={"name": "Core API", "description": None},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Core API"
    assert update_response.json()["description"] is None

    archive_response = client.post(
        f"/api/v1/projects/{project_id}/archive",
        headers=editor.headers,
    )
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "ARCHIVED"

    outsider_get_response = client.get(f"/api/v1/projects/{project_id}", headers=outsider.headers)
    assert outsider_get_response.status_code == 403

    delete_response = client.delete(f"/api/v1/projects/{project_id}", headers=owner.headers)
    assert delete_response.status_code == 204

    deleted_get_response = client.get(f"/api/v1/projects/{project_id}", headers=viewer.headers)
    assert deleted_get_response.status_code == 404


def test_project_endpoints_require_bearer_token(client: TestClient) -> None:
    response = client.get("/api/v1/workspaces/1/projects")

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
