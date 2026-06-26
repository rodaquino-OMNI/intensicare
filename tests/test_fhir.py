"""
Testes para o módulo de integração FHIR R4.

Cobre:
- FHIRPatientData parsing from mock bundles
- FHIRClient gracefully returning None when unconfigured
- FHIRClient returning enriched data with mocked responses
- Patient service enrichment path (when FHIR configured)
- Patient service skipping enrichment (when FHIR not configured)
- API endpoint with enrich=true/false
"""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from intensicare.fhir.client import (
    FHIRClient,
    FHIRPatientData,
    get_fhir_client,
)
from intensicare.schemas.patients import FHIREnrichment


# ═══════════════════════════════════════════════════════════════════════════
# Mock FHIR bundles (realistic HAPI FHIR R4 JSON)
# ═══════════════════════════════════════════════════════════════════════════

MOCK_FHIR_BUNDLE = {
    "resourceType": "Bundle",
    "type": "searchset",
    "entry": [
        {
            "resource": {
                "resourceType": "Patient",
                "id": "pat-001",
                "identifier": [{"system": "urn:oid:mpi", "value": "MPI-12345"}],
                "name": [
                    {
                        "use": "official",
                        "prefix": ["Mr."],
                        "given": ["João"],
                        "family": "Silva",
                    }
                ],
                "gender": "male",
                "birthDate": "1965-03-15",
                "maritalStatus": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus",
                            "code": "M",
                            "display": "Married",
                        }
                    ]
                },
                "telecom": [
                    {"system": "phone", "value": "+55-11-99999-0001", "use": "home"},
                    {"system": "email", "value": "joao.silva@example.com"},
                ],
                "address": [
                    {
                        "use": "home",
                        "line": ["Rua das Flores, 123"],
                        "city": "São Paulo",
                        "state": "SP",
                        "postalCode": "01001-000",
                    }
                ],
            }
        },
        {
            "resource": {
                "resourceType": "Condition",
                "id": "cond-001",
                "clinicalStatus": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": "active",
                        }
                    ]
                },
                "code": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "38341003",
                            "display": "Hypertension",
                        }
                    ]
                },
                "subject": {"reference": "Patient/pat-001"},
            }
        },
        {
            "resource": {
                "resourceType": "Condition",
                "id": "cond-002",
                "clinicalStatus": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": "active",
                        }
                    ]
                },
                "code": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "44054006",
                            "display": "Diabetes mellitus type 2",
                        }
                    ]
                },
                "subject": {"reference": "Patient/pat-001"},
            }
        },
        {
            "resource": {
                "resourceType": "AllergyIntolerance",
                "id": "allergy-001",
                "code": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "91936005",
                            "display": "Penicillin",
                        }
                    ]
                },
                "patient": {"reference": "Patient/pat-001"},
            }
        },
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-001",
                "status": "final",
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "29463-7",
                            "display": "Body Weight",
                        }
                    ]
                },
                "valueQuantity": {
                    "value": 78.5,
                    "unit": "kg",
                    "system": "http://unitsofmeasure.org",
                },
                "subject": {"reference": "Patient/pat-001"},
            }
        },
    ],
}


MOCK_FHIR_MINIMAL_BUNDLE = {
    "resourceType": "Bundle",
    "type": "searchset",
    "entry": [
        {
            "resource": {
                "resourceType": "Patient",
                "id": "pat-002",
                "name": [{"text": "Maria Souza"}],
                "gender": "female",
            }
        }
    ],
}


MOCK_FHIR_OBSERVATION_BUNDLE = {
    "resourceType": "Bundle",
    "type": "searchset",
    "entry": [
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-002",
                "status": "final",
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "8867-4",
                            "display": "Heart Rate",
                        }
                    ]
                },
                "valueQuantity": {
                    "value": 72,
                    "unit": "bpm",
                    "system": "http://unitsofmeasure.org",
                },
                "effectiveDateTime": "2025-06-20T10:30:00Z",
                "subject": {"reference": "Patient/pat-001"},
            }
        }
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# FHIRPatientData tests
# ═══════════════════════════════════════════════════════════════════════════


