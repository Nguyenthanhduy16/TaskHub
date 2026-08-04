from typing import Annotated

from fastapi import BackgroundTasks, Depends, Query, Response, status

from app.api.openapi import documented_router
from app.core.dependencies import (
    CacheDependency,
    SessionDependency,
    SessionFactoryDependency,
    get_current_user,
)
from app.models.enums import TaskPriority, TaskStatus
from app.models.user import User
from app.schemas.tasks import TaskCreate, TaskPage, TaskRead, TaskUpdate
from app.services.task import TaskService

router = documented_router()
CurrentUserDependency = Annotated[User, Depends(get_current_user)]


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task in a project",
)
async def create_task(
    project_id: int,
    payload: TaskCreate,
    current_user: CurrentUserDependency,
    session: SessionDependency,
    cache: CacheDependency,
    session_factory: SessionFactoryDependency,
    background_tasks: BackgroundTasks,
) -> TaskRead:
    task = await TaskService(session, cache).create_task(
        current_user,
        project_id,
        payload,
        background_tasks,
        session_factory,
    )
    return TaskRead.model_validate(task)


@router.get(
    "/projects/{project_id}/tasks",
    response_model=TaskPage,
    summary="List project tasks",
)
async def list_tasks(
    project_id: int,
    current_user: CurrentUserDependency,
    session: SessionDependency,
    cache: CacheDependency,
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: TaskPriority | None = None,
    assignee_id: int | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> TaskPage:
    return await TaskService(session, cache).list_tasks(
        current_user,
        project_id,
        task_status=task_status,
        priority=priority,
        assignee_id=assignee_id,
        page=page,
        limit=limit,
    )


@router.get("/tasks/{task_id}", response_model=TaskRead, summary="Get task")
async def get_task(
    task_id: int,
    current_user: CurrentUserDependency,
    session: SessionDependency,
    cache: CacheDependency,
) -> TaskRead:
    task = await TaskService(session, cache).get_task(current_user, task_id)
    return TaskRead.model_validate(task)


@router.patch("/tasks/{task_id}", response_model=TaskRead, summary="Update task")
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    current_user: CurrentUserDependency,
    session: SessionDependency,
    cache: CacheDependency,
    session_factory: SessionFactoryDependency,
    background_tasks: BackgroundTasks,
) -> TaskRead:
    task = await TaskService(session, cache).update_task(
        current_user,
        task_id,
        payload,
        background_tasks,
        session_factory,
    )
    return TaskRead.model_validate(task)


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task",
)
async def delete_task(
    task_id: int,
    current_user: CurrentUserDependency,
    session: SessionDependency,
    cache: CacheDependency,
) -> Response:
    await TaskService(session, cache).delete_task(current_user, task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
