"""Configuração de thresholds de alerta por tenant e unidade."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from intensicare.core.database import Base


class ThresholdConfig(Base):
    """Configuração de thresholds de alerta."""

    __tablename__ = "threshold_config"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(32), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(64))
    score_type: Mapped[str] = mapped_column(String(16), nullable=False)
    watch_threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    urgent_threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    critical_threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    rate_limit_per_hour: Mapped[int | None] = mapped_column(Integer)
    cooldown_minutes: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_by: Mapped[str | None] = mapped_column(String(255))
