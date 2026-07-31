from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TaskPriority, TaskStatus
from app.models.task import Task
from app.repositories.base import BaseRepository, Page


class TaskRepository(BaseRepository[Task]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Task)

    async def list_for_project(
        self,
        project_id: int,
        *,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assignee_id: int | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> Page[Task]:
        statement = select(Task).where(Task.project_id == project_id)
        if status is not None:
            statement = statement.where(Task.status == status)
        if priority is not None:
            statement = statement.where(Task.priority == priority)
        if assignee_id is not None:
            statement = statement.where(Task.assignee_id == assignee_id)
        statement = statement.order_by(Task.id)
        return await self.paginate(page=page, limit=limit, statement=statement)
