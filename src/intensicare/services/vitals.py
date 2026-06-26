"""
Serviço de ingestão de sinais vitais com idempotência e scoring MEWS + NEWS2.

Responsável por:
- Validar e persistir sinais vitais no banco
- Garantir idempotência via chave de idempotência (X-Idempotency-Key)
- Calcular MEWS e NEWS2 sincronamente após ingestão
- Persistir scores clínicos com versionamento
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from intensicare.models import Alert, ClinicalScore, VitalSign
from intensicare.schemas.vitals import VitalSignCreate, VitalSignResponse
from intensicare.services.alert_engine import process_clinical_score
from intensicare.services.mews import calculate_mews, compute_trend, MEWS_VERSION
from intensicare.services.news2 import calculate_news2
from intensicare.services.sofa import calculate_sofa, SOFA_VERSION
from intensicare.services.qsofa import calculate_qsofa, QSOFA_VERSION


class IdempotencyStore:
    """Armazena chaves de idempotência processadas.

    Implementação em memória para uso em testes/desenvolvimento.
    Produção deve usar Redis com TTL.
    """

    def __init__(self) -> None:
        self._store: dict[str, int] = {}

    def key_exists(self, key: str) -> bool:
        """Verifica se a chave de idempotência já foi processada."""
        return key in self._store

    def store_key(self, key: str, vital_sign_id: int) -> None:
        """Armazena a chave associada ao ID do registro criado."""
        self._store[key] = vital_sign_id

    def get_stored_id(self, key: str) -> int | None:
        """Retorna o ID do vital_sign previamente processado para esta chave."""
        return self._store.get(key)

    def clear(self) -> None:
        """Limpa o armazenamento (útil para testes)."""
        self._store.clear()


# Instância global do idempotency store
_idempotency_store = IdempotencyStore()


def get_idempotency_store() -> IdempotencyStore:
    """Retorna a instância global do IdempotencyStore."""
    return _idempotency_store


async def find_previous_mews_score(
    db: AsyncSession, mpi_id: str, before: datetime
) -> tuple[int | None, int | None]:
    """Busca o score MEWS mais recente antes de um determinado timestamp.

    Args:
        db: Sessão assíncrona do SQLAlchemy.
        mpi_id: ID do paciente.
        before: Timestamp de referência.

    Returns:
        Tuple de (score_value, score_id) do último MEWS anterior,
        ou (None, None) se não houver score anterior.
    """
    stmt = (
        select(ClinicalScore.score_value, ClinicalScore.id)
        .where(
            ClinicalScore.mpi_id == mpi_id,
            ClinicalScore.score_type == "MEWS",
            ClinicalScore.calculated_at < before,
        )
        .order_by(ClinicalScore.calculated_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.first()
    if row is None:
        return None, None
    return row.score_value, row.id


async def ingest_vitals(
    db: AsyncSession,
    data: VitalSignCreate,
    idempotency_key: str | None = None,
) -> tuple[VitalSignResponse, list[Alert]]:
    """Ingere sinais vitais com idempotência, scoring e alert engine.

    Fluxo:
    1. Verifica idempotency key (se fornecida) — retorna resultado existente.
    2. Persiste registro em vital_sign.
    3. Calcula MEWS, NEWS2, SOFA, qSOFA sincronamente.
    4. Persiste clinical_scores com versão do algoritmo.
    5. Executa alert engine para cada score e coleta alertas gerados.
    6. Armazena idempotency key para requisições futuras.

    Args:
        db: Sessão assíncrona do SQLAlchemy.
        data: Schema Pydantic com os sinais vitais.
        idempotency_key: Chave de idempotência (MSH-10 / X-Idempotency-Key).

    Returns:
        Tuple of (VitalSignResponse, list of created Alert objects).
    """
    store = get_idempotency_store()

    # 1. Verifica idempotência
    if idempotency_key and store.key_exists(idempotency_key):
        stored_id = store.get_stored_id(idempotency_key)
        # Busca o registro já existente para montar resposta
        stmt = select(VitalSign).where(VitalSign.id == stored_id)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is not None:
            mews_score = await _get_mews_for_vital(db, stored_id)
            news2_score, news2_risk = await _get_news2_for_vital(db, stored_id)
            sofa_score, sofa_risk = await _get_sofa_for_vital(db, stored_id)
            qsofa_score, qsofa_high_risk = await _get_qsofa_for_vital(db, stored_id)
            return VitalSignResponse(
                id=existing.id,
                mpi_id=existing.mpi_id,
                recorded_at=existing.recorded_at,
                ingested_at=existing.ingested_at,
                mews_score=mews_score,
                news2_score=news2_score,
                news2_risk_category=news2_risk,
                sofa_score=sofa_score,
                sofa_mortality_risk=sofa_risk,
                qsofa_score=qsofa_score,
                qsofa_is_high_risk=qsofa_high_risk,
                message="Idempotent replay — vital signs already ingested",
            ), []

    # 2. Persiste sinais vitais
    now = datetime.now(timezone.utc)
    vital = VitalSign(
        mpi_id=data.mpi_id,
        recorded_at=data.recorded_at,
        heart_rate=data.heart_rate,
        systolic_bp=data.systolic_bp,
        diastolic_bp=data.diastolic_bp,
        temperature=data.temperature,
        spo2=data.spo2,
        respiratory_rate=data.respiratory_rate,
        avpu=data.avpu,
        supplemental_o2=data.supplemental_o2,
        source_system=data.source_system,
        ingested_at=now,
        # Lab fields for SOFA/qSOFA
        pao2_fio2=data.pao2_fio2,
        mechanical_ventilation=data.mechanical_ventilation,
        platelets=data.platelets,
        bilirubin=data.bilirubin,
        map_value=data.map_value,
        vasopressor_type=data.vasopressor_type,
        vasopressor_dose_mcg_kg_min=data.vasopressor_dose_mcg_kg_min,
        gcs=data.gcs,
        creatinine=data.creatinine,
        urine_output_ml_day=data.urine_output_ml_day,
    )
    db.add(vital)
    await db.flush()  # Obtém o ID sem commitar a transação

    # Garante que o ID foi populado pelo banco
    assert vital.id is not None, "vital_sign.id deve ser populado após flush"

    # 3. Calcula MEWS
    score_value, components = calculate_mews(
        heart_rate=data.heart_rate,
        systolic_bp=data.systolic_bp,
        respiratory_rate=data.respiratory_rate,
        temperature=data.temperature,
        avpu=data.avpu,
    )

    # 4. Determina tendência vs score anterior
    prev_score, prev_id = await find_previous_mews_score(db, data.mpi_id, now)
    trend: str | None = None
    delta: int | None = None
    if prev_score is not None:
        delta = score_value - prev_score
        if delta > 0:
            trend = "increasing"
        elif delta < 0:
            trend = "decreasing"
        else:
            trend = "stable"
    else:
        # Primeiro score — sem tendência
        trend = None
        delta = None

    # 5. Persiste clinical_score MEWS
    score = ClinicalScore(
        mpi_id=data.mpi_id,
        score_type="MEWS",
        score_value=score_value,
        algorithm_version=MEWS_VERSION,
        calculated_at=now,
        vital_sign_id=vital.id,
        components=components,
        trend=trend,
        delta_from_previous=delta,
    )
    db.add(score)
    await db.flush()

    # 6. Calcula e persiste NEWS2
    news2_result = calculate_news2(
        respiratory_rate=data.respiratory_rate,
        spo2=data.spo2,
        hypercapnic=False,
        supplemental_o2=data.supplemental_o2,
        systolic_bp=data.systolic_bp,
        heart_rate=data.heart_rate,
        avpu=data.avpu,
        temperature=data.temperature,
    )
    news2_score = ClinicalScore(
        mpi_id=data.mpi_id,
        score_type="NEWS2",
        score_value=news2_result.total_score,
        algorithm_version="NEWS2-v1.0",
        calculated_at=now,
        vital_sign_id=vital.id,
        components=asdict(news2_result.components),
        trend=None,
        delta_from_previous=None,
    )
    db.add(news2_score)
    await db.flush()

    # 6b. Calcula e persiste SOFA
    sofa_result = calculate_sofa(
        pao2_fio2=data.pao2_fio2,
        mechanical_ventilation=data.mechanical_ventilation,
        platelets=data.platelets,
        bilirubin=data.bilirubin,
        map_value=data.map_value,
        vasopressor_type=data.vasopressor_type,
        vasopressor_dose_mcg_kg_min=data.vasopressor_dose_mcg_kg_min,
        gcs=data.gcs,
        creatinine=data.creatinine,
        urine_output_ml_day=data.urine_output_ml_day,
    )
    sofa_score_cs = ClinicalScore(
        mpi_id=data.mpi_id,
        score_type="SOFA",
        score_value=sofa_result.total_score,
        algorithm_version=SOFA_VERSION,
        calculated_at=now,
        vital_sign_id=vital.id,
        components=asdict(sofa_result.components),
        trend=None,
        delta_from_previous=None,
    )
    db.add(sofa_score_cs)
    await db.flush()

    # 6c. Calcula e persiste qSOFA
    qsofa_result = calculate_qsofa(
        respiratory_rate=data.respiratory_rate,
        systolic_bp=data.systolic_bp,
        gcs=data.gcs,
    )
    qsofa_cs = ClinicalScore(
        mpi_id=data.mpi_id,
        score_type="qSOFA",
        score_value=qsofa_result.total_score,
        algorithm_version=QSOFA_VERSION,
        calculated_at=now,
        vital_sign_id=vital.id,
        components=asdict(qsofa_result.components),
        trend=None,
        delta_from_previous=None,
    )
    db.add(qsofa_cs)
    await db.flush()

    # 7. Executa alert engine — verifica thresholds e cria alertas
    alerts: list[Alert] = []

    # Check MEWS score against thresholds
    mews_alert = await process_clinical_score(db=db, score=score)
    if mews_alert is not None:
        alerts.append(mews_alert)

    # Check NEWS2 score against thresholds
    news2_alert = await process_clinical_score(db=db, score=news2_score)
    if news2_alert is not None:
        alerts.append(news2_alert)

    # Check SOFA score against thresholds
    sofa_alert = await process_clinical_score(db=db, score=sofa_score_cs)
    if sofa_alert is not None:
        alerts.append(sofa_alert)

    # Check qSOFA score against thresholds
    qsofa_alert = await process_clinical_score(db=db, score=qsofa_cs)
    if qsofa_alert is not None:
        alerts.append(qsofa_alert)

    # 8. Armazena idempotency key
    if idempotency_key:
        store.store_key(idempotency_key, vital.id)

    return VitalSignResponse(
        id=vital.id,
        mpi_id=vital.mpi_id,
        recorded_at=vital.recorded_at,
        ingested_at=vital.ingested_at,
        mews_score=score_value,
        news2_score=news2_result.total_score,
        news2_risk_category=news2_result.risk_category,
        sofa_score=sofa_result.total_score,
        sofa_mortality_risk=sofa_result.sepsis_mortality_risk,
        qsofa_score=qsofa_result.total_score,
        qsofa_is_high_risk=qsofa_result.is_high_risk,
        message="Vital signs ingested successfully",
    ), alerts


async def _get_mews_for_vital(db: AsyncSession, vital_sign_id: int) -> int | None:
    """Busca o MEWS score associado a um registro de vital_sign."""
    stmt = select(ClinicalScore.score_value).where(
        ClinicalScore.vital_sign_id == vital_sign_id,
        ClinicalScore.score_type == "MEWS",
    )
    result = await db.execute(stmt)
    row = result.first()
    return row.score_value if row else None


async def _get_news2_for_vital(db: AsyncSession, vital_sign_id: int) -> tuple[int | None, str | None]:
    """Busca o NEWS2 score e risk_category associados a um registro de vital_sign."""
    stmt = select(ClinicalScore.score_value, ClinicalScore.algorithm_version).where(
        ClinicalScore.vital_sign_id == vital_sign_id,
        ClinicalScore.score_type == "NEWS2",
    )
    result = await db.execute(stmt)
    row = result.first()
    if row is None:
        return None, None
    # Derive risk_category from score_value (mirrors NEWS2Result.risk_category)
    score = row.score_value
    if score >= 7:
        risk = "high"
    elif score >= 5:
        risk = "medium"
    else:
        risk = "low"
    return score, risk


async def _get_sofa_for_vital(db: AsyncSession, vital_sign_id: int) -> tuple[int | None, str | None]:
    """Busca o SOFA score e mortality_risk associados a um registro de vital_sign."""
    stmt = select(ClinicalScore.score_value).where(
        ClinicalScore.vital_sign_id == vital_sign_id,
        ClinicalScore.score_type == "SOFA",
    )
    result = await db.execute(stmt)
    row = result.first()
    if row is None:
        return None, None
    score = row.score_value
    if score >= 11:
        risk = "Very High (>90%)"
    elif score >= 9:
        risk = "High (50-90%)"
    elif score >= 5:
        risk = "Moderate (20-50%)"
    else:
        risk = "Low (<20%)"
    return score, risk


async def _get_qsofa_for_vital(db: AsyncSession, vital_sign_id: int) -> tuple[int | None, bool | None]:
    """Busca o qSOFA score e is_high_risk associados a um registro de vital_sign."""
    stmt = select(ClinicalScore.score_value).where(
        ClinicalScore.vital_sign_id == vital_sign_id,
        ClinicalScore.score_type == "qSOFA",
    )
    result = await db.execute(stmt)
    row = result.first()
    if row is None:
        return None, None
    return row.score_value, row.score_value >= 2 if row.score_value is not None else None
