from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Project)

    async def list_for_workspace(self, workspace_id: int) -> list[Project]:
        statement = select(Project).where(Project.workspace_id == workspace_id).order_by(Project.id)
        result = await self.session.scalars(statement)
        return list(result.all())
