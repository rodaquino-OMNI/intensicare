"""
Testes unitários para o engine de scoring MEWS.

Cobre todos os componentes do score, casos de borda, valores ausentes,
e a função de tendência.
"""

from __future__ import annotations

import pytest

from intensicare.services.mews import (
    MEWS_VERSION,
    calculate_mews,
    compute_trend,
    _score_heart_rate,
    _score_systolic_bp,
    _score_respiratory_rate,
    _score_temperature,
    _score_avpu,
)


# ═══════════════════════════════════════════════════════════════════════════
# Heart Rate
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize(
    "value,expected",
    [
        (None, 0),
        (30, 3),   # bradicardia severa
        (40, 3),   # limite bradicardia severa
        (41, 2),   # bradicardia moderada
        (50, 2),   # limite bradicardia moderada
        (51, 0),   # normal
        (75, 0),   # normal
        (100, 0),  # normal (limite)
        (101, 1),  # taquicardia leve
        (110, 1),  # taquicardia leve (limite)
        (111, 2),  # taquicardia moderada
        (129, 2),  # taquicardia moderada (limite)
        (130, 3),  # taquicardia severa
        (180, 3),  # taquicardia severa
    ],
)
def test_score_heart_rate(value, expected):
    """Cada faixa de frequência cardíaca deve retornar o score correto."""
    result = _score_heart_rate(value)
    assert result["heart_rate"] == expected
    if value is None:
        assert "heart_rate_status" in result


# ═══════════════════════════════════════════════════════════════════════════
# Systolic BP
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize(
    "value,expected",
    [
        (None, 0),
        (60, 3),   # hipotensão severa
        (70, 3),   # limite hipotensão severa
        (71, 2),   # hipotensão moderada
        (80, 2),   # limite hipotensão moderada
        (81, 1),   # hipotensão leve
        (100, 1),  # hipotensão leve (limite)
        (101, 0),  # normal
        (140, 0),  # normal
        (199, 0),  # normal (limite)
        (200, 2),  # hipertensão severa
        (250, 2),  # hipertensão severa
    ],
)
def test_score_systolic_bp(value, expected):
    """Cada faixa de pressão sistólica deve retornar o score correto."""
    result = _score_systolic_bp(value)
    assert result["systolic_bp"] == expected


# ═══════════════════════════════════════════════════════════════════════════
# Respiratory Rate
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize(
    "value,expected",
    [
        (None, 0),
        (5, 3),    # bradipneia severa
        (8, 3),    # limite bradipneia severa
        (9, 0),    # normal
        (14, 0),   # normal (limite)
        (15, 1),   # taquipneia leve
        (20, 1),   # taquipneia leve (limite)
        (21, 2),   # taquipneia moderada
        (29, 2),   # taquipneia moderada (limite)
        (30, 3),   # taquipneia severa
        (40, 3),   # taquipneia severa
    ],
)
def test_score_respiratory_rate(value, expected):
    """Cada faixa de frequência respiratória deve retornar o score correto."""
    result = _score_respiratory_rate(value)
    assert result["respiratory_rate"] == expected


# ═══════════════════════════════════════════════════════════════════════════
# Temperature
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize(
    "value,expected",
    [
        (None, 0),
        (33.0, 3),   # hipotermia
        (35.0, 3),   # limite hipotermia
        (35.1, 1),   # temperatura baixa
        (36.0, 1),   # temperatura baixa (limite)
        (36.1, 0),   # normal
        (37.0, 0),   # normal
        (38.0, 0),   # normal (limite)
        (38.1, 1),   # febre leve
        (38.5, 1),   # febre leve (limite)
        (38.6, 2),   # febre
        (40.0, 2),   # febre
    ],
)
def test_score_temperature(value, expected):
    """Cada faixa de temperatura deve retornar o score correto."""
    result = _score_temperature(value)
    assert result["temperature"] == expected


# ═══════════════════════════════════════════════════════════════════════════
# AVPU
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize(
    "value,expected",
    [
        (None, 0),
        ("A", 0),
        ("a", 0),   # case insensitive
        ("V", 1),
        ("v", 1),
        ("P", 2),
        ("p", 2),
        ("U", 3),
        ("u", 3),
        ("Alert", 0),  # unknown maps to 0
        ("", 0),        # empty maps to 0
    ],
)
def test_score_avpu(value, expected):
    """AVPU deve mapear A=0, V=1, P=2, U=3, case-insensitive."""
    result = _score_avpu(value)
    assert result["avpu"] == expected


# ═══════════════════════════════════════════════════════════════════════════
# calculate_mews — integração
# ═══════════════════════════════════════════════════════════════════════════

def test_calculate_mews_normal_vitals():
    """Paciente com todos os sinais normais deve ter MEWS = 0."""
    score, components = calculate_mews(
        heart_rate=75,
        systolic_bp=120,
        respiratory_rate=14,
        temperature=37.0,
        avpu="A",
    )
    assert score == 0
    assert components["algorithm_version"] == MEWS_VERSION
    assert components["heart_rate"] == 0
    assert components["systolic_bp"] == 0
    assert components["respiratory_rate"] == 0
    assert components["temperature"] == 0
    assert components["avpu"] == 0


