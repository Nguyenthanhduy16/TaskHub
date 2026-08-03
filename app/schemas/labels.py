from pydantic import Field

from app.schemas.base import APIModel


class LabelCreate(APIModel):
    name: str = Field(min_length=1, max_length=100)
    color: str = Field(min_length=1, max_length=32)


class LabelUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None, min_length=1, max_length=32)


class LabelRead(APIModel):
    id: int
    project_id: int
    name: str
    color: str
