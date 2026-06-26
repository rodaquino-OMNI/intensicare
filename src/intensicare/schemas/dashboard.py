"""Pydantic schemas for the clinical dashboard."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PatientBedSummary(BaseModel):
    """Summary of a patient for the bed grid dashboard."""

    mpi_id: str
    bed_id: str | None = None
    display_name: str
    unit: str | None = None
    latest_mews: int | None = None
    latest_news2: int | None = None
    news2_risk: str | None = None  # low, medium, high
    mews_trend: str | None = None  # increasing, decreasing, stable
    news2_trend: str | None = None
    active_alerts_count: int = 0
    highest_alert_severity: str | None = None  # info, warning, critical
    last_updated: str | None = None


class DashboardResponse(BaseModel):
    """Dashboard response with list of patient bed summaries."""

    patients: list[PatientBedSummary] = Field(default_factory=list)
    total: int = 0
    active_alerts_total: int = 0


class VitalsHistoryPoint(BaseModel):
    """A single vitals data point for charting."""

    recorded_at: str
    heart_rate: int | None = None
    systolic_bp: int | None = None
    diastolic_bp: int | None = None
    temperature: float | None = None
    spo2: int | None = None
    respiratory_rate: int | None = None
    avpu: str | None = None
    supplemental_o2: bool | None = None


class ScoreHistoryPoint(BaseModel):
    """A single score data point for charting."""

    calculated_at: str
    score_type: str
    score_value: int
    trend: str | None = None


class PatientDetailResponse(BaseModel):
    """Detailed patient view with vitals history and scores."""

    mpi_id: str
    bed_id: str | None = None
    display_name: str
    unit: str | None = None
    vitals_history: list[VitalsHistoryPoint] = Field(default_factory=list)
    mews_history: list[ScoreHistoryPoint] = Field(default_factory=list)
    news2_history: list[ScoreHistoryPoint] = Field(default_factory=list)
    active_alerts: list = Field(default_factory=list)
