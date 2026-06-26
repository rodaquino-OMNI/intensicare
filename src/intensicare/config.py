"""
Configuracao centralizada da aplicacao usando pydantic-settings.
"""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracoes da aplicacao Intensicare."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["development", "testing", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    debug: bool = False
    secret_key: SecretStr = SecretStr("change-me-in-production")

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False
    api_workers: int = 1
    cors_origins: list[str] = ["*"]

    # JWT settings
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "intensicare"
    postgres_password: SecretStr = SecretStr("intensicare_dev")
    postgres_db: str = "intensicare"
    postgres_min_connections: int = 2
    postgres_max_connections: int = 10

    @computed_field
    @property
    def database_url(self) -> str:
        pw = self.postgres_password.get_secret_value()
        return f"postgresql+asyncpg://{self.postgres_user}:{pw}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @computed_field
    @property
    def database_sync_url(self) -> str:
        pw = self.postgres_password.get_secret_value()
        return f"postgresql+psycopg2://{self.postgres_user}:{pw}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: SecretStr = SecretStr("")

    @computed_field
    @property
    def redis_url(self) -> str:
        pw = self.redis_password.get_secret_value()
        if pw:
            return f"redis://:{pw}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # JWT settings
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    jwt_refresh_expire_days: int = 7

@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
