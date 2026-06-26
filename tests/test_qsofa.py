"""
Unit tests for qSOFA (Quick Sequential Organ Failure Assessment) scoring engine.

Covers all 3 binary criteria, boundary values, missing values,
determinism, high-risk classification, and full score integration.
"""

from __future__ import annotations

import pytest

from intensicare.services.qsofa import (
    QSOFA_VERSION,
    qSOFAComponents,
    qSOFAResult,
    calculate_qsofa,
    score_respiratory_rate_qsofa,
    score_systolic_bp_qsofa,
    score_altered_mentation_qsofa,
)


# ═══════════════════════════════════════════════════════════════════════════
# Respiratory Rate
# ═══════════════════════════════════════════════════════════════════════════

class TestRespiratoryRateqSOFA:
    @pytest.mark.parametrize(
        "rr,expected",
        [
            (None, (0, "missing")),
            (12, (0, None)),     # <22
            (18, (0, None)),     # <22
            (21, (0, None)),     # <22, just under threshold
            (22, (1, None)),     # ≥22, boundary
            (25, (1, None)),     # ≥22
            (30, (1, None)),     # ≥22, tachypneic
            (40, (1, None)),     # ≥22, severe tachypnea
            (0, (0, None)),      # very low (bradypnea is NOT a qSOFA criterion)
        ],
    )
    def test_score_respiratory_rate(self, rr, expected):
        assert score_respiratory_rate_qsofa(rr) == expected


# ═══════════════════════════════════════════════════════════════════════════
# Systolic BP
# ═══════════════════════════════════════════════════════════════════════════

class TestSystolicBPqSOFA:
    @pytest.mark.parametrize(
        "sbp,expected",
        [
            (None, (0, "missing")),
            (60, (1, None)),     # ≤100
            (80, (1, None)),     # ≤100
            (95, (1, None)),     # ≤100
            (100, (1, None)),    # ≤100, boundary
            (101, (0, None)),    # >100
            (120, (0, None)),    # >100
            (140, (0, None)),    # >100
            (200, (0, None)),    # >100
        ],
    )
    def test_score_systolic_bp(self, sbp, expected):
        assert score_systolic_bp_qsofa(sbp) == expected


# ═══════════════════════════════════════════════════════════════════════════
# Altered Mentation (GCS)
# ═══════════════════════════════════════════════════════════════════════════

class TestAlteredMentationqSOFA:
    @pytest.mark.parametrize(
        "gcs,expected",
        [
            (None, (0, "missing")),
            (15, (0, None)),     # normal mentation
            (14, (1, None)),     # altered
            (13, (1, None)),     # altered
            (10, (1, None)),     # altered
            (8, (1, None)),      # altered
            (6, (1, None)),      # altered
            (3, (1, None)),      # altered (minimum GCS)
        ],
    )
    def test_score_altered_mentation(self, gcs, expected):
        assert score_altered_mentation_qsofa(gcs) == expected

    def test_gcs_15_is_normal(self):
        """Only GCS=15 is considered normal mentation (score 0). GCS<15 = 1."""
        assert score_altered_mentation_qsofa(15) == (0, None)
        assert score_altered_mentation_qsofa(14) == (1, None)


# ═══════════════════════════════════════════════════════════════════════════
# qSOFAComponents dataclass
# ═══════════════════════════════════════════════════════════════════════════

class TestqSOFAComponents:
    def test_defaults(self):
        c = qSOFAComponents()
        assert c.respiratory_rate == 0
        assert c.systolic_bp == 0
        assert c.altered_mentation == 0

    def test_custom_values(self):
        c = qSOFAComponents(
            respiratory_rate=1,
            systolic_bp=1,
            altered_mentation=0,
        )
        assert c.respiratory_rate == 1
        assert c.systolic_bp == 1
        assert c.altered_mentation == 0


# ═══════════════════════════════════════════════════════════════════════════
# qSOFAResult dataclass
# ═══════════════════════════════════════════════════════════════════════════

class TestqSOFAResult:
    def test_version(self):
        comps = qSOFAComponents()
        result = qSOFAResult(total_score=0, components=comps)
        assert result.algorithm_version == QSOFA_VERSION

    def test_missing_criteria_default(self):
        comps = qSOFAComponents()
        result = qSOFAResult(total_score=0, components=comps)
        assert result.missing_criteria == []

    def test_missing_criteria_custom(self):
        comps = qSOFAComponents()
        result = qSOFAResult(
            total_score=0,
            components=comps,
            missing_criteria=["gcs"],
        )
        assert result.missing_criteria == ["gcs"]

    @pytest.mark.parametrize(
        "score,expected_risk,expected_high_risk",
        [
            (0, "low_risk", False),
            (1, "low_risk", False),
            (2, "high_risk", True),
            (3, "high_risk", True),
        ],
    )
    def test_risk_classification(self, score, expected_risk, expected_high_risk):
        comps = qSOFAComponents()
        result = qSOFAResult(total_score=score, components=comps)
        assert result.risk_level == expected_risk
        assert result.is_high_risk == expected_high_risk


# ═══════════════════════════════════════════════════════════════════════════
# Full qSOFA Calculation
# ═══════════════════════════════════════════════════════════════════════════

