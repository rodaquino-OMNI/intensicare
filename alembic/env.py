"""Alembic environment configuration for async PostgreSQL/TimescaleDB."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from intensicare.config import settings
from intensicare.core.database import Base

# Importa todos os modelos para que Base.metadata contenha todas as tabelas
# import intensicare.models  # noqa: F401 — descomente quando criar modelos

# Alembic Config object
config = context.config

# Configura logging via alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData para autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Executa migrações em modo 'offline' (gera SQL sem conexão).

    O Alembic usa a URL do alembic.ini se disponível, ou a DATABASE_URL.
    """
    url = settings.database_sync_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Executa migrações com uma conexão ativa."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Cria engine assíncrona e executa migrações online."""
    connectable = create_async_engine(settings.database_url)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Executa migrações em modo 'online' (conectado ao banco)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
