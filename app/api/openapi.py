from typing import Any

from fastapi import APIRouter

from app.schemas.errors import ErrorResponse

STANDARD_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse, "description": "The request violates a business rule."},
    401: {"model": ErrorResponse, "description": "Authentication is required or invalid."},
    403: {"model": ErrorResponse, "description": "The action is not permitted."},
    404: {"model": ErrorResponse, "description": "The requested resource was not found."},
    409: {"model": ErrorResponse, "description": "The request conflicts with current state."},
    422: {"model": ErrorResponse, "description": "Request validation failed."},
    500: {"model": ErrorResponse, "description": "An unexpected server error occurred."},
}


def documented_router() -> APIRouter:
    return APIRouter(responses=STANDARD_ERROR_RESPONSES)
