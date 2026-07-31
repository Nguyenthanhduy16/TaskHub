from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.enums import ProjectStatus, WorkspaceRole
from app.models.project import Project
from app.models.user import User
from app.repositories.project import ProjectRepository
from app.repositories.workspace import WorkspaceMemberRepository, WorkspaceRepository
from app.schemas.projects import ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectRepository(session)
        self.workspaces = WorkspaceRepository(session)
        self.members = WorkspaceMemberRepository(session)

    async def create_project(
        self,
        current_user: User,
        workspace_id: int,
        payload: ProjectCreate,
    ) -> Project:
        await self._require_workspace(workspace_id)
        await self._require_role(
            workspace_id,
            current_user.id,
            {WorkspaceRole.OWNER, WorkspaceRole.EDITOR},
        )
        project = await self.projects.create(
            workspace_id=workspace_id,
            name=payload.name.strip(),
            description=payload.description,
            status=ProjectStatus.ACTIVE,
        )
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def list_projects(self, current_user: User, workspace_id: int) -> list[Project]:
        await self._require_workspace(workspace_id)
        await self._require_membership(workspace_id, current_user.id)
        return await self.projects.list_for_workspace(workspace_id)

    async def get_project(self, current_user: User, project_id: int) -> Project:
        project = await self._require_project(project_id)
        await self._require_membership(project.workspace_id, current_user.id)
        return project

    async def update_project(
        self,
        current_user: User,
        project_id: int,
        payload: ProjectUpdate,
    ) -> Project:
        project = await self._require_project(project_id)
        await self._require_role(
            project.workspace_id,
            current_user.id,
            {WorkspaceRole.OWNER, WorkspaceRole.EDITOR},
        )
        updates = payload.model_dump(exclude_unset=True)
        name = updates.get("name")
        if isinstance(name, str):
            project.name = name.strip()
        if "description" in updates:
            project.description = updates["description"]
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def archive_project(self, current_user: User, project_id: int) -> Project:
        project = await self._require_project(project_id)
        await self._require_role(
            project.workspace_id,
            current_user.id,
            {WorkspaceRole.OWNER, WorkspaceRole.EDITOR},
        )
        project.status = ProjectStatus.ARCHIVED
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def delete_project(self, current_user: User, project_id: int) -> None:
        project = await self._require_project(project_id)
        await self._require_role(
            project.workspace_id,
            current_user.id,
            {WorkspaceRole.OWNER, WorkspaceRole.EDITOR},
        )
        await self.projects.delete(project)
        await self.session.commit()

    async def _require_workspace(self, workspace_id: int) -> None:
        workspace = await self.workspaces.get(workspace_id)
        if workspace is None:
            raise AppError(
                "Workspace was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
                code="workspace_not_found",
            )

    async def _require_project(self, project_id: int) -> Project:
        project = await self.projects.get(project_id)
        if project is None:
            raise AppError(
                "Project was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
                code="project_not_found",
            )
        return project

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
