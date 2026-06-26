"""NEWS2 (National Early Warning Score 2) scoring engine.

Implements the Royal College of Physicians NEWS2 protocol with all 7 parameters.
"""

from dataclasses import dataclass, field


@dataclass
class NEWS2Components:
    """Individual component scores for NEWS2."""

    respiratory_rate: int = 0
    spo2: int = 0
    supplemental_o2: int = 0
    systolic_bp: int = 0
    heart_rate: int = 0
    consciousness: int = 0
    temperature: int = 0


@dataclass
class NEWS2Result:
    """Result of a NEWS2 calculation."""

    total_score: int
    components: NEWS2Components
    algorithm_version: str = "NEWS2-v1.0"

    @property
    def risk_category(self) -> str:
        """Classify the total score into risk category."""
        if self.total_score >= 7:
            return "high"
        if self.total_score >= 5:
            return "medium"
        return "low"

    @property
    def requires_urgent_assessment(self) -> bool:
        """Whether an urgent clinical assessment is recommended."""
        return self.total_score >= 5 or any(
            score == 3 for score in [
                self.components.respiratory_rate,
                self.components.spo2,
                self.components.systolic_bp,
                self.components.heart_rate,
                self.components.consciousness,
                self.components.temperature,
            ]
        )


def _score_numeric(value: int | float | None, thresholds: list[tuple[float | None, float | None, int]]) -> int:
    """Score a numeric value against a list of (min, max, score) thresholds.

    Each threshold is (min_inclusive, max_inclusive, score).
    None means unbounded.
    """
    if value is None:
        return 0

    for lo, hi, score in thresholds:
        lo_ok = lo is None or value >= lo
        hi_ok = hi is None or value <= hi
        if lo_ok and hi_ok:
            return score

    return 0


def score_respiratory_rate(rr: int | None) -> int:
    """Score respiratory rate per NEWS2.

    ≤8 = 3, 9-11 = 1, 12-20 = 0, 21-24 = 2, ≥25 = 3
    """
    return _score_numeric(rr, [
        (None, 8, 3),
        (9, 11, 1),
        (12, 20, 0),
        (21, 24, 2),
        (25, None, 3),
    ])


def score_spo2(spo2: int | None, hypercapnic: bool = False) -> int:
    """Score SpO2 per NEWS2.

    Scale 1 (non-hypercapnic): ≥96=0, 94-95=1, 92-93=2, ≤91=3
    Scale 2 (hypercapnic):     ≥93=0, 88-92=1, 86-87=2, 84-85=2, ≤83=3
    """
    if spo2 is None:
        return 0

    if hypercapnic:
        return _score_numeric(spo2, [
            (93, None, 0),
            (88, 92, 1),
            (86, 87, 2),
            (84, 85, 2),
            (None, 83, 3),
        ])

    return _score_numeric(spo2, [
        (96, None, 0),
        (94, 95, 1),
        (92, 93, 2),
        (None, 91, 3),
    ])


def score_supplemental_o2(on_o2: bool | None) -> int:
    """Score supplemental oxygen: +2 if on O2."""
    return 2 if on_o2 else 0


def score_systolic_bp(sbp: int | None) -> int:
    """Score systolic blood pressure per NEWS2.

    ≤90=3, 91-100=2, 101-110=1, 111-219=0, ≥220=3
    """
    return _score_numeric(sbp, [
        (None, 90, 3),
        (91, 100, 2),
        (101, 110, 1),
        (111, 219, 0),
        (220, None, 3),
    ])


def score_heart_rate(hr: int | None) -> int:
    """Score heart rate per NEWS2.

    ≤40=3, 41-50=1, 51-90=0, 91-110=1, 111-130=2, ≥131=3
    """
    return _score_numeric(hr, [
        (None, 40, 3),
        (41, 50, 1),
        (51, 90, 0),
        (91, 110, 1),
        (111, 130, 2),
        (131, None, 3),
    ])


def score_consciousness(avpu: str | None) -> int:
    """Score consciousness per NEWS2.

    Alert (A) = 0
    CVPU (any altered level: C/V/P/U) = 3
    """
    if avpu is None:
        return 0
    avpu_upper = avpu.strip().upper()
    if avpu_upper == "A":
        return 0
    return 3


def score_temperature(temp: float | None) -> int:
    """Score temperature per NEWS2.

    ≤35.0=3, 35.1-36.0=1, 36.1-38.0=0, 38.1-39.0=1, ≥39.1=2
    """
    return _score_numeric(temp, [
        (None, 35.0, 3),
        (35.1, 36.0, 1),
        (36.1, 38.0, 0),
        (38.1, 39.0, 1),
        (39.1, None, 2),
    ])


def calculate_news2(
    respiratory_rate: int | None = None,
    spo2: int | None = None,
    hypercapnic: bool = False,
    supplemental_o2: bool | None = None,
    systolic_bp: int | None = None,
    heart_rate: int | None = None,
    avpu: str | None = None,
    temperature: float | None = None,
) -> NEWS2Result:
    """Calculate the full NEWS2 score from all 7 parameters.

    Args:
        respiratory_rate: Breaths per minute.
        spo2: Oxygen saturation (%).
        hypercapnic: Whether the patient has hypercapnic respiratory failure
                     (changes SpO2 scale from Scale 1 to Scale 2).
        supplemental_o2: Whether the patient is on supplemental oxygen.
        systolic_bp: Systolic blood pressure (mmHg).
        heart_rate: Heart rate (bpm).
        avpu: Consciousness level (A=Alert, C/V/P/U=altered).
        temperature: Body temperature (°C).

    Returns:
        NEWS2Result with total score and component breakdown.
    """
    components = NEWS2Components(
        respiratory_rate=score_respiratory_rate(respiratory_rate),
        spo2=score_spo2(spo2, hypercapnic=hypercapnic),
        supplemental_o2=score_supplemental_o2(supplemental_o2),
        systolic_bp=score_systolic_bp(systolic_bp),
        heart_rate=score_heart_rate(heart_rate),
        consciousness=score_consciousness(avpu),
        temperature=score_temperature(temperature),
    )

    total = sum([
        components.respiratory_rate,
        components.spo2,
        components.supplemental_o2,
        components.systolic_bp,
        components.heart_rate,
        components.consciousness,
        components.temperature,
    ])

    return NEWS2Result(total_score=total, components=components)
