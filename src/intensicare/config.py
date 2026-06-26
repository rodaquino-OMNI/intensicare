"""
Configuração centralizada da aplicação usando pydantic-settings.
"""

from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação Intensicare."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Ambiente
    environment: Literal["development", "testing", "staging", "production"] = (
        "development"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    debug: bool = False
    secret_key: SecretStr = SecretStr("change-me-in-production")

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False
    api_workers: int = 1
    cors_origins: list[str] = ["*"]

    # PostgreSQL / TimescaleDB
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
        """Connection string assíncrona para SQLAlchemy."""
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.postgres_user,
                password=self.postgres_password.get_secret_value(),
                host=self.postgres_host,
                port=self.postgres_port,
                path=self.postgres_db,
            )
        )

    @computed_field
    @property
    def database_sync_url(self) -> str:
        """Connection string síncrona (usada pelo Alembic)."""
        return str(
            PostgresDsn.build(
                scheme="postgresql+psycopg2",
                username=self.postgres_user,
                password=self.postgres_password.get_secret_value(),
                host=self.postgres_host,
                port=self.postgres_port,
                path=self.postgres_db,
            )
        )

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: SecretStr = SecretStr("")

    @computed_field
    @property
    def redis_url(self) -> str:
        """Connection string para Redis."""
        pwd = self.redis_password.get_secret_value()
        if pwd:
            url = "redis://" + pwd + "@" + self.redis_host + ":" + str(self.redis_port) + "/" + str(self.redis_db)
        else:
            url = "redis://" + self.redis_host + ":" + str(self.redis_port) + "/" + str(self.redis_db)
        return url


@lru_cache
def get_settings() -> Settings:
    """Retorna instância cacheada das configurações."""
    return Settings()


# Instância global
settings = get_settings()