class TestCalculateqSOFA:
    def test_all_normal(self):
        """Patient with normal vitals should score 0."""
        result = calculate_qsofa(
            respiratory_rate=16,
            systolic_bp=120,
            gcs=15,
        )
        assert result.total_score == 0
        assert result.algorithm_version == QSOFA_VERSION
        assert result.components.respiratory_rate == 0
        assert result.components.systolic_bp == 0
        assert result.components.altered_mentation == 0
        assert result.is_high_risk is False
        assert result.risk_level == "low_risk"
        assert result.missing_criteria == []

    def test_one_criterion(self):
        """One positive criterion → score 1, not high risk."""
        result = calculate_qsofa(
            respiratory_rate=25,   # 1 point
            systolic_bp=120,       # 0 points
            gcs=15,                # 0 points
        )
        assert result.total_score == 1
        assert result.is_high_risk is False
        assert result.risk_level == "low_risk"

    def test_two_criteria_high_risk(self):
        """Two positive criteria → score 2, high risk."""
        result = calculate_qsofa(
            respiratory_rate=25,   # 1 point
            systolic_bp=95,        # 1 point
            gcs=15,                # 0 points
        )
        assert result.total_score == 2
        assert result.is_high_risk is True
        assert result.risk_level == "high_risk"

    def test_three_criteria_max_score(self):
        """All three criteria positive → score 3, high risk."""
        result = calculate_qsofa(
            respiratory_rate=30,   # 1 point
            systolic_bp=80,        # 1 point
            gcs=12,                # 1 point
        )
        assert result.total_score == 3
        assert result.is_high_risk is True
        assert result.risk_level == "high_risk"
        assert result.components.respiratory_rate == 1
        assert result.components.systolic_bp == 1
        assert result.components.altered_mentation == 1

    def test_boundary_values(self):
        """Test values exactly at the boundaries."""
        # RR exactly at 22
        result = calculate_qsofa(respiratory_rate=22, systolic_bp=120, gcs=15)
        assert result.components.respiratory_rate == 1
        assert result.total_score == 1

        # SBP exactly at 100
        result = calculate_qsofa(respiratory_rate=16, systolic_bp=100, gcs=15)
        assert result.components.systolic_bp == 1
        assert result.total_score == 1

        # GCS exactly at 14
        result = calculate_qsofa(respiratory_rate=16, systolic_bp=120, gcs=14)
        assert result.components.altered_mentation == 1
        assert result.total_score == 1

        # Just below boundaries
        result = calculate_qsofa(respiratory_rate=21, systolic_bp=101, gcs=15)
        assert result.total_score == 0

    def test_septic_shock_scenario(self):
        """Patient in septic shock: tachypnea + hypotension + altered."""
        result = calculate_qsofa(
            respiratory_rate=35,
            systolic_bp=70,
            gcs=9,
        )
        assert result.total_score == 3
        assert result.is_high_risk is True

    def test_all_missing(self):
        """Without any data, all criteria should be marked missing and score 0."""
        result = calculate_qsofa()
        assert result.total_score == 0
        assert result.algorithm_version == QSOFA_VERSION
        assert "respiratory_rate" in result.missing_criteria
        assert "systolic_bp" in result.missing_criteria
        assert "gcs" in result.missing_criteria
        assert len(result.missing_criteria) == 3

    def test_some_missing_some_present(self):
        """Mix of present and missing criteria."""
        result = calculate_qsofa(
            respiratory_rate=28,
            systolic_bp=None,
            gcs=13,
        )
        assert result.total_score == 2
        assert "respiratory_rate" not in result.missing_criteria
        assert "systolic_bp" in result.missing_criteria
        assert "gcs" not in result.missing_criteria
        assert result.is_high_risk is True

    def test_deterministic(self):
        """Same inputs must produce same outputs."""
        args = dict(
            respiratory_rate=26,
            systolic_bp=98,
            gcs=14,
        )
        result1 = calculate_qsofa(**args)
        result2 = calculate_qsofa(**args)
        assert result1.total_score == result2.total_score
        assert result1.components == result2.components
        assert result1.missing_criteria == result2.missing_criteria

    def test_missing_does_not_count(self):
        """Missing criteria should NOT count toward the score."""
        result = calculate_qsofa(
            respiratory_rate=None,
            systolic_bp=None,
            gcs=None,
        )
        assert result.total_score == 0
        assert result.is_high_risk is False

    def test_high_risk_boundary(self):
        """Score 2 is high risk, score 1 is not — boundary test."""
        # Score 1
        result1 = calculate_qsofa(respiratory_rate=16, systolic_bp=100, gcs=15)
        assert result1.total_score == 1
        assert result1.is_high_risk is False

        # Score 2
        result2 = calculate_qsofa(respiratory_rate=22, systolic_bp=100, gcs=15)
        assert result2.total_score == 2
        assert result2.is_high_risk is True

    def test_known_clinical_example_suspected_infection(self):
        """Known clinical qSOFA example: suspected infection patient.

        RR=24 (1), SBP=90 (1), GCS=15 (0) → Score 2 → High risk
        """
        result = calculate_qsofa(
            respiratory_rate=24,
            systolic_bp=90,
            gcs=15,
        )
        assert result.total_score == 2
        assert result.is_high_risk is True
        assert result.risk_level == "high_risk"

    def test_known_clinical_example_no_sepsis(self):
        """Patient without sepsis criteria.

        RR=18 (0), SBP=130 (0), GCS=15 (0) → Score 0 → Low risk
        """
        result = calculate_qsofa(
            respiratory_rate=18,
            systolic_bp=130,
            gcs=15,
        )
        assert result.total_score == 0
        assert result.is_high_risk is False
        assert result.risk_level == "low_risk"
