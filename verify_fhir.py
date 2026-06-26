"""Standalone FHIR module verification (no DB required)."""
from datetime import date
from intensicare.fhir.client import FHIRPatientData, FHIRClient
import asyncio

# Test full bundle parsing
bundle = {
    "resourceType": "Bundle",
    "type": "searchset",
    "entry": [
        {
            "resource": {
                "resourceType": "Patient",
                "id": "pat-001",
                "name": [{"use": "official", "given": ["João"], "family": "Silva"}],
                "gender": "male",
                "birthDate": "1965-03-15",
                "maritalStatus": {"coding": [{"code": "M", "display": "Married"}]},
                "telecom": [{"system": "phone", "value": "+55-11-99999-0001"}],
                "address": [{"line": ["Rua das Flores, 123"], "city": "São Paulo", "state": "SP", "postalCode": "01001-000"}]
            }
        },
        {
            "resource": {
                "resourceType": "Condition",
                "clinicalStatus": {"coding": [{"code": "active"}]},
                "code": {"coding": [{"display": "Hypertension"}]},
                "subject": {"reference": "Patient/pat-001"}
            }
        },
        {
            "resource": {
                "resourceType": "AllergyIntolerance",
                "code": {"coding": [{"display": "Penicillin"}]},
                "patient": {"reference": "Patient/pat-001"}
            }
        },
        {
            "resource": {
                "resourceType": "Observation",
                "code": {"coding": [{"display": "Body Weight"}]},
                "valueQuantity": {"value": 78.5, "unit": "kg"},
                "subject": {"reference": "Patient/pat-001"}
            }
        }
    ]
}

data = FHIRPatientData.from_fhir_bundle("MPI-12345", bundle)
assert data.mpi_id == "MPI-12345"
assert data.display_name == "João Silva"
assert data.gender == "male"
assert data.birth_date == date(1965, 3, 15)
assert data.marital_status == "Married"
assert data.phone == "+55-11-99999-0001"
assert data.address is not None and "Rua das Flores, 123" in data.address
assert data.primary_condition == "Hypertension"
assert data.condition_list == ["Hypertension"]
assert data.allergy_list == ["Penicillin"]
assert "Body Weight" in data.latest_observations
assert data.latest_observations["Body Weight"]["value"] == 78.5

# Test empty bundle
data2 = FHIRPatientData.from_fhir_bundle("MPI-EMPTY", {"resourceType": "Bundle", "entry": []})
assert data2.mpi_id == "MPI-EMPTY"
assert data2.display_name is None
assert data2.condition_list == []

# Test minimal bundle
data3 = FHIRPatientData.from_fhir_bundle("MPI-002", {
    "resourceType": "Bundle",
    "entry": [{"resource": {"resourceType": "Patient", "name": [{"text": "Maria"}], "gender": "female"}}]
})
assert data3.display_name == "Maria"
assert data3.gender == "female"

# Test non-bundle
data4 = FHIRPatientData.from_fhir_bundle("MPI-X", {"resourceType": "Patient", "id": "x"})
assert data4.mpi_id == "MPI-X"
assert data4.display_name is None


async def test_unconfigured():
    client = FHIRClient(base_url="")
    assert client.is_configured is False
    assert await client.get_patient("X") is None
    assert await client.get_observation("X", "8867-4") is None
    assert await client.search("Patient", identifier="X") is None

asyncio.run(test_unconfigured())

print("ALL FHIR CHECKS PASSED")
