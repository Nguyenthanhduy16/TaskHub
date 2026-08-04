from fastapi import Response, status

from app.api.openapi import documented_router
from app.core.dependencies import SessionDependency, SettingsDependency
from app.schemas.auth import LogoutRequest, RefreshTokenRequest, TokenPair, UserCreate, UserLogin
from app.schemas.users import UserRead
from app.services.auth import AuthService

router = documented_router()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    payload: UserCreate,
    session: SessionDependency,
    settings: SettingsDependency,
) -> UserRead:
    user = await AuthService(session, settings).register(payload)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenPair, summary="Login with email and password")
async def login(
    payload: UserLogin,
    session: SessionDependency,
    settings: SettingsDependency,
) -> TokenPair:
    return await AuthService(session, settings).login(payload)


@router.post("/refresh", response_model=TokenPair, summary="Rotate a refresh token")
async def refresh_token(
    payload: RefreshTokenRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> TokenPair:
    return await AuthService(session, settings).refresh(payload.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a refresh token",
)
async def logout(
    payload: LogoutRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> Response:
    await AuthService(session, settings).logout(payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
