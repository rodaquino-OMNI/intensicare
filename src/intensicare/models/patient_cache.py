"""Cache local de dados demográficos do paciente."""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from intensicare.core.database import Base


class PatientCache(Base):
    """Cache local de dados demográficos. Fonte primária: MPI da AMH."""

    __tablename__ = "patient_cache"

    mpi_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mrn: Mapped[str | None] = mapped_column(String(64))
    gender: Mapped[str | None] = mapped_column(String(16))
    birth_date: Mapped[date | None] = mapped_column(Date)
    admission_dt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    bed_id: Mapped[str | None] = mapped_column(String(32))
    unit: Mapped[str | None] = mapped_column(String(64))
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
