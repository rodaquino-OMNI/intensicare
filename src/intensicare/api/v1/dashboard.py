"""Dashboard API endpoints — patient list, patient detail."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from intensicare.core.database import get_db
from intensicare.schemas.dashboard import DashboardResponse, PatientDetailResponse
from intensicare.services.dashboard import get_dashboard, get_patient_detail

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Clinical dashboard — bed grid",
    description="Returns summary for all active patients with latest MEWS, NEWS2, and alert status.",
)
async def dashboard(
    unit: str | None = Query(None, description="Filter by unit"),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    """Get the clinical dashboard bed grid data."""
    try:
        return await get_dashboard(db=db, unit=unit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load dashboard: {exc}",
        ) from exc


@router.get(
    "/patients/{mpi_id}/detail",
    response_model=PatientDetailResponse,
    summary="Patient detail view",
    description="Returns detailed patient data with vitals history (24h), score history, and active alerts.",
)
async def patient_detail(
    mpi_id: str,
    db: AsyncSession = Depends(get_db),
) -> PatientDetailResponse:
    """Get detailed patient information for the detail view."""
    result = await get_patient_detail(db=db, mpi_id=mpi_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient not found: {mpi_id}",
        )
    return result
