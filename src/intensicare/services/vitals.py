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

from intensicare.models import ClinicalScore, VitalSign
from intensicare.schemas.vitals import VitalSignCreate, VitalSignResponse
from intensicare.services.mews import calculate_mews, compute_trend, MEWS_VERSION
from intensicare.services.news2 import calculate_news2


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
) -> VitalSignResponse:
    """Ingere sinais vitais com idempotência e dispara scoring MEWS síncrono.

    Fluxo:
    1. Verifica idempotency key (se fornecida) — retorna resultado existente.
    2. Persiste registro em vital_sign.
    3. Calcula MEWS sincronamente.
    4. Persiste clinical_score com versão do algoritmo.
    5. Armazena idempotency key para requisições futuras.

    Args:
        db: Sessão assíncrona do SQLAlchemy.
        data: Schema Pydantic com os sinais vitais.
        idempotency_key: Chave de idempotência (MSH-10 / X-Idempotency-Key).

    Returns:
        VitalSignResponse com ID do registro e MEWS calculado.
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
            return VitalSignResponse(
                id=existing.id,
                mpi_id=existing.mpi_id,
                recorded_at=existing.recorded_at,
                ingested_at=existing.ingested_at,
                mews_score=mews_score,
                news2_score=news2_score,
                news2_risk_category=news2_risk,
                message="Idempotent replay — vital signs already ingested",
            )

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

    # 7. Armazena idempotency key
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
        message="Vital signs ingested successfully",
    )


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
