# =============================================================================
# Intensicare — Dockerfile multi-estágio
# =============================================================================

FROM python:3.12-slim-bookworm AS development

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    ENVIRONMENT=development \
    LOG_LEVEL=DEBUG

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala dependências diretamente (sem build system)
RUN pip install --upgrade pip setuptools wheel \
    && pip install \
        "fastapi[standard]>=0.115,<1.0" \
        "uvicorn[standard]>=0.30,<1.0" \
        "sqlalchemy[asyncio]>=2.0,<3.0" \
        "alembic>=1.13,<2.0" \
        "asyncpg>=0.29,<1.0" \
        "redis[hiredis]>=5.0,<6.0" \
        "pydantic>=2.7,<3.0" \
        "pydantic-settings>=2.2,<3.0" \
        "python-hl7>=0.4,<1.0" \
        "fhir.resources>=7.1,<8.0" \
        "httpx>=0.27,<1.0" \
        "python-multipart>=0.0.9,<1.0" \
        "tenacity>=8.3,<9.0" \
        "python-jose[cryptography]>=3.3,<4.0" \
        "passlib[bcrypt]>=1.7,<2.0" \
    && pip install \
        "pytest>=8.2,<9.0" \
        "pytest-asyncio>=0.23,<1.0" \
        "pytest-cov>=5.0,<6.0" \
        "ruff>=0.4,<1.0" \
        "mypy>=1.10,<2.0" \
        "pre-commit>=3.7,<4.0"

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
    ENVIRONMENT=production

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --upgrade pip \
    && pip install \
        "fastapi[standard]>=0.115,<1.0" \
        "uvicorn[standard]>=0.30,<1.0" \
        "sqlalchemy[asyncio]>=2.0,<3.0" \
        "alembic>=1.13,<2.0" \
        "asyncpg>=0.29,<1.0" \
        "redis[hiredis]>=5.0,<6.0" \
        "pydantic>=2.7,<3.0" \
        "pydantic-settings>=2.2,<3.0" \
        "python-hl7>=0.4,<1.0" \
        "fhir.resources>=7.1,<8.0" \
        "httpx>=0.27,<1.0" \
        "python-multipart>=0.0.9,<1.0" \
        "tenacity>=8.3,<9.0" \
        "python-jose[cryptography]>=3.3,<4.0" \
        "passlib[bcrypt]>=1.7,<2.0"

COPY src/ ./src/
COPY alembic/ ./alembic/
COPY pyproject.toml ./

RUN groupadd -r intensicare && useradd -r -g intensicare -d /app -s /sbin/nologin intensicare \
    && chown -R intensicare:intensicare /app
USER intensicare

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()" || exit 1

CMD ["uvicorn", "intensicare.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
