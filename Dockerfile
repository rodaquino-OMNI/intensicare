# =============================================================================
# Intensicare — Dockerfile multi-estágio
# =============================================================================

FROM python:3.12-slim-bookworm AS development

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    ENVIRONMENT=development \
    LOG_LEVEL=DEBUG \
    PYTHONPATH=/app/src

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Runtime dependencies
RUN pip install --upgrade pip \
    && pip install \
        "fastapi[standard]" \
        "uvicorn[standard]" \
        "sqlalchemy[asyncio]" \
        alembic \
        asyncpg \
        "redis[hiredis]" \
        pydantic \
        pydantic-settings \
        hl7apy \
        httpx \
        python-multipart \
        tenacity \
        "python-jose[cryptography]" \
        "passlib[bcrypt]"

# Dev dependencies
RUN pip install pytest pytest-asyncio pytest-cov ruff mypy pre-commit

COPY src/ ./src/
COPY tests/ ./tests/
COPY alembic/ ./alembic/
COPY pyproject.toml ./

EXPOSE 8000

CMD ["uvicorn", "intensicare.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "src"]


FROM python:3.12-slim-bookworm AS production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    ENVIRONMENT=production \
    PYTHONPATH=/app/src

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --upgrade pip \
    && pip install \
        "fastapi[standard]" \
        "uvicorn[standard]" \
        "sqlalchemy[asyncio]" \
        alembic \
        asyncpg \
        "redis[hiredis]" \
        pydantic \
        pydantic-settings \
        hl7apy \
        httpx \
        tenacity \
        "python-jose[cryptography]" \
        "passlib[bcrypt]"

COPY src/ ./src/
COPY alembic/ ./alembic/

RUN groupadd -r intensicare && useradd -r -g intensicare -d /app -s /sbin/nologin intensicare \
    && chown -R intensicare:intensicare /app
USER intensicare

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()" || exit 1

CMD ["uvicorn", "intensicare.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