class TestFHIRPatientData:
    """Unit tests for FHIRPatientData.from_fhir_bundle parsing."""

    def test_parses_full_bundle(self) -> None:
        """Full bundle yields all structured fields."""
        data = FHIRPatientData.from_fhir_bundle("MPI-12345", MOCK_FHIR_BUNDLE)

        assert data.mpi_id == "MPI-12345"
        assert data.display_name == "Mr. João Silva"
        assert data.gender == "male"
        assert data.birth_date == date(1965, 3, 15)
        assert data.marital_status == "Married"
        assert data.phone == "+55-11-99999-0001"
        assert "Rua das Flores, 123" in (data.address or "")
        assert data.primary_condition == "Hypertension"
        assert len(data.condition_list) == 2
        assert "Diabetes mellitus type 2" in data.condition_list
        assert len(data.allergy_list) == 1
        assert "Penicillin" in data.allergy_list
        assert "Body Weight" in data.latest_observations
        assert data.latest_observations["Body Weight"]["value"] == 78.5

    def test_parses_minimal_bundle(self) -> None:
        """Minimal bundle with only a Patient resource."""
        data = FHIRPatientData.from_fhir_bundle("MPI-002", MOCK_FHIR_MINIMAL_BUNDLE)

        assert data.mpi_id == "MPI-002"
        assert data.display_name == "Maria Souza"
        assert data.gender == "female"
        assert data.birth_date is None
        assert data.condition_list == []
        assert data.allergy_list == []
        assert data.latest_observations == {}

    def test_empty_bundle(self) -> None:
        """Empty bundle yields placeholder data."""
        data = FHIRPatientData.from_fhir_bundle("MPI-EMPTY", {"resourceType": "Bundle", "entry": []})
        assert data.mpi_id == "MPI-EMPTY"
        assert data.display_name is None

    def test_non_bundle_resource(self) -> None:
        """Non-Bundle resource is handled gracefully."""
        data = FHIRPatientData.from_fhir_bundle(
            "MPI-X", {"resourceType": "Patient", "id": "x"}
        )
        assert data.mpi_id == "MPI-X"
        assert data.display_name is None


# ═══════════════════════════════════════════════════════════════════════════
# FHIRClient tests
# ═══════════════════════════════════════════════════════════════════════════


class TestFHIRClientUnconfigured:
    """FHIRClient with no base_url should always return None gracefully."""

    @pytest.mark.anyio
    async def test_is_configured_false(self) -> None:
        client = FHIRClient(base_url="")
        assert client.is_configured is False

    @pytest.mark.anyio
    async def test_get_patient_returns_none(self) -> None:
        client = FHIRClient(base_url="")
        result = await client.get_patient("MPI-12345")
        assert result is None

    @pytest.mark.anyio
    async def test_get_observation_returns_none(self) -> None:
        client = FHIRClient(base_url="")
        result = await client.get_observation("MPI-12345", "8867-4")
        assert result is None

    @pytest.mark.anyio
    async def test_search_returns_none(self) -> None:
        client = FHIRClient(base_url="")
        result = await client.search("Patient", identifier="MPI-12345")
        assert result is None


class TestFHIRClientConfigured:
    """FHIRClient with a base_url should make real HTTP calls (mocked)."""

    @pytest.mark.anyio
    async def test_get_patient_success(self) -> None:
        """Simulate a successful FHIR Patient query."""
        client = FHIRClient(base_url="https://fhir.example.com/fhir")

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_FHIR_BUNDLE
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.get.return_value = mock_response

        with patch.object(client, "_get_client", return_value=mock_http):
            result = await client.get_patient("MPI-12345")

        assert result is not None
        assert result.display_name == "Mr. João Silva"
        assert result.gender == "male"
        assert result.primary_condition == "Hypertension"

    @pytest.mark.anyio
    async def test_get_patient_404(self) -> None:
        """404 from FHIR returns a FHIRPatientData with only mpi_id."""
        client = FHIRClient(base_url="https://fhir.example.com/fhir")

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 404
        http_error = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        mock_response.raise_for_status.side_effect = http_error

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.get.return_value = mock_response

        with patch.object(client, "_get_client", return_value=mock_http):
            result = await client.get_patient("MPI-UNKNOWN")

        assert result is not None
        assert result.mpi_id == "MPI-UNKNOWN"
        assert result.display_name is None

    @pytest.mark.anyio
    async def test_get_patient_connection_error(self) -> None:
        """Connection error returns None gracefully."""
        client = FHIRClient(base_url="https://fhir.example.com/fhir")

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.get.side_effect = httpx.ConnectError("Connection refused")

        with patch.object(client, "_get_client", return_value=mock_http):
            result = await client.get_patient("MPI-12345")

        assert result is None

    @pytest.mark.anyio
    async def test_get_patient_timeout(self) -> None:
        """Timeout returns None gracefully."""
        client = FHIRClient(base_url="https://fhir.example.com/fhir")

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.get.side_effect = httpx.TimeoutException("Timeout")

        with patch.object(client, "_get_client", return_value=mock_http):
            result = await client.get_patient("MPI-12345")

        assert result is None

    @pytest.mark.anyio
    async def test_get_observation_success(self) -> None:
        """Successful Observation fetch returns the resource."""
        client = FHIRClient(base_url="https://fhir.example.com/fhir")

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_FHIR_OBSERVATION_BUNDLE
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.get.return_value = mock_response

        with patch.object(client, "_get_client", return_value=mock_http):
            result = await client.get_observation("MPI-12345", "8867-4")

        assert result is not None
        assert result["resourceType"] == "Observation"
        assert result["code"]["coding"][0]["code"] == "8867-4"

    @pytest.mark.anyio
    async def test_close_cleans_up(self) -> None:
        """close() should close the underlying HTTP client."""
        client = FHIRClient(base_url="https://fhir.example.com/fhir")

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.get.return_value = MagicMock(status_code=200)
        client._client = mock_http

        await client.close()
        mock_http.aclose.assert_called_once()
        assert client._client is None


# ═══════════════════════════════════════════════════════════════════════════
# Patient service integration tests
# ═══════════════════════════════════════════════════════════════════════════


