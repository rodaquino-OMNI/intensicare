"""
FHIR R4 client for HAPI FHIR server integration.

Queries Patient and Observation resources from a configurable FHIR endpoint.
Gracefully degrades when no FHIR server is configured.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from functools import lru_cache
from typing import Any

import httpx

from intensicare.config import settings

logger = logging.getLogger(__name__)


@dataclass
class FHIRPatientData:
    """Enriched patient data fetched from a FHIR server."""

    mpi_id: str
    display_name: str | None = None
    gender: str | None = None
    birth_date: date | None = None
    marital_status: str | None = None
    phone: str | None = None
    address: str | None = None
    primary_condition: str | None = None
    condition_list: list[str] = field(default_factory=list)
    allergy_list: list[str] = field(default_factory=list)
    latest_observations: dict[str, Any] = field(default_factory=dict)
    raw_patient_resource: dict[str, Any] | None = None

    @classmethod
    def from_fhir_bundle(cls, mpi_id: str, bundle: dict[str, Any]) -> FHIRPatientData:
        """Parse a FHIR searchset bundle into structured FHIRPatientData.

        Expects a bundle with Patient, Condition, AllergyIntolerance, and
        Observation entries (typically from a $everything or composite query).
        """
        data: dict[str, Any] = {"mpi_id": mpi_id}

        if bundle.get("resourceType") != "Bundle":
            return cls(mpi_id=mpi_id)

        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {})
            if resource is None:
                continue
            rt = resource.get("resourceType")

            if rt == "Patient":
                data.update(cls._parse_patient(resource))
                if "raw_patient_resource" not in data:
                    data["raw_patient_resource"] = resource
            elif rt == "Condition":
                cls._parse_condition(resource, data)
            elif rt == "AllergyIntolerance":
                cls._parse_allergy(resource, data)
            elif rt == "Observation":
                cls._parse_observation(resource, data)

        return cls(**data)

    @staticmethod
    def _parse_patient(resource: dict[str, Any]) -> dict[str, Any]:
        parsed: dict[str, Any] = {}

        # Name
        names = resource.get("name", [])
        if names:
            official = next((n for n in names if n.get("use") == "official"), names[0])
            parts = []
            for prefix in ("prefix", "given", "family"):
                val = official.get(prefix)
                if val:
                    parts.extend(val if isinstance(val, list) else [val])
            parsed["display_name"] = " ".join(parts) if parts else official.get("text")

        # Gender
        parsed["gender"] = resource.get("gender")

        # Birth date
        bd = resource.get("birthDate")
        if bd:
            try:
                parsed["birth_date"] = date.fromisoformat(bd)
            except (ValueError, TypeError):
                pass

        # Marital status
        ms = resource.get("maritalStatus", {})
        if ms:
            coding = ms.get("coding", [{}])[0] if ms.get("coding") else {}
            parsed["marital_status"] = coding.get("display") or ms.get("text")

        # Phone
        telecoms = resource.get("telecom", [])
        for t in telecoms:
            if t.get("system") == "phone":
                parsed["phone"] = t.get("value")
                break

        # Address
        addresses = resource.get("address", [])
        if addresses:
            addr = addresses[0]
            lines = addr.get("line", [])
            city = addr.get("city", "")
            state = addr.get("state", "")
            postal = addr.get("postalCode", "")
            full = ", ".join([*lines, city, state, postal] if city or state else lines)
            parsed["address"] = full if full else addr.get("text")

        return parsed

    @staticmethod
    def _parse_condition(resource: dict[str, Any], data: dict[str, Any]) -> None:
        code = resource.get("code", {})
        coding_list = code.get("coding", [])
        display = (
            coding_list[0].get("display")
            if coding_list
            else code.get("text")
        )
        if display:
            conditions = data.setdefault("condition_list", [])
            conditions.append(display)
            # First active problem is the primary condition
            clinical_status = resource.get("clinicalStatus", {}).get("coding", [{}])
            is_active = any(
                c.get("code") == "active" for c in clinical_status
            )
            if is_active and "primary_condition" not in data:
                data["primary_condition"] = display

    @staticmethod
    def _parse_allergy(resource: dict[str, Any], data: dict[str, Any]) -> None:
        code = resource.get("code", {})
        coding_list = code.get("coding", [])
        display = (
            coding_list[0].get("display")
            if coding_list
            else code.get("text")
        )
        if display:
            allergies = data.setdefault("allergy_list", [])
            allergies.append(display)

    @staticmethod
    def _parse_observation(resource: dict[str, Any], data: dict[str, Any]) -> None:
        code = resource.get("code", {})
        coding_list = code.get("coding", [])
        obs_name = (
            coding_list[0].get("display")
            or coding_list[0].get("code")
            or code.get("text")
        )
        if not obs_name:
            return

        value = None
        if "valueQuantity" in resource:
            vq = resource["valueQuantity"]
            value = {
                "value": vq.get("value"),
                "unit": vq.get("unit"),
                "system": vq.get("system"),
            }
        elif "valueCodeableConcept" in resource:
            vc = resource["valueCodeableConcept"]
            coding = vc.get("coding", [{}])[0] if vc.get("coding") else {}
            value = coding.get("display") or vc.get("text")
        elif "valueString" in resource:
            value = resource["valueString"]

        if value is not None:
            observations = data.setdefault("latest_observations", {})
            observations[obs_name] = value


class FHIRClient:
    """Async client for querying a HAPI FHIR R4 server.

    Requires FHIR_BASE_URL to be configured.  When the base URL is empty or
    None every public method returns None gracefully (no-op mode).
    """

    def __init__(
        self,
        base_url: str | None = None,
        auth_token: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        self._base_url = (base_url or "").rstrip("/")
        self._auth_token = auth_token
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def is_configured(self) -> bool:
        """True when a FHIR base URL has been set."""
        return bool(self._base_url)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers: dict[str, str] = {
                "Accept": "application/fhir+json",
            }
            if self._auth_token:
                headers["Authorization"] = f"Bearer {self._auth_token}"

            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers=headers,
                timeout=httpx.Timeout(self._timeout),
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ── public read API ───────────────────────────────────────────────

    async def get_patient(self, mpi_id: str) -> FHIRPatientData | None:
        """Fetch patient demographics + conditions + allergies + observations.

        Returns None when FHIR is not configured or the patient is not found.
        """
        if not self.is_configured:
            return None

        try:
            client = await self._get_client()
            # Use _include / _revinclude to fetch related resources in one call
            params: dict[str, str | int] = {
                "identifier": mpi_id,
                "_include": "Patient:organization",
                "_revinclude": "Condition:subject",
                "_revinclude": "AllergyIntolerance:patient",
                "_revinclude": "Observation:patient",
                "_count": 50,
            }
            response = await client.get("/Patient", params=params)
            response.raise_for_status()
            bundle = response.json()

            return FHIRPatientData.from_fhir_bundle(mpi_id, bundle)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.info("FHIR patient not found: %s", mpi_id)
                return FHIRPatientData(mpi_id=mpi_id)
            logger.warning("FHIR HTTP error for patient %s: %s", mpi_id, exc)
            return None
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            logger.warning("FHIR request failed for patient %s: %s", mpi_id, exc)
            return None

    async def get_observation(
        self, mpi_id: str, loinc_code: str
    ) -> dict[str, Any] | None:
        """Fetch the latest Observation for a patient by LOINC code.

        Returns None when FHIR is not configured or no result is found.
        """
        if not self.is_configured:
            return None

        try:
            client = await self._get_client()
            params: dict[str, str | int] = {
                "patient": mpi_id,
                "code": loinc_code,
                "_sort": "-date",
                "_count": 1,
            }
            response = await client.get("/Observation", params=params)
            response.raise_for_status()
            bundle = response.json()

            entries = bundle.get("entry", [])
            if entries:
                return entries[0].get("resource")
            return None
        except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException) as exc:
            logger.warning("FHIR observation fetch failed: %s", exc)
            return None

    async def search(
        self, resource_type: str, **params: str | int
    ) -> dict[str, Any] | None:
        """Generic FHIR search returning the raw bundle.

        Returns None when FHIR is not configured.
        """
        if not self.is_configured:
            return None

        try:
            client = await self._get_client()
            response = await client.get(f"/{resource_type}", params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException) as exc:
            logger.warning("FHIR search %s failed: %s", resource_type, exc)
            return None


@lru_cache
def get_fhir_client() -> FHIRClient:
    """Return a cached, lazily-initialized FHIR client from app settings."""
    base = settings.fhir_base_url or None
    token = settings.fhir_auth_token.get_secret_value() if settings.fhir_auth_token else None
    return FHIRClient(base_url=base, auth_token=token)
