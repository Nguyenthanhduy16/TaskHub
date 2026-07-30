from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.dependencies import SessionDependency, SettingsDependency, get_current_user
from app.models.user import User
from app.schemas.users import ChangePasswordRequest, UserRead, UserUpdate
from app.services.auth import AuthService

router = APIRouter()
CurrentUserDependency = Annotated[User, Depends(get_current_user)]


@router.get("/me", response_model=UserRead, summary="Get current user profile")
async def get_my_profile(current_user: CurrentUserDependency) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead, summary="Update current user profile")
async def update_my_profile(
    payload: UserUpdate,
    current_user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> UserRead:
    user = await AuthService(session, settings).update_profile(current_user, payload)
    return UserRead.model_validate(user)


@router.post(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change current user password",
)
async def change_my_password(
    payload: ChangePasswordRequest,
    current_user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> None:
    await AuthService(session, settings).change_password(current_user, payload)
