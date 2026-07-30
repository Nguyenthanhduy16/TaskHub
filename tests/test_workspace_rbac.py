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


def test_workspace_owner_editor_viewer_permissions(client: TestClient) -> None:
    owner = create_user_and_headers(client, "owner@example.com")
    editor = create_user_and_headers(client, "editor@example.com")
    viewer = create_user_and_headers(client, "viewer@example.com")
    outsider = create_user_and_headers(client, "outsider@example.com")

    create_response = client.post(
        "/api/v1/workspaces",
        headers=owner.headers,
        json={"name": "Product Team"},
    )
    assert create_response.status_code == 201
    workspace = create_response.json()
    workspace_id = workspace["id"]
    assert workspace["owner_id"] == owner.user_id

    owner_members_response = client.get(
        f"/api/v1/workspaces/{workspace_id}/members",
        headers=owner.headers,
    )
    assert owner_members_response.status_code == 200
    assert owner_members_response.json() == [
        {"workspace_id": workspace_id, "user_id": owner.user_id, "role": "OWNER"},
    ]

    outsider_get_response = client.get(
        f"/api/v1/workspaces/{workspace_id}",
        headers=outsider.headers,
    )
    assert outsider_get_response.status_code == 403

    editor_invite_response = client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        headers=owner.headers,
        json={"email": "editor@example.com", "role": "EDITOR"},
    )
    assert editor_invite_response.status_code == 201
    assert editor_invite_response.json()["role"] == "EDITOR"

    viewer_invite_response = client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        headers=owner.headers,
        json={"email": "viewer@example.com", "role": "VIEWER"},
    )
    assert viewer_invite_response.status_code == 201
    assert viewer_invite_response.json()["role"] == "VIEWER"

    editor_update_response = client.patch(
        f"/api/v1/workspaces/{workspace_id}",
        headers=editor.headers,
        json={"name": "Product Platform"},
    )
    assert editor_update_response.status_code == 200
    assert editor_update_response.json()["name"] == "Product Platform"

    viewer_read_response = client.get(
        f"/api/v1/workspaces/{workspace_id}",
        headers=viewer.headers,
    )
    assert viewer_read_response.status_code == 200

    viewer_update_response = client.patch(
        f"/api/v1/workspaces/{workspace_id}",
        headers=viewer.headers,
        json={"name": "Viewer Rename"},
    )
    assert viewer_update_response.status_code == 403

    editor_invite_denied_response = client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        headers=editor.headers,
        json={"email": "outsider@example.com", "role": "VIEWER"},
    )
    assert editor_invite_denied_response.status_code == 403

    owner_role_assign_response = client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        headers=owner.headers,
        json={"email": "outsider@example.com", "role": "OWNER"},
    )
    assert owner_role_assign_response.status_code == 400

    promote_viewer_response = client.patch(
        f"/api/v1/workspaces/{workspace_id}/members/{viewer.user_id}",
        headers=owner.headers,
        json={"role": "EDITOR"},
    )
    assert promote_viewer_response.status_code == 200
    assert promote_viewer_response.json()["role"] == "EDITOR"

    promoted_viewer_update_response = client.patch(
        f"/api/v1/workspaces/{workspace_id}",
        headers=viewer.headers,
        json={"name": "Promoted Rename"},
    )
    assert promoted_viewer_update_response.status_code == 200

    remove_owner_response = client.delete(
        f"/api/v1/workspaces/{workspace_id}/members/{owner.user_id}",
        headers=owner.headers,
    )
    assert remove_owner_response.status_code == 400

    remove_editor_response = client.delete(
        f"/api/v1/workspaces/{workspace_id}/members/{editor.user_id}",
        headers=owner.headers,
    )
    assert remove_editor_response.status_code == 204

    removed_editor_get_response = client.get(
        f"/api/v1/workspaces/{workspace_id}",
        headers=editor.headers,
    )
    assert removed_editor_get_response.status_code == 403

    delete_response = client.delete(f"/api/v1/workspaces/{workspace_id}", headers=owner.headers)
    assert delete_response.status_code == 204

    deleted_get_response = client.get(f"/api/v1/workspaces/{workspace_id}", headers=viewer.headers)
    assert deleted_get_response.status_code == 404


def test_workspace_endpoints_require_bearer_token(client: TestClient) -> None:
    response = client.post("/api/v1/workspaces", json={"name": "No Auth"})

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
