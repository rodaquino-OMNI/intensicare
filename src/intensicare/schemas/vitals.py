"""Pydantic schemas para ingestão de sinais vitais."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


AVPU_VALUES = frozenset({"A", "V", "P", "U"})


class VitalSignCreate(BaseModel):
    """Schema para criação de registro de sinais vitais.

    Todos os campos são opcionais exceto mpi_id e recorded_at.
    """

    mpi_id: str = Field(
        ...,
        max_length=64,
        description="Master Patient Identifier (FK para MPI da AMH)",
        examples=["MPI-00012345"],
    )
    recorded_at: datetime = Field(
        ...,
        description="Momento da coleta do sinal vital (ISO 8601 com timezone)",
    )
    heart_rate: int | None = Field(
        None, ge=0, le=300, description="Frequência cardíaca (bpm)"
    )
    systolic_bp: int | None = Field(
        None, ge=0, le=350, description="Pressão sistólica (mmHg)"
    )
    diastolic_bp: int | None = Field(
        None, ge=0, le=250, description="Pressão diastólica (mmHg)"
    )
    temperature: float | None = Field(
        None, ge=25.0, le=45.0, description="Temperatura (°C)"
    )
    spo2: int | None = Field(
        None, ge=0, le=100, description="Saturação de O2 (%)"
    )
    respiratory_rate: int | None = Field(
        None, ge=0, le=80, description="Frequência respiratória (rpm)"
    )
    avpu: str | None = Field(
        None,
        max_length=4,
        description="Nível de consciência: A(Alert), V(Voice), P(Pain), U(Unresponsive)",
    )
    supplemental_o2: bool | None = Field(
        None, description="Uso de oxigênio suplementar"
    )
    source_system: str | None = Field(
        None, max_length=32, description="Sistema de origem (ex: tasy, philips_monitor)"
    )

    @field_validator("avpu")
    @classmethod
    def validate_avpu(cls, v: str | None) -> str | None:
        """Normaliza e valida o campo AVPU."""
        if v is None:
            return None
        upper = v.upper().strip()
        if upper not in AVPU_VALUES:
            raise ValueError(
                f"avpu deve ser um de {sorted(AVPU_VALUES)}, recebido: {v!r}"
            )
        return upper


class VitalSignResponse(BaseModel):
    """Schema de resposta após criação de registro de sinais vitais."""

    id: int = Field(..., description="ID do registro de sinais vitais criado")
    mpi_id: str = Field(..., description="Master Patient Identifier")
    recorded_at: datetime = Field(..., description="Momento da coleta")
    ingested_at: datetime = Field(..., description="Timestamp de ingestão")
    mews_score: int | None = Field(
        None, description="MEWS calculado (None se dados insuficientes)"
    )
    news2_score: int | None = Field(
        None, description="NEWS2 calculado (None se dados insuficientes)"
    )
    news2_risk_category: str | None = Field(
        None, description="Categoria de risco NEWS2: low, medium, high"
    )
    message: str = Field(
        default="Vital signs ingested successfully",
        description="Mensagem de status",
    )

    model_config = {"from_attributes": True}
