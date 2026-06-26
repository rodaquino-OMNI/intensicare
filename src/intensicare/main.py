"""
Aplicacao principal FastAPI — Intensicare.

Inicializa a aplicacao, registra rotas, middlewares e handlers de ciclo de vida.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from intensicare.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Gerencia o ciclo de vida da aplicacao.

    - Startup: inicializa conexoes com banco e Redis.
    - Shutdown: fecha conexoes gracefulmente.
    """
    # Startup
    from intensicare.core.database import get_engine
    from intensicare.core.redis import get_redis

    get_engine()  # Init DB engine
    get_redis()  # Init Redis client
    app.state.started = True

    yield

    # Shutdown
    from intensicare.core.redis import close_redis

    await close_redis()
    app.state.started = False


def create_app() -> FastAPI:
    """Factory que cria e configura a aplicacao FastAPI."""

    app = FastAPI(
        title="Intensicare API",
        description="Plataforma de monitoramento continuo para UTI",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check
    @app.get("/health", tags=["system"])
    async def health_check():
        return JSONResponse(
            content={
                "status": "healthy",
                "version": "0.1.0",
                "environment": settings.environment,
            }
        )

    # Register routers
    from intensicare.api.v1 import (
        auth_router,
        alerts_router,
        vitals_router,
        patients_router,
    )

    app.include_router(auth_router)
    app.include_router(alerts_router)
    app.include_router(vitals_router, prefix="/api/v1", tags=["vitals"])
    app.include_router(patients_router, prefix="/api/v1", tags=["patients"])

    return app


app = create_app()
