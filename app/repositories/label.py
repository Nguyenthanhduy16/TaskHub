from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.label import Label
from app.repositories.base import BaseRepository


class LabelRepository(BaseRepository[Label]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Label)

    async def list_for_project(self, project_id: int) -> list[Label]:
        statement = (
            select(Label).where(Label.project_id == project_id).order_by(Label.id)
        )
        result = await self.session.scalars(statement)
        return list(result.all())

    async def get_for_project(self, project_id: int, label_id: int) -> Label | None:
        statement = select(Label).where(Label.id == label_id, Label.project_id == project_id)
        return cast(Label | None, await self.session.scalar(statement))
