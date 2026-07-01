"""애플리케이션 설정 — 환경변수에서 로드."""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """환경변수 기반 설정. .env 파일에서 자동 로드."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "Affect Cartography API"
    app_env: str = "development"
    app_debug: bool = True
    cors_origins: str = "http://localhost:3000,http://localhost:8080"

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://affect_user:affect_pass@localhost:5432/affect_cartography"
    )
    database_url_sync: str = Field(
        default="postgresql://affect_user:affect_pass@localhost:5432/affect_cartography"
    )

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 43200  # 30 days

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_zero_data_retention: bool = True

    # Admin
    admin_code: str = "change-me"
    admin_code_salt: str = "change-me-salt"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Safety
    crisis_hotline: str = "1393"
    kaist_counseling: str = "042-350-2181"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
