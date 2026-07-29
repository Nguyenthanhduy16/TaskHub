from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.base import BaseRepository


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with async_session() as db_session:
        yield db_session

    await engine.dispose()


@pytest.mark.anyio
async def test_base_repository_crud_and_pagination(session: AsyncSession) -> None:
    repository = BaseRepository(session, User)

    created = await repository.create(
        email="member@example.com",
        full_name="TaskHub Member",
        hashed_password="hashed-password",
        role=UserRole.MEMBER,
    )
    await session.commit()

    found = await repository.get(created.id)
    assert found is not None
    assert found.email == "member@example.com"

    page = await repository.paginate(page=1, limit=10)
    assert page.total == 1
    assert page.pages == 1
    assert page.items[0].id == created.id

    updated = await repository.update(created, full_name="Updated Member")
    await session.commit()
    assert updated.full_name == "Updated Member"

    await repository.delete(created)
    await session.commit()

    assert await repository.get(created.id) is None

