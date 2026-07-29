from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.errors import ErrorDetail, ErrorResponse


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "app_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    content = ErrorResponse(error=ErrorDetail(code=code, message=message, details=details))
    return JSONResponse(status_code=status_code, content=content.model_dump(mode="json"))


async def app_error_handler(_: Request, exc: Exception) -> Response:
    if not isinstance(exc, AppError):
        raise exc

    return _error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def http_error_handler(_: Request, exc: Exception) -> Response:
    if not isinstance(exc, StarletteHTTPException):
        raise exc

    return _error_response(
        status_code=exc.status_code,
        code="http_error",
        message=str(exc.detail),
    )


async def validation_error_handler(_: Request, exc: Exception) -> Response:
    if not isinstance(exc, RequestValidationError):
        raise exc

    return _error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="validation_error",
        message="Request validation failed.",
        details={"errors": exc.errors()},
    )
