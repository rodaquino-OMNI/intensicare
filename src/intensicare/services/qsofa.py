"""
qSOFA (Quick Sequential Organ Failure Assessment) scoring engine.

Identifies patients at high risk for sepsis using 3 binary criteria:
- Respiratory rate ≥ 22/min
- Systolic blood pressure ≤ 100 mmHg
- Altered mentation (GCS < 15)

A qSOFA score ≥ 2 (out of 3) indicates high risk for sepsis and poor outcomes
in patients with suspected infection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

QSOFA_VERSION = "qSOFA-v1.0"


@dataclass
class qSOFAComponents:
    """Individual binary criteria for qSOFA."""

    respiratory_rate: int = 0     # 1 if RR ≥ 22, else 0
    systolic_bp: int = 0          # 1 if SBP ≤ 100, else 0
    altered_mentation: int = 0    # 1 if GCS < 15, else 0


@dataclass
class qSOFAResult:
    """Result of a qSOFA calculation."""

    total_score: int
    components: qSOFAComponents
    algorithm_version: str = QSOFA_VERSION
    missing_criteria: list[str] = field(default_factory=list)

    @property
    def is_high_risk(self) -> bool:
        """qSOFA ≥ 2 indicates high risk for sepsis."""
        return self.total_score >= 2

    @property
    def risk_level(self) -> str:
        """Return risk level string based on score."""
        if self.total_score >= 2:
            return "high_risk"
        return "low_risk"


# ═══════════════════════════════════════════════════════════════════════════
# Individual criterion scoring
# ═══════════════════════════════════════════════════════════════════════════

def score_respiratory_rate_qsofa(rr: int | None) -> tuple[int, str | None]:
    """Score respiratory rate for qSOFA.

    RR ≥ 22 = 1 point (tachypnea)
    RR < 22 = 0 points

    Args:
        rr: Respiratory rate in breaths per minute, or None.

    Returns:
        Tuple of (score, status_or_None).
    """
    if rr is None:
        return 0, "missing"
    return (1, None) if rr >= 22 else (0, None)


def score_systolic_bp_qsofa(sbp: int | None) -> tuple[int, str | None]:
    """Score systolic blood pressure for qSOFA.

    SBP ≤ 100 mmHg = 1 point (hypotension)
    SBP > 100 mmHg = 0 points

    Args:
        sbp: Systolic blood pressure in mmHg, or None.

    Returns:
        Tuple of (score, status_or_None).
    """
    if sbp is None:
        return 0, "missing"
    return (1, None) if sbp <= 100 else (0, None)


def score_altered_mentation_qsofa(gcs: int | None) -> tuple[int, str | None]:
    """Score altered mentation for qSOFA.

    GCS < 15 = 1 point (altered mentation)
    GCS = 15 = 0 points

    Args:
        gcs: Glasgow Coma Scale score (3-15), or None.

    Returns:
        Tuple of (score, status_or_None).
    """
    if gcs is None:
        return 0, "missing"
    return (1, None) if gcs < 15 else (0, None)


# ═══════════════════════════════════════════════════════════════════════════
# Full qSOFA Calculation
# ═══════════════════════════════════════════════════════════════════════════

def calculate_qsofa(
    respiratory_rate: int | None = None,
    systolic_bp: int | None = None,
    gcs: int | None = None,
) -> qSOFAResult:
    """Calculate qSOFA score from 3 binary criteria.

    Args:
        respiratory_rate: Breaths per minute.
        systolic_bp: Systolic blood pressure in mmHg.
        gcs: Glasgow Coma Scale score (3-15).

    Returns:
        qSOFAResult with total score (0-3), component breakdown, and missing list.
    """
    missing: list[str] = []

    rr_score, rr_status = score_respiratory_rate_qsofa(respiratory_rate)
    if rr_status == "missing":
        missing.append("respiratory_rate")

    sbp_score, sbp_status = score_systolic_bp_qsofa(systolic_bp)
    if sbp_status == "missing":
        missing.append("systolic_bp")

    gcs_score, gcs_status = score_altered_mentation_qsofa(gcs)
    if gcs_status == "missing":
        missing.append("gcs")

    components = qSOFAComponents(
        respiratory_rate=rr_score,
        systolic_bp=sbp_score,
        altered_mentation=gcs_score,
    )

    total = rr_score + sbp_score + gcs_score

    return qSOFAResult(
        total_score=total,
        components=components,
        missing_criteria=missing,
    )
