"""Tests for alert CRUD endpoints."""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from intensicare.models.alert import Alert
from intensicare.models.user import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_test_alert(db: AsyncSession, status="active", severity="watch") -> Alert:
    """Helper to create a test alert."""
    alert = Alert(
        mpi_id="MPI-1001",
        score_id=None,
        severity=severity,
        status=status,
        title=f"Test Alert - {severity}",
        body="Test alert body",
        created_at=datetime.now(timezone.utc),
    )
    db.add(alert)
    await db.flush()
    await db.refresh(alert)
    return alert


async def create_test_user(db: AsyncSession) -> tuple[User, str]:
    """Create a test user and return (user, token)."""
    user = User(
        username="testuser",
        email="test@test.com",
        hashed_password=pwd_context.hash("test1234"),
        display_name="Test User",
        is_admin=False,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    # We need to get a token - use the login endpoint via the client
    return user


class TestListAlerts:
    """Tests for GET /api/v1/alerts."""

    @pytest.mark.asyncio
    async def test_list_active_alerts(self, client: AsyncClient, db_session: AsyncSession):
        """Should list active alerts."""
        await create_test_alert(db_session, status="active", severity="watch")
        await create_test_alert(db_session, status="acknowledged", severity="urgent")

        response = await client.get("/api/v1/alerts?status=active")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert all(a["status"] == "active" for a in data)

    @pytest.mark.asyncio
    async def test_list_alerts_with_mpi_filter(self, client: AsyncClient, db_session: AsyncSession):
        """Should filter by mpi_id."""
        await create_test_alert(db_session, status="active")

        response = await client.get("/api/v1/alerts?status=active&mpi_id=MPI-1001")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert all(a["mpi_id"] == "MPI-1001" for a in data)

    @pytest.mark.asyncio
    async def test_list_alerts_empty(self, client: AsyncClient):
        """Should return empty list when no alerts."""
        response = await client.get("/api/v1/alerts?status=active")

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_alerts_respects_limit(self, client: AsyncClient, db_session: AsyncSession):
        """Should respect the limit parameter."""
        for i in range(5):
            alert = Alert(
                mpi_id=f"MPI-{1000+i}",
                severity="watch",
                status="active",
                title=f"Alert {i}",
                body="test",
                created_at=datetime.now(timezone.utc),
            )
            db_session.add(alert)
        await db_session.flush()

        response = await client.get("/api/v1/alerts?status=active&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2


class TestAcknowledgeAlert:
    """Tests for POST /api/v1/alerts/{alert_id}/acknowledge."""

    @pytest.mark.asyncio
    async def test_acknowledge_requires_auth(self, client: AsyncClient, db_session: AsyncSession):
        """Should return 401 without auth."""
        alert = await create_test_alert(db_session)

        response = await client.post(f"/api/v1/alerts/{alert.id}/acknowledge")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_acknowledge_not_found(self, client: AsyncClient, db_session: AsyncSession):
        """Should return 404 for non-existent alert."""
        user = User(
            username="nurse",
            email="nurse@test.com",
            hashed_password=pwd_context.hash("nurse1234"),
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(user)
        await db_session.flush()

        # Login to get token
        from intensicare.auth.jwt import create_access_token
        token = create_access_token({"sub": user.username, "user_id": user.id})

        response = await client.post(
            "/api/v1/alerts/99999/acknowledge",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_acknowledge_already_acknowledged(self, client: AsyncClient, db_session: AsyncSession):
        """Should return 409 if already acknowledged."""
        alert = await create_test_alert(db_session, status="acknowledged")
        user = User(
            username="nurse",
            email="nurse@test.com",
            hashed_password=pwd_context.hash("nurse1234"),
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(user)
        await db_session.flush()

        from intensicare.auth.jwt import create_access_token
        token = create_access_token({"sub": user.username, "user_id": user.id})

        response = await client.post(
            f"/api/v1/alerts/{alert.id}/acknowledge",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 409


class TestTraceAlert:
    """Tests for GET /api/v1/alerts/{alert_id}/trace."""

    @pytest.mark.asyncio
    async def test_trace_alert_success(self, client: AsyncClient, db_session: AsyncSession):
        """Should return alert details."""
        alert = await create_test_alert(db_session)

        response = await client.get(f"/api/v1/alerts/{alert.id}/trace")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == alert.id
        assert data["mpi_id"] == alert.mpi_id
        assert data["severity"] == alert.severity
        assert data["status"] == alert.status

    @pytest.mark.asyncio
    async def test_trace_alert_not_found(self, client: AsyncClient):
        """Should return 404 for non-existent alert."""
        response = await client.get("/api/v1/alerts/99999/trace")

        assert response.status_code == 404
