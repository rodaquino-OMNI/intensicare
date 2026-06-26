"""Unit tests for NEWS2 scoring engine."""

import pytest

from intensicare.services.news2 import (
    NEWS2Components,
    NEWS2Result,
    calculate_news2,
    score_consciousness,
    score_heart_rate,
    score_respiratory_rate,
    score_spo2,
    score_supplemental_o2,
    score_systolic_bp,
    score_temperature,
)


# ════════════════════════════════════════════════════════════════════════════
# Respiratory Rate
# ════════════════════════════════════════════════════════════════════════════

class TestRespiratoryRate:
    def test_low_critical(self):
        """≤8 = 3"""
        assert score_respiratory_rate(8) == 3
        assert score_respiratory_rate(5) == 3
        assert score_respiratory_rate(0) == 3

    def test_low_warning(self):
        """9-11 = 1"""
        assert score_respiratory_rate(9) == 1
        assert score_respiratory_rate(10) == 1
        assert score_respiratory_rate(11) == 1

    def test_normal(self):
        """12-20 = 0"""
        assert score_respiratory_rate(12) == 0
        assert score_respiratory_rate(16) == 0
        assert score_respiratory_rate(20) == 0

    def test_elevated(self):
        """21-24 = 2"""
        assert score_respiratory_rate(21) == 2
        assert score_respiratory_rate(22) == 2
        assert score_respiratory_rate(24) == 2

    def test_high_critical(self):
        """≥25 = 3"""
        assert score_respiratory_rate(25) == 3
        assert score_respiratory_rate(30) == 3
        assert score_respiratory_rate(60) == 3

    def test_none_returns_zero(self):
        assert score_respiratory_rate(None) == 0


# ════════════════════════════════════════════════════════════════════════════
# SpO2 — Scale 1 (non-hypercapnic)
# ════════════════════════════════════════════════════════════════════════════

class TestSpO2Scale1:
    def test_normal(self):
        """≥96 = 0"""
        assert score_spo2(96, hypercapnic=False) == 0
        assert score_spo2(98, hypercapnic=False) == 0
        assert score_spo2(100, hypercapnic=False) == 0

    def test_mild(self):
        """94-95 = 1"""
        assert score_spo2(94, hypercapnic=False) == 1
        assert score_spo2(95, hypercapnic=False) == 1

    def test_moderate(self):
        """92-93 = 2"""
        assert score_spo2(92, hypercapnic=False) == 2
        assert score_spo2(93, hypercapnic=False) == 2

    def test_severe(self):
        """≤91 = 3"""
        assert score_spo2(91, hypercapnic=False) == 3
        assert score_spo2(85, hypercapnic=False) == 3
        assert score_spo2(70, hypercapnic=False) == 3

    def test_none_returns_zero(self):
        assert score_spo2(None, hypercapnic=False) == 0


# ════════════════════════════════════════════════════════════════════════════
# SpO2 — Scale 2 (hypercapnic)
# ════════════════════════════════════════════════════════════════════════════

class TestSpO2Scale2:
    def test_normal(self):
        """≥93 = 0"""
        assert score_spo2(93, hypercapnic=True) == 0
        assert score_spo2(95, hypercapnic=True) == 0
        assert score_spo2(100, hypercapnic=True) == 0

    def test_mild(self):
        """88-92 = 1"""
        assert score_spo2(88, hypercapnic=True) == 1
        assert score_spo2(90, hypercapnic=True) == 1
        assert score_spo2(92, hypercapnic=True) == 1

    def test_moderate(self):
        """86-87 = 2, 84-85 = 2"""
        assert score_spo2(84, hypercapnic=True) == 2
        assert score_spo2(85, hypercapnic=True) == 2
        assert score_spo2(86, hypercapnic=True) == 2
        assert score_spo2(87, hypercapnic=True) == 2

    def test_severe(self):
        """≤83 = 3"""
        assert score_spo2(83, hypercapnic=True) == 3
        assert score_spo2(80, hypercapnic=True) == 3
        assert score_spo2(50, hypercapnic=True) == 3

    def test_none_returns_zero(self):
        assert score_spo2(None, hypercapnic=True) == 0


# ════════════════════════════════════════════════════════════════════════════
# Supplemental Oxygen
# ════════════════════════════════════════════════════════════════════════════

