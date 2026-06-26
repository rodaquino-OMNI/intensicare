"""
Rotas da API v1 — ingestão de sinais vitais.

POST /api/v1/vitals — Ingere sinais vitais com idempotência e scoring MEWS.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from intensicare.core.database import get_db
from intensicare.core.websocket import get_websocket_manager
from intensicare.schemas.vitals import VitalSignCreate, VitalSignResponse
from intensicare.services.vitals import ingest_vitals

router = APIRouter()


@router.post(
    "/vitals",
    response_model=VitalSignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingerir sinais vitais",
    description=(
        "Recebe sinais vitais de um paciente, persiste no banco, "
        "calcula MEWS sincronamente e retorna o resultado. "
        "Suporta idempotência via header `X-Idempotency-Key`."
    ),
    responses={
        201: {"description": "Sinais vitais ingeridos com sucesso"},
        200: {"description": "Requisição idempotente — dados já processados"},
        422: {"description": "Erro de validação nos dados enviados"},
    },
)
async def create_vitals(
    body: VitalSignCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_idempotency_key: str | None = Header(
        None,
        alias="X-Idempotency-Key",
        description="Chave de idempotência (MSH-10). Evita duplicação de registros.",
    ),
) -> VitalSignResponse:
    """Ingere sinais vitais com idempotência, scoring e alert engine."""
    try:
        result, alerts = await ingest_vitals(
            db=db,
            data=body,
            idempotency_key=x_idempotency_key,
        )

        # Broadcast any created alerts to WebSocket clients
        if alerts:
            manager = get_websocket_manager()
            for alert in alerts:
                alert_data = {
                    "type": "alert",
                    "id": alert.id,
                    "mpi_id": alert.mpi_id,
                    "severity": alert.severity,
                    "status": alert.status,
                    "title": alert.title,
                    "body": alert.body,
                    "created_at": alert.created_at.isoformat() if alert.created_at else None,
                }
                await manager.broadcast_alert(alert_data)

        return result
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao processar sinais vitais: {exc}",
        ) from exc
