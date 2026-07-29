'''Application settings loaded from environment variables and optional .env file'''

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dataclasses import dataclass

from pydantic import Field, SecretStr 
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _PROJECT_ROOT / ".env"


@dataclass(frozen=True, slots=True)
class PostgresSettings:
    url: str
    

@dataclass(frozen=True, slots=True)
class RedisSettings:
    url: str
    

@dataclass(frozen=True, slots=True)
class XaiSettings:
    api_key: SecretStr
    base_url: str
    model: str
    

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    postgres_url: str = Field(..., description="SQLAlchemy URL")
    redis_url: str = Field(..., description="Redis URL")
    
    xai_api_key: SecretStr = Field(..., description="xAI API key")
    xai_base_url: str = Field(..., description="xAI base URL")
    llm_model: str = Field(default="grok-4.5", description="LLM model id")
    

    langsmith_api_key: SecretStr | None = None
    langsmith_tracing: bool = False
    langsmith_project: str = "crypto-intel"
    
    
    @property
    def postgres(self) -> PostgresSettings:
        return PostgresSettings(url=self.postgres_url)
    
    @property
    def redis(self) -> RedisSettings:
        return RedisSettings(url=self.redis_url)
    
    @property
    def xai(self) -> XaiSettings:
        return XaiSettings(
            api_key=self.xai_api_key,
            base_url=self.xai_base_url.rstrip("/"),
            model=self.llm_model,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()