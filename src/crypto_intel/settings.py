'''Application settings loaded from environment variables and optional .env file'''

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _PROJECT_ROOT / ".env"

class Settings(BaseSettings):
    """Runtime config. Values come from env vars; .env is for local development only"""
    

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore", # allow POSTGRES_* in .env for Docker Compose without declaring them here
        case_sensitive=False,
    )

    database_url: str = Field(
        ...,
        description="SQLAlchemy URL",
    )
    redis_url: str = Field(
        ...,
        description="Redis URL")
    
    open_api_key: SecretStr | None = None
    langsmith_api_key: SecretStr | None = None
    langsmith_tracing: bool = False
    langsmith_project: str = "crypto-intel"
    

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