class TestPatientServiceFHIREnrichment:
    """Test the patient service with FHIR enrichment on/off."""

    @pytest.mark.anyio
    async def test_enrich_skipped_when_fhir_not_configured(self) -> None:
        """When FHIR_BASE_URL is empty, enrichment returns None."""
        from intensicare.services.patients import _enrich_from_fhir

        # Patch settings so fhir_base_url is empty
        with patch("intensicare.services.patients.settings") as mock_settings:
            mock_settings.fhir_base_url = ""
            result = await _enrich_from_fhir("MPI-12345")
            assert result is None

    @pytest.mark.anyio
    async def test_get_patient_status_without_enrich(
        self, mock_db_session: AsyncMock
    ) -> None:
        """When enrich=False, fhir field stays None."""
        from intensicare.services.patients import get_patient_status

        result = await get_patient_status(
            db=mock_db_session, mpi_id="MPI-12345", score_type="MEWS", enrich=False
        )

        assert result.fhir is None
        assert result.mpi_id == "MPI-12345"

    @pytest.mark.anyio
    async def test_get_patient_status_with_enrich_success(
        self, mock_db_session: AsyncMock
    ) -> None:
        """When enrich=True and FHIR returns data, fhir field is populated."""
        from intensicare.services.patients import get_patient_status

        with patch(
            "intensicare.services.patients._enrich_from_fhir",
            return_value=FHIREnrichment(
                display_name="João Silva",
                gender="male",
                birth_date="1965-03-15",
                marital_status="Married",
                condition_list=["Hypertension"],
                allergy_list=["Penicillin"],
            ),
        ):
            result = await get_patient_status(
                db=mock_db_session,
                mpi_id="MPI-12345",
                score_type="MEWS",
                enrich=True,
            )

        assert result.fhir is not None
        assert result.fhir.display_name == "João Silva"
        assert result.fhir.gender == "male"
        assert "Hypertension" in result.fhir.condition_list


# ═══════════════════════════════════════════════════════════════════════════
# API endpoint integration tests
# ═══════════════════════════════════════════════════════════════════════════


class TestPatientStatusAPI:
    """Test the /patients/{mpi_id}/status endpoint with enrich parameter."""

    @pytest.mark.anyio
    async def test_status_without_enrich(
        self, mock_client: httpx.AsyncClient
    ) -> None:
        """GET without enrich returns no fhir field."""
        response = await mock_client.get("/api/v1/patients/MPI-NOEXIST/status")
        assert response.status_code == 200
        data = response.json()
        assert data["mpi_id"] == "MPI-NOEXIST"
        # When enrich is False (default), fhir should be null
        assert data.get("fhir") is None

    @pytest.mark.anyio
    async def test_status_with_enrich_fhir_not_configured(
        self, mock_client: httpx.AsyncClient
    ) -> None:
        """GET with enrich=true but empty FHIR_BASE_URL — fhir stays null."""
        with patch("intensicare.services.patients.settings") as mock_settings:
            mock_settings.fhir_base_url = ""
            response = await mock_client.get(
                "/api/v1/patients/MPI-NOEXIST/status", params={"enrich": "true"}
            )
        assert response.status_code == 200
        data = response.json()
        assert data.get("fhir") is None

    @pytest.mark.anyio
    async def test_status_with_enrich_configured(
        self, mock_client: httpx.AsyncClient
    ) -> None:
        """GET with enrich=true and FHIR configured — enrichment is attempted."""
        mock_fhir = FHIREnrichment(
            display_name="Test Patient",
            gender="female",
            condition_list=["Anemia"],
        )

        with patch(
            "intensicare.services.patients._enrich_from_fhir",
            return_value=mock_fhir,
        ):
            response = await mock_client.get(
                "/api/v1/patients/MPI-NOEXIST/status",
                params={"enrich": "true"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data.get("fhir") is not None
        assert data["fhir"]["display_name"] == "Test Patient"
        assert data["fhir"]["gender"] == "female"
        assert "Anemia" in data["fhir"]["condition_list"]


# ═══════════════════════════════════════════════════════════════════════════
# get_fhir_client factory
# ═══════════════════════════════════════════════════════════════════════════


class TestGetFHIRClient:
    """Tests for the get_fhir_client factory function."""

    def test_returns_client(self) -> None:
        """Returns a FHIRClient instance."""
        with patch("intensicare.fhir.client.settings") as mock_settings:
            mock_settings.fhir_base_url = "https://fhir.example.com/fhir"
            mock_settings.fhir_auth_token = MagicMock()
            mock_settings.fhir_auth_token.get_secret_value.return_value = "test-token"

            # Clear the lru_cache
            get_fhir_client.cache_clear()

            client = get_fhir_client()
            assert isinstance(client, FHIRClient)
            assert client.is_configured is True

    def test_unconfigured_client(self) -> None:
        """Unconfigured client has is_configured = False."""
        with patch("intensicare.fhir.client.settings") as mock_settings:
            mock_settings.fhir_base_url = ""
            mock_settings.fhir_auth_token = None

            get_fhir_client.cache_clear()

            client = get_fhir_client()
            assert client.is_configured is False