class TestSupplementalO2:
    def test_on_o2(self):
        assert score_supplemental_o2(True) == 2

    def test_off_o2(self):
        assert score_supplemental_o2(False) == 0

    def test_none_returns_zero(self):
        assert score_supplemental_o2(None) == 0


# ════════════════════════════════════════════════════════════════════════════
# Systolic Blood Pressure
# ════════════════════════════════════════════════════════════════════════════

class TestSystolicBP:
    def test_low_critical(self):
        """≤90 = 3"""
        assert score_systolic_bp(90) == 3
        assert score_systolic_bp(70) == 3
        assert score_systolic_bp(60) == 3

    def test_low_warning(self):
        """91-100 = 2"""
        assert score_systolic_bp(91) == 2
        assert score_systolic_bp(95) == 2
        assert score_systolic_bp(100) == 2

    def test_borderline(self):
        """101-110 = 1"""
        assert score_systolic_bp(101) == 1
        assert score_systolic_bp(105) == 1
        assert score_systolic_bp(110) == 1

    def test_normal(self):
        """111-219 = 0"""
        assert score_systolic_bp(111) == 0
        assert score_systolic_bp(120) == 0
        assert score_systolic_bp(160) == 0
        assert score_systolic_bp(219) == 0

    def test_high_critical(self):
        """≥220 = 3"""
        assert score_systolic_bp(220) == 3
        assert score_systolic_bp(250) == 3

    def test_none_returns_zero(self):
        assert score_systolic_bp(None) == 0


# ════════════════════════════════════════════════════════════════════════════
# Heart Rate
# ════════════════════════════════════════════════════════════════════════════

class TestHeartRate:
    def test_bradycardia_critical(self):
        """≤40 = 3"""
        assert score_heart_rate(40) == 3
        assert score_heart_rate(30) == 3
        assert score_heart_rate(20) == 3

    def test_bradycardia_mild(self):
        """41-50 = 1"""
        assert score_heart_rate(41) == 1
        assert score_heart_rate(45) == 1
        assert score_heart_rate(50) == 1

    def test_normal(self):
        """51-90 = 0"""
        assert score_heart_rate(51) == 0
        assert score_heart_rate(70) == 0
        assert score_heart_rate(90) == 0

    def test_tachycardia_mild(self):
        """91-110 = 1"""
        assert score_heart_rate(91) == 1
        assert score_heart_rate(100) == 1
        assert score_heart_rate(110) == 1

    def test_tachycardia_moderate(self):
        """111-130 = 2"""
        assert score_heart_rate(111) == 2
        assert score_heart_rate(120) == 2
        assert score_heart_rate(130) == 2

    def test_tachycardia_critical(self):
        """≥131 = 3"""
        assert score_heart_rate(131) == 3
        assert score_heart_rate(150) == 3
        assert score_heart_rate(200) == 3

    def test_none_returns_zero(self):
        assert score_heart_rate(None) == 0


# ════════════════════════════════════════════════════════════════════════════
# Consciousness (AVPU)
# ════════════════════════════════════════════════════════════════════════════

class TestConsciousness:
    def test_alert(self):
        assert score_consciousness("A") == 0
        assert score_consciousness("a") == 0
        assert score_consciousness("Alert") == 3  # Not just "A"

    def test_cvpu(self):
        """Any non-Alert = 3"""
        assert score_consciousness("C") == 3
        assert score_consciousness("V") == 3
        assert score_consciousness("P") == 3
        assert score_consciousness("U") == 3
        assert score_consciousness("c") == 3
        assert score_consciousness("v") == 3

    def test_whitespace_handled(self):
        assert score_consciousness(" A ") == 0
        assert score_consciousness(" V ") == 3

    def test_none_returns_zero(self):
        assert score_consciousness(None) == 0


# ════════════════════════════════════════════════════════════════════════════
# Temperature
# ════════════════════════════════════════════════════════════════════════════

