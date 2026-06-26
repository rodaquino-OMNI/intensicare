"""
Fixtures e configurações compartilhadas para todos os testes.

Fornece:
- Cliente HTTP assíncrono (httpx.AsyncClient)
- Banco de dados de teste isolado
- Redis de teste
- Factories para dados sintéticos
"""

import asyncio
from collections.abc import AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from intensicare.config import get_settings, settings
from intensicare.core.database import Base, get_db
from intensicare.main import app


# ═══════════════════════════════════════════════════════════════════════════
# Configuração de teste
# ═══════════════════════════════════════════════════════════════════════════

# Sobrescreve database URL com banco de teste
TEST_DATABASE_URL = settings.database_url.replace(
    settings.postgres_db, f"{settings.postgres_db}_test"
)


@pytest.fixture(scope="session")
def event_loop():
    """Cria event loop para toda a sessão de teste."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Engine assíncrona para o banco de testes."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables(engine):
    """Cria todas as tabelas antes dos testes."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Sessão de banco isolada por teste (com rollback)."""
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        async with session.begin():
            yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Cliente HTTP assíncrono para testar a API."""

    # Sobrescreve a dependência get_db para usar a sessão de teste
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def settings_override():
    """Retorna settings com valores de teste."""
    return get_settings()
