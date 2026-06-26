"""Scores clínicos — TimescaleDB hypertable em calculated_at."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from intensicare.core.database import Base


class ClinicalScore(Base):
    """Scores clínicos calculados. Hypertable em calculated_at."""

    __tablename__ = "clinical_score"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    mpi_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    score_type: Mapped[str] = mapped_column(String(16), nullable=False)
    score_value: Mapped[int] = mapped_column(Integer, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    vital_sign_id: Mapped[int | None] = mapped_column(BigInteger)
    components: Mapped[dict | None] = mapped_column(JSONB)
    trend: Mapped[str | None] = mapped_column(String(16))
    delta_from_previous: Mapped[int | None] = mapped_column(Integer)
