"""Alert engine — checks clinical scores against thresholds and creates alerts."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from intensicare.core.redis import get_redis
from intensicare.models.alert import Alert
from intensicare.models.clinical_score import ClinicalScore
from intensicare.models.patient_cache import PatientCache
from intensicare.models.threshold_config import ThresholdConfig


async def check_score_against_thresholds(
    db: AsyncSession,
    clinical_score: ClinicalScore,
    tenant_id: str,
    unit: str | None = None,
) -> Alert | None:
    """Check a clinical score against thresholds and create an alert if warranted.

    Returns the created Alert or None if no threshold was exceeded.
    Implements rate limiting via Redis.
    """
    # Find matching threshold config
    config_query = select(ThresholdConfig).where(
        ThresholdConfig.tenant_id == tenant_id,
        ThresholdConfig.score_type == clinical_score.score_type,
    )

    # Try unit-specific config first, fall back to tenant-wide
    if unit:
        unit_config_result = await db.execute(
            config_query.where(ThresholdConfig.unit == unit)
        )
        config = unit_config_result.scalar_one_or_none()

    if not unit or config is None:
        global_config_result = await db.execute(
            config_query.where(ThresholdConfig.unit.is_(None))
        )
        config = global_config_result.scalar_one_or_none()

    if config is None:
        # No threshold config — no alert
        return None

    # Determine severity based on score vs thresholds
    severity = None
    score_value = clinical_score.score_value

    if score_value >= config.critical_threshold:
        severity = "critical"
    elif score_value >= config.urgent_threshold:
        severity = "urgent"
    elif score_value >= config.watch_threshold:
        severity = "watch"

    if severity is None:
        return None

    # Rate limiting via Redis
    redis_client = get_redis()
    rate_limit_key = f"alert_rate:{clinical_score.mpi_id}:{clinical_score.score_type}"
    rate_limit = config.rate_limit_per_hour or 10

    current_count = await redis_client.get(rate_limit_key)
    if current_count and int(current_count) >= rate_limit:
        return None  # Rate limited

    # Cooldown check
    if config.cooldown_minutes:
        cooldown_key = f"alert_cooldown:{clinical_score.mpi_id}:{clinical_score.score_type}:{severity}"
        if await redis_client.exists(cooldown_key):
            return None  # Still in cooldown

    # Create the alert
    title = f"{clinical_score.score_type} {severity.upper()}: {score_value}"
    body = (
        f"Patient {clinical_score.mpi_id} — {clinical_score.score_type} score: {score_value}\n"
        f"Threshold: {getattr(config, severity + '_threshold')}\n"
        f"Tenant: {tenant_id}, Unit: {unit or 'N/A'}"
    )

    alert = Alert(
        mpi_id=clinical_score.mpi_id,
        score_id=clinical_score.id,
        severity=severity,
        status="active",
        title=title,
        body=body,
        created_at=datetime.now(timezone.utc),
    )
    db.add(alert)
    await db.flush()

    # Update rate limit counter
    pipe = redis_client.pipeline()
    pipe.incr(rate_limit_key)
    pipe.expire(rate_limit_key, 3600)  # 1 hour window
    if config.cooldown_minutes:
        cooldown_key = f"alert_cooldown:{clinical_score.mpi_id}:{clinical_score.score_type}:{severity}"
        pipe.setex(cooldown_key, config.cooldown_minutes * 60, "1")
    await pipe.execute()

    return alert


async def process_clinical_score(
    db: AsyncSession,
    score: ClinicalScore,
) -> Alert | None:
    """Process a clinical score: find the patient's tenant/unit and check thresholds."""
    # Get patient info for tenant/unit context
    result = await db.execute(
        select(PatientCache).where(PatientCache.mpi_id == score.mpi_id)
    )
    patient = result.scalar_one_or_none()

    if patient is None:
        return None  # No patient cache — can't determine tenant

    return await check_score_against_thresholds(
        db=db,
        clinical_score=score,
        tenant_id=patient.tenant_id,
        unit=patient.unit,
    )
