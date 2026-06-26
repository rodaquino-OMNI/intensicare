"""
Serviço de consulta de status do paciente.

Agrega sinais vitais recentes, scores e tendências
para o endpoint GET /api/v1/patients/{mpi_id}/status.

Suporta enriquecimento opcional via FHIR R4 (HAPI FHIR / AMH Data Platform).
Quando FHIR_BASE_URL não está configurado, o enriquecimento é saltado
graciosamente.
"""

from __future__ import annotations

import logging

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from intensicare.config import settings
from intensicare.fhir.client import FHIRPatientData
from intensicare.models import ClinicalScore, VitalSign
from intensicare.schemas.patients import (
    FHIREnrichment,
    PatientStatusResponse,
    ScoreSummary,
    TrendSummary,
    VitalSignSummary,
)
from intensicare.services.mews import compute_trend

logger = logging.getLogger(__name__)


def _fhir_data_to_enrichment(data: FHIRPatientData) -> FHIREnrichment:
    """Convert FHIRPatientData to the API schema FHIREnrichment."""
    return FHIREnrichment(
        display_name=data.display_name,
        gender=data.gender,
        birth_date=data.birth_date.isoformat() if data.birth_date else None,
        marital_status=data.marital_status,
        phone=data.phone,
        address=data.address,
        primary_condition=data.primary_condition,
        condition_list=data.condition_list,
        allergy_list=data.allergy_list,
        latest_observations=data.latest_observations,
    )


async def _enrich_from_fhir(mpi_id: str) -> FHIREnrichment | None:
    """Attempt to enrich patient data from the FHIR server.

    Returns None when FHIR is not configured or the request fails.
    """
    # Skip if FHIR is not configured
    if not settings.fhir_base_url:
        return None

    try:
        from intensicare.fhir.client import get_fhir_client

        client = get_fhir_client()
        fhir_data = await client.get_patient(mpi_id)
        if fhir_data is None:
            return None
        # Only return enrichment if we actually got something beyond mpi_id
        if (
            fhir_data.display_name is None
            and fhir_data.gender is None
            and not fhir_data.condition_list
        ):
            return None
        return _fhir_data_to_enrichment(fhir_data)
    except Exception:
        logger.exception("FHIR enrichment failed for patient %s", mpi_id)
        return None


async def get_patient_status(
    db: AsyncSession,
    mpi_id: str,
    score_type: str = "MEWS",
    enrich: bool = False,
) -> PatientStatusResponse:
    """Consulta o status atual de um paciente.

    Agrega:
    - Sinais vitais mais recentes (último registro).
    - Último score MEWS calculado.
    - Tendência dos últimos 5 scores.
    - Dados FHIR enriquecidos (se enrich=True e FHIR configurado).

    Args:
        db: Sessão assíncrona do SQLAlchemy.
        mpi_id: ID do paciente.
        score_type: Tipo de score a consultar (default: 'MEWS').
        enrich: Se True, tenta enriquecer com dados do FHIR.

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

    # FHIR enrichment (optional, graceful degradation)
    fhir_enrichment = None
    if enrich:
        fhir_enrichment = await _enrich_from_fhir(mpi_id)

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
        fhir=fhir_enrichment,
    )
