from dataclasses import dataclass
from math import ceil
from typing import Any, Generic, TypeVar, cast

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


@dataclass(frozen=True)
class Page(Generic[ModelT]):
    items: list[ModelT]
    total: int
    page: int
    limit: int

    @property
    def pages(self) -> int:
        if self.total == 0:
            return 0
        return ceil(self.total / self.limit)


class BaseRepository(Generic[ModelT]):
    def __init__(self, session: AsyncSession, model_type: type[ModelT]) -> None:
        self.session = session
        self.model_type = model_type

    async def get(self, object_id: Any) -> ModelT | None:
        return cast(ModelT | None, await self.session.get(self.model_type, object_id))

    async def list(self, *, offset: int = 0, limit: int = 100) -> list[ModelT]:
        statement = select(self.model_type).offset(offset).limit(limit)
        result = await self.session.scalars(statement)
        return list(result.all())

    async def paginate(
        self,
        *,
        page: int = 1,
        limit: int = 20,
        statement: Select[tuple[ModelT]] | None = None,
    ) -> Page[ModelT]:
        safe_page = max(page, 1)
        safe_limit = min(max(limit, 1), 100)
        base_statement = statement or select(self.model_type)

        total_statement = select(func.count()).select_from(base_statement.order_by(None).subquery())
        total = await self.session.scalar(total_statement)

        result = await self.session.scalars(
            base_statement.offset((safe_page - 1) * safe_limit).limit(safe_limit),
        )
        return Page(
            items=list(result.all()),
            total=total or 0,
            page=safe_page,
            limit=safe_limit,
        )

    async def create(self, **data: Any) -> ModelT:
        instance = self.model_type(**data)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update(self, instance: ModelT, **data: Any) -> ModelT:
        for field, value in data.items():
            setattr(instance, field, value)
        await self.session.flush()
        return instance

    async def delete(self, instance: ModelT) -> None:
        await self.session.delete(instance)
        await self.session.flush()

