"""Tests for the alert engine."""

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from intensicare.models.alert import Alert
from intensicare.models.clinical_score import ClinicalScore
from intensicare.models.patient_cache import PatientCache
from intensicare.models.threshold_config import ThresholdConfig
from intensicare.services.alert_engine import (
    check_score_against_thresholds,
    process_clinical_score,
)


async def create_patient(db: AsyncSession, mpi_id="MPI-1001", tenant_id="austa", unit="ICU"):
    """Create a test patient."""
    patient = PatientCache(
        mpi_id=mpi_id,
        tenant_id=tenant_id,
        display_name="Test Patient",
        unit=unit,
        is_active=True,
    )
    db.add(patient)
    await db.flush()
    return patient


async def create_threshold_config(
    db: AsyncSession,
    tenant_id="austa",
    unit=None,
    score_type="MEWS",
    watch=3,
    urgent=5,
    critical=7,
    rate_limit=10,
    cooldown=5,
):
    """Create a test threshold config."""
    config = ThresholdConfig(
        tenant_id=tenant_id,
        unit=unit,
        score_type=score_type,
        watch_threshold=watch,
        urgent_threshold=urgent,
        critical_threshold=critical,
        rate_limit_per_hour=rate_limit,
        cooldown_minutes=cooldown,
    )
    db.add(config)
    await db.flush()
    return config


class TestCheckScoreAgainstThresholds:
    """Tests for check_score_against_thresholds."""

    @pytest.mark.asyncio
    async def test_no_config_returns_none(self, db_session: AsyncSession):
        """Should return None when no threshold config exists."""
        score = ClinicalScore(
            mpi_id="MPI-1001",
            score_type="MEWS",
            score_value=5,
            calculated_at=datetime.now(timezone.utc),
        )
        db_session.add(score)
        await db_session.flush()

        result = await check_score_against_thresholds(
            db=db_session,
            clinical_score=score,
            tenant_id="unknown",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_below_watch_returns_none(self, db_session: AsyncSession):
        """Should return None when score is below watch threshold."""
        await create_threshold_config(db_session, watch=3, urgent=5, critical=7)

        score = ClinicalScore(
            mpi_id="MPI-1001",
            score_type="MEWS",
            score_value=2,
            calculated_at=datetime.now(timezone.utc),
        )
        db_session.add(score)
        await db_session.flush()

        result = await check_score_against_thresholds(
            db=db_session,
            clinical_score=score,
            tenant_id="austa",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_watch_threshold_creates_watch_alert(self, db_session: AsyncSession):
        """Should create watch alert when score hits watch threshold."""
        await create_threshold_config(db_session, watch=3, urgent=5, critical=7)

        score = ClinicalScore(
            mpi_id="MPI-1001",
            score_type="MEWS",
            score_value=3,
            calculated_at=datetime.now(timezone.utc),
        )
        db_session.add(score)
        await db_session.flush()

        result = await check_score_against_thresholds(
            db=db_session,
            clinical_score=score,
            tenant_id="austa",
        )
        assert result is not None
        assert result.severity == "watch"
        assert result.status == "active"
        assert result.mpi_id == "MPI-1001"
        assert result.score_id == score.id

    @pytest.mark.asyncio
    async def test_urgent_threshold_creates_urgent_alert(self, db_session: AsyncSession):
        """Should create urgent alert when score hits urgent threshold."""
        await create_threshold_config(db_session, watch=3, urgent=5, critical=7)

        score = ClinicalScore(
            mpi_id="MPI-1001",
            score_type="MEWS",
            score_value=6,
            calculated_at=datetime.now(timezone.utc),
        )
        db_session.add(score)
        await db_session.flush()

        result = await check_score_against_thresholds(
            db=db_session,
            clinical_score=score,
            tenant_id="austa",
        )
        assert result is not None
        assert result.severity == "urgent"

    @pytest.mark.asyncio
    async def test_critical_threshold_creates_critical_alert(self, db_session: AsyncSession):
        """Should create critical alert when score hits critical threshold."""
        await create_threshold_config(db_session, watch=3, urgent=5, critical=7)

        score = ClinicalScore(
            mpi_id="MPI-1001",
            score_type="MEWS",
            score_value=8,
            calculated_at=datetime.now(timezone.utc),
        )
        db_session.add(score)
        await db_session.flush()

        result = await check_score_against_thresholds(
            db=db_session,
            clinical_score=score,
            tenant_id="austa",
        )
        assert result is not None
        assert result.severity == "critical"

    @pytest.mark.asyncio
    async def test_unit_specific_config_takes_precedence(self, db_session: AsyncSession):
        """Unit-specific threshold should take precedence over tenant-wide."""
        await create_threshold_config(db_session, unit=None, watch=3, urgent=5, critical=7)
        await create_threshold_config(db_session, unit="ICU", watch=2, urgent=4, critical=6)

        score = ClinicalScore(
            mpi_id="MPI-1001",
            score_type="MEWS",
            score_value=3,
            calculated_at=datetime.now(timezone.utc),
        )
        db_session.add(score)
        await db_session.flush()

        # With ICU config (watch=2): score 3 should trigger watch
        result = await check_score_against_thresholds(
            db=db_session,
            clinical_score=score,
            tenant_id="austa",
            unit="ICU",
        )
        assert result is not None
        assert result.severity == "watch"

    @pytest.mark.asyncio
    async def test_non_icu_unit_falls_back_to_tenant(self, db_session: AsyncSession):
        """Units without specific config should use tenant-wide config."""
        await create_threshold_config(db_session, unit=None, watch=3, urgent=5, critical=7)

        score = ClinicalScore(
            mpi_id="MPI-1001",
            score_type="MEWS",
            score_value=3,
            calculated_at=datetime.now(timezone.utc),
        )
        db_session.add(score)
        await db_session.flush()

        result = await check_score_against_thresholds(
            db=db_session,
            clinical_score=score,
            tenant_id="austa",
            unit="ER",
        )
        assert result is not None
        assert result.severity == "watch"


class TestProcessClinicalScore:
    """Tests for process_clinical_score."""

    @pytest.mark.asyncio
    async def test_no_patient_returns_none(self, db_session: AsyncSession):
        """Should return None when patient doesn't exist in cache."""
        await create_threshold_config(db_session, watch=3, urgent=5, critical=7)

        score = ClinicalScore(
            mpi_id="MPI-9999",
            score_type="MEWS",
            score_value=5,
            calculated_at=datetime.now(timezone.utc),
        )
        db_session.add(score)
        await db_session.flush()

        result = await process_clinical_score(db=db_session, score=score)
        assert result is None

    @pytest.mark.asyncio
    async def test_with_patient_creates_alert(self, db_session: AsyncSession):
        """Should create alert when patient exists and threshold is exceeded."""
        await create_patient(db_session, mpi_id="MPI-1001", tenant_id="austa", unit="ICU")
        await create_threshold_config(db_session, watch=3, urgent=5, critical=7)

        score = ClinicalScore(
            mpi_id="MPI-1001",
            score_type="MEWS",
            score_value=6,
            calculated_at=datetime.now(timezone.utc),
        )
        db_session.add(score)
        await db_session.flush()

        result = await process_clinical_score(db=db_session, score=score)
        assert result is not None
        assert result.severity == "urgent"
        assert result.mpi_id == "MPI-1001"
