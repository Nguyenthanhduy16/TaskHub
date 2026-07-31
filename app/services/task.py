from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.enums import TaskPriority, TaskStatus, WorkspaceRole
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.repositories.base import Page
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.repositories.workspace import WorkspaceMemberRepository
from app.schemas.tasks import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectRepository(session)
        self.tasks = TaskRepository(session)
        self.members = WorkspaceMemberRepository(session)

    async def create_task(
        self,
        current_user: User,
        project_id: int,
        payload: TaskCreate,
    ) -> Task:
        project = await self._require_project(project_id)
        await self._require_role(
            project.workspace_id,
            current_user.id,
            {WorkspaceRole.OWNER, WorkspaceRole.EDITOR},
        )
        if payload.assignee_id is not None:
            await self._require_assignee_member(project.workspace_id, payload.assignee_id)

        task = await self.tasks.create(
            project_id=project.id,
            assignee_id=payload.assignee_id,
            title=payload.title.strip(),
            description=payload.description,
            status=payload.status,
            priority=payload.priority,
            due_date=payload.due_date,
            created_by=current_user.id,
        )
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def list_tasks(
        self,
        current_user: User,
        project_id: int,
        *,
        task_status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assignee_id: int | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> Page[Task]:
        project = await self._require_project(project_id)
        await self._require_membership(project.workspace_id, current_user.id)
        if assignee_id is not None:
            await self._require_assignee_member(project.workspace_id, assignee_id)
        return await self.tasks.list_for_project(
            project_id,
            status=task_status,
            priority=priority,
            assignee_id=assignee_id,
            page=page,
            limit=limit,
        )

    async def get_task(self, current_user: User, task_id: int) -> Task:
        task = await self._require_task(task_id)
        project = await self._require_project(task.project_id)
        await self._require_membership(project.workspace_id, current_user.id)
        return task

    async def update_task(
        self,
        current_user: User,
        task_id: int,
        payload: TaskUpdate,
    ) -> Task:
        task = await self._require_task(task_id)
        project = await self._require_project(task.project_id)
        await self._require_role(
            project.workspace_id,
            current_user.id,
            {WorkspaceRole.OWNER, WorkspaceRole.EDITOR},
        )

        updates = payload.model_dump(exclude_unset=True)
        if "assignee_id" in updates and updates["assignee_id"] is not None:
            await self._require_assignee_member(project.workspace_id, updates["assignee_id"])
        title = updates.get("title")
        if isinstance(title, str):
            task.title = title.strip()
        if "description" in updates:
            task.description = updates["description"]
        if "assignee_id" in updates:
            task.assignee_id = updates["assignee_id"]
        if "status" in updates:
            task.status = updates["status"]
        if "priority" in updates:
            task.priority = updates["priority"]
        if "due_date" in updates:
            task.due_date = updates["due_date"]

        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def delete_task(self, current_user: User, task_id: int) -> None:
        task = await self._require_task(task_id)
        project = await self._require_project(task.project_id)
        await self._require_role(
            project.workspace_id,
            current_user.id,
            {WorkspaceRole.OWNER, WorkspaceRole.EDITOR},
        )
        await self.tasks.delete(task)
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

    async def _require_membership(self, workspace_id: int, user_id: int) -> None:
        membership = await self.members.get_member(workspace_id, user_id)
        if membership is None:
            raise AppError(
                "Workspace access is denied.",
                status_code=status.HTTP_403_FORBIDDEN,
                code="workspace_access_denied",
            )

    async def _require_role(
        self,
        workspace_id: int,
        user_id: int,
        allowed_roles: set[WorkspaceRole],
    ) -> None:
        membership = await self.members.get_member(workspace_id, user_id)
        if membership is None:
            raise AppError(
                "Workspace access is denied.",
                status_code=status.HTTP_403_FORBIDDEN,
                code="workspace_access_denied",
            )
        if membership.role not in allowed_roles:
            raise AppError(
                "Workspace action is not permitted.",
                status_code=status.HTTP_403_FORBIDDEN,
                code="workspace_permission_denied",
            )

    async def _require_assignee_member(self, workspace_id: int, user_id: int) -> None:
        membership = await self.members.get_member(workspace_id, user_id)
        if membership is None:
            raise AppError(
                "Task assignee must be a workspace member.",
                status_code=status.HTTP_400_BAD_REQUEST,
                code="invalid_task_assignee",
            )