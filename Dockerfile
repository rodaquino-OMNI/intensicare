# =============================================================================
# Intensicare — Dockerfile multi-estágio
# Estágios: development (dev) e production (prod)
# =============================================================================

# ---------------------------------------------------------------------------
# Estágio base — dependências comuns
# ---------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Dependências de sistema para asyncpg + build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala dependências Python via pyproject.toml
COPY pyproject.toml .

RUN pip install --upgrade pip setuptools wheel \
    && pip install -e ".[dev]"

# ---------------------------------------------------------------------------
# Estágio de desenvolvimento — código montado via volume
# ---------------------------------------------------------------------------
FROM base AS development

ENV ENVIRONMENT=development \
    LOG_LEVEL=DEBUG

# Copia código mínimo (a maior parte vem por volume mount)
COPY src/ ./src/
COPY tests/ ./tests/
COPY alembic/ ./alembic/

EXPOSE 8000

CMD ["uvicorn", "intensicare.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "src"]

# ---------------------------------------------------------------------------
# Estágio de produção — código copiado, sem dev dependencies
# ---------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    ENVIRONMENT=production

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia e instala apenas dependências de runtime
COPY pyproject.toml .
RUN pip install --upgrade pip \
    && pip install -e ".[test]"  # test inclui httpx para healthcheck
RUN pip uninstall -y pytest pytest-cov pytest-asyncio factory-boy faker ruff mypy pre-commit || true

# Copia código fonte
COPY src/ ./src/
COPY alembic/ ./alembic/

# Cria usuário não-root
RUN groupadd -r intensicare && useradd -r -g intensicare -d /app -s /sbin/nologin intensicare \
    && chown -R intensicare:intensicare /app
USER intensicare

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()" || exit 1

CMD ["uvicorn", "intensicare.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
