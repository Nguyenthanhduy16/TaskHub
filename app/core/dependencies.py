from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.db.session import get_db_session
from app.models.user import User
from app.services.auth import decode_access_token, require_int_subject

bearer_scheme = HTTPBearer(scheme_name="BearerAuth")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


def get_app_settings() -> Settings:
    return get_settings()


SessionDependency = Annotated[AsyncSession, Depends(get_session)]
SettingsDependency = Annotated[Settings, Depends(get_app_settings)]
AccessTokenDependency = Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]


async def get_current_user(
    session: SessionDependency,
    settings: SettingsDependency,
    token: AccessTokenDependency,
) -> User:
    payload = decode_access_token(token.credentials, settings)
    user_id = require_int_subject(payload)
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError(
            "Invalid authentication credentials.",
            status_code=401,
            code="invalid_credentials",
        )
    return user
