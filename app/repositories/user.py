from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return cast(User | None, await self.session.scalar(statement))


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RefreshToken)

    async def get_by_token_id(self, token_id: str) -> RefreshToken | None:
        statement = select(RefreshToken).where(RefreshToken.token_id == token_id)
        return cast(RefreshToken | None, await self.session.scalar(statement))
