from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import (
    AppError,
    app_error_handler,
    http_error_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from app.core.lifespan import lifespan
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware

_OPENAPI_TAGS = [
    {"name": "auth", "description": "Registration and token lifecycle."},
    {"name": "users", "description": "Authenticated user profile operations."},
    {"name": "workspaces", "description": "Workspace membership and role management."},
    {"name": "projects", "description": "Projects scoped to accessible workspaces."},
    {"name": "tasks", "description": "Task management, filtering, and pagination."},
    {"name": "labels", "description": "Project labels and task label assignments."},
    {"name": "comments", "description": "Task discussion comments."},
    {"name": "health", "description": "Service health information."},
]


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        description="Task management API with workspace-scoped role-based access control.",
        version=settings.app_version,
        debug=settings.app_debug,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        openapi_tags=_OPENAPI_TAGS,
    )

    app.add_middleware(RequestContextMiddleware)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)

    return app


app = create_app()
