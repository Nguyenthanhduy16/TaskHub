from pydantic import Field

from app.schemas.base import APIModel

_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class UserCreate(APIModel):
    email: str = Field(min_length=3, max_length=255, pattern=_EMAIL_PATTERN)
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(APIModel):
    email: str = Field(min_length=3, max_length=255, pattern=_EMAIL_PATTERN)
    password: str = Field(min_length=1, max_length=128)


class TokenPair(APIModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(APIModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(APIModel):
    refresh_token: str = Field(min_length=1)
