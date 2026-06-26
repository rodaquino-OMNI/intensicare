"""Pydantic schemas para status do paciente."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class VitalSignSummary(BaseModel):
    """Resumo dos sinais vitais mais recentes."""

    id: int
    recorded_at: datetime
    heart_rate: int | None = None
    systolic_bp: int | None = None
    diastolic_bp: int | None = None
    temperature: float | None = None
    spo2: int | None = None
    respiratory_rate: int | None = None
    avpu: str | None = None
    supplemental_o2: bool | None = None

    model_config = {"from_attributes": True}


class ScoreSummary(BaseModel):
    """Resumo de um score clínico."""

    id: int
    score_type: str
    score_value: int
    calculated_at: datetime
    components: dict | None = None
    trend: str | None = None
    delta_from_previous: int | None = None

    model_config = {"from_attributes": True}


class TrendSummary(BaseModel):
    """Resumo de tendência dos scores (últimos 5)."""

    values: list[int] = Field(
        default_factory=list,
        description="Últimos valores de score em ordem cronológica",
    )
    current_trend: str | None = Field(
        None, description="Tendência atual: increasing, decreasing, stable"
    )


class FHIREnrichment(BaseModel):
    """FHIR-enriched demographics and clinical context from HAPI FHIR.

    Only populated when FHIR_BASE_URL is configured and enrichment
    is requested (enrich=true query parameter).
    """

    display_name: str | None = None
    gender: str | None = None
    birth_date: str | None = None
    marital_status: str | None = None
    phone: str | None = None
    address: str | None = None
    primary_condition: str | None = None
    condition_list: list[str] = Field(default_factory=list)
    allergy_list: list[str] = Field(default_factory=list)
    latest_observations: dict = Field(default_factory=dict)


class PatientStatusResponse(BaseModel):
    """Resposta completa do status do paciente."""

    mpi_id: str = Field(..., description="Master Patient Identifier")
    latest_vitals: VitalSignSummary | None = Field(
        None, description="Sinais vitais mais recentes"
    )
    latest_mews: ScoreSummary | None = Field(
        None, description="Último score MEWS calculado"
    )
    trend: TrendSummary = Field(
        default_factory=lambda: TrendSummary(),
        description="Tendência de scores",
    )
    last_updated: datetime | None = Field(
        None, description="Timestamp da última atualização"
    )
    fhir: FHIREnrichment | None = Field(
        None,
        description="FHIR enrichment data (only when enrich=true is requested "
        "and FHIR_BASE_URL is configured).",
    )

    model_config = {"from_attributes": True}
