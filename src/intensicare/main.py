"""
Aplicacao principal FastAPI — Intensicare.

Inicializa a aplicacao, registra rotas, middlewares e handlers de ciclo de vida.
"""

import json

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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
    from intensicare.core.websocket import get_websocket_manager

    get_engine()  # Init DB engine
    get_redis()  # Init Redis client
    get_websocket_manager()  # Init WebSocket manager
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

    # WebSocket endpoint for real-time alerts
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        from intensicare.core.websocket import get_websocket_manager

        manager = get_websocket_manager()
        await manager.connect(websocket)

        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                except json.JSONDecodeError:
                    await manager.send_error(
                        websocket, "Invalid JSON message"
                    )
                    continue

                action = message.get("action")
                patient_id = message.get("patient_id")

                if action == "subscribe" and patient_id:
                    await manager.subscribe(websocket, patient_id)
                    await websocket.send_json(
                        {
                            "type": "subscribed",
                            "patient_id": patient_id,
                        }
                    )
                elif action == "unsubscribe" and patient_id:
                    await manager.unsubscribe(websocket, patient_id)
                    await websocket.send_json(
                        {
                            "type": "unsubscribed",
                            "patient_id": patient_id,
                        }
                    )
                elif action == "ping":
                    await websocket.send_json({"type": "pong"})
                else:
                    await manager.send_error(
                        websocket,
                        f"Unknown action: {action}. "
                        "Supported: subscribe, unsubscribe, ping",
                    )
        except WebSocketDisconnect:
            pass
        finally:
            manager.disconnect(websocket)

    # Register routers
    from intensicare.api.v1 import (
        auth_router,
        alerts_router,
        dashboard_router,
        vitals_router,
        patients_router,
    )
    from intensicare.api.thresholds import router as thresholds_router

    app.include_router(auth_router)
    app.include_router(alerts_router)
    app.include_router(dashboard_router)
    app.include_router(vitals_router, prefix="/api/v1", tags=["vitals"])
    app.include_router(patients_router, prefix="/api/v1", tags=["patients"])
    app.include_router(thresholds_router)

    return app


app = create_app()
