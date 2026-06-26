"""
SOFA (Sequential Organ Failure Assessment) scoring engine.

Implements the SOFA score with 6 organ systems:
- Respiration (PaO2/FiO2 ratio)
- Coagulation (platelets)
- Liver (bilirubin)
- Cardiovascular (MAP + vasopressor use)
- Neurological (Glasgow Coma Scale)
- Renal (creatinine + urine output)

Each organ system scores 0-4; total SOFA score ranges 0-24.
Higher scores indicate more severe organ dysfunction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SOFA_VERSION = "SOFA-v1.0"


@dataclass
class SOFAComponents:
    """Individual organ system scores for SOFA."""

    respiration: int = 0
    coagulation: int = 0
    liver: int = 0
    cardiovascular: int = 0
    neurological: int = 0
    renal: int = 0


@dataclass
class SOFAResult:
    """Result of a SOFA calculation."""

    total_score: int
    components: SOFAComponents
    algorithm_version: str = SOFA_VERSION
    missing_components: list[str] = field(default_factory=list)

    @property
    def sepsis_mortality_risk(self) -> str:
        """Estimated mortality risk based on SOFA score.

        SOFA ≥2 increase in mortality of ≈2-25%.
        SOFA 0-6: ~<10% mortality
        SOFA 7-9: ~15-20%
        SOFA 10-12: ~40-50%
        SOFA 13-14: ~50-60%
        SOFA 15-24: ~80-90%
        SOFA >15: ~>90%
        """
        if self.total_score <= 6:
            return "low"
        if self.total_score <= 9:
            return "moderate"
        if self.total_score <= 12:
            return "high"
        return "very_high"


# ═══════════════════════════════════════════════════════════════════════════
# Respiration — PaO2/FiO2 ratio
# ═══════════════════════════════════════════════════════════════════════════

def score_respiration(
    pao2_fio2: float | None = None,
    mechanical_ventilation: bool = False,
) -> tuple[int, str | None]:
    """Score respiration based on PaO2/FiO2 ratio.

    ≥400 mmHg = 0
    <400     = 1
    <300     = 2
    <200 AND mechanical ventilation = 3
    <100 AND mechanical ventilation = 4

    If not on mechanical ventilation, <200 and <100 still score 2
    (ventilation is required for scores 3-4).

    Args:
        pao2_fio2: PaO2/FiO2 ratio in mmHg, or None if unavailable.
        mechanical_ventilation: Whether patient is on mechanical ventilation.

    Returns:
        Tuple of (score, status_string_or_None).
    """
    if pao2_fio2 is None:
        return 0, "missing"

    if pao2_fio2 >= 400:
        return 0, None
    if pao2_fio2 >= 300:
        return 1, None
    if pao2_fio2 >= 200:
        return 2, None
    # pao2_fio2 < 200
    if mechanical_ventilation:
        if pao2_fio2 >= 100:
            return 3, None
        return 4, None
    # Not ventilated: cap at 2
    return 2, None


# ═══════════════════════════════════════════════════════════════════════════
# Coagulation — Platelets
# ═══════════════════════════════════════════════════════════════════════════

def score_coagulation(platelets: float | None = None) -> tuple[int, str | None]:
    """Score coagulation based on platelet count (×10³/µL).

    ≥150 = 0
    <150 = 1
    <100 = 2
    <50  = 3
    <20  = 4

    Args:
        platelets: Platelet count in ×10³/µL, or None if unavailable.

    Returns:
        Tuple of (score, status_string_or_None).
    """
    if platelets is None:
        return 0, "missing"

    if platelets >= 150:
        return 0, None
    if platelets >= 100:
        return 1, None
    if platelets >= 50:
        return 2, None
    if platelets >= 20:
        return 3, None
    return 4, None


# ═══════════════════════════════════════════════════════════════════════════
# Liver — Bilirubin
# ═══════════════════════════════════════════════════════════════════════════

def score_liver(bilirubin: float | None = None) -> tuple[int, str | None]:
    """Score liver function based on bilirubin (mg/dL or µmol/L).

    Thresholds in mg/dL:
    <1.2    = 0
    1.2-1.9 = 1
    2.0-5.9 = 2
    6.0-11.9 = 3
    ≥12.0   = 4

    Args:
        bilirubin: Total bilirubin in mg/dL, or None if unavailable.

    Returns:
        Tuple of (score, status_string_or_None).
    """
    if bilirubin is None:
        return 0, "missing"

    if bilirubin < 1.2:
        return 0, None
    if bilirubin < 2.0:
        return 1, None
    if bilirubin < 6.0:
        return 2, None
    if bilirubin < 12.0:
        return 3, None
    return 4, None


# ═══════════════════════════════════════════════════════════════════════════
# Cardiovascular — MAP + vasopressors
# ═══════════════════════════════════════════════════════════════════════════

def score_cardiovascular(
    map_value: float | None = None,
    vasopressor_type: str | None = None,
    vasopressor_dose_mcg_kg_min: float | None = None,
) -> tuple[int, str | None]:
    """Score cardiovascular system based on MAP and vasopressor support.

    MAP ≥70 mmHg, no vasopressors = 0
    MAP <70 mmHg, no vasopressors = 1
    Dopamine ≤5 µg/kg/min OR dobutamine (any) = 2
    Dopamine >5 µg/kg/min OR epinephrine ≤0.1 µg/kg/min OR norepinephrine ≤0.1 µg/kg/min = 3
    Dopamine >15 µg/kg/min OR epinephrine >0.1 µg/kg/min OR norepinephrine >0.1 µg/kg/min = 4

    Simplified scoring when vasopressor_type is just a boolean/string:
    - vasopressor_type=None or "" or False: no vasopressors → score based on MAP
    - vasopressor_type="dobutamine" or dose unknown: score 2
    - vasopressor_type="dopamine" with dose ≤5: score 2; dose >5 and ≤15: score 3; dose >15: score 4
    - vasopressor_type="epinephrine" or "norepinephrine" with dose ≤0.1: score 3; dose >0.1: score 4

    Args:
        map_value: Mean Arterial Pressure in mmHg, or None if unavailable.
        vasopressor_type: Type of vasopressor ('dopamine', 'dobutamine',
            'epinephrine', 'norepinephrine'), or None.
        vasopressor_dose_mcg_kg_min: Dose in µg/kg/min, or None.

    Returns:
        Tuple of (score, status_string_or_None).
    """
    if map_value is None:
        return 0, "missing"

    if not vasopressor_type or vasopressor_type.lower() in ("none", ""):
        # Score based on MAP alone
        if map_value >= 70:
            return 0, None
        return 1, None

    # Has vasopressor — determine level
    vtype = vasopressor_type.lower().strip()
    dose = vasopressor_dose_mcg_kg_min

    if vtype == "dobutamine":
        return 2, None

    if vtype == "dopamine":
        if dose is None:
            # Unknown dose, default to moderate (2-3 range)
            return 2, None
        if dose <= 5:
            return 2, None
        if dose <= 15:
            return 3, None
        return 4, None

    if vtype in ("epinephrine", "norepinephrine", "noradrenaline"):
        if dose is None:
            # Unknown dose, default to moderate-high
            return 3, None
        if dose <= 0.1:
            return 3, None
        return 4, None

    # Unknown vasopressor type — default to mid-range
    return 2, None


# ═══════════════════════════════════════════════════════════════════════════
# Neurological — Glasgow Coma Scale
# ═══════════════════════════════════════════════════════════════════════════

def score_neurological(gcs: int | None = None) -> tuple[int, str | None]:
    """Score neurological function based on Glasgow Coma Scale.

    15     = 0
    13-14  = 1
    10-12  = 2
    6-9    = 3
    <6     = 4

    Args:
        gcs: Glasgow Coma Scale score (3-15), or None if unavailable.

    Returns:
        Tuple of (score, status_string_or_None).
    """
    if gcs is None:
        return 0, "missing"

    if gcs == 15:
        return 0, None
    if gcs >= 13:
        return 1, None
    if gcs >= 10:
        return 2, None
    if gcs >= 6:
        return 3, None
    return 4, None


# ═══════════════════════════════════════════════════════════════════════════
# Renal — Creatinine + urine output
# ═══════════════════════════════════════════════════════════════════════════

def score_renal(
    creatinine: float | None = None,
    urine_output_ml_day: float | None = None,
) -> tuple[int, str | None]:
    """Score renal function based on creatinine and urine output.

    Creatinine thresholds (mg/dL):
    <1.2 = 0  (1.2-1.9=1, 2.0-3.4=2, 3.5-4.9=3, ≥5.0=4)

    Urine output can upgrade the score:
    <500 mL/day → minimum score 3
    <200 mL/day → minimum score 4

    The final score is the maximum of the creatinine-based score and the
    urine-output-based score.

    Args:
        creatinine: Serum creatinine in mg/dL, or None if unavailable.
        urine_output_ml_day: 24-hour urine output in mL, or None if unavailable.

    Returns:
        Tuple of (score, status_string_or_None).
    """
    both_missing = creatinine is None and urine_output_ml_day is None
    if both_missing:
        return 0, "missing"

    # Creatinine-based score
    if creatinine is None:
        cr_score = 0
    elif creatinine < 1.2:
        cr_score = 0
    elif creatinine < 2.0:
        cr_score = 1
    elif creatinine < 3.5:
        cr_score = 2
    elif creatinine < 5.0:
        cr_score = 3
    else:
        cr_score = 4

    # Urine output-based score
    if urine_output_ml_day is None:
        uo_score = 0
    elif urine_output_ml_day < 200:
        uo_score = 4
    elif urine_output_ml_day < 500:
        uo_score = 3
    else:
        uo_score = 0

    return max(cr_score, uo_score), None


# ═══════════════════════════════════════════════════════════════════════════
# Full SOFA Calculation
# ═══════════════════════════════════════════════════════════════════════════

def calculate_sofa(
    pao2_fio2: float | None = None,
    mechanical_ventilation: bool = False,
    platelets: float | None = None,
    bilirubin: float | None = None,
    map_value: float | None = None,
    vasopressor_type: str | None = None,
    vasopressor_dose_mcg_kg_min: float | None = None,
    gcs: int | None = None,
    creatinine: float | None = None,
    urine_output_ml_day: float | None = None,
) -> SOFAResult:
    """Calculate the full SOFA score from all 6 organ system parameters.

    Args:
        pao2_fio2: PaO2/FiO2 ratio in mmHg.
        mechanical_ventilation: Whether the patient is on mechanical ventilation.
        platelets: Platelet count in ×10³/µL.
        bilirubin: Total bilirubin in mg/dL.
        map_value: Mean Arterial Pressure in mmHg.
        vasopressor_type: Type of vasopressor ('dopamine', 'dobutamine',
            'epinephrine', 'norepinephrine'), or None.
        vasopressor_dose_mcg_kg_min: Vasopressor dose in µg/kg/min.
        gcs: Glasgow Coma Scale score (3-15).
        creatinine: Serum creatinine in mg/dL.
        urine_output_ml_day: 24-hour urine output in mL.

    Returns:
        SOFAResult with total score, component breakdown, and missing list.
    """
    missing: list[str] = []

    resp_score, resp_status = score_respiration(pao2_fio2, mechanical_ventilation)
    if resp_status == "missing":
        missing.append("pao2_fio2")

    coag_score, coag_status = score_coagulation(platelets)
    if coag_status == "missing":
        missing.append("platelets")

    liver_score, liver_status = score_liver(bilirubin)
    if liver_status == "missing":
        missing.append("bilirubin")

    cv_score, cv_status = score_cardiovascular(
        map_value, vasopressor_type, vasopressor_dose_mcg_kg_min,
    )
    if cv_status == "missing":
        missing.append("map_value")

    neuro_score, neuro_status = score_neurological(gcs)
    if neuro_status == "missing":
        missing.append("gcs")

    renal_score, renal_status = score_renal(creatinine, urine_output_ml_day)
    if renal_status == "missing":
        missing.append("creatinine_and_urine_output")

    components = SOFAComponents(
        respiration=resp_score,
        coagulation=coag_score,
        liver=liver_score,
        cardiovascular=cv_score,
        neurological=neuro_score,
        renal=renal_score,
    )

    total = (
        resp_score + coag_score + liver_score
        + cv_score + neuro_score + renal_score
    )

    return SOFAResult(
        total_score=total,
        components=components,
        missing_components=missing,
    )
