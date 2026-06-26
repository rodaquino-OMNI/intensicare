"""Pydantic schemas for threshold configuration."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


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
