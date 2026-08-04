from fastapi import status

from app.core.exceptions import AppError
from app.models.enums import WorkspaceRole
from app.models.workspace import WorkspaceMember
from app.repositories.workspace import WorkspaceMemberRepository


class WorkspaceAccessPolicy:
    """Centralized workspace membership and role checks for resource services."""

    def __init__(self, members: WorkspaceMemberRepository) -> None:
        self.members = members

    async def require_membership(self, workspace_id: int, user_id: int) -> WorkspaceMember:
        membership = await self.members.get_member(workspace_id, user_id)
        if membership is None:
            raise AppError(
                "Workspace access is denied.",
                status_code=status.HTTP_403_FORBIDDEN,
                code="workspace_access_denied",
            )
        return membership

    async def require_role(
        self,
        workspace_id: int,
        user_id: int,
        allowed_roles: set[WorkspaceRole],
    ) -> WorkspaceMember:
        membership = await self.require_membership(workspace_id, user_id)
        if membership.role not in allowed_roles:
            raise AppError(
                "Workspace action is not permitted.",
                status_code=status.HTTP_403_FORBIDDEN,
                code="workspace_permission_denied",
            )
        return membership
