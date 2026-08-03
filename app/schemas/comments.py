from datetime import datetime

from pydantic import Field

from app.schemas.base import APIModel


class CommentCreate(APIModel):
    content: str = Field(min_length=1, max_length=5000)


class CommentRead(APIModel):
    id: int
    task_id: int
    author_id: int
    content: str
    created_at: datetime
