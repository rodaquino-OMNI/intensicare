""""
Fixtures e configurações compartilhadas para todos os testes.

Fornece:
- Cliente HTTP assíncrono (httpx.AsyncClient)
- Banco de dados de teste isolado (apenas quando solicitado via --db ou marker)
- Redis de teste
- Factories para dados sintéticos
"""

import asyncio
import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from intensicare.config import get_settings, settings
from intensicare.core.database import Base, get_db
from intensicare.main import app


# ═══════════════════════════════════════════════════════════════════════════
# Configuração de teste
# ═══════════════════════════════════════════════════════════════════════════

# Sobrescreve database URL com banco de teste
# Usa TEST_DATABASE_URL do ambiente, ou constrói com localhost + _test suffix
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    (
        f"postgresql+asyncpg://{settings.postgres_user}:"
        f"{settings.postgres_password.get_secret_value()}"
        f"@localhost:{settings.postgres_port}/{settings.postgres_db}_test"
    ),
)

# Marker para testes que precisam de banco de dados real
DB_REQUIRED = pytest.mark.db_required


def pytest_configure(config: pytest.Config) -> None:
    """Registra markers customizados."""
    config.addinivalue_line(
        "markers",
        "db_required: tests that require a real PostgreSQL database",
    )


@pytest.fixture(scope="session")
def event_loop():
    """Cria event loop para toda a sessão de teste."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Engine assíncrona para o banco de testes.

    NOTA: Esta fixture não é autouse. Apenas testes que explicitamente
    dependem de db_session (direta ou indiretamente) vão acionar a engine.
    """
    eng = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="session")
async def create_tables(engine):
    """Cria todas as tabelas antes dos testes e remove depois.

    Esta fixture NÃO é autouse — apenas executa quando a engine é
    solicitada.  Isso evita que testes unitários puros (que não precisam
    de banco) tentem conectar ao PostgreSQL.

    O uso de engine.begin() garante que a conexão/transação usada para
    DDL seja liberada antes do yield, evitando conflitos de "another
    operation is in progress" com asyncpg.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(
    engine, create_tables
) -> AsyncGenerator[AsyncSession, None]:
    """Sessão de banco isolada por teste (com rollback).

    Cada teste recebe sua própria sessão transacional.  Ao final do
    teste a transação sofre rollback, garantindo isolamento total.

    A sessão é criada com expire_on_commit=False porque nunca damos
    commit de verdade — sempre fazemos rollback.
    """
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        async with session.begin():
            yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Cliente HTTP assíncrono para testar a API.

    Sobrescreve a dependência get_db do FastAPI para injetar a sessão
    de teste transacional.
    """

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


@pytest.fixture(autouse=True)
def reset_idempotency_store():
    """Limpa o IdempotencyStore antes de cada teste."""
    from intensicare.services.vitals import get_idempotency_store

    store = get_idempotency_store()
    store.clear()
    yield
    store.clear()


# ═══════════════════════════════════════════════════════════════════════════
# JWT / Auth helpers
# ═══════════════════════════════════════════════════════════════════════════

from datetime import datetime, timedelta, timezone

from jose import jwt

from intensicare.auth.jwt import create_access_token, create_refresh_token
from intensicare.config import settings

# Gera token JWT diretamente com a secret conhecida
def _make_test_token(sub: str, user_id: int) -> str:
    from datetime import datetime, timedelta, timezone
    from jose import jwt as jose_jwt
    expire = datetime.now(timezone.utc) + timedelta(minutes=60)
    return jose_jwt.encode(
        {"sub": sub, "user_id": user_id, "exp": expire, "type": "access"},
        settings.secret_key.get_secret_value(),
        algorithm="HS256",
    )
from intensicare.models.user import User
from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_password(password: str) -> str:
    return _pwd_context.hash(password)


async def _create_user(
    db: AsyncSession,
    username: str,
    email: str,
    password: str,
    is_admin: bool = False,
) -> User:
    """Create a test user in the database."""
    user = User(
        username=username,
        email=email,
        hashed_password=_hash_password(password),
        display_name=username.title(),
        is_admin=is_admin,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin user for tests that need authorization."""
    return await _create_user(
        db_session, "testadmin", "admin@test.io", "admin123", is_admin=True
    )


@pytest_asyncio.fixture
async def regular_user(db_session: AsyncSession) -> User:
    """Create a regular (non-admin) user for tests that need authorization."""
    return await _create_user(
        db_session, "testuser", "user@test.io", "user1234", is_admin=False
    )


@pytest.fixture
def admin_headers(admin_user: User) -> dict[str, str]:
    """Authorization header with a valid JWT for an admin user."""
    token = _make_test_token(admin_user.username, admin_user.id or 1)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_headers(regular_user: User) -> dict[str, str]:
    """Authorization header with a valid JWT for a regular user."""
    token = _make_test_token(regular_user.username, regular_user.id or 2)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def no_auth_headers() -> dict[str, str]:
    """Empty headers for testing unauthenticated requests."""
    return {}


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Sessão de banco mockada para testes unitários.

    Use esta fixture quando o teste precisar simular interações com o
    banco de dados sem conectar a um PostgreSQL real.  Ideal para
    testes de serviços como patients, mews, etc.

    IMPORTANTE: O valor retornado por ``await db.execute(...)`` é um
    MagicMock (não AsyncMock) porque os métodos do Result do SQLAlchemy
    (``fetchall``, ``scalar_one_or_none``, etc.) são síncronos.
    """
    from unittest.mock import MagicMock

    mock = AsyncMock(spec=AsyncSession)

    # O execute() é async, mas o Result retornado tem métodos sync
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.fetchall.return_value = []
    mock.execute.return_value = mock_result

    return mock


@pytest_asyncio.fixture
async def mock_client(
    mock_db_session: AsyncMock,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Cliente HTTP para testes de API sem banco de dados real.

    Usa mock_db_session como dependência get_db do FastAPI, permitindo
    testar endpoints HTTP sem um PostgreSQL disponível.
    """

    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
