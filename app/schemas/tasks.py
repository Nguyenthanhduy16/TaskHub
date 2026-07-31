from datetime import datetime

from pydantic import Field

from app.models.enums import TaskPriority, TaskStatus
from app.schemas.base import APIModel


class TaskCreate(APIModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    assignee_id: int | None = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: datetime | None = None


class TaskUpdate(APIModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    assignee_id: int | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None


class TaskRead(APIModel):
    id: int
    project_id: int
    assignee_id: int | None
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: datetime | None
    created_by: int
    created_at: datetime


class TaskPage(APIModel):
    items: list[TaskRead]
    total: int
    page: int
    limit: int
    pages: int
