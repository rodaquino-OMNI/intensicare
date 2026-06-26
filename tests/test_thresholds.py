"""Integration tests for threshold configuration CRUD API."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from intensicare.models.threshold_config import ThresholdConfig


# ════════════════════════════════════════════════════════════════════════════
# Authorization tests
# ════════════════════════════════════════════════════════════════════════════

class TestThresholdAuth:
    """Verify that only admin users can access threshold endpoints."""

    async def test_list_requires_auth(self, client: AsyncClient, no_auth_headers):
        """No token = 401."""
        response = await client.get("/api/v1/thresholds", headers=no_auth_headers)
        assert response.status_code == 401

    async def test_list_requires_admin_role(
        self, client: AsyncClient, user_headers
    ):
        """User role (non-admin) = 403."""
        response = await client.get("/api/v1/thresholds", headers=user_headers)
        assert response.status_code == 403

    async def test_list_accepts_admin(self, client: AsyncClient, admin_headers):
        """Admin role = 200."""
        response = await client.get("/api/v1/thresholds", headers=admin_headers)
        assert response.status_code == 200

    async def test_create_requires_admin(self, client: AsyncClient, user_headers):
        """POST requires admin."""
        payload = {
            "tenant_id": "tenant-1",
            "score_type": "MEWS",
            "watch_threshold": 3,
            "urgent_threshold": 5,
            "critical_threshold": 7,
        }
        response = await client.post(
            "/api/v1/thresholds", json=payload, headers=user_headers
        )
        assert response.status_code == 403


# ════════════════════════════════════════════════════════════════════════════
# CRUD tests
# ════════════════════════════════════════════════════════════════════════════

class TestThresholdCRUD:
    """Test full CRUD lifecycle for threshold configurations."""

    async def test_create_threshold(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers
    ):
        """Create a new threshold configuration."""
        payload = {
            "tenant_id": "tenant-1",
            "unit": "ICU-A",
            "score_type": "NEWS2",
            "watch_threshold": 3,
            "urgent_threshold": 5,
            "critical_threshold": 7,
            "rate_limit_per_hour": 10,
            "cooldown_minutes": 30,
        }
        response = await client.post(
            "/api/v1/thresholds", json=payload, headers=admin_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["tenant_id"] == "tenant-1"
        assert data["unit"] == "ICU-A"
        assert data["score_type"] == "NEWS2"
        assert data["watch_threshold"] == 3
        assert data["urgent_threshold"] == 5
        assert data["critical_threshold"] == 7
        assert data["rate_limit_per_hour"] == 10
        assert data["cooldown_minutes"] == 30
        assert data["updated_by"] == "testadmin"
        assert data["updated_at"] is not None
        assert "id" in data

    async def test_create_threshold_minimal(self, client: AsyncClient, admin_headers):
        """Create with only required fields."""
        payload = {
            "tenant_id": "tenant-2",
            "score_type": "MEWS",
            "watch_threshold": 4,
            "urgent_threshold": 6,
            "critical_threshold": 8,
        }
        response = await client.post(
            "/api/v1/thresholds", json=payload, headers=admin_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["unit"] is None
        assert data["rate_limit_per_hour"] is None
        assert data["cooldown_minutes"] is None

    async def test_list_thresholds(self, client: AsyncClient, admin_headers):
        """List all threshold configs."""
        # Create a couple first
        for i in range(3):
            await client.post(
                "/api/v1/thresholds",
                json={
                    "tenant_id": f"tenant-{i}",
                    "score_type": "MEWS",
                    "watch_threshold": 3,
                    "urgent_threshold": 5,
                    "critical_threshold": 7,
                },
                headers=admin_headers,
            )

        response = await client.get("/api/v1/thresholds", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    async def test_list_thresholds_filter_by_tenant(
        self, client: AsyncClient, admin_headers
    ):
        """Filter thresholds by tenant_id query param."""
        response = await client.get(
            "/api/v1/thresholds?tenant_id=tenant-0", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        for item in data:
            assert item["tenant_id"] == "tenant-0"

    async def test_get_threshold_by_id(self, client: AsyncClient, admin_headers):
        """Get a single threshold by ID."""
        # Create one first
        create_resp = await client.post(
            "/api/v1/thresholds",
            json={
                "tenant_id": "tenant-get",
                "score_type": "NEWS2",
                "watch_threshold": 2,
                "urgent_threshold": 4,
                "critical_threshold": 6,
            },
            headers=admin_headers,
        )
        threshold_id = create_resp.json()["id"]

        response = await client.get(
            f"/api/v1/thresholds/{threshold_id}", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == threshold_id
        assert data["tenant_id"] == "tenant-get"

    async def test_get_threshold_not_found(self, client: AsyncClient, admin_headers):
        """404 for non-existent threshold."""
        response = await client.get("/api/v1/thresholds/99999", headers=admin_headers)
        assert response.status_code == 404

    async def test_update_threshold(self, client: AsyncClient, admin_headers):
        """Update an existing threshold."""
        # Create
        create_resp = await client.post(
            "/api/v1/thresholds",
            json={
                "tenant_id": "tenant-update",
                "score_type": "MEWS",
                "watch_threshold": 2,
                "urgent_threshold": 4,
                "critical_threshold": 6,
            },
            headers=admin_headers,
        )
        threshold_id = create_resp.json()["id"]

        # Update
        update_payload = {
            "watch_threshold": 5,
            "urgent_threshold": 7,
            "critical_threshold": 9,
            "cooldown_minutes": 15,
        }
        response = await client.put(
            f"/api/v1/thresholds/{threshold_id}",
            json=update_payload,
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["watch_threshold"] == 5
        assert data["urgent_threshold"] == 7
        assert data["critical_threshold"] == 9
        assert data["cooldown_minutes"] == 15
        assert data["tenant_id"] == "tenant-update"  # Unchanged
        assert data["score_type"] == "MEWS"  # Unchanged

    async def test_update_threshold_not_found(
        self, client: AsyncClient, admin_headers
    ):
        """404 on update of non-existent threshold."""
        response = await client.put(
            "/api/v1/thresholds/99999",
            json={"watch_threshold": 5},
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_update_requires_admin(self, client: AsyncClient, admin_headers, user_headers):
        """403 for non-admin update."""
        create_resp = await client.post(
            "/api/v1/thresholds",
            json={
                "tenant_id": "tenant-auth",
                "score_type": "MEWS",
                "watch_threshold": 2,
                "urgent_threshold": 4,
                "critical_threshold": 6,
            },
            headers=admin_headers,
        )
        threshold_id = create_resp.json()["id"]

        response = await client.put(
            f"/api/v1/thresholds/{threshold_id}",
            json={"watch_threshold": 5},
            headers=user_headers,
        )
        assert response.status_code == 403

    async def test_delete_threshold(self, client: AsyncClient, admin_headers):
        """Delete a threshold configuration."""
        # Create
        create_resp = await client.post(
            "/api/v1/thresholds",
            json={
                "tenant_id": "tenant-delete",
                "score_type": "MEWS",
                "watch_threshold": 2,
                "urgent_threshold": 4,
                "critical_threshold": 6,
            },
            headers=admin_headers,
        )
        threshold_id = create_resp.json()["id"]

        # Delete
        response = await client.delete(
            f"/api/v1/thresholds/{threshold_id}", headers=admin_headers
        )
        assert response.status_code == 204

        # Verify gone
        response = await client.get(
            f"/api/v1/thresholds/{threshold_id}", headers=admin_headers
        )
        assert response.status_code == 404

    async def test_delete_not_found(self, client: AsyncClient, admin_headers):
        """404 for delete of non-existent threshold."""
        response = await client.delete(
            "/api/v1/thresholds/99999", headers=admin_headers
        )
        assert response.status_code == 404

    async def test_delete_requires_admin(self, client: AsyncClient, admin_headers, user_headers):
        """403 for non-admin delete."""
        create_resp = await client.post(
            "/api/v1/thresholds",
            json={
                "tenant_id": "tenant-auth",
                "score_type": "MEWS",
                "watch_threshold": 2,
                "urgent_threshold": 4,
                "critical_threshold": 6,
            },
            headers=admin_headers,
        )
        threshold_id = create_resp.json()["id"]

        response = await client.delete(
            f"/api/v1/thresholds/{threshold_id}", headers=user_headers
        )
        assert response.status_code == 403

    async def test_validation_rejects_negative_thresholds(
        self, client: AsyncClient, admin_headers
    ):
        """Pydantic validation rejects negative threshold values."""
        payload = {
            "tenant_id": "tenant-1",
            "score_type": "MEWS",
            "watch_threshold": -1,
            "urgent_threshold": 5,
            "critical_threshold": 7,
        }
        response = await client.post(
            "/api/v1/thresholds", json=payload, headers=admin_headers
        )
        assert response.status_code == 422


class TestThresholdConfigModel:
    """Test the ThresholdConfig SQLAlchemy model directly."""

    async def test_create_model_instance(self, db_session: AsyncSession):
        """Verify model can be created and persisted."""
        from datetime import datetime, timezone

        config = ThresholdConfig(
            tenant_id="model-test",
            unit="ICU-B",
            score_type="NEWS2",
            watch_threshold=4,
            urgent_threshold=6,
            critical_threshold=8,
            rate_limit_per_hour=20,
            cooldown_minutes=60,
            updated_at=datetime.now(timezone.utc),
            updated_by="testuser",
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        assert config.id is not None
        assert config.tenant_id == "model-test"
        assert config.unit == "ICU-B"
        assert config.score_type == "NEWS2"

        # Verify persisted
        result = await db_session.execute(
            select(ThresholdConfig).where(ThresholdConfig.id == config.id)
        )
        fetched = result.scalar_one()
        assert fetched.tenant_id == "model-test"
