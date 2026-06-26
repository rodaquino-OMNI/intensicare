"""initial: cria todas as tabelas do Intensicare com TimescaleDB hypertables

Revision ID: 0001
Revises:
Create Date: 2026-06-26 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # TimescaleDB extension
    # ------------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")

    # ------------------------------------------------------------------
    # 1. patient_cache
    # ------------------------------------------------------------------
    op.create_table(
        "patient_cache",
        sa.Column("mpi_id", sa.String(64), nullable=False),
        sa.Column("tenant_id", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("mrn", sa.String(64), nullable=True),
        sa.Column("gender", sa.String(16), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("admission_dt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("bed_id", sa.String(32), nullable=True),
        sa.Column("unit", sa.String(64), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("mpi_id"),
    )
    op.create_index("ix_patient_cache_tenant_id", "patient_cache", ["tenant_id"])

    # ------------------------------------------------------------------
    # 2. vital_sign (TimescaleDB hypertable on recorded_at)
    # ------------------------------------------------------------------
    op.create_table(
        "vital_sign",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("mpi_id", sa.String(64), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("heart_rate", sa.Integer(), nullable=True),
        sa.Column("systolic_bp", sa.Integer(), nullable=True),
        sa.Column("diastolic_bp", sa.Integer(), nullable=True),
        sa.Column("temperature", sa.Numeric(4, 1), nullable=True),
        sa.Column("spo2", sa.Integer(), nullable=True),
        sa.Column("respiratory_rate", sa.Integer(), nullable=True),
        sa.Column("avpu", sa.String(4), nullable=True),
        sa.Column("supplemental_o2", sa.Boolean(), nullable=True),
        sa.Column("source_system", sa.String(32), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vital_sign_mpi_id", "vital_sign", ["mpi_id"])
    # TimescaleDB hypertable
    op.execute(
        "SELECT create_hypertable('vital_sign', 'recorded_at', if_not_exists => true)"
    )

    # ------------------------------------------------------------------
    # 3. clinical_score (TimescaleDB hypertable on calculated_at)
    # ------------------------------------------------------------------
    op.create_table(
        "clinical_score",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("mpi_id", sa.String(64), nullable=False),
        sa.Column("score_type", sa.String(16), nullable=False),
        sa.Column("score_value", sa.Integer(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("vital_sign_id", sa.BigInteger(), nullable=True),
        sa.Column("components", postgresql.JSONB(), nullable=True),
        sa.Column("trend", sa.String(16), nullable=True),
        sa.Column("delta_from_previous", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clinical_score_mpi_id", "clinical_score", ["mpi_id"])
    # TimescaleDB hypertable
    op.execute(
        "SELECT create_hypertable('clinical_score', 'calculated_at', if_not_exists => true)"
    )

    # ------------------------------------------------------------------
    # 4. alert (TimescaleDB hypertable on created_at)
    # ------------------------------------------------------------------
    op.create_table(
        "alert",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("mpi_id", sa.String(64), nullable=False),
        sa.Column("score_id", sa.BigInteger(), nullable=True),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'active'")),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", sa.String(255), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution", sa.String(32), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_mpi_id", "alert", ["mpi_id"])
    # TimescaleDB hypertable
    op.execute(
        "SELECT create_hypertable('alert', 'created_at', if_not_exists => true)"
    )

    # ------------------------------------------------------------------
    # 5. threshold_config
    # ------------------------------------------------------------------
    op.create_table(
        "threshold_config",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.String(32), nullable=False),
        sa.Column("unit", sa.String(64), nullable=True),
        sa.Column("score_type", sa.String(16), nullable=False),
        sa.Column("watch_threshold", sa.Integer(), nullable=False),
        sa.Column("urgent_threshold", sa.Integer(), nullable=False),
        sa.Column("critical_threshold", sa.Integer(), nullable=False),
        sa.Column("rate_limit_per_hour", sa.Integer(), nullable=True),
        sa.Column("cooldown_minutes", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("threshold_config")
    op.drop_table("alert")
    op.drop_table("clinical_score")
    op.drop_table("vital_sign")
    op.drop_table("patient_cache")
