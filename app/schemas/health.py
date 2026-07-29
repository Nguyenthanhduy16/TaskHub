from app.core.config import Environment
from app.schemas.base import APIModel


class HealthCheckResponse(APIModel):
    status: str
    service: str
    environment: Environment
    version: str
