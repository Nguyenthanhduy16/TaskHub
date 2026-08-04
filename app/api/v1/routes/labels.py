from typing import Annotated

from fastapi import Depends, Response, status

from app.api.openapi import documented_router
from app.core.dependencies import SessionDependency, get_current_user
from app.models.user import User
from app.schemas.labels import LabelCreate, LabelRead, LabelUpdate
from app.services.label import LabelService

router = documented_router()
CurrentUserDependency = Annotated[User, Depends(get_current_user)]


@router.post(
    "/projects/{project_id}/labels",
    response_model=LabelRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a label in a project",
)
async def create_label(
    project_id: int,
    payload: LabelCreate,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> LabelRead:
    label = await LabelService(session).create_label(current_user, project_id, payload)
    return LabelRead.model_validate(label)


@router.get(
    "/projects/{project_id}/labels",
    response_model=list[LabelRead],
    summary="List project labels",
)
async def list_labels(
    project_id: int,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> list[LabelRead]:
    labels = await LabelService(session).list_labels(current_user, project_id)
    return [LabelRead.model_validate(label) for label in labels]


@router.patch("/labels/{label_id}", response_model=LabelRead, summary="Update label")
async def update_label(
    label_id: int,
    payload: LabelUpdate,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> LabelRead:
    label = await LabelService(session).update_label(current_user, label_id, payload)
    return LabelRead.model_validate(label)


@router.delete(
    "/labels/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete label",
)
async def delete_label(
    label_id: int,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> Response:
    await LabelService(session).delete_label(current_user, label_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/tasks/{task_id}/labels",
    response_model=list[LabelRead],
    summary="List labels assigned to a task",
)
async def list_task_labels(
    task_id: int,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> list[LabelRead]:
    labels = await LabelService(session).list_task_labels(current_user, task_id)
    return [LabelRead.model_validate(label) for label in labels]


@router.post(
    "/tasks/{task_id}/labels/{label_id}",
    response_model=LabelRead,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a label to a task",
)
async def attach_task_label(
    task_id: int,
    label_id: int,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> LabelRead:
    label = await LabelService(session).attach_label(current_user, task_id, label_id)
    return LabelRead.model_validate(label)


@router.delete(
    "/tasks/{task_id}/labels/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a label from a task",
)
async def detach_task_label(
    task_id: int,
    label_id: int,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> Response:
    await LabelService(session).detach_label(current_user, task_id, label_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
