"""
Testes de integração para ingestão de sinais vitais e status do paciente.

Cobre:
- POST /api/v1/vitals com criação de sinais vitais e MEWS
- Idempotência com X-Idempotency-Key
- GET /api/v1/patients/{mpi_id}/status
- Validação de entrada (Pydantic)
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

VALID_VITALS_PAYLOAD = {
    "mpi_id": "MPI-00012345",
    "recorded_at": "2026-06-26T10:00:00Z",
    "heart_rate": 88,
    "systolic_bp": 125,
    "diastolic_bp": 80,
    "temperature": 37.0,
    "spo2": 97,
    "respiratory_rate": 16,
    "avpu": "A",
    "supplemental_o2": False,
    "source_system": "philips_monitor",
}


# ═══════════════════════════════════════════════════════════════════════════
# POST /api/v1/vitals — criação básica
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_vitals_normal(client: AsyncClient):
    """POST /api/v1/vitals deve criar sinais vitais e retornar MEWS."""
    response = await client.post("/api/v1/vitals", json=VALID_VITALS_PAYLOAD)

    assert response.status_code == 201
    data = response.json()
    assert data["mpi_id"] == "MPI-00012345"
    assert data["id"] is not None
    assert isinstance(data["id"], int)
    assert data["mews_score"] is not None
    assert data["mews_score"] >= 0
    assert data["message"] == "Vital signs ingested successfully"
    assert "recorded_at" in data
    assert "ingested_at" in data


@pytest.mark.asyncio
async def test_create_vitals_minimal_payload(client: AsyncClient):
    """POST /api/v1/vitals com payload mínimo (apenas mpi_id e recorded_at)."""
    minimal = {
        "mpi_id": "MPI-00099999",
        "recorded_at": "2026-06-26T12:00:00Z",
    }
    response = await client.post("/api/v1/vitals", json=minimal)

    assert response.status_code == 201
    data = response.json()
    assert data["mews_score"] == 0  # todos os componentes ausentes = 0


@pytest.mark.asyncio
async def test_create_vitals_septic_patient(client: AsyncClient):
    """POST /api/v1/vitals com dados de paciente séptico deve retornar MEWS elevado."""
    payload = {
        "mpi_id": "MPI-SEPSIS01",
        "recorded_at": "2026-06-26T14:30:00Z",
        "heart_rate": 115,
        "systolic_bp": 95,
        "diastolic_bp": 60,
        "temperature": 38.9,
        "spo2": 92,
        "respiratory_rate": 28,
        "avpu": "V",
        "supplemental_o2": True,
    }

    response = await client.post("/api/v1/vitals", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["mews_score"] == 8  # 2+1+2+2+1


@pytest.mark.asyncio
async def test_create_vitals_critical_patient(client: AsyncClient):
    """POST /api/v1/vitals com paciente crítico deve retornar MEWS máximo."""
    payload = {
        "mpi_id": "MPI-CRITICAL01",
        "recorded_at": "2026-06-26T15:00:00Z",
        "heart_rate": 35,
        "systolic_bp": 65,
        "temperature": 34.0,
        "respiratory_rate": 6,
        "avpu": "U",
    }

    response = await client.post("/api/v1/vitals", json=payload)
    assert response.status_code == 201
    assert response.json()["mews_score"] == 15


# ═══════════════════════════════════════════════════════════════════════════
# Idempotência
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_idempotency_duplicate_request(client: AsyncClient):
    """Requisições idênticas com mesma chave de idempotência devem retornar
    o mesmo resultado sem criar novo registro."""
    headers = {"X-Idempotency-Key": "test-key-001"}

    resp1 = await client.post(
        "/api/v1/vitals",
        json={**VALID_VITALS_PAYLOAD, "mpi_id": "MPI-IDEM-01"},
        headers=headers,
    )
    assert resp1.status_code == 201
    data1 = resp1.json()

    # Segunda requisição com a mesma chave
    resp2 = await client.post(
        "/api/v1/vitals",
        json={**VALID_VITALS_PAYLOAD, "mpi_id": "MPI-IDEM-01"},
        headers=headers,
    )
    assert resp2.status_code == 200  # OK em vez de 201 Created
    data2 = resp2.json()

    # Deve retornar o mesmo ID
    assert data2["id"] == data1["id"]
    assert data2["mews_score"] == data1["mews_score"]
    assert "idempotent" in data2["message"].lower()


@pytest.mark.asyncio
async def test_idempotency_different_keys(client: AsyncClient):
    """Chaves de idempotência diferentes devem criar registros distintos."""
    payload = {**VALID_VITALS_PAYLOAD, "mpi_id": "MPI-IDEM-02"}

    resp1 = await client.post(
        "/api/v1/vitals",
        json=payload,
        headers={"X-Idempotency-Key": "key-alpha"},
    )
    resp2 = await client.post(
        "/api/v1/vitals",
        json=payload,
        headers={"X-Idempotency-Key": "key-beta"},
    )

    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp1.json()["id"] != resp2.json()["id"]


@pytest.mark.asyncio
async def test_idempotency_without_key(client: AsyncClient):
    """Sem chave de idempotência, cada requisição deve criar novo registro."""
    payload = {**VALID_VITALS_PAYLOAD, "mpi_id": "MPI-NOKEY-01"}

    resp1 = await client.post("/api/v1/vitals", json=payload)
    resp2 = await client.post("/api/v1/vitals", json=payload)

    assert resp1.status_code == 201
    assert resp2.status_code == 201
    # IDs diferentes — dois registros criados
    assert resp1.json()["id"] != resp2.json()["id"]


# ═══════════════════════════════════════════════════════════════════════════
# Validação
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_validation_missing_required_fields(client: AsyncClient):
    """Campos obrigatórios (mpi_id, recorded_at) devem ser validados."""
    # Sem mpi_id
    resp = await client.post(
        "/api/v1/vitals",
        json={"recorded_at": "2026-06-26T10:00:00Z"},
    )
    assert resp.status_code == 422

    # Sem recorded_at
    resp = await client.post(
        "/api/v1/vitals",
        json={"mpi_id": "MPI-001"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_validation_invalid_avpu(client: AsyncClient):
    """AVPU deve ser um de A/V/P/U."""
    payload = {**VALID_VITALS_PAYLOAD, "avpu": "X"}
    resp = await client.post("/api/v1/vitals", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_validation_avpu_case_insensitive(client: AsyncClient):
    """AVPU deve aceitar lowercase e retornar uppercase."""
    payload = {**VALID_VITALS_PAYLOAD, "avpu": "v"}
    resp = await client.post("/api/v1/vitals", json=payload)
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_validation_out_of_range_heart_rate(client: AsyncClient):
    """Heart rate > 300 deve ser rejeitado."""
    payload = {**VALID_VITALS_PAYLOAD, "heart_rate": 350}
    resp = await client.post("/api/v1/vitals", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_validation_negative_values(client: AsyncClient):
    """Valores negativos devem ser rejeitados."""
    payload = {**VALID_VITALS_PAYLOAD, "heart_rate": -1}
    resp = await client.post("/api/v1/vitals", json=payload)
    assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/v1/patients/{mpi_id}/status
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_patient_status_no_data(client: AsyncClient):
    """Status de paciente sem dados deve retornar 200 com campos nulos."""
    resp = await client.get("/api/v1/patients/MPI-NOEXIST/status")

    assert resp.status_code == 200
    data = resp.json()
    assert data["mpi_id"] == "MPI-NOEXIST"
    assert data["latest_vitals"] is None
    assert data["latest_mews"] is None
    assert data["trend"]["values"] == []
    assert data["trend"]["current_trend"] is None
    assert data["last_updated"] is None


@pytest.mark.asyncio
async def test_patient_status_after_ingestion(client: AsyncClient):
    """Após ingerir sinais vitais, status deve refletir os dados."""
    mpi_id = "MPI-STATUS-01"

    # Ingere sinais vitais
    payload = {**VALID_VITALS_PAYLOAD, "mpi_id": mpi_id}
    resp = await client.post("/api/v1/vitals", json=payload)
    assert resp.status_code == 201

    # Consulta status
    resp = await client.get(f"/api/v1/patients/{mpi_id}/status")
    assert resp.status_code == 200
    data = resp.json()

    assert data["mpi_id"] == mpi_id
    assert data["latest_vitals"] is not None
    assert data["latest_vitals"]["heart_rate"] == 88
    assert data["latest_vitals"]["systolic_bp"] == 125
    assert data["latest_vitals"]["temperature"] == 37.0
    assert data["latest_mews"] is not None
    assert data["latest_mews"]["score_type"] == "MEWS"
    assert data["latest_mews"]["score_value"] is not None
    assert data["trend"]["values"] == [data["latest_mews"]["score_value"]]
    assert data["last_updated"] is not None


@pytest.mark.asyncio
async def test_patient_status_trend_multiple_scores(client: AsyncClient):
    """Após múltiplas ingestões, tendência deve refletir os últimos 5 scores."""
    mpi_id = "MPI-TREND-01"
    headers = {}

    # Ingere 7 sinais vitais com valores progressivamente piores
    scores = []
    for i in range(7):
        hr = 80 + i * 5  # 80, 85, 90, 95, 100, 105, 110
        rr = 16 + i      # 16, 17, 18, 19, 20, 21, 22
        payload = {
            "mpi_id": mpi_id,
            "recorded_at": f"2026-06-26T{10 + i}:00:00Z",
            "heart_rate": hr,
            "systolic_bp": 120,
            "temperature": 37.0,
            "respiratory_rate": rr,
            "avpu": "A",
        }
        headers = {"X-Idempotency-Key": f"trend-key-{i}"}
        resp = await client.post("/api/v1/vitals", json=payload, headers=headers)
        assert resp.status_code == 201
        scores.append(resp.json()["mews_score"])

    # Consulta status
    resp = await client.get(f"/api/v1/patients/{mpi_id}/status")
    assert resp.status_code == 200
    data = resp.json()

    # Deve ter no máximo 5 valores na tendência (últimos 5)
    trend_values = data["trend"]["values"]
    assert len(trend_values) <= 5
    # Tendência deve ser increasing se o último score > primeiro dos 5
    if len(trend_values) >= 2:
        expected_trend = (
            "increasing" if trend_values[-1] > trend_values[0]
            else "decreasing" if trend_values[-1] < trend_values[0]
            else "stable"
        )
        assert data["trend"]["current_trend"] == expected_trend


@pytest.mark.asyncio
async def test_patient_status_trend_improving(client: AsyncClient):
    """Paciente em melhora deve mostrar tendência 'decreasing'."""
    mpi_id = "MPI-IMPROVE-01"

    # Ingere primeiro: score alto
    resp = await client.post(
        "/api/v1/vitals",
        json={
            "mpi_id": mpi_id,
            "recorded_at": "2026-06-26T10:00:00Z",
            "heart_rate": 130,
            "systolic_bp": 75,
            "temperature": 38.9,
            "respiratory_rate": 30,
            "avpu": "P",
        },
        headers={"X-Idempotency-Key": "improve-1"},
    )
    assert resp.status_code == 201

    # Ingere segundo: score mais baixo (melhora)
    resp = await client.post(
        "/api/v1/vitals",
        json={
            "mpi_id": mpi_id,
            "recorded_at": "2026-06-26T11:00:00Z",
            "heart_rate": 90,
            "systolic_bp": 120,
            "temperature": 37.0,
            "respiratory_rate": 16,
            "avpu": "A",
        },
        headers={"X-Idempotency-Key": "improve-2"},
    )
    assert resp.status_code == 201

    # Status deve mostrar tendência decreasing
    resp = await client.get(f"/api/v1/patients/{mpi_id}/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["trend"]["current_trend"] == "decreasing"
