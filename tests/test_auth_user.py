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


def test_auth_user_flow(client: TestClient) -> None:
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "Member@Example.com",
            "full_name": "TaskHub Member",
            "password": "initial-password",
        },
    )
    assert register_response.status_code == 201
    assert register_response.json()["email"] == "member@example.com"

    duplicate_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "member@example.com",
            "full_name": "Duplicate Member",
            "password": "initial-password",
        },
    )
    assert duplicate_response.status_code == 409

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "member@example.com", "password": "initial-password"},
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    profile_response = client.get("/api/v1/users/me", headers=auth_headers)
    assert profile_response.status_code == 200
    assert profile_response.json()["full_name"] == "TaskHub Member"

    update_response = client.patch(
        "/api/v1/users/me",
        headers=auth_headers,
        json={"full_name": "Updated Member", "email": "updated@example.com"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["email"] == "updated@example.com"
    assert update_response.json()["full_name"] == "Updated Member"

    refresh_response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 200
    rotated_refresh_token = refresh_response.json()["refresh_token"]

    reused_refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert reused_refresh_response.status_code == 401

    logout_response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": rotated_refresh_token},
    )
    assert logout_response.status_code == 204

    revoked_refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": rotated_refresh_token},
    )
    assert revoked_refresh_response.status_code == 401

    second_login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "updated@example.com", "password": "initial-password"},
    )
    assert second_login_response.status_code == 200
    second_tokens = second_login_response.json()

    change_password_response = client.post(
        "/api/v1/users/me/change-password",
        headers={"Authorization": f"Bearer {second_tokens['access_token']}"},
        json={"current_password": "initial-password", "new_password": "changed-password"},
    )
    assert change_password_response.status_code == 204

    old_password_response = client.post(
        "/api/v1/auth/login",
        json={"email": "updated@example.com", "password": "initial-password"},
    )
    assert old_password_response.status_code == 401

    new_password_response = client.post(
        "/api/v1/auth/login",
        json={"email": "updated@example.com", "password": "changed-password"},
    )
    assert new_password_response.status_code == 200


def test_openapi_documents_bearer_auth(client: TestClient) -> None:
    response = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    security_scheme = response.json()["components"]["securitySchemes"]["BearerAuth"]
    assert security_scheme["type"] == "http"
    assert security_scheme["scheme"] == "bearer"
