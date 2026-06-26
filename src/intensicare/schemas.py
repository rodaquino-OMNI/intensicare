"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ════════════════════════════════════════════════════════════════════════════
# Vital Sign schemas
# ════════════════════════════════════════════════════════════════════════════

class VitalsIngestRequest(BaseModel):
    """Request body for ingesting a new set of vital signs."""

    mpi_id: str = Field(..., min_length=1, max_length=64, description="Master Patient Index ID")
    recorded_at: datetime = Field(..., description="Timestamp when vitals were recorded")
    heart_rate: Optional[int] = Field(None, ge=0, le=300, description="Heart rate (bpm)")
    systolic_bp: Optional[int] = Field(None, ge=0, le=300, description="Systolic blood pressure (mmHg)")
    diastolic_bp: Optional[int] = Field(None, ge=0, le=250, description="Diastolic blood pressure (mmHg)")
    temperature: Optional[float] = Field(None, ge=25.0, le=45.0, description="Temperature (°C)")
    spo2: Optional[int] = Field(None, ge=0, le=100, description="Oxygen saturation (%)")
    respiratory_rate: Optional[int] = Field(None, ge=0, le=80, description="Respiratory rate (bpm)")
    avpu: Optional[str] = Field(None, pattern=r"^[AVPVCUavpu]$", description="AVPU consciousness level")
    supplemental_o2: Optional[bool] = Field(None, description="Patient on supplemental oxygen")
    hypercapnic: Optional[bool] = Field(False, description="Patient has hypercapnic respiratory failure")
    source_system: Optional[str] = Field(None, max_length=32, description="Source system identifier")


class ScoreSummary(BaseModel):
    """Summary of a calculated clinical score."""

    score_type: str
    total_score: int
    algorithm_version: str
    risk_category: str


class VitalsIngestResponse(BaseModel):
    """Response after ingesting vital signs."""

    vital_sign_id: int
    mpi_id: str
    recorded_at: datetime
    ingested_at: datetime
    scores: list[ScoreSummary]


# ════════════════════════════════════════════════════════════════════════════
# Threshold Config schemas
# ════════════════════════════════════════════════════════════════════════════

class ThresholdConfigBase(BaseModel):
    """Base fields for threshold configuration."""

    tenant_id: str = Field(..., min_length=1, max_length=32)
    unit: Optional[str] = Field(None, max_length=64)
    score_type: str = Field(..., min_length=1, max_length=16)
    watch_threshold: int = Field(..., ge=0)
    urgent_threshold: int = Field(..., ge=0)
    critical_threshold: int = Field(..., ge=0)
    rate_limit_per_hour: Optional[int] = Field(None, ge=0)
    cooldown_minutes: Optional[int] = Field(None, ge=0)


class ThresholdConfigCreate(ThresholdConfigBase):
    """Request body for creating a threshold configuration."""

    pass


class ThresholdConfigUpdate(BaseModel):
    """Request body for updating a threshold configuration (partial)."""

    tenant_id: Optional[str] = Field(None, min_length=1, max_length=32)
    unit: Optional[str] = Field(None, max_length=64)
    score_type: Optional[str] = Field(None, min_length=1, max_length=16)
    watch_threshold: Optional[int] = Field(None, ge=0)
    urgent_threshold: Optional[int] = Field(None, ge=0)
    critical_threshold: Optional[int] = Field(None, ge=0)
    rate_limit_per_hour: Optional[int] = Field(None, ge=0)
    cooldown_minutes: Optional[int] = Field(None, ge=0)


class ThresholdConfigResponse(ThresholdConfigBase):
    """Response for a threshold configuration (includes id and timestamps)."""

    id: int
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None

    model_config = {"from_attributes": True}
