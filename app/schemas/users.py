from datetime import datetime

from pydantic import Field

from app.models.enums import UserRole
from app.schemas.base import APIModel

_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class UserRead(APIModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UserUpdate(APIModel):
    email: str | None = Field(default=None, min_length=3, max_length=255, pattern=_EMAIL_PATTERN)
    full_name: str | None = Field(default=None, min_length=1, max_length=255)


class ChangePasswordRequest(APIModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
