from datetime import timedelta
from typing import Any, NoReturn

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.security import (
    TokenError,
    create_jwt,
    decode_jwt,
    generate_token_id,
    hash_password,
    verify_password,
)
from app.db.base import utc_now
from app.models.enums import UserRole
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.user import RefreshTokenRepository, UserRepository
from app.schemas.auth import TokenPair, UserCreate, UserLogin
from app.schemas.users import ChangePasswordRequest, UserUpdate


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    async def register(self, payload: UserCreate) -> User:
        email = _normalize_email(payload.email)
        existing_user = await self.users.get_by_email(email)
        if existing_user is not None:
            raise AppError(
                "Email is already registered.",
                status_code=status.HTTP_409_CONFLICT,
                code="email_already_registered",
            )

        user = await self.users.create(
            email=email,
            full_name=payload.full_name.strip(),
            hashed_password=hash_password(payload.password),
            role=UserRole.MEMBER,
        )
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def login(self, payload: UserLogin) -> TokenPair:
        user = await self.users.get_by_email(_normalize_email(payload.email))
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise_invalid_credentials()
        if not user.is_active:
            raise AppError(
                "User account is inactive.",
                status_code=status.HTTP_403_FORBIDDEN,
                code="inactive_user",
            )

        token_pair = await self._issue_token_pair(user)
        await self.session.commit()
        return token_pair

    async def refresh(self, refresh_token: str) -> TokenPair:
        payload = decode_refresh_token(refresh_token, self.settings)
        token_id = require_string_claim(payload, "jti")
        user_id = require_int_subject(payload)

        stored_token = await self.refresh_tokens.get_by_token_id(token_id)
        if stored_token is None or stored_token.revoked_at is not None:
            raise_invalid_credentials()

        user = await self.users.get(user_id)
        if user is None or not user.is_active or stored_token.user_id != user.id:
            raise_invalid_credentials()

        stored_token.revoked_at = utc_now()
        token_pair = await self._issue_token_pair(user)
        await self.session.commit()
        return token_pair

    async def logout(self, refresh_token: str) -> None:
        payload = decode_refresh_token(refresh_token, self.settings)
        token_id = require_string_claim(payload, "jti")
        stored_token = await self.refresh_tokens.get_by_token_id(token_id)
        if stored_token is None:
            raise_invalid_credentials()
        if stored_token.revoked_at is None:
            stored_token.revoked_at = utc_now()
            await self.session.commit()

    async def update_profile(self, user: User, payload: UserUpdate) -> User:
        updates = payload.model_dump(exclude_unset=True)
        email_value = updates.get("email")
        if isinstance(email_value, str):
            email = _normalize_email(email_value)
            if email != user.email:
                existing_user = await self.users.get_by_email(email)
                if existing_user is not None:
                    raise AppError(
                        "Email is already registered.",
                        status_code=status.HTTP_409_CONFLICT,
                        code="email_already_registered",
                    )
                user.email = email

        full_name_value = updates.get("full_name")
        if isinstance(full_name_value, str):
            user.full_name = full_name_value.strip()

        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def change_password(self, user: User, payload: ChangePasswordRequest) -> None:
        if not verify_password(payload.current_password, user.hashed_password):
            raise AppError(
                "Current password is incorrect.",
                status_code=status.HTTP_400_BAD_REQUEST,
                code="invalid_current_password",
            )

        user.hashed_password = hash_password(payload.new_password)
        for refresh_token in await self._active_refresh_tokens_for_user(user.id):
            refresh_token.revoked_at = utc_now()
        await self.session.commit()

    async def _issue_token_pair(self, user: User) -> TokenPair:
        access_token, _ = create_jwt(
            subject=str(user.id),
            token_type="access",
            secret_key=self.settings.secret_key,
            expires_delta=timedelta(minutes=self.settings.access_token_expire_minutes),
        )

        refresh_token_id = generate_token_id()
        refresh_token, expires_at = create_jwt(
            subject=str(user.id),
            token_type="refresh",
            secret_key=self.settings.secret_key,
            expires_delta=timedelta(days=self.settings.refresh_token_expire_days),
            token_id=refresh_token_id,
        )
        await self.refresh_tokens.create(
            token_id=refresh_token_id,
            user_id=user.id,
            expires_at=expires_at,
        )
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    async def _active_refresh_tokens_for_user(self, user_id: int) -> list[RefreshToken]:
        statement = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        result = await self.session.scalars(statement)
        return list(result.all())


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    payload = decode_token(token, settings)
    token_type = payload.get("type")
    if token_type != "access":
        raise_invalid_credentials()
    return payload


def decode_refresh_token(token: str, settings: Settings) -> dict[str, Any]:
    payload = decode_token(token, settings)
    token_type = payload.get("type")
    if token_type != "refresh":
        raise_invalid_credentials()
    return payload


def decode_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        return decode_jwt(token, secret_key=settings.secret_key)
    except TokenError as exc:
        raise invalid_credentials_error() from exc


def require_int_subject(payload: dict[str, Any]) -> int:
    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise_invalid_credentials()
    try:
        return int(subject)
    except ValueError as exc:
        raise invalid_credentials_error() from exc


def require_string_claim(payload: dict[str, Any], claim: str) -> str:
    value = payload.get(claim)
    if not isinstance(value, str) or value == "":
        raise_invalid_credentials()
    return value


def invalid_credentials_error() -> AppError:
    return AppError(
        "Invalid authentication credentials.",
        status_code=status.HTTP_401_UNAUTHORIZED,
        code="invalid_credentials",
    )


def raise_invalid_credentials() -> NoReturn:
    raise invalid_credentials_error()


def _normalize_email(email: str) -> str:
    return email.strip().lower()
