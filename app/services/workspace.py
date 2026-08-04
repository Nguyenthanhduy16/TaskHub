from typing import NoReturn

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.enums import WorkspaceRole
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.repositories.user import UserRepository
from app.repositories.workspace import WorkspaceMemberRepository, WorkspaceRepository
from app.schemas.workspaces import (
    WorkspaceCreate,
    WorkspaceInviteRequest,
    WorkspaceMemberRoleUpdate,
    WorkspaceUpdate,
)
from app.services.access import WorkspaceAccessPolicy


class WorkspaceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.workspaces = WorkspaceRepository(session)
        self.members = WorkspaceMemberRepository(session)
        self.access = WorkspaceAccessPolicy(self.members)

    async def create_workspace(self, current_user: User, payload: WorkspaceCreate) -> Workspace:
        workspace = await self.workspaces.create(
            name=payload.name.strip(),
            owner_id=current_user.id,
        )
        await self.members.create(
            workspace_id=workspace.id,
            user_id=current_user.id,
            role=WorkspaceRole.OWNER,
        )
        await self.session.commit()
        await self.session.refresh(workspace)
        return workspace

    async def list_workspaces(self, current_user: User) -> list[Workspace]:
        return await self.workspaces.list_for_user(current_user.id)

    async def get_workspace(self, current_user: User, workspace_id: int) -> Workspace:
        workspace = await self._require_workspace(workspace_id)
        await self.access.require_membership(workspace_id, current_user.id)
        return workspace

    async def update_workspace(
        self,
        current_user: User,
        workspace_id: int,
        payload: WorkspaceUpdate,
    ) -> Workspace:
        workspace = await self._require_workspace(workspace_id)
        await self.access.require_role(
            workspace_id,
            current_user.id,
            {WorkspaceRole.OWNER, WorkspaceRole.EDITOR},
        )
        updates = payload.model_dump(exclude_unset=True)
        name = updates.get("name")
        if isinstance(name, str):
            workspace.name = name.strip()
        await self.session.commit()
        await self.session.refresh(workspace)
        return workspace

    async def delete_workspace(self, current_user: User, workspace_id: int) -> None:
        workspace = await self._require_workspace(workspace_id)
        await self.access.require_role(workspace_id, current_user.id, {WorkspaceRole.OWNER})
        await self.workspaces.delete(workspace)
        await self.session.commit()

    async def list_members(self, current_user: User, workspace_id: int) -> list[WorkspaceMember]:
        await self._require_workspace(workspace_id)
        await self.access.require_membership(workspace_id, current_user.id)
        return await self.members.list_for_workspace(workspace_id)

    async def invite_member(
        self,
        current_user: User,
        workspace_id: int,
        payload: WorkspaceInviteRequest,
    ) -> WorkspaceMember:
        await self._require_workspace(workspace_id)
        await self.access.require_role(workspace_id, current_user.id, {WorkspaceRole.OWNER})
        role = _require_assignable_member_role(payload.role)

        invited_user = await self.users.get_by_email(payload.email.strip().lower())
        if invited_user is None:
            raise AppError(
                "User to invite was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
                code="invited_user_not_found",
            )

        existing_member = await self.members.get_member(workspace_id, invited_user.id)
        if existing_member is not None:
            raise AppError(
                "User is already a workspace member.",
                status_code=status.HTTP_409_CONFLICT,
                code="workspace_member_already_exists",
            )

        membership = await self.members.create(
            workspace_id=workspace_id,
            user_id=invited_user.id,
            role=role,
        )
        await self.session.commit()
        await self.session.refresh(membership)
        return membership

    async def update_member_role(
        self,
        current_user: User,
        workspace_id: int,
        user_id: int,
        payload: WorkspaceMemberRoleUpdate,
    ) -> WorkspaceMember:
        workspace = await self._require_workspace(workspace_id)
        await self.access.require_role(workspace_id, current_user.id, {WorkspaceRole.OWNER})
        role = _require_assignable_member_role(payload.role)

        membership = await self.access.require_membership(workspace_id, user_id)
        if membership.user_id == workspace.owner_id:
            raise_cannot_modify_owner()

        membership.role = role
        await self.session.commit()
        await self.session.refresh(membership)
        return membership

    async def remove_member(self, current_user: User, workspace_id: int, user_id: int) -> None:
        workspace = await self._require_workspace(workspace_id)
        await self.access.require_role(workspace_id, current_user.id, {WorkspaceRole.OWNER})
        membership = await self.access.require_membership(workspace_id, user_id)
        if membership.user_id == workspace.owner_id:
            raise_cannot_modify_owner()
        await self.members.delete(membership)
        await self.session.commit()

    async def _require_workspace(self, workspace_id: int) -> Workspace:
        workspace = await self.workspaces.get(workspace_id)
        if workspace is None:
            raise AppError(
                "Workspace was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
                code="workspace_not_found",
            )
        return workspace

def _require_assignable_member_role(role: WorkspaceRole) -> WorkspaceRole:
    if role == WorkspaceRole.OWNER:
        raise AppError(
            "OWNER role cannot be assigned through member management.",
            status_code=status.HTTP_400_BAD_REQUEST,
            code="owner_role_not_assignable",
        )
    return role


def raise_cannot_modify_owner() -> NoReturn:
    raise AppError(
        "Workspace owner membership cannot be modified.",
        status_code=status.HTTP_400_BAD_REQUEST,
        code="workspace_owner_cannot_be_modified",
    )
