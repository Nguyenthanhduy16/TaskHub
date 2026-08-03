from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.enums import WorkspaceRole
from app.models.label import Label
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.repositories.label import LabelRepository
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.repositories.task_label import TaskLabelRepository
from app.repositories.workspace import WorkspaceMemberRepository
from app.schemas.labels import LabelCreate, LabelUpdate


class LabelService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectRepository(session)
        self.tasks = TaskRepository(session)
        self.labels = LabelRepository(session)
        self.task_labels = TaskLabelRepository(session)
        self.members = WorkspaceMemberRepository(session)

    async def create_label(
        self,
        current_user: User,
        project_id: int,
        payload: LabelCreate,
    ) -> Label:
        project = await self._require_project(project_id)
        await self._require_role(
            project.workspace_id,
            current_user.id,
            {WorkspaceRole.OWNER, WorkspaceRole.EDITOR},
        )
        label = await self.labels.create(
            project_id=project.id,
            name=payload.name.strip(),
            color=payload.color.strip(),
        )
        await self.session.commit()
        await self.session.refresh(label)
        return label

    async def list_labels(self, current_user: User, project_id: int) -> list[Label]:
        project = await self._require_project(project_id)
        await self._require_membership(project.workspace_id, current_user.id)
        return await self.labels.list_for_project(project_id)

    async def update_label(
        self,
        current_user: User,
        label_id: int,
        payload: LabelUpdate,
    ) -> Label:
        label = await self._require_label(label_id)
        project = await self._require_project(label.project_id)
        await self._require_role(
            project.workspace_id,
            current_user.id,
            {WorkspaceRole.OWNER, WorkspaceRole.EDITOR},
        )
        updates = payload.model_dump(exclude_unset=True)
        name = updates.get("name")
        if isinstance(name, str):
            label.name = name.strip()
        color = updates.get("color")
        if isinstance(color, str):
            label.color = color.strip()
        await self.session.commit()
        await self.session.refresh(label)
        return label

    async def delete_label(self, current_user: User, label_id: int) -> None:
        label = await self._require_label(label_id)
        project = await self._require_project(label.project_id)
        await self._require_role(
            project.workspace_id,
            current_user.id,
            {WorkspaceRole.OWNER, WorkspaceRole.EDITOR},
        )
        await self.labels.delete(label)
        await self.session.commit()

    async def list_task_labels(self, current_user: User, task_id: int) -> list[Label]:
        task = await self._require_task(task_id)
        project = await self._require_project(task.project_id)
        await self._require_membership(project.workspace_id, current_user.id)
        return await self.task_labels.list_labels_for_task(task_id)

    async def attach_label(self, current_user: User, task_id: int, label_id: int) -> Label:
        task = await self._require_task(task_id)
        project = await self._require_project(task.project_id)
        await self._require_role(
            project.workspace_id,
            current_user.id,
            {WorkspaceRole.OWNER, WorkspaceRole.EDITOR},
        )
        label = await self._require_label(label_id)
        if label.project_id != project.id:
            raise AppError(
                "Label does not belong to the task's project.",
                status_code=status.HTTP_400_BAD_REQUEST,
                code="label_project_mismatch",
            )
        await self.task_labels.attach(task_id, label_id)
        await self.session.commit()
        return label

    async def detach_label(self, current_user: User, task_id: int, label_id: int) -> None:
        task = await self._require_task(task_id)
        project = await self._require_project(task.project_id)
        await self._require_role(
            project.workspace_id,
            current_user.id,
            {WorkspaceRole.OWNER, WorkspaceRole.EDITOR},
        )
        await self.task_labels.detach(task_id, label_id)
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

    async def _require_label(self, label_id: int) -> Label:
        label = await self.labels.get(label_id)
        if label is None:
            raise AppError(
                "Label was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
                code="label_not_found",
            )
        return label

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
