"""Dashboard service — aggregates patient data for the clinical dashboard."""

from __future__ import annotations

from sqlalchemy import desc, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from intensicare.models import PatientCache, Alert, ClinicalScore, VitalSign
from intensicare.schemas.dashboard import (
    PatientBedSummary,
    DashboardResponse,
    PatientDetailResponse,
    VitalsHistoryPoint,
    ScoreHistoryPoint,
)
from intensicare.services.mews import compute_trend


async def get_dashboard(
    db: AsyncSession,
    unit: str | None = None,
) -> DashboardResponse:
    """Get all patients with their latest scores and alert status for the bed grid.

    Args:
        db: Async database session.
        unit: Optional unit filter.
    """
    # Get all active patients
    patient_query = select(PatientCache).where(PatientCache.is_active == True)
    if unit:
        patient_query = patient_query.where(PatientCache.unit == unit)
    patient_query = patient_query.order_by(PatientCache.bed_id)
    result = await db.execute(patient_query)
    patients = result.scalars().all()

    if not patients:
        return DashboardResponse(patients=[], total=0, active_alerts_total=0)

    mpi_ids = [p.mpi_id for p in patients]
    patient_map = {p.mpi_id: p for p in patients}

    # Get latest MEWS for each patient — use a single query with DISTINCT ON
    # or iterate. For simplicity, do a subquery approach.
    # Get all alert counts grouped by mpi_id
    alert_counts = {}
    alert_severities = {}
    alert_query = (
        select(
            Alert.mpi_id,
            Alert.severity,
            func.count(Alert.id).over(partition_by=Alert.mpi_id),
        )
        .where(Alert.mpi_id.in_(mpi_ids), Alert.status == "active")
        .order_by(Alert.mpi_id, Alert.created_at.desc())
    )
    alert_result = await db.execute(alert_query)
    alert_rows = alert_result.fetchall()
    seen_mpi = set()
    for row in alert_rows:
        mpi = row[0]
        sev = row[1]
        cnt = row[2]
        if mpi not in seen_mpi:
            alert_counts[mpi] = cnt
            alert_severities[mpi] = sev
            seen_mpi.add(mpi)

    total_alerts = sum(alert_counts.values())

    # Get latest MEWS and NEWS2 scores per patient
    # Use a raw approach: get all latest scores in subquery
    from sqlalchemy import and_

    # Latest MEWS per patient
    mews_subq = (
        select(
            ClinicalScore.mpi_id,
            ClinicalScore.score_value,
            ClinicalScore.trend,
            func.row_number()
            .over(
                partition_by=ClinicalScore.mpi_id,
                order_by=desc(ClinicalScore.calculated_at),
            )
            .label("rn"),
        )
        .where(
            ClinicalScore.mpi_id.in_(mpi_ids),
            ClinicalScore.score_type == "MEWS",
        )
        .subquery()
    )
    mews_query = select(
        mews_subq.c.mpi_id,
        mews_subq.c.score_value,
        mews_subq.c.trend,
    ).where(mews_subq.c.rn == 1)
    mews_result = await db.execute(mews_query)
    mews_map = {row[0]: (row[1], row[2]) for row in mews_result.fetchall()}

    # Latest NEWS2 per patient
    news2_subq = (
        select(
            ClinicalScore.mpi_id,
            ClinicalScore.score_value,
            ClinicalScore.trend,
            ClinicalScore.components,
            func.row_number()
            .over(
                partition_by=ClinicalScore.mpi_id,
                order_by=desc(ClinicalScore.calculated_at),
            )
            .label("rn"),
        )
        .where(
            ClinicalScore.mpi_id.in_(mpi_ids),
            ClinicalScore.score_type == "NEWS2",
        )
        .subquery()
    )
    news2_query = select(
        news2_subq.c.mpi_id,
        news2_subq.c.score_value,
        news2_subq.c.trend,
        news2_subq.c.components,
    ).where(news2_subq.c.rn == 1)
    news2_result = await db.execute(news2_query)
    news2_map = {}
    for row in news2_result.fetchall():
        news2_map[row[0]] = (row[1], row[2])

    # Build response
    bed_summaries = []
    for p in patients:
        mews_data = mews_map.get(p.mpi_id)
        news2_data = news2_map.get(p.mpi_id)

        # Determine NEWS2 risk category
        news2_risk = None
        news2_score = None
        if news2_data:
            news2_score = news2_data[0]
            if news2_score >= 7:
                news2_risk = "high"
            elif news2_score >= 5:
                news2_risk = "medium"
            else:
                news2_risk = "low"

        bed_summaries.append(
            PatientBedSummary(
                mpi_id=p.mpi_id,
                bed_id=p.bed_id,
                display_name=p.display_name,
                unit=p.unit,
                latest_mews=mews_data[0] if mews_data else None,
                latest_news2=news2_score,
                news2_risk=news2_risk,
                mews_trend=mews_data[1] if mews_data else None,
                news2_trend=news2_data[1] if news2_data else None,
                active_alerts_count=alert_counts.get(p.mpi_id, 0),
                highest_alert_severity=alert_severities.get(p.mpi_id),
                last_updated=p.synced_at.isoformat() if p.synced_at else None,
            )
        )

    return DashboardResponse(
        patients=bed_summaries,
        total=len(bed_summaries),
        active_alerts_total=total_alerts,
    )