def test_calculate_mews_septic_patient():
    """Paciente séptico típico: taquicardia, taquipneia, febre, alterado."""
    score, components = calculate_mews(
        heart_rate=115,        # 2 pts (111-129)
        systolic_bp=95,        # 1 pt (81-100)
        respiratory_rate=28,   # 2 pts (21-29)
        temperature=38.9,      # 2 pts (≥38.6)
        avpu="V",              # 1 pt
    )
    assert score == 8  # 2 + 1 + 2 + 2 + 1
    assert components["heart_rate"] == 2
    assert components["systolic_bp"] == 1
    assert components["respiratory_rate"] == 2
    assert components["temperature"] == 2
    assert components["avpu"] == 1


def test_calculate_mews_critical_patient():
    """Paciente crítico: todos os scores no máximo."""
    score, components = calculate_mews(
        heart_rate=35,         # 3 pts (≤40)
        systolic_bp=65,        # 3 pts (≤70)
        respiratory_rate=6,    # 3 pts (≤8)
        temperature=34.0,      # 3 pts (≤35.0)
        avpu="U",              # 3 pts
    )
    assert score == 15  # máximo teórico


def test_calculate_mews_missing_components():
    """Componentes ausentes devem contribuir com 0 e ser marcados como missing."""
    score, components = calculate_mews(
        heart_rate=80,
        systolic_bp=None,
        respiratory_rate=None,
        temperature=None,
        avpu="A",
    )
    assert score == 0
    assert "missing_components" in components
    missing = components["missing_components"]
    assert "systolic_bp" in missing
    assert "respiratory_rate" in missing
    assert "temperature" in missing
    assert "heart_rate" not in missing
    assert "avpu" not in missing


def test_calculate_mews_all_missing():
    """Sem nenhum dado, score deve ser 0 e todos marcados como missing."""
    score, components = calculate_mews()
    assert score == 0
    assert "missing_components" in components
    assert len(components["missing_components"]) == 5
    assert components["algorithm_version"] == MEWS_VERSION


def test_calculate_mews_boundary_values():
    """Testa valores nos limites exatos das faixas."""
    # Todos nos limites da faixa normal máxima
    score, _ = calculate_mews(
        heart_rate=100,       # normal limite
        systolic_bp=199,      # normal limite
        respiratory_rate=14,  # normal limite
        temperature=38.0,     # normal limite
        avpu="A",
    )
    assert score == 0

    # Todos nos limites da faixa mínima anormal
    score2, _ = calculate_mews(
        heart_rate=101,       # taquicardia leve
        systolic_bp=200,      # hipertensão severa
        respiratory_rate=15,  # taquipneia leve
        temperature=38.1,     # febre leve
        avpu="V",             # voz
    )
    assert score2 == 1 + 2 + 1 + 1 + 1


def test_calculate_mews_is_deterministic():
    """Mesmos inputs devem sempre produzir mesmos outputs."""
    args = dict(
        heart_rate=90,
        systolic_bp=110,
        respiratory_rate=18,
        temperature=37.5,
        avpu="A",
    )
    score1, comp1 = calculate_mews(**args)
    score2, comp2 = calculate_mews(**args)
    assert score1 == score2
    assert comp1 == comp2


def test_calculate_mews_with_floats():
    """Temperatura como float deve ser tratada corretamente."""
    score, comp = calculate_mews(temperature=35.05)
    # 35.05 > 35.0, então <= 35.0 é False, cai no próximo: <= 36.0 -> 1 pt
    assert score == 1
    assert comp["temperature"] == 1


# ═══════════════════════════════════════════════════════════════════════════
# compute_trend
# ═══════════════════════════════════════════════════════════════════════════

def test_compute_trend_increasing():
    """Scores crescentes devem retornar 'increasing'."""
    assert compute_trend([0, 2, 4]) == "increasing"
    assert compute_trend([1, 3]) == "increasing"


def test_compute_trend_decreasing():
    """Scores decrescentes devem retornar 'decreasing'."""
    assert compute_trend([5, 3, 1]) == "decreasing"
    assert compute_trend([4, 0]) == "decreasing"


def test_compute_trend_stable():
    """Scores estáveis devem retornar 'stable'."""
    assert compute_trend([3, 3, 3]) == "stable"
    assert compute_trend([0, 0]) == "stable"


def test_compute_trend_single_value():
    """Um único valor não tem tendência definida."""
    assert compute_trend([3]) is None


def test_compute_trend_empty():
    """Lista vazia não tem tendência."""
    assert compute_trend([]) is None


def test_compute_trend_fluctuating():
    """Flutuação que termina acima do início é 'increasing'."""
    assert compute_trend([2, 0, 4, 1, 3]) == "increasing"


def test_compute_trend_same_start_end():
    """Mesmo valor no início e fim é 'stable' independente do meio."""
    assert compute_trend([3, 5, 2, 3]) == "stable"
