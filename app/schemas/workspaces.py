from datetime import datetime

from pydantic import Field

from app.models.enums import WorkspaceRole
from app.schemas.base import APIModel

_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class WorkspaceCreate(APIModel):
    name: str = Field(min_length=1, max_length=255)


class WorkspaceUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)


class WorkspaceRead(APIModel):
    id: int
    name: str
    owner_id: int
    created_at: datetime


class WorkspaceInviteRequest(APIModel):
    email: str = Field(min_length=3, max_length=255, pattern=_EMAIL_PATTERN)
    role: WorkspaceRole = WorkspaceRole.VIEWER


class WorkspaceMemberRoleUpdate(APIModel):
    role: WorkspaceRole


class WorkspaceMemberRead(APIModel):
    workspace_id: int
    user_id: int
    role: WorkspaceRole