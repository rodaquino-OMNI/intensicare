"""
Unit tests for SOFA (Sequential Organ Failure Assessment) scoring engine.

Covers all 6 organ systems, boundary values, missing values,
determinism, and full score integration.
"""

from __future__ import annotations

import pytest

from intensicare.services.sofa import (
    SOFA_VERSION,
    SOFAComponents,
    SOFAResult,
    calculate_sofa,
    score_respiration,
    score_coagulation,
    score_liver,
    score_cardiovascular,
    score_neurological,
    score_renal,
)


# ═══════════════════════════════════════════════════════════════════════════
# Respiration — PaO2/FiO2
# ═══════════════════════════════════════════════════════════════════════════

class TestRespiration:
    @pytest.mark.parametrize(
        "pao2_fio2,vent,expected",
        [
            # Without ventilation
            (None, False, (0, "missing")),
            (500, False, (0, None)),    # ≥400
            (400, False, (0, None)),    # boundary
            (350, False, (1, None)),    # 300-399
            (300, False, (1, None)),    # boundary
            (250, False, (2, None)),    # 200-299
            (200, False, (2, None)),    # boundary
            (150, False, (2, None)),    # <200 without vent → capped at 2
            (50, False, (2, None)),     # <100 without vent → capped at 2
            # With ventilation
            (350, True, (1, None)),     # vent doesn't change 300-399
            (200, True, (2, None)),     # vent at 200 → still 2
            (150, True, (3, None)),     # <200 with vent → 3
            (100, True, (3, None)),     # boundary
            (80, True, (4, None)),      # <100 with vent → 4
            (50, True, (4, None)),      # <100 with vent → 4
        ],
    )
    def test_score_respiration(self, pao2_fio2, vent, expected):
        assert score_respiration(pao2_fio2, vent) == expected

    def test_high_pao2_fio2(self):
        """Very high PaO2/FiO2 should score 0."""
        assert score_respiration(600, False) == (0, None)
        assert score_respiration(700, True) == (0, None)

    def test_borderline_without_vent(self):
        """Without ventilation, scores cap at 2 even for very low ratios."""
        assert score_respiration(30, False) == (2, None)
        assert score_respiration(199, False) == (2, None)


# ═══════════════════════════════════════════════════════════════════════════
# Coagulation — Platelets
# ═══════════════════════════════════════════════════════════════════════════

class TestCoagulation:
    @pytest.mark.parametrize(
        "platelets,expected",
        [
            (None, (0, "missing")),
            (200, (0, None)),     # ≥150
            (150, (0, None)),     # boundary
            (140, (1, None)),     # 100-149
            (100, (1, None)),     # boundary
            (80, (2, None)),      # 50-99
            (50, (2, None)),      # boundary
            (40, (3, None)),      # 20-49
            (20, (3, None)),      # boundary
            (15, (4, None)),      # <20
            (5, (4, None)),       # very low
        ],
    )
    def test_score_coagulation(self, platelets, expected):
        assert score_coagulation(platelets) == expected


# ═══════════════════════════════════════════════════════════════════════════
# Liver — Bilirubin
# ═══════════════════════════════════════════════════════════════════════════

class TestLiver:
    @pytest.mark.parametrize(
        "bilirubin,expected",
        [
            (None, (0, "missing")),
            (0.5, (0, None)),      # <1.2
            (1.1, (0, None)),      # <1.2
            (1.2, (1, None)),      # 1.2-1.9
            (1.5, (1, None)),
            (1.9, (1, None)),      # boundary
            (2.0, (2, None)),      # 2.0-5.9
            (4.0, (2, None)),
            (5.9, (2, None)),      # boundary
            (6.0, (3, None)),      # 6.0-11.9
            (10.0, (3, None)),
            (11.9, (3, None)),     # boundary
            (12.0, (4, None)),     # ≥12.0
            (20.0, (4, None)),
        ],
    )
    def test_score_liver(self, bilirubin, expected):
        assert score_liver(bilirubin) == expected


# ═══════════════════════════════════════════════════════════════════════════
# Cardiovascular — MAP + Vasopressors
# ═══════════════════════════════════════════════════════════════════════════

class TestCardiovascular:
    def test_missing_map(self):
        assert score_cardiovascular(None) == (0, "missing")

    def test_map_ge_70_no_vasopressor(self):
        assert score_cardiovascular(70) == (0, None)
        assert score_cardiovascular(90) == (0, None)
        assert score_cardiovascular(120) == (0, None)

    def test_map_lt_70_no_vasopressor(self):
        assert score_cardiovascular(65) == (1, None)
        assert score_cardiovascular(69) == (1, None)
        assert score_cardiovascular(50) == (1, None)

    def test_dobutamine(self):
        """Dobutamine at any dose = 2."""
        assert score_cardiovascular(70, "dobutamine", 5.0) == (2, None)
        assert score_cardiovascular(65, "dobutamine", None) == (2, None)

    def test_dopamine_low(self):
        """Dopamine ≤5 = 2."""
        assert score_cardiovascular(65, "dopamine", 3.0) == (2, None)
        assert score_cardiovascular(70, "dopamine", 5.0) == (2, None)

    def test_dopamine_medium(self):
        """Dopamine >5 and ≤15 = 3."""
        assert score_cardiovascular(65, "dopamine", 6.0) == (3, None)
        assert score_cardiovascular(60, "dopamine", 15.0) == (3, None)

    def test_dopamine_high(self):
        """Dopamine >15 = 4."""
        assert score_cardiovascular(55, "dopamine", 16.0) == (4, None)
        assert score_cardiovascular(50, "dopamine", 30.0) == (4, None)

    def test_dopamine_unknown_dose(self):
        """Unknown dose defaults to 2."""
        assert score_cardiovascular(65, "dopamine", None) == (2, None)

    def test_norepinephrine_low(self):
        """Norepinephrine ≤0.1 = 3."""
        assert score_cardiovascular(60, "norepinephrine", 0.05) == (3, None)
        assert score_cardiovascular(65, "norepinephrine", 0.1) == (3, None)

    def test_norepinephrine_high(self):
        """Norepinephrine >0.1 = 4."""
        assert score_cardiovascular(55, "norepinephrine", 0.2) == (4, None)
        assert score_cardiovascular(50, "norepinephrine", 0.5) == (4, None)

    def test_epinephrine_low(self):
        """Epinephrine ≤0.1 = 3."""
        assert score_cardiovascular(60, "epinephrine", 0.05) == (3, None)
        assert score_cardiovascular(65, "epinephrine", 0.1) == (3, None)

    def test_epinephrine_high(self):
        """Epinephrine >0.1 = 4."""
        assert score_cardiovascular(55, "epinephrine", 0.15) == (4, None)
        assert score_cardiovascular(50, "epinephrine", 0.3) == (4, None)

    def test_unknown_vasopressor_default(self):
        """Unknown vasopressor type defaults to 2."""
        assert score_cardiovascular(65, "vasopressin", 1.0) == (2, None)

    def test_none_or_empty_vasopressor_type(self):
        """Explicit None or empty vasopressor_type means no vasopressor."""
        assert score_cardiovascular(65, None, None) == (1, None)
        assert score_cardiovascular(65, "", None) == (1, None)
        assert score_cardiovascular(65, "none", None) == (1, None)
        assert score_cardiovascular(75, "none", None) == (0, None)

    def test_noradrenaline_alias(self):
        """noradrenaline should be treated same as norepinephrine."""
        assert score_cardiovascular(60, "noradrenaline", 0.05) == (3, None)

    def test_case_insensitive(self):
        """Vasopressor type should be case-insensitive."""
        assert score_cardiovascular(60, "NOREPINEPHRINE", 0.05) == (3, None)
        assert score_cardiovascular(65, "Dopamine", 3.0) == (2, None)


# ═══════════════════════════════════════════════════════════════════════════
# Neurological — GCS
# ═══════════════════════════════════════════════════════════════════════════

class TestNeurological:
    @pytest.mark.parametrize(
        "gcs,expected",
        [
            (None, (0, "missing")),
            (15, (0, None)),
            (14, (1, None)),
            (13, (1, None)),
            (12, (2, None)),
            (10, (2, None)),
            (9, (3, None)),
            (6, (3, None)),
            (5, (4, None)),
            (3, (4, None)),
        ],
    )
    def test_score_neurological(self, gcs, expected):
        assert score_neurological(gcs) == expected


# ═══════════════════════════════════════════════════════════════════════════
# Renal — Creatinine + Urine output
# ═══════════════════════════════════════════════════════════════════════════

class TestRenal:
    def test_both_missing(self):
        assert score_renal(None, None) == (0, "missing")

    @pytest.mark.parametrize(
        "creatinine,expected",
        [
            (0.8, (0, None)),    # <1.2
            (1.1, (0, None)),    # <1.2
            (1.2, (1, None)),    # 1.2-1.9
            (1.5, (1, None)),
            (1.9, (1, None)),    # boundary
            (2.0, (2, None)),    # 2.0-3.4
            (3.0, (2, None)),
            (3.4, (2, None)),    # boundary
            (3.5, (3, None)),    # 3.5-4.9
            (4.5, (3, None)),
            (4.9, (3, None)),    # boundary
            (5.0, (4, None)),    # ≥5.0
            (8.0, (4, None)),
        ],
    )
    def test_creatinine_only(self, creatinine, expected):
        """Creatinine without urine output."""
        assert score_renal(creatinine, None) == expected

    def test_urine_output_upgrades_score(self):
        """Low urine output should upgrade the score from creatinine-based."""
        # creatinine 1.0 (score 0) + urine <500 → score 3
        assert score_renal(1.0, 400) == (3, None)
        # creatinine 1.0 (score 0) + urine <200 → score 4
        assert score_renal(1.0, 150) == (4, None)
        # creatinine 3.5 (score 3) + urine <500 → still 3 (max)
        assert score_renal(3.5, 400) == (3, None)
        # creatinine 3.5 (score 3) + urine <200 → score 4
        assert score_renal(3.5, 150) == (4, None)

    def test_normal_urine_output_no_effect(self):
        """Normal urine output should not affect score."""
        assert score_renal(1.0, 1000) == (0, None)
        assert score_renal(2.0, 800) == (2, None)

    def test_urine_output_only(self):
        """Only urine output, no creatinine."""
        assert score_renal(None, 600) == (0, None)
        assert score_renal(None, 400) == (3, None)
        assert score_renal(None, 150) == (4, None)
        assert score_renal(None, None) == (0, "missing")


# ═══════════════════════════════════════════════════════════════════════════
# SOFAComponents dataclass
# ═══════════════════════════════════════════════════════════════════════════

class TestSOFAComponents:
    def test_defaults(self):
        c = SOFAComponents()
        assert c.respiration == 0
        assert c.coagulation == 0
        assert c.liver == 0
        assert c.cardiovascular == 0
        assert c.neurological == 0
        assert c.renal == 0

    def test_custom_values(self):
        c = SOFAComponents(
            respiration=4,
            coagulation=3,
            liver=2,
            cardiovascular=4,
            neurological=3,
            renal=4,
        )
        assert c.respiration == 4
        assert c.coagulation == 3
        assert c.liver == 2
        assert c.cardiovascular == 4
        assert c.neurological == 3
        assert c.renal == 4


# ═══════════════════════════════════════════════════════════════════════════
# SOFAResult dataclass
# ═══════════════════════════════════════════════════════════════════════════

class TestSOFAResult:
    def test_version(self):
        comps = SOFAComponents()
        result = SOFAResult(total_score=0, components=comps)
        assert result.algorithm_version == SOFA_VERSION

    def test_missing_components_default(self):
        comps = SOFAComponents()
        result = SOFAResult(total_score=0, components=comps)
        assert result.missing_components == []

    def test_missing_components_custom(self):
        comps = SOFAComponents()
        result = SOFAResult(
            total_score=0,
            components=comps,
            missing_components=["platelets", "bilirubin"],
        )
        assert result.missing_components == ["platelets", "bilirubin"]

    @pytest.mark.parametrize(
        "score,risk",
        [
            (0, "low"),
            (3, "low"),
            (6, "low"),
            (7, "moderate"),
            (9, "moderate"),
            (10, "high"),
            (12, "high"),
            (13, "very_high"),
            (15, "very_high"),
            (20, "very_high"),
            (24, "very_high"),
        ],
    )
    def test_sepsis_mortality_risk(self, score, risk):
        comps = SOFAComponents()
        result = SOFAResult(total_score=score, components=comps)
        assert result.sepsis_mortality_risk == risk


# ═══════════════════════════════════════════════════════════════════════════
# Full SOFA Calculation
# ═══════════════════════════════════════════════════════════════════════════

class TestCalculateSOFA:
    def test_all_normal(self):
        """Patient with all normal values should score 0."""
        result = calculate_sofa(
            pao2_fio2=450,
            mechanical_ventilation=False,
            platelets=200,
            bilirubin=0.8,
            map_value=85,
            vasopressor_type=None,
            vasopressor_dose_mcg_kg_min=None,
            gcs=15,
            creatinine=1.0,
            urine_output_ml_day=1000,
        )
        assert result.total_score == 0
        assert result.algorithm_version == SOFA_VERSION
        assert result.components.respiration == 0
        assert result.components.coagulation == 0
        assert result.components.liver == 0
        assert result.components.cardiovascular == 0
        assert result.components.neurological == 0
        assert result.components.renal == 0
        assert result.missing_components == []

    def test_septic_patient_typical(self):
        """Typical septic patient with multi-organ dysfunction."""
        result = calculate_sofa(
            pao2_fio2=180,          # <200, no vent → 2
            mechanical_ventilation=False,
            platelets=80,           # 50-99 → 2
            bilirubin=2.5,          # 2.0-5.9 → 2
            map_value=60,           # <70 → 1
            vasopressor_type=None,
            vasopressor_dose_mcg_kg_min=None,
            gcs=13,                 # 13-14 → 1
            creatinine=3.0,         # 2.0-3.4 → 2
            urine_output_ml_day=600,  # ≥500 → no upgrade
        )
        assert result.total_score == 10
        assert result.components.respiration == 2
        assert result.components.coagulation == 2
        assert result.components.liver == 2
        assert result.components.cardiovascular == 1
        assert result.components.neurological == 1
        assert result.components.renal == 2

    def test_critical_patient_max_scores(self):
        """Patient with maximum scores in all organ systems."""
        result = calculate_sofa(
            pao2_fio2=60,           # <100, vent → 4
            mechanical_ventilation=True,
            platelets=10,           # <20 → 4
            bilirubin=15.0,         # ≥12 → 4
            map_value=45,           # low but on vasopressor
            vasopressor_type="norepinephrine",
            vasopressor_dose_mcg_kg_min=0.5,  # >0.1 → 4
            gcs=3,                  # <6 → 4
            creatinine=7.0,          # ≥5.0 → 4
            urine_output_ml_day=100,  # <200 → 4
        )
        assert result.total_score == 24  # Theoretical maximum
        assert result.components.respiration == 4
        assert result.components.coagulation == 4
        assert result.components.liver == 4
        assert result.components.cardiovascular == 4
        assert result.components.neurological == 4
        assert result.components.renal == 4

    def test_all_missing(self):
        """Without any data, all components should be marked missing and score 0."""
        result = calculate_sofa()
        assert result.total_score == 0
        assert result.algorithm_version == SOFA_VERSION
        assert "pao2_fio2" in result.missing_components
        assert "platelets" in result.missing_components
        assert "bilirubin" in result.missing_components
        assert "map_value" in result.missing_components
        assert "gcs" in result.missing_components
        assert "creatinine_and_urine_output" in result.missing_components
        assert len(result.missing_components) == 6

    def test_some_missing_some_present(self):
        """Mix of present and missing values."""
        result = calculate_sofa(
            platelets=90,
            bilirubin=None,
            gcs=12,
        )
        assert result.total_score == 4  # platelets=2 + gcs=2
        assert "platelets" not in result.missing_components
        assert "bilirubin" in result.missing_components
        assert "gcs" not in result.missing_components

    def test_deterministic(self):
        """Same inputs must produce same outputs."""
        args = dict(
            pao2_fio2=250,
            mechanical_ventilation=False,
            platelets=120,
            bilirubin=1.5,
            map_value=75,
            vasopressor_type=None,
            vasopressor_dose_mcg_kg_min=None,
            gcs=14,
            creatinine=1.8,
            urine_output_ml_day=800,
        )
        result1 = calculate_sofa(**args)
        result2 = calculate_sofa(**args)
        assert result1.total_score == result2.total_score
        assert result1.components == result2.components
        assert result1.missing_components == result2.missing_components

    def test_ventilation_affects_respiration_only(self):
        """Mechanical ventilation should only affect respiration score."""
        result_no_vent = calculate_sofa(
            pao2_fio2=150,
            mechanical_ventilation=False,
            map_value=70,
            gcs=15,
            platelets=200,
            bilirubin=0.5,
            creatinine=1.0,
            urine_output_ml_day=1000,
        )
        result_vent = calculate_sofa(
            pao2_fio2=150,
            mechanical_ventilation=True,
            map_value=70,
            gcs=15,
            platelets=200,
            bilirubin=0.5,
            creatinine=1.0,
            urine_output_ml_day=1000,
        )
        # With vent: respiration=3, others unchanged
        assert result_no_vent.components.respiration == 2
        assert result_vent.components.respiration == 3
        assert result_no_vent.components.coagulation == result_vent.components.coagulation
        assert result_no_vent.components.liver == result_vent.components.liver
        assert result_no_vent.components.cardiovascular == result_vent.components.cardiovascular
        assert result_no_vent.components.neurological == result_vent.components.neurological
        assert result_no_vent.components.renal == result_vent.components.renal

    def test_known_clinical_example_moderate_sepsis(self):
        """Test a known clinical example of moderate sepsis.

        PaO2/FiO2=220 (2), Platelets=110 (1), Bilirubin=1.8 (1),
        MAP=65 no vasopressors (1), GCS=14 (1), Creatinine=1.9 (1)
        Total: 7
        """
        result = calculate_sofa(
            pao2_fio2=220,
            mechanical_ventilation=False,
            platelets=110,
            bilirubin=1.8,
            map_value=65,
            vasopressor_type=None,
            vasopressor_dose_mcg_kg_min=None,
            gcs=14,
            creatinine=1.9,
            urine_output_ml_day=800,
        )
        assert result.total_score == 7
        assert result.sepsis_mortality_risk == "moderate"

    def test_known_clinical_example_severe_sepsis(self):
        """Test a known clinical example of severe sepsis with organ failure.

        PaO2/FiO2=150+MechVent (3), Platelets=60 (2), Bilirubin=3.5 (2),
        MAP=55+Norepi0.15 (4), GCS=10 (2), Creatinine=2.8 (2) + Urine400 (3) → renal=3
        Total: 16
        """
        result = calculate_sofa(
            pao2_fio2=150,
            mechanical_ventilation=True,
            platelets=60,
            bilirubin=3.5,
            map_value=55,
            vasopressor_type="norepinephrine",
            vasopressor_dose_mcg_kg_min=0.15,
            gcs=10,
            creatinine=2.8,
            urine_output_ml_day=400,
        )
        assert result.total_score == 16
        assert result.sepsis_mortality_risk == "very_high"

    def test_renal_urine_output_upgrade_in_full_calc(self):
        """Verify urine output properly upgrades renal score in full calculation."""
        # With normal urine output: creatinine 0.9 → renal=0
        result_normal_uo = calculate_sofa(
            pao2_fio2=450, platelets=200, bilirubin=0.5,
            map_value=80, gcs=15, creatinine=0.9, urine_output_ml_day=1000,
        )
        assert result_normal_uo.components.renal == 0

        # With low urine output: creatinine 0.9 → renal=3
        result_low_uo = calculate_sofa(
            pao2_fio2=450, platelets=200, bilirubin=0.5,
            map_value=80, gcs=15, creatinine=0.9, urine_output_ml_day=300,
        )
        assert result_low_uo.components.renal == 3
