from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.notification import NotificationRepository


async def notify_task_assigned(
    session_factory: async_sessionmaker[AsyncSession],
    assignee_id: int,
    task_id: int,
    task_title: str,
) -> None:
    async with session_factory() as session:
        notifications = NotificationRepository(session)
        await notifications.create(
            user_id=assignee_id,
            task_id=task_id,
            message=f'You were assigned to task "{task_title}".',
            is_read=False,
        )
        await session.commit()
