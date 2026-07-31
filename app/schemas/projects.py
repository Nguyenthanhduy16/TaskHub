from datetime import datetime

from pydantic import Field

from app.models.enums import ProjectStatus
from app.schemas.base import APIModel


class ProjectCreate(APIModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProjectUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class ProjectRead(APIModel):
    id: int
    workspace_id: int
    name: str
    description: str | None
    status: ProjectStatus
    created_at: datetime
