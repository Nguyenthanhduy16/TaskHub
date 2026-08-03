import asyncio
import json
from collections.abc import AsyncGenerator, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.dependencies import get_cache_client, get_session, get_session_factory
from app.main import create_app
from app.models import Base
from app.models.notification import Notification


class FakeCacheClient:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, *, ttl_seconds: int) -> None:
        self.store[key] = value

    async def delete_prefix(self, prefix: str) -> None:
        for key in [k for k in self.store if k.startswith(prefix)]:
            del self.store[key]

    async def close(self) -> None:
        return None


class ClientContext:
    def __init__(
        self,
        client: TestClient,
        async_session: async_sessionmaker[AsyncSession],
        cache: FakeCacheClient,
    ) -> None:
        self.client = client
        self.async_session = async_session
        self.cache = cache


@pytest.fixture
def ctx() -> Iterator[ClientContext]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    fake_cache = FakeCacheClient()

    async def create_schema() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with async_session() as session:
            yield session

    asyncio.run(create_schema())
    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_session_factory] = lambda: async_session
    app.dependency_overrides[get_cache_client] = lambda: fake_cache

    with TestClient(app) as test_client:
        yield ClientContext(test_client, async_session, fake_cache)

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def test_label_crud_and_task_label_assignment(ctx: ClientContext) -> None:
    client = ctx.client
    owner = create_user_and_headers(client, "owner.label@example.com")
    editor = create_user_and_headers(client, "editor.label@example.com")
    viewer = create_user_and_headers(client, "viewer.label@example.com")

    workspace_id = create_workspace(client, owner.headers)
    invite_member(client, owner.headers, workspace_id, "editor.label@example.com", "EDITOR")
    invite_member(client, owner.headers, workspace_id, "viewer.label@example.com", "VIEWER")
    project_id = create_project(client, editor.headers, workspace_id)
    other_project_id = create_project(client, editor.headers, workspace_id)

    viewer_create_response = client.post(
        f"/api/v1/projects/{project_id}/labels",
        headers=viewer.headers,
        json={"name": "Bug", "color": "#ff0000"},
    )
    assert viewer_create_response.status_code == 403

    create_response = client.post(
        f"/api/v1/projects/{project_id}/labels",
        headers=editor.headers,
        json={"name": "Bug", "color": "#ff0000"},
    )
    assert create_response.status_code == 201
    label = create_response.json()
    label_id = label["id"]
    assert label["project_id"] == project_id
    assert label["name"] == "Bug"
    assert label["color"] == "#ff0000"

    other_label_response = client.post(
        f"/api/v1/projects/{other_project_id}/labels",
        headers=editor.headers,
        json={"name": "Feature", "color": "#00ff00"},
    )
    assert other_label_response.status_code == 201
    other_label_id = other_label_response.json()["id"]

    list_response = client.get(f"/api/v1/projects/{project_id}/labels", headers=viewer.headers)
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [label_id]

    update_response = client.patch(
        f"/api/v1/labels/{label_id}",
        headers=owner.headers,
        json={"name": "Critical Bug"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Critical Bug"

    task_response = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=editor.headers,
        json={"title": "Fix crash"},
    )
    assert task_response.status_code == 201
    task_id = task_response.json()["id"]

    viewer_attach_response = client.post(
        f"/api/v1/tasks/{task_id}/labels/{label_id}",
        headers=viewer.headers,
    )
    assert viewer_attach_response.status_code == 403

    mismatch_response = client.post(
        f"/api/v1/tasks/{task_id}/labels/{other_label_id}",
        headers=editor.headers,
    )
    assert mismatch_response.status_code == 400

    attach_response = client.post(
        f"/api/v1/tasks/{task_id}/labels/{label_id}",
        headers=editor.headers,
    )
    assert attach_response.status_code == 201
    assert attach_response.json()["id"] == label_id

    task_labels_response = client.get(f"/api/v1/tasks/{task_id}/labels", headers=viewer.headers)
    assert task_labels_response.status_code == 200
    assert [item["id"] for item in task_labels_response.json()] == [label_id]

    detach_response = client.delete(
        f"/api/v1/tasks/{task_id}/labels/{label_id}",
        headers=editor.headers,
    )
    assert detach_response.status_code == 204

    empty_task_labels_response = client.get(
        f"/api/v1/tasks/{task_id}/labels",
        headers=viewer.headers,
    )
    assert empty_task_labels_response.json() == []

    delete_response = client.delete(f"/api/v1/labels/{label_id}", headers=owner.headers)
    assert delete_response.status_code == 204

    delete_again_response = client.delete(f"/api/v1/labels/{label_id}", headers=owner.headers)
    assert delete_again_response.status_code == 404


def test_comment_add_list_delete_permissions(ctx: ClientContext) -> None:
    client = ctx.client
    owner = create_user_and_headers(client, "owner.comment@example.com")
    editor = create_user_and_headers(client, "editor.comment@example.com")
    viewer = create_user_and_headers(client, "viewer.comment@example.com")
    outsider = create_user_and_headers(client, "outsider.comment@example.com")

    workspace_id = create_workspace(client, owner.headers)
    invite_member(client, owner.headers, workspace_id, "editor.comment@example.com", "EDITOR")
    invite_member(client, owner.headers, workspace_id, "viewer.comment@example.com", "VIEWER")
    project_id = create_project(client, editor.headers, workspace_id)
    task_response = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=editor.headers,
        json={"title": "Discuss rollout"},
    )
    task_id = task_response.json()["id"]

    outsider_comment_response = client.post(
        f"/api/v1/tasks/{task_id}/comments",
        headers=outsider.headers,
        json={"content": "Not allowed"},
    )
    assert outsider_comment_response.status_code == 403

    viewer_comment_response = client.post(
        f"/api/v1/tasks/{task_id}/comments",
        headers=viewer.headers,
        json={"content": "Looks good to me"},
    )
    assert viewer_comment_response.status_code == 201
    viewer_comment = viewer_comment_response.json()
    assert viewer_comment["author_id"] == viewer.user_id
    assert viewer_comment["content"] == "Looks good to me"

    editor_comment_response = client.post(
        f"/api/v1/tasks/{task_id}/comments",
        headers=editor.headers,
        json={"content": "Please add tests"},
    )
    assert editor_comment_response.status_code == 201
    editor_comment_id = editor_comment_response.json()["id"]

    list_response = client.get(f"/api/v1/tasks/{task_id}/comments", headers=viewer.headers)
    assert list_response.status_code == 200
    assert {item["id"] for item in list_response.json()} == {
        viewer_comment["id"],
        editor_comment_id,
    }

    outsider_list_response = client.get(
        f"/api/v1/tasks/{task_id}/comments",
        headers=outsider.headers,
    )
    assert outsider_list_response.status_code == 403

    viewer_delete_editor_comment_response = client.delete(
        f"/api/v1/comments/{editor_comment_id}",
        headers=viewer.headers,
    )
    assert viewer_delete_editor_comment_response.status_code == 403

    viewer_delete_own_comment_response = client.delete(
        f"/api/v1/comments/{viewer_comment['id']}",
        headers=viewer.headers,
    )
    assert viewer_delete_own_comment_response.status_code == 204

    editor_delete_response = client.delete(
        f"/api/v1/comments/{editor_comment_id}",
        headers=editor.headers,
    )
    assert editor_delete_response.status_code == 204

    delete_missing_response = client.delete(
        f"/api/v1/comments/{editor_comment_id}",
        headers=owner.headers,
    )
    assert delete_missing_response.status_code == 404


