from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.repositories.base import BaseRepository


class CommentRepository(BaseRepository[Comment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Comment)

    async def list_for_task(self, task_id: int) -> list[Comment]:
        statement = (
            select(Comment).where(Comment.task_id == task_id).order_by(Comment.id)
        )
        result = await self.session.scalars(statement)
        return list(result.all())
