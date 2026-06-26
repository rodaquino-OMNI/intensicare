"""
Aplicação principal FastAPI — Intensicare.

Inicializa a aplicação, registra rotas, middlewares e handlers de ciclo de vida.
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
    Gerencia o ciclo de vida da aplicação.

    - Startup: inicializa conexões com banco e Redis.
    - Shutdown: fecha conexões gracefulmente.
    """
    # Startup
    # TODO: Inicializar pool de conexões (engine SQLAlchemy, Redis client)
    app.state.started = True

    yield

    # Shutdown
    # TODO: Fechar pool de conexões
    app.state.started = False


def create_app() -> FastAPI:
    """Factory que cria e configura a aplicação FastAPI."""

    app = FastAPI(
        title="Intensicare API",
        description="Plataforma de monitoramento contínuo para UTI",
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

    # TODO: Registrar routers
    # from intensicare.api import patients, alerts, vitals
    # app.include_router(patients.router, prefix="/api/v1/patients", tags=["patients"])
    # app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])

    return app


app = create_app()
