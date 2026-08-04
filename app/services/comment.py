from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.comment import Comment
from app.models.enums import WorkspaceRole
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.repositories.comment import CommentRepository
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.repositories.workspace import WorkspaceMemberRepository
from app.schemas.comments import CommentCreate
from app.services.access import WorkspaceAccessPolicy


class CommentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectRepository(session)
        self.tasks = TaskRepository(session)
        self.comments = CommentRepository(session)
        self.members = WorkspaceMemberRepository(session)
        self.access = WorkspaceAccessPolicy(self.members)

    async def list_comments(self, current_user: User, task_id: int) -> list[Comment]:
        task = await self._require_task(task_id)
        project = await self._require_project(task.project_id)
        await self.access.require_membership(project.workspace_id, current_user.id)
        return await self.comments.list_for_task(task_id)

    async def add_comment(
        self,
        current_user: User,
        task_id: int,
        payload: CommentCreate,
    ) -> Comment:
        task = await self._require_task(task_id)
        project = await self._require_project(task.project_id)
        await self.access.require_membership(project.workspace_id, current_user.id)
        comment = await self.comments.create(
            task_id=task.id,
            author_id=current_user.id,
            content=payload.content.strip(),
        )
        await self.session.commit()
        await self.session.refresh(comment)
        return comment

    async def delete_comment(self, current_user: User, comment_id: int) -> None:
        comment = await self._require_comment(comment_id)
        task = await self._require_task(comment.task_id)
        project = await self._require_project(task.project_id)
        membership = await self.access.require_membership(
            project.workspace_id,
            current_user.id,
        )
        is_author = comment.author_id == current_user.id
        is_moderator = membership.role in {WorkspaceRole.OWNER, WorkspaceRole.EDITOR}
        if not is_author and not is_moderator:
            raise AppError(
                "Only the comment author or a workspace editor can delete this comment.",
                status_code=status.HTTP_403_FORBIDDEN,
                code="workspace_permission_denied",
            )
        await self.comments.delete(comment)
        await self.session.commit()

    async def _require_project(self, project_id: int) -> Project:
        project = await self.projects.get(project_id)
        if project is None:
            raise AppError(
                "Project was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
                code="project_not_found",
            )
        return project

    async def _require_task(self, task_id: int) -> Task:
        task = await self.tasks.get(task_id)
        if task is None:
            raise AppError(
                "Task was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
                code="task_not_found",
            )
        return task

    async def _require_comment(self, comment_id: int) -> Comment:
        comment = await self.comments.get(comment_id)
        if comment is None:
            raise AppError(
                "Comment was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
                code="comment_not_found",
            )
        return comment
