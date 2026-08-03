from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.dependencies import SessionDependency, get_current_user
from app.models.user import User
from app.schemas.comments import CommentCreate, CommentRead
from app.services.comment import CommentService

router = APIRouter()
CurrentUserDependency = Annotated[User, Depends(get_current_user)]


@router.get(
    "/tasks/{task_id}/comments",
    response_model=list[CommentRead],
    summary="List comments on a task",
)
async def list_comments(
    task_id: int,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> list[CommentRead]:
    comments = await CommentService(session).list_comments(current_user, task_id)
    return [CommentRead.model_validate(comment) for comment in comments]


@router.post(
    "/tasks/{task_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment to a task",
)
async def add_comment(
    task_id: int,
    payload: CommentCreate,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> CommentRead:
    comment = await CommentService(session).add_comment(current_user, task_id, payload)
    return CommentRead.model_validate(comment)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a comment",
)
async def delete_comment(
    comment_id: int,
    current_user: CurrentUserDependency,
    session: SessionDependency,
) -> Response:
    await CommentService(session).delete_comment(current_user, comment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