async def get_patient_detail(
    db: AsyncSession,
    mpi_id: str,
) -> PatientDetailResponse | None:
    """Get detailed patient information including vitals history and scores.

    Args:
        db: Async database session.
        mpi_id: Patient MPI ID.
    """
    # Get patient cache
    patient_result = await db.execute(
        select(PatientCache).where(PatientCache.mpi_id == mpi_id)
    )
    patient = patient_result.scalar_one_or_none()
    if not patient:
        return None

    # Get vitals history (last 24h)
    from datetime import datetime, timezone, timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    vitals_query = (
        select(VitalSign)
        .where(VitalSign.mpi_id == mpi_id, VitalSign.recorded_at >= cutoff)
        .order_by(VitalSign.recorded_at.asc())
        .limit(200)
    )
    vitals_result = await db.execute(vitals_query)
    vitals = vitals_result.scalars().all()

    vitals_history = [
        VitalsHistoryPoint(
            recorded_at=v.recorded_at.isoformat(),
            heart_rate=v.heart_rate,
            systolic_bp=v.systolic_bp,
            diastolic_bp=v.diastolic_bp,
            temperature=float(v.temperature) if v.temperature else None,
            spo2=v.spo2,
            respiratory_rate=v.respiratory_rate,
            avpu=v.avpu,
            supplemental_o2=v.supplemental_o2,
        )
        for v in vitals
    ]

    # Get MEWS history
    mews_query = (
        select(ClinicalScore)
        .where(
            ClinicalScore.mpi_id == mpi_id,
            ClinicalScore.score_type == "MEWS",
            ClinicalScore.calculated_at >= cutoff,
        )
        .order_by(ClinicalScore.calculated_at.asc())
        .limit(200)
    )
    mews_result = await db.execute(mews_query)
    mews_history = [
        ScoreHistoryPoint(
            calculated_at=s.calculated_at.isoformat(),
            score_type=s.score_type,
            score_value=s.score_value,
            trend=s.trend,
        )
        for s in mews_result.scalars().all()
    ]

    # Get NEWS2 history
    news2_query = (
        select(ClinicalScore)
        .where(
            ClinicalScore.mpi_id == mpi_id,
            ClinicalScore.score_type == "NEWS2",
            ClinicalScore.calculated_at >= cutoff,
        )
        .order_by(ClinicalScore.calculated_at.asc())
        .limit(200)
    )
    news2_result = await db.execute(news2_query)
    news2_history = [
        ScoreHistoryPoint(
            calculated_at=s.calculated_at.isoformat(),
            score_type=s.score_type,
            score_value=s.score_value,
            trend=s.trend,
        )
        for s in news2_result.scalars().all()
    ]

    # Get active alerts
    alerts_query = (
        select(Alert)
        .where(Alert.mpi_id == mpi_id, Alert.status == "active")
        .order_by(Alert.created_at.desc())
        .limit(50)
    )
    alerts_result = await db.execute(alerts_query)
    alerts_list = []
    for a in alerts_result.scalars().all():
        alerts_list.append({
            "id": a.id,
            "mpi_id": a.mpi_id,
            "score_id": a.score_id,
            "severity": a.severity,
            "status": a.status,
            "title": a.title,
            "body": a.body,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
            "acknowledged_by": a.acknowledged_by,
            "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
            "resolution": a.resolution,
        })

    return PatientDetailResponse(
        mpi_id=patient.mpi_id,
        bed_id=patient.bed_id,
        display_name=patient.display_name,
        unit=patient.unit,
        vitals_history=vitals_history,
        mews_history=mews_history,
        news2_history=news2_history,
        active_alerts=alerts_list,
    )
