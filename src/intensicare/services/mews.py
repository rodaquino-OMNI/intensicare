"""
MEWS (Modified Early Warning Score) — engine de scoring determinístico e versionado.

Implementa o algoritmo MEWS conforme especificação clínica:
- heart_rate
- systolic_bp
- respiratory_rate
- temperature
- avpu

Cada componente retorna 0-3 pontos. Score total = soma dos componentes avaliáveis.
Componentes ausentes (None) contribuem com 0 pontos e são marcados como 'missing'.
"""

from __future__ import annotations

from typing import Any

MEWS_VERSION = "MEWS-v1.0"


def _score_heart_rate(value: int | None) -> dict[str, Any]:
    """MEWS sub-score para frequência cardíaca (bpm).

    ≤40   = 3 (bradicardia severa)
    41-50 = 2 (bradicardia moderada)
    51-100 = 0 (normal)
    101-110 = 1 (taquicardia leve)
    111-129 = 2 (taquicardia moderada)
    ≥130  = 3 (taquicardia severa)
    """
    if value is None:
        return {"heart_rate": 0, "heart_rate_status": "missing"}
    if value <= 40:
        pts = 3
    elif value <= 50:
        pts = 2
    elif value <= 100:
        pts = 0
    elif value <= 110:
        pts = 1
    elif value <= 129:
        pts = 2
    else:
        pts = 3
    return {"heart_rate": pts}


def _score_systolic_bp(value: int | None) -> dict[str, Any]:
    """MEWS sub-score para pressão sistólica (mmHg).

    ≤70   = 3 (hipotensão severa)
    71-80 = 2 (hipotensão moderada)
    81-100 = 1 (hipotensão leve)
    101-199 = 0 (normal)
    ≥200  = 2 (hipertensão severa)
    """
    if value is None:
        return {"systolic_bp": 0, "systolic_bp_status": "missing"}
    if value <= 70:
        pts = 3
    elif value <= 80:
        pts = 2
    elif value <= 100:
        pts = 1
    elif value <= 199:
        pts = 0
    else:
        pts = 2
    return {"systolic_bp": pts}


def _score_respiratory_rate(value: int | None) -> dict[str, Any]:
    """MEWS sub-score para frequência respiratória (rpm).

    ≤8    = 3 (bradipneia severa)
    9-14  = 0 (normal)
    15-20 = 1 (taquipneia leve)
    21-29 = 2 (taquipneia moderada)
    ≥30   = 3 (taquipneia severa)
    """
    if value is None:
        return {"respiratory_rate": 0, "respiratory_rate_status": "missing"}
    if value <= 8:
        pts = 3
    elif value <= 14:
        pts = 0
    elif value <= 20:
        pts = 1
    elif value <= 29:
        pts = 2
    else:
        pts = 3
    return {"respiratory_rate": pts}


def _score_temperature(value: float | None) -> dict[str, Any]:
    """MEWS sub-score para temperatura (°C).

    ≤35.0      = 3 (hipotermia)
    35.1-36.0  = 1 (temperatura baixa)
    36.1-38.0  = 0 (normal)
    38.1-38.5  = 1 (febre leve)
    ≥38.6      = 2 (febre)
    """
    if value is None:
        return {"temperature": 0, "temperature_status": "missing"}
    if value <= 35.0:
        pts = 3
    elif value <= 36.0:
        pts = 1
    elif value <= 38.0:
        pts = 0
    elif value <= 38.5:
        pts = 1
    else:
        pts = 2
    return {"temperature": pts}


def _score_avpu(value: str | None) -> dict[str, Any]:
    """MEWS sub-score para nível de consciência (AVPU).

    Alert        = 0
    Voice        = 1
    Pain         = 2
    Unresponsive = 3
    """
    if value is None:
        return {"avpu": 0, "avpu_status": "missing"}

    avpu_map: dict[str, int] = {"A": 0, "V": 1, "P": 2, "U": 3}
    upper = value.upper().strip()
    pts = avpu_map.get(upper, 0)
    return {"avpu": pts}


def calculate_mews(
    heart_rate: int | None = None,
    systolic_bp: int | None = None,
    respiratory_rate: int | None = None,
    temperature: float | None = None,
    avpu: str | None = None,
) -> tuple[int, dict[str, Any]]:
    """Calcula o MEWS (Modified Early Warning Score).

    Função determinística e pura: mesmos inputs sempre produzem mesmos outputs.
    Cada parâmetro é um componente do score; ausentes contribuem com 0.

    Args:
        heart_rate: Frequência cardíaca em bpm.
        systolic_bp: Pressão sistólica em mmHg.
        respiratory_rate: Frequência respiratória em rpm.
        temperature: Temperatura em °C.
        avpu: Nível de consciência (A/V/P/U).

    Returns:
        Tuple de (score_total, components_dict) onde:
        - score_total: int com a soma dos sub-scores (0-15).
        - components_dict: dict com sub-scores individuais e status.
          Inclui 'algorithm_version' = 'MEWS-v1.0' e 'missing_components' se houver.
    """
    components: dict[str, Any] = {"algorithm_version": MEWS_VERSION}

    hr = _score_heart_rate(heart_rate)
    sbp = _score_systolic_bp(systolic_bp)
    rr = _score_respiratory_rate(respiratory_rate)
    temp = _score_temperature(temperature)
    avpu_score = _score_avpu(avpu)

    components.update(hr)
    components.update(sbp)
    components.update(rr)
    components.update(temp)
    components.update(avpu_score)

    # Identifica componentes ausentes
    missing = [k.replace("_status", "") for k, v in components.items() if k.endswith("_status")]
    if missing:
        components["missing_components"] = missing

    # Remove chaves de status do dicionário final de componentes de score
    status_keys = [k for k in components if k.endswith("_status")]
    for k in status_keys:
        del components[k]

    # Soma apenas os sub-scores numéricos
    score_total = int(
        components.get("heart_rate", 0)
        + components.get("systolic_bp", 0)
        + components.get("respiratory_rate", 0)
        + components.get("temperature", 0)
        + components.get("avpu", 0)
    )

    return score_total, components


def compute_trend(scores: list[int]) -> str | None:
    """Determina a tendência a partir de uma lista de scores consecutivos.

    Compara o último score com o primeiro da lista.

    Args:
        scores: Lista de valores de score em ordem cronológica (mais antigo primeiro).

    Returns:
        'increasing', 'decreasing', 'stable', ou None se lista tiver < 2 elementos.
    """
    if len(scores) < 2:
        return None
    first, last = scores[0], scores[-1]
    if last > first:
        return "increasing"
    elif last < first:
        return "decreasing"
    else:
        return "stable"
