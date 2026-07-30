from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace, WorkspaceMember
from app.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Workspace)

    async def list_for_user(self, user_id: int) -> list[Workspace]:
        statement = (
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.id)
        )
        result = await self.session.scalars(statement)
        return list(result.all())


class WorkspaceMemberRepository(BaseRepository[WorkspaceMember]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, WorkspaceMember)

    async def get_member(self, workspace_id: int, user_id: int) -> WorkspaceMember | None:
        statement = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        return cast(WorkspaceMember | None, await self.session.scalar(statement))

    async def list_for_workspace(self, workspace_id: int) -> list[WorkspaceMember]:
        statement = (
            select(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.user_id)
        )
        result = await self.session.scalars(statement)
        return list(result.all())