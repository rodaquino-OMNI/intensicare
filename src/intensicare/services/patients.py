"""
Serviço de consulta de status do paciente.

Agrega sinais vitais recentes, scores e tendências
para o endpoint GET /api/v1/patients/{mpi_id}/status.
"""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from intensicare.models import ClinicalScore, VitalSign
from intensicare.schemas.patients import (
    PatientStatusResponse,
    ScoreSummary,
    TrendSummary,
    VitalSignSummary,
)
from intensicare.services.mews import compute_trend


async def get_patient_status(
    db: AsyncSession,
    mpi_id: str,
    score_type: str = "MEWS",
) -> PatientStatusResponse:
    """Consulta o status atual de um paciente.

    Agrega:
    - Sinais vitais mais recentes (último registro).
    - Último score MEWS calculado.
    - Tendência dos últimos 5 scores.

    Args:
        db: Sessão assíncrona do SQLAlchemy.
        mpi_id: ID do paciente.
        score_type: Tipo de score a consultar (default: 'MEWS').

    Returns:
        PatientStatusResponse com dados agregados.
    """
    # Sinais vitais mais recentes
    vitals_stmt = (
        select(VitalSign)
        .where(VitalSign.mpi_id == mpi_id)
        .order_by(desc(VitalSign.recorded_at))
        .limit(1)
    )
    vitals_result = await db.execute(vitals_stmt)
    latest_vital = vitals_result.scalar_one_or_none()

    # Último score MEWS
    score_stmt = (
        select(ClinicalScore)
        .where(
            ClinicalScore.mpi_id == mpi_id,
            ClinicalScore.score_type == score_type,
        )
        .order_by(desc(ClinicalScore.calculated_at))
        .limit(1)
    )
    score_result = await db.execute(score_stmt)
    latest_score = score_result.scalar_one_or_none()

    # Últimos 5 scores para tendência
    trend_stmt = (
        select(ClinicalScore.score_value)
        .where(
            ClinicalScore.mpi_id == mpi_id,
            ClinicalScore.score_type == score_type,
        )
        .order_by(desc(ClinicalScore.calculated_at))
        .limit(5)
    )
    trend_result = await db.execute(trend_stmt)
    recent_scores = [row.score_value for row in trend_result.fetchall()]
    # Reverte para ordem cronológica (mais antigo primeiro)
    recent_scores.reverse()

    trend = compute_trend(recent_scores)

    # Determina last_updated
    last_updated = None
    if latest_vital and latest_score:
        last_updated = max(latest_vital.recorded_at, latest_score.calculated_at)
    elif latest_vital:
        last_updated = latest_vital.recorded_at
    elif latest_score:
        last_updated = latest_score.calculated_at

    return PatientStatusResponse(
        mpi_id=mpi_id,
        latest_vitals=(
            VitalSignSummary.model_validate(latest_vital)
            if latest_vital
            else None
        ),
        latest_mews=(
            ScoreSummary.model_validate(latest_score)
            if latest_score
            else None
        ),
        trend=TrendSummary(values=recent_scores, current_trend=trend),
        last_updated=last_updated,
    )
