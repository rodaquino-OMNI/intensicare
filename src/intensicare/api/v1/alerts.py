"""Alert endpoints — list, acknowledge, trace."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from intensicare.auth.dependencies import get_current_user
from intensicare.core.database import get_db
from intensicare.models.alert import Alert
from intensicare.models.user import User

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


class AlertResponse(BaseModel):
    """Alert response schema."""

    id: int
    mpi_id: str
    score_id: int | None
    severity: str
    status: str
    title: str
    body: str | None
    created_at: str
    acknowledged_at: str | None
    acknowledged_by: str | None
    resolved_at: str | None
    resolution: str | None

    model_config = {"from_attributes": True}


class AcknowledgeRequest(BaseModel):
    """Acknowledge an alert."""

    notes: str | None = None


@router.get("", response_model=list[AlertResponse])
async def list_alerts(
    status_filter: str = Query("active", alias="status"),
    unit: str | None = Query(None, alias="unit"),
    mpi_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List alerts with optional filters."""
    query = select(Alert)

    if status_filter:
        query = query.where(Alert.status == status_filter)
    if mpi_id:
        query = query.where(Alert.mpi_id == mpi_id)

    query = query.order_by(Alert.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    alerts = result.scalars().all()

    return [
        AlertResponse(
            id=a.id,
            mpi_id=a.mpi_id,
            score_id=a.score_id,
            severity=a.severity,
            status=a.status,
            title=a.title,
            body=a.body,
            created_at=a.created_at.isoformat() if a.created_at else None,
            acknowledged_at=a.acknowledged_at.isoformat() if a.acknowledged_at else None,
            acknowledged_by=a.acknowledged_by,
            resolved_at=a.resolved_at.isoformat() if a.resolved_at else None,
            resolution=a.resolution,
        )
        for a in alerts
    ]


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: int,
    request_body: AcknowledgeRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Acknowledge an alert (authenticated)."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    if alert.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Alert is already {alert.status}",
        )

    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = current_user.username

    await db.flush()
    await db.refresh(alert)

    return AlertResponse(
        id=alert.id,
        mpi_id=alert.mpi_id,
        score_id=alert.score_id,
        severity=alert.severity,
        status=alert.status,
        title=alert.title,
        body=alert.body,
        created_at=alert.created_at.isoformat() if alert.created_at else None,
        acknowledged_at=alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        acknowledged_by=alert.acknowledged_by,
        resolved_at=alert.resolved_at.isoformat() if alert.resolved_at else None,
        resolution=alert.resolution,
    )


@router.get("/{alert_id}/trace", response_model=AlertResponse)
async def trace_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed trace of a specific alert."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    return AlertResponse(
        id=alert.id,
        mpi_id=alert.mpi_id,
        score_id=alert.score_id,
        severity=alert.severity,
        status=alert.status,
        title=alert.title,
        body=alert.body,
        created_at=alert.created_at.isoformat() if alert.created_at else None,
        acknowledged_at=alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        acknowledged_by=alert.acknowledged_by,
        resolved_at=alert.resolved_at.isoformat() if alert.resolved_at else None,
        resolution=alert.resolution,
    )
