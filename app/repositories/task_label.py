from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.label import Label, TaskLabel


class TaskLabelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_labels_for_task(self, task_id: int) -> list[Label]:
        statement = (
            select(Label)
            .join(TaskLabel, TaskLabel.label_id == Label.id)
            .where(TaskLabel.task_id == task_id)
            .order_by(Label.id)
        )
        result = await self.session.scalars(statement)
        return list(result.all())

    async def is_attached(self, task_id: int, label_id: int) -> bool:
        statement = select(TaskLabel).where(
            TaskLabel.task_id == task_id,
            TaskLabel.label_id == label_id,
        )
        return await self.session.scalar(statement) is not None

    async def attach(self, task_id: int, label_id: int) -> None:
        if await self.is_attached(task_id, label_id):
            return
        self.session.add(TaskLabel(task_id=task_id, label_id=label_id))
        await self.session.flush()

    async def detach(self, task_id: int, label_id: int) -> None:
        statement = delete(TaskLabel).where(
            TaskLabel.task_id == task_id,
            TaskLabel.label_id == label_id,
        )
        await self.session.execute(statement)
        await self.session.flush()
