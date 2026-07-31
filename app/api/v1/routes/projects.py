from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.dependencies import SessionDependency, get_current_user
from app.models.user import User
from app.schemas.projects import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.project import ProjectService

router = APIRouter()
CurrentUserDependency = Annotated[User, Depends(get_current_user)]


@router.post(
    "/workspaces/{workspace_id}/projects",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project in a workspace",
)
async def create_project(
    workspace_id: int,
    payload: ProjectCreate,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> ProjectRead:
    project = await ProjectService(session).create_project(current_user, workspace_id, payload)
    return ProjectRead.model_validate(project)


@router.get(
    "/workspaces/{workspace_id}/projects",
    response_model=list[ProjectRead],
    summary="List workspace projects",
)
async def list_projects(
    workspace_id: int,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> list[ProjectRead]:
    projects = await ProjectService(session).list_projects(current_user, workspace_id)
    return [ProjectRead.model_validate(project) for project in projects]


@router.get("/projects/{project_id}", response_model=ProjectRead, summary="Get project")
async def get_project(
    project_id: int,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> ProjectRead:
    project = await ProjectService(session).get_project(current_user, project_id)
    return ProjectRead.model_validate(project)


@router.patch("/projects/{project_id}", response_model=ProjectRead, summary="Update project")
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> ProjectRead:
    project = await ProjectService(session).update_project(current_user, project_id, payload)
    return ProjectRead.model_validate(project)


@router.post(
    "/projects/{project_id}/archive",
    response_model=ProjectRead,
    summary="Archive project",
)
async def archive_project(
    project_id: int,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> ProjectRead:
    project = await ProjectService(session).archive_project(current_user, project_id)
    return ProjectRead.model_validate(project)


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project",
)
async def delete_project(
    project_id: int,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> Response:
    await ProjectService(session).delete_project(current_user, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