def test_task_list_cache_hit_and_invalidation(ctx: ClientContext) -> None:
    client = ctx.client
    owner = create_user_and_headers(client, "owner.cache@example.com")
    editor = create_user_and_headers(client, "editor.cache@example.com")

    workspace_id = create_workspace(client, owner.headers)
    invite_member(client, owner.headers, workspace_id, "editor.cache@example.com", "EDITOR")
    project_id = create_project(client, editor.headers, workspace_id)

    create_response = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=editor.headers,
        json={"title": "Ship feature"},
    )
    assert create_response.status_code == 201

    first_list_response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=editor.headers,
    )
    assert first_list_response.status_code == 200
    assert first_list_response.json()["total"] == 1

    cache_prefix = f"tasks:project:{project_id}:list:"
    cache_keys = [key for key in ctx.cache.store if key.startswith(cache_prefix)]
    assert len(cache_keys) == 1
    cache_key = cache_keys[0]

    sentinel_payload = {
        "items": [],
        "total": 999,
        "page": 1,
        "limit": 20,
        "pages": 1,
    }
    ctx.cache.store[cache_key] = json.dumps(sentinel_payload)

    cached_list_response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=editor.headers,
    )
    assert cached_list_response.status_code == 200
    assert cached_list_response.json()["total"] == 999

    second_create_response = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=editor.headers,
        json={"title": "Write docs"},
    )
    assert second_create_response.status_code == 201

    assert not [key for key in ctx.cache.store if key.startswith(cache_prefix)]

    fresh_list_response = client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=editor.headers,
    )
    assert fresh_list_response.status_code == 200
    assert fresh_list_response.json()["total"] == 2


def test_notification_created_on_task_assignment(ctx: ClientContext) -> None:
    client = ctx.client
    owner = create_user_and_headers(client, "owner.notify@example.com")
    editor = create_user_and_headers(client, "editor.notify@example.com")
    assignee = create_user_and_headers(client, "assignee.notify@example.com")

    workspace_id = create_workspace(client, owner.headers)
    invite_member(client, owner.headers, workspace_id, "editor.notify@example.com", "EDITOR")
    invite_member(client, owner.headers, workspace_id, "assignee.notify@example.com", "VIEWER")
    project_id = create_project(client, editor.headers, workspace_id)

    create_response = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=editor.headers,
        json={"title": "Onboard new hire", "assignee_id": assignee.user_id},
    )
    assert create_response.status_code == 201
    task_id = create_response.json()["id"]

    notifications = fetch_notifications_for_user(ctx.async_session, assignee.user_id)
    assert len(notifications) == 1
    assert notifications[0].task_id == task_id

    unassign_response = client.patch(
        f"/api/v1/tasks/{task_id}",
        headers=editor.headers,
        json={"assignee_id": None},
    )
    assert unassign_response.status_code == 200
    assert len(fetch_notifications_for_user(ctx.async_session, assignee.user_id)) == 1

    reassign_response = client.patch(
        f"/api/v1/tasks/{task_id}",
        headers=editor.headers,
        json={"assignee_id": assignee.user_id},
    )
    assert reassign_response.status_code == 200
    assert len(fetch_notifications_for_user(ctx.async_session, assignee.user_id)) == 2


def fetch_notifications_for_user(
    async_session: async_sessionmaker[AsyncSession],
    user_id: int,
) -> list[Notification]:
    async def _fetch() -> list[Notification]:
        async with async_session() as session:
            result = await session.scalars(
                select(Notification)
                .where(Notification.user_id == user_id)
                .order_by(Notification.id)
            )
            return list(result.all())

    return asyncio.run(_fetch())


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
