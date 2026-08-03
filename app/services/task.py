from fastapi import BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.cache import CacheClient, task_list_cache_key, task_list_cache_prefix
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.models.enums import TaskPriority, TaskStatus, WorkspaceRole
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.repositories.workspace import WorkspaceMemberRepository
from app.schemas.tasks import TaskCreate, TaskPage, TaskRead, TaskUpdate
from app.services.notification import notify_task_assigned


class TaskService:
    def __init__(self, session: AsyncSession, cache: CacheClient) -> None:
        self.session = session
        self.cache = cache
        self.cache_ttl_seconds = get_settings().task_list_cache_ttl_seconds
        self.projects = ProjectRepository(session)
        self.tasks = TaskRepository(session)
        self.members = WorkspaceMemberRepository(session)

    async def create_task(
        self,
        current_user: User,
        project_id: int,
        payload: TaskCreate,
        background_tasks: BackgroundTasks,
        session_factory: async_sessionmaker[AsyncSession],
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
        await self.cache.delete_prefix(task_list_cache_prefix(project.id))
        assignee_id = task.assignee_id
        if assignee_id is not None:
            background_tasks.add_task(
                notify_task_assigned,
                session_factory,
                assignee_id,
                task.id,
                task.title,
            )
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
    ) -> TaskPage:
        project = await self._require_project(project_id)
        await self._require_membership(project.workspace_id, current_user.id)
        if assignee_id is not None:
            await self._require_assignee_member(project.workspace_id, assignee_id)

        cache_key = task_list_cache_key(
            project_id,
            status=task_status.value if task_status is not None else None,
            priority=priority.value if priority is not None else None,
            assignee_id=assignee_id,
            page=page,
            limit=limit,
        )
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return TaskPage.model_validate_json(cached)

        task_page = await self.tasks.list_for_project(
            project_id,
            status=task_status,
            priority=priority,
            assignee_id=assignee_id,
            page=page,
            limit=limit,
        )
        response = TaskPage(
            items=[TaskRead.model_validate(task) for task in task_page.items],
            total=task_page.total,
            page=task_page.page,
            limit=task_page.limit,
            pages=task_page.pages,
        )
        await self.cache.set(
            cache_key,
            response.model_dump_json(),
            ttl_seconds=self.cache_ttl_seconds,
        )
        return response

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
        background_tasks: BackgroundTasks,
        session_factory: async_sessionmaker[AsyncSession],
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
        previous_assignee_id = task.assignee_id
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
        await self.cache.delete_prefix(task_list_cache_prefix(project.id))
        assignee_id = task.assignee_id
        if assignee_id is not None and assignee_id != previous_assignee_id:
            background_tasks.add_task(
                notify_task_assigned,
                session_factory,
                assignee_id,
                task.id,
                task.title,
            )
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
        await self.cache.delete_prefix(task_list_cache_prefix(project.id))

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