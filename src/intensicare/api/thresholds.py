"""Threshold configuration CRUD API — admin-only endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from intensicare.auth import require_admin
from intensicare.core.database import get_db
from intensicare.models.threshold_config import ThresholdConfig
from intensicare.schemas import (
    ThresholdConfigCreate,
    ThresholdConfigResponse,
    ThresholdConfigUpdate,
)

router = APIRouter(
    prefix="/api/v1/thresholds",
    tags=["thresholds"],
    dependencies=[Depends(require_admin)],
)


async def _get_threshold_or_404(
    session: AsyncSession, threshold_id: int
) -> ThresholdConfig:
    """Fetch a threshold config by ID or raise 404."""
    result = await session.execute(
        select(ThresholdConfig).where(ThresholdConfig.id == threshold_id)
    )
    threshold = result.scalar_one_or_none()
    if threshold is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Threshold configuration {threshold_id} not found",
        )
    return threshold


@router.get(
    "",
    response_model=list[ThresholdConfigResponse],
    summary="List all threshold configurations",
)
async def list_thresholds(
    tenant_id: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> list[ThresholdConfig]:
    """List all threshold configurations, optionally filtered by tenant_id."""
    stmt = select(ThresholdConfig)
    if tenant_id:
        stmt = stmt.where(ThresholdConfig.tenant_id == tenant_id)
    stmt = stmt.order_by(ThresholdConfig.id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get(
    "/{threshold_id}",
    response_model=ThresholdConfigResponse,
    summary="Get a threshold configuration by ID",
)
async def get_threshold(
    threshold_id: int,
    session: AsyncSession = Depends(get_db),
) -> ThresholdConfig:
    """Retrieve a single threshold configuration by its ID."""
    return await _get_threshold_or_404(session, threshold_id)


@router.post(
    "",
    response_model=ThresholdConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new threshold configuration",
)
async def create_threshold(
    body: ThresholdConfigCreate,
    session: AsyncSession = Depends(get_db),
    current_user: dict[str, str] = Depends(require_admin),
) -> ThresholdConfig:
    """Create a new threshold configuration (admin-only)."""
    threshold = ThresholdConfig(
        tenant_id=body.tenant_id,
        unit=body.unit,
        score_type=body.score_type,
        watch_threshold=body.watch_threshold,
        urgent_threshold=body.urgent_threshold,
        critical_threshold=body.critical_threshold,
        rate_limit_per_hour=body.rate_limit_per_hour,
        cooldown_minutes=body.cooldown_minutes,
        updated_at=datetime.now(timezone.utc),
        updated_by=current_user["sub"],
    )
    session.add(threshold)
    await session.commit()
    await session.refresh(threshold)
    return threshold


@router.put(
    "/{threshold_id}",
    response_model=ThresholdConfigResponse,
    summary="Update a threshold configuration",
)
async def update_threshold(
    threshold_id: int,
    body: ThresholdConfigUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: dict[str, str] = Depends(require_admin),
) -> ThresholdConfig:
    """Update an existing threshold configuration (admin-only)."""
    threshold = await _get_threshold_or_404(session, threshold_id)

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(threshold, field, value)

    threshold.updated_at = datetime.now(timezone.utc)
    threshold.updated_by = current_user["sub"]

    await session.commit()
    await session.refresh(threshold)
    return threshold


@router.delete(
    "/{threshold_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a threshold configuration",
)
async def delete_threshold(
    threshold_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict[str, str] = Depends(require_admin),
) -> None:
    """Delete a threshold configuration (admin-only)."""
    threshold = await _get_threshold_or_404(session, threshold_id)
    await session.delete(threshold)
    await session.commit()
