from typing import Any

from app.schemas.base import APIModel


class ErrorDetail(APIModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(APIModel):
    error: ErrorDetail
