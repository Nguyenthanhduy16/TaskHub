from typing import Annotated

from fastapi import Depends

from app.api.openapi import documented_router
from app.core.config import Settings
from app.core.dependencies import get_app_settings
from app.schemas.health import HealthCheckResponse

router = documented_router()
SettingsDependency = Annotated[Settings, Depends(get_app_settings)]


@router.get("/health", response_model=HealthCheckResponse, summary="Check API health")
async def health_check(settings: SettingsDependency) -> HealthCheckResponse:
    return HealthCheckResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
        version=settings.app_version,
    )
