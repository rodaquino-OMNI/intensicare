"""
Rotas da API v1 — consulta de status do paciente.

GET /api/v1/patients/{mpi_id}/status — Status agregado do paciente.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from intensicare.core.database import get_db
from intensicare.schemas.patients import PatientStatusResponse
from intensicare.services.patients import get_patient_status

router = APIRouter()


@router.get(
    "/patients/{mpi_id}/status",
    response_model=PatientStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Status do paciente",
    description=(
        "Retorna o status agregado do paciente: sinais vitais mais recentes, "
        "último score MEWS e tendência dos últimos 5 scores."
    ),
    responses={
        200: {"description": "Status do paciente"},
        404: {"description": "Paciente não encontrado"},
    },
)
async def patient_status(
    mpi_id: str,
    db: AsyncSession = Depends(get_db),
    score_type: str = Query(
        "MEWS",
        description="Tipo de score a consultar (MEWS, NEWS2, SOFA, qSOFA)",
        max_length=16,
    ),
) -> PatientStatusResponse:
    """Retorna status agregado do paciente."""
    try:
        result = await get_patient_status(
            db=db,
            mpi_id=mpi_id,
            score_type=score_type,
        )
        # Retorna 200 mesmo sem dados — o frontend decide como tratar
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao consultar status do paciente: {exc}",
        ) from exc
