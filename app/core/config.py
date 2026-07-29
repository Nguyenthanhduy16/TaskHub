from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "development", "staging", "production", "test"]


class Settings(BaseSettings):
    app_name: str = Field(default="TaskHub API", min_length=1)
    app_env: Environment = "local"
    app_debug: bool = True
    app_version: str = Field(default="0.1.0", min_length=1)
    api_v1_prefix: str = Field(default="/api/v1", pattern=r"^/.+")
    log_level: str = Field(default="INFO", pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    database_url: str = Field(default="sqlite+aiosqlite:///./taskhub.db", min_length=1)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
