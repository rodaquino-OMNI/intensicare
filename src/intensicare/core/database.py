"""Configuração do banco de dados — SQLAlchemy async engine + session."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from intensicare.config import settings


class Base(DeclarativeBase):
    """Base declarativa para todos os modelos SQLAlchemy."""


def create_engine() -> AsyncEngine:
    """Cria engine assíncrona para PostgreSQL/TimescaleDB."""
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_size=settings.postgres_min_connections,
        max_overflow=settings.postgres_max_connections - settings.postgres_min_connections,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


# Engine global (inicializada lazy no primeiro acesso)
_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    """Retorna a engine assíncrona (lazy init)."""
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine


# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=get_engine(),
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency que fornece uma sessão de banco por request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