class TestTemperature:
    def test_hypothermia_critical(self):
        """≤35.0 = 3"""
        assert score_temperature(35.0) == 3
        assert score_temperature(34.0) == 3
        assert score_temperature(33.5) == 3

    def test_hypothermia_mild(self):
        """35.1-36.0 = 1"""
        assert score_temperature(35.1) == 1
        assert score_temperature(35.5) == 1
        assert score_temperature(36.0) == 1

    def test_normal(self):
        """36.1-38.0 = 0"""
        assert score_temperature(36.1) == 0
        assert score_temperature(37.0) == 0
        assert score_temperature(38.0) == 0

    def test_pyrexia_mild(self):
        """38.1-39.0 = 1"""
        assert score_temperature(38.1) == 1
        assert score_temperature(38.5) == 1
        assert score_temperature(39.0) == 1

    def test_pyrexia_moderate(self):
        """≥39.1 = 2"""
        assert score_temperature(39.1) == 2
        assert score_temperature(40.0) == 2
        assert score_temperature(42.0) == 2

    def test_none_returns_zero(self):
        assert score_temperature(None) == 0


# ════════════════════════════════════════════════════════════════════════════
# Full NEWS2 Calculation
# ════════════════════════════════════════════════════════════════════════════

class TestCalculateNEWS2:
    def test_all_normal_returns_zero(self):
        """A patient with all normal vitals should score 0."""
        result = calculate_news2(
            respiratory_rate=16,
            spo2=98,
            hypercapnic=False,
            supplemental_o2=False,
            systolic_bp=120,
            heart_rate=75,
            avpu="A",
            temperature=37.0,
        )
        assert result.total_score == 0
        assert result.algorithm_version == "NEWS2-v1.0"
        assert result.risk_category == "low"

    def test_high_risk_patient(self):
        """A patient with multiple deranged parameters."""
        result = calculate_news2(
            respiratory_rate=30,  # 3
            spo2=88,  # 3 (Scale 1)
            hypercapnic=False,
            supplemental_o2=True,  # 2
            systolic_bp=85,  # 3
            heart_rate=135,  # 3
            avpu="V",  # 3
            temperature=34.0,  # 3
        )
        assert result.total_score == 20  # All maximum except temp which is 3
        assert result.risk_category == "high"

    def test_hypercapnic_spo2_scale(self):
        """Hypercapnic patients use Scale 2 for SpO2."""
        result = calculate_news2(
            respiratory_rate=18,  # 0
            spo2=88,  # 1 on Scale 2 (vs 3 on Scale 1)
            hypercapnic=True,
            supplemental_o2=False,  # 0
            systolic_bp=120,  # 0
            heart_rate=80,  # 0
            avpu="A",  # 0
            temperature=37.0,  # 0
        )
        assert result.total_score == 1
        assert result.components.spo2 == 1

    def test_missing_values_default_to_zero(self):
        """None values should be scored as 0."""
        result = calculate_news2(
            respiratory_rate=None,
            spo2=None,
            hypercapnic=False,
            supplemental_o2=None,
            systolic_bp=None,
            heart_rate=None,
            avpu=None,
            temperature=None,
        )
        assert result.total_score == 0

    def test_components_dataclass(self):
        """Verify component scores are tracked individually."""
        result = calculate_news2(
            respiratory_rate=10,  # 1
            spo2=95,  # 1
            hypercapnic=False,
            supplemental_o2=False,  # 0
            systolic_bp=120,  # 0
            heart_rate=70,  # 0
            avpu="A",  # 0
            temperature=37.0,  # 0
        )
        assert result.components.respiratory_rate == 1
        assert result.components.spo2 == 1
        assert result.components.supplemental_o2 == 0
        assert result.components.systolic_bp == 0
        assert result.components.heart_rate == 0
        assert result.components.consciousness == 0
        assert result.components.temperature == 0
        assert result.total_score == 2

    def test_requires_urgent_assessment(self):
        """Score >= 5 or any individual component = 3 should trigger urgent assessment."""
        # Total >= 5
        result = calculate_news2(
            respiratory_rate=10, spo2=94, hypercapnic=False,
            supplemental_o2=False, systolic_bp=105, heart_rate=115,
            avpu="A", temperature=38.5,
        )  # 1+1+0+1+2+0+1 = 6
        assert result.requires_urgent_assessment is True

        # Single component = 3
        result = calculate_news2(
            respiratory_rate=8, spo2=98, hypercapnic=False,
            supplemental_o2=False, systolic_bp=120, heart_rate=75,
            avpu="A", temperature=37.0,
        )  # 3+0+0+0+0+0+0 = 3 — but RR=3 triggers
        assert result.requires_urgent_assessment is True

        # Low score, no 3s
        result = calculate_news2(
            respiratory_rate=16, spo2=96, hypercapnic=False,
            supplemental_o2=False, systolic_bp=120, heart_rate=75,
            avpu="A", temperature=37.0,
        )
        assert result.requires_urgent_assessment is False

    def test_risk_category_boundaries(self):
        """Test risk category classification boundaries."""
        # Low: 0-4
        assert calculate_news2(
            respiratory_rate=16, spo2=96, hypercapnic=False,
            supplemental_o2=False, systolic_bp=120, heart_rate=75,
            avpu="A", temperature=37.0,
        ).risk_category == "low"

        # Medium: 5-6
        assert calculate_news2(
            respiratory_rate=25, spo2=94, hypercapnic=False,
            supplemental_o2=False, systolic_bp=105, heart_rate=91,
            avpu="A", temperature=37.0,
        ).risk_category == "medium"  # 3+1+0+1+1+0+0 = 6

        # High: >= 7
        assert calculate_news2(
            respiratory_rate=25, spo2=92, hypercapnic=False,
            supplemental_o2=True, systolic_bp=120, heart_rate=75,
            avpu="A", temperature=37.0,
        ).risk_category == "high"  # 3+2+2+0+0+0+0 = 7

    def test_result_dataclass(self):
        """NEWS2Result dataclass properties."""
        components = NEWS2Components(
            respiratory_rate=1, spo2=1, supplemental_o2=0,
            systolic_bp=0, heart_rate=0, consciousness=0, temperature=1,
        )
        result = NEWS2Result(total_score=3, components=components)
        assert result.risk_category == "low"
        assert result.algorithm_version == "NEWS2-v1.0"
        assert result.requires_urgent_assessment is False

    def test_known_news2_examples(self):
        """Test against known NEWS2 example calculations from clinical literature.

        Example 1: Normal patient
            RR=16 (0), SpO2=97 (0), O2=No (0), SBP=125 (0), HR=72 (0), AVPU=A (0), Temp=36.8 (0)
            Total: 0

        Example 2: Moderate deterioration
            RR=23 (2), SpO2=93 (2), O2=Yes (2), SBP=100 (2), HR=115 (2), AVPU=V (3), Temp=35.5 (1)
            Total: 14

        Example 3: Severe COPD with hypercapnia
            RR=28 (3), SpO2=87 [Scale2] (1), O2=Yes (2), SBP=108 (1), HR=95 (1), AVPU=A (0), Temp=38.2 (1)
            Total: 9
        """
        # Example 1
        result = calculate_news2(
            respiratory_rate=16, spo2=97, hypercapnic=False,
            supplemental_o2=False, systolic_bp=125, heart_rate=72,
            avpu="A", temperature=36.8,
        )
        assert result.total_score == 0, f"Expected 0, got {result.total_score}"

        # Example 2
        result = calculate_news2(
            respiratory_rate=23, spo2=93, hypercapnic=False,
            supplemental_o2=True, systolic_bp=100, heart_rate=115,
            avpu="V", temperature=35.5,
        )
        assert result.total_score == 14, f"Expected 14, got {result.total_score}"

        # Example 3
        result = calculate_news2(
            respiratory_rate=28, spo2=87, hypercapnic=True,
            supplemental_o2=True, systolic_bp=108, heart_rate=95,
            avpu="A", temperature=38.2,
        )
        assert result.total_score == 9, f"Expected 9, got {result.total_score}"


class TestNEWS2Components:
    """Test the NEWS2Components dataclass."""

    def test_defaults(self):
        c = NEWS2Components()
        assert c.respiratory_rate == 0
        assert c.spo2 == 0
        assert c.supplemental_o2 == 0
        assert c.systolic_bp == 0
        assert c.heart_rate == 0
        assert c.consciousness == 0
        assert c.temperature == 0

    def test_custom_values(self):
        c = NEWS2Components(
            respiratory_rate=3, spo2=2, supplemental_o2=2,
            systolic_bp=1, heart_rate=3, consciousness=3, temperature=1,
        )
        assert c.respiratory_rate == 3
        assert c.spo2 == 2
        assert c.supplemental_o2 == 2
        assert c.systolic_bp == 1
        assert c.heart_rate == 3
        assert c.consciousness == 3
        assert c.temperature == 1
