"""Sinais vitais — TimescaleDB hypertable em recorded_at."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from intensicare.core.database import Base


class VitalSign(Base):
    """Sinais vitais recebidos. Hypertable em recorded_at."""

    __tablename__ = "vital_sign"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    mpi_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    heart_rate: Mapped[int | None] = mapped_column(Integer)
    systolic_bp: Mapped[int | None] = mapped_column(Integer)
    diastolic_bp: Mapped[int | None] = mapped_column(Integer)
    temperature: Mapped[float | None] = mapped_column(Numeric(4, 1))
    spo2: Mapped[int | None] = mapped_column(Integer)
    respiratory_rate: Mapped[int | None] = mapped_column(Integer)
    avpu: Mapped[str | None] = mapped_column(String(4))
    supplemental_o2: Mapped[bool | None] = mapped_column(Boolean)
    source_system: Mapped[str | None] = mapped_column(String(32))
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
