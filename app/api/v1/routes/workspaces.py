from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.dependencies import SessionDependency, get_current_user
from app.models.user import User
from app.schemas.workspaces import (
    WorkspaceCreate,
    WorkspaceInviteRequest,
    WorkspaceMemberRead,
    WorkspaceMemberRoleUpdate,
    WorkspaceRead,
    WorkspaceUpdate,
)
from app.services.workspace import WorkspaceService

router = APIRouter()
CurrentUserDependency = Annotated[User, Depends(get_current_user)]


@router.post(
    "",
    response_model=WorkspaceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a workspace",
)
async def create_workspace(
    payload: WorkspaceCreate,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> WorkspaceRead:
    workspace = await WorkspaceService(session).create_workspace(current_user, payload)
    return WorkspaceRead.model_validate(workspace)


@router.get("", response_model=list[WorkspaceRead], summary="List my workspaces")
async def list_workspaces(
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> list[WorkspaceRead]:
    workspaces = await WorkspaceService(session).list_workspaces(current_user)
    return [WorkspaceRead.model_validate(workspace) for workspace in workspaces]


@router.get("/{workspace_id}", response_model=WorkspaceRead, summary="Get workspace")
async def get_workspace(
    workspace_id: int,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> WorkspaceRead:
    workspace = await WorkspaceService(session).get_workspace(current_user, workspace_id)
    return WorkspaceRead.model_validate(workspace)


@router.patch("/{workspace_id}", response_model=WorkspaceRead, summary="Update workspace")
async def update_workspace(
    workspace_id: int,
    payload: WorkspaceUpdate,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> WorkspaceRead:
    workspace = await WorkspaceService(session).update_workspace(
        current_user,
        workspace_id,
        payload,
    )
    return WorkspaceRead.model_validate(workspace)


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete workspace",
)
async def delete_workspace(
    workspace_id: int,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> Response:
    await WorkspaceService(session).delete_workspace(current_user, workspace_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{workspace_id}/members",
    response_model=list[WorkspaceMemberRead],
    summary="List workspace members",
)
async def list_members(
    workspace_id: int,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> list[WorkspaceMemberRead]:
    members = await WorkspaceService(session).list_members(current_user, workspace_id)
    return [WorkspaceMemberRead.model_validate(member) for member in members]


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberRead,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a workspace member",
)
async def invite_member(
    workspace_id: int,
    payload: WorkspaceInviteRequest,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> WorkspaceMemberRead:
    member = await WorkspaceService(session).invite_member(current_user, workspace_id, payload)
    return WorkspaceMemberRead.model_validate(member)


@router.patch(
    "/{workspace_id}/members/{user_id}",
    response_model=WorkspaceMemberRead,
    summary="Update a workspace member role",
)
async def update_member_role(
    workspace_id: int,
    user_id: int,
    payload: WorkspaceMemberRoleUpdate,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> WorkspaceMemberRead:
    member = await WorkspaceService(session).update_member_role(
        current_user,
        workspace_id,
        user_id,
        payload,
    )
    return WorkspaceMemberRead.model_validate(member)


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a workspace member",
)
async def remove_member(
    workspace_id: int,
    user_id: int,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> Response:
    await WorkspaceService(session).remove_member(current_user, workspace_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)