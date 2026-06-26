"""Integration tests for WebSocket real-time alerts.

Tests:
- WebSocket manager connection management (connect/disconnect)
- Ping/pong message handling via the manager
- Subscribe/unsubscribe to patient_ids
- Broadcast filtering by patient_id subscriptions
- Alert broadcast after vitals ingestion triggers alert engine
- Singleton pattern for get/set/reset_websocket_manager
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from intensicare.core.websocket import (
    WebSocketManager,
    get_websocket_manager,
    reset_websocket_manager,
    set_websocket_manager,
)
from intensicare.models.patient_cache import PatientCache
from intensicare.models.threshold_config import ThresholdConfig


async def create_test_patient(
    db: AsyncSession,
    mpi_id: str = "MPI-WS-TEST",
    tenant_id: str = "austa",
    unit: str = "ICU",
) -> PatientCache:
    """Create a test patient in the patient cache."""
    patient = PatientCache(
        mpi_id=mpi_id,
        tenant_id=tenant_id,
        display_name=f"Test Patient {mpi_id}",
        unit=unit,
        is_active=True,
    )
    db.add(patient)
    await db.flush()
    return patient


async def create_threshold_for_test(
    db: AsyncSession,
    tenant_id: str = "austa",
    score_type: str = "MEWS",
    watch: int = 1,
    urgent: int = 3,
    critical: int = 5,
) -> ThresholdConfig:
    """Create a threshold config that triggers alerts at low scores for testing."""
    config = ThresholdConfig(
        tenant_id=tenant_id,
        score_type=score_type,
        watch_threshold=watch,
        urgent_threshold=urgent,
        critical_threshold=critical,
        rate_limit_per_hour=100,
        cooldown_minutes=0,
    )
    db.add(config)
    await db.flush()
    return config


def _make_mock_websocket() -> AsyncMock:
    """Create a mock Starlette WebSocket for testing the manager."""
    mock = AsyncMock()
    mock.send_json = AsyncMock()
    return mock


class TestWebSocketManagerLifecycle:
    """Tests for WebSocket connection lifecycle management."""

    def test_initial_active_connections(self):
        """Manager should start with zero active connections."""
        manager = WebSocketManager()
        assert manager.active_connections == 0

    @pytest.mark.asyncio
    async def test_connect_increases_count(self):
        """Connect should accept the websocket and increment the count."""
        manager = WebSocketManager()
        ws = _make_mock_websocket()

        await manager.connect(ws)
        assert manager.active_connections == 1
        ws.accept.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_decreases_count(self):
        """Disconnect should remove the websocket and decrement the count."""
        manager = WebSocketManager()
        ws = _make_mock_websocket()

        await manager.connect(ws)
        assert manager.active_connections == 1

        manager.disconnect(ws)
        assert manager.active_connections == 0

    @pytest.mark.asyncio
    async def test_disconnect_unknown_websocket_is_safe(self):
        """Disconnecting a websocket that was never connected should not raise."""
        manager = WebSocketManager()
        ws = _make_mock_websocket()
        manager.disconnect(ws)  # Should not raise
        assert manager.active_connections == 0

    def test_multiple_instances_are_independent(self):
        """Each manager instance should be independent."""
        m1 = WebSocketManager()
        m2 = WebSocketManager()
        assert m1 is not m2
        assert m1.active_connections == 0
        assert m2.active_connections == 0


class TestWebSocketSubscriptions:
    """Tests for patient_id subscription filtering."""

    @pytest.mark.asyncio
    async def test_subscribe_adds_patient_id(self):
        """Subscribe should add the patient_id to the websocket's subscription set."""
        manager = WebSocketManager()
        ws = _make_mock_websocket()

        await manager.connect(ws)
        await manager.subscribe(ws, "MPI-001")

        # Verify by broadcasting — should filter based on subscriptions
        alert = _make_alert("MPI-001")
        await manager.broadcast_alert(alert)
        ws.send_json.assert_called_once_with(alert)

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_patient_id(self):
        """Unsubscribe should remove the patient_id from the subscription set."""
        manager = WebSocketManager()
        ws = _make_mock_websocket()

        await manager.connect(ws)
        await manager.subscribe(ws, "MPI-001")
        await manager.unsubscribe(ws, "MPI-001")

        # Now broadcasting for MPI-001 should NOT reach this client
        ws.send_json.reset_mock()
        await manager.broadcast_alert(_make_alert("MPI-001"))
        ws.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_subscription_filters_alerts(self):
        """Only alerts matching subscribed patient_ids should be received."""
        manager = WebSocketManager()
        ws = _make_mock_websocket()

        await manager.connect(ws)
        await manager.subscribe(ws, "MPI-001")

        # Alert for subscribed patient — received
        await manager.broadcast_alert(_make_alert("MPI-001"))
        assert ws.send_json.call_count == 1
        ws.send_json.reset_mock()

        # Alert for different patient — NOT received
        await manager.broadcast_alert(_make_alert("MPI-OTHER"))
        ws.send_json.assert_not_called()

        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_multiple_subscriptions(self):
        """A client can subscribe to multiple patient_ids."""
        manager = WebSocketManager()
        ws = _make_mock_websocket()

        await manager.connect(ws)
        await manager.subscribe(ws, "MPI-001")
        await manager.subscribe(ws, "MPI-002")

        # Both subscribed patients should trigger alerts
        await manager.broadcast_alert(_make_alert("MPI-001"))
        await manager.broadcast_alert(_make_alert("MPI-002"))
        assert ws.send_json.call_count == 2
        ws.send_json.reset_mock()

        # Unrelated patient should not
        await manager.broadcast_alert(_make_alert("MPI-OTHER"))
        ws.send_json.assert_not_called()

        manager.disconnect(ws)


class TestWebSocketBroadcast:
    """Tests for alert broadcasting behavior."""

    @pytest.mark.asyncio
    async def test_broadcast_without_subscriptions_sends_to_all(self):
        """Without any subscriptions, all connected clients receive all alerts."""
        manager = WebSocketManager()
        ws = _make_mock_websocket()

        await manager.connect(ws)
        # No subscription — should receive all alerts

        await manager.broadcast_alert(_make_alert("ANY-PATIENT"))
        ws.send_json.assert_called_once()

        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_clients(self):
        """Alerts should be broadcast to all connected clients (respecting filters)."""
        manager = WebSocketManager()
        ws1 = _make_mock_websocket()
        ws2 = _make_mock_websocket()

        await manager.connect(ws1)
        await manager.connect(ws2)
        assert manager.active_connections == 2

        # No subscriptions on either — both get the alert
        alert = _make_alert("MPI-X")
        await manager.broadcast_alert(alert)
        ws1.send_json.assert_called_once_with(alert)
        ws2.send_json.assert_called_once_with(alert)

        manager.disconnect(ws1)
        manager.disconnect(ws2)

    @pytest.mark.asyncio
    async def test_broadcast_handles_disconnected_client(self):
        """Broadcast should gracefully handle clients that disconnect mid-stream."""
        manager = WebSocketManager()
        ws_good = _make_mock_websocket()
        ws_bad = _make_mock_websocket()
        ws_bad.send_json = AsyncMock(side_effect=Exception("Connection lost"))

        await manager.connect(ws_good)
        await manager.connect(ws_bad)

        alert = _make_alert("MPI-Z")
        await manager.broadcast_alert(alert)

        # Good client got the alert
        ws_good.send_json.assert_called_once_with(alert)
        # Bad client was removed
        assert manager.active_connections == 1

        manager.disconnect(ws_good)

    @pytest.mark.asyncio
    async def test_send_error(self):
        """send_error should send a properly formatted error message."""
        manager = WebSocketManager()
        ws = _make_mock_websocket()

        await manager.connect(ws)
        await manager.send_error(ws, "Something went wrong")
        ws.send_json.assert_called_once_with(
            {"type": "error", "message": "Something went wrong"}
        )

        manager.disconnect(ws)


class TestAlertBroadcastAfterIngestion:
    """Integration test: verify alert broadcast after vitals ingestion."""

    @pytest.mark.asyncio
    async def test_vitals_ingestion_triggers_alert_broadcast(
        self,
        client,
        db_session: AsyncSession,
    ):
        """After vitals ingestion that exceeds thresholds, alerts should be
        broadcast to connected WebSocket clients via the manager."""
        # Setup: patient + threshold config
        await create_test_patient(
            db_session, mpi_id="MPI-WS-001", tenant_id="austa", unit="ICU"
        )
        await create_threshold_for_test(
            db_session, score_type="MEWS", watch=1, urgent=3, critical=5
        )
        await create_threshold_for_test(
            db_session, score_type="NEWS2", watch=1, urgent=3, critical=5
        )

        # Set up a WebSocket manager with a mock client connected
        manager = WebSocketManager()
        set_websocket_manager(manager)
        mock_ws = _make_mock_websocket()
        await manager.connect(mock_ws)

        # Send vitals that will trigger a high MEWS score (HR 130, SBP 90,
        # RR 28, Temp 38.5, AVPU=V -> MEWS=5 or so)
        vitals_payload = {
            "mpi_id": "MPI-WS-001",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "heart_rate": 130,
            "systolic_bp": 90,
            "respiratory_rate": 28,
            "temperature": 38.5,
            "avpu": "V",
            "spo2": 90,
            "supplemental_o2": True,
        }

        response = await client.post("/api/v1/vitals", json=vitals_payload)
        assert response.status_code in (200, 201)

        # Verify that the WebSocket client received at least one alert
        # (MEWS score should be high enough to trigger at watch level)
        assert mock_ws.send_json.call_count >= 1, (
            f"Expected at least 1 alert broadcast, got "
            f"{mock_ws.send_json.call_count}"
        )

        # Verify alert structure
        first_call = mock_ws.send_json.call_args_list[0]
        alert_data = first_call[0][0]
        assert alert_data["type"] == "alert"
        assert alert_data["mpi_id"] == "MPI-WS-001"
        assert alert_data["severity"] in ("watch", "urgent", "critical")
        assert alert_data["status"] == "active"
        assert alert_data["id"] is not None

        # Cleanup
        manager.disconnect(mock_ws)
        reset_websocket_manager()

    @pytest.mark.asyncio
    async def test_alert_only_for_subscribed_patient(
        self,
        client,
        db_session: AsyncSession,
    ):
        """When a client subscribes to a specific patient, they should only
        receive alerts for that patient after ingestion."""
        # Setup two patients
        await create_test_patient(
            db_session, mpi_id="MPI-WS-SUB", tenant_id="austa", unit="ICU"
        )
        await create_test_patient(
            db_session, mpi_id="MPI-WS-OTHER", tenant_id="austa", unit="ICU"
        )
        # Thresholds for both MEWS and NEWS2
        await create_threshold_for_test(
            db_session, score_type="MEWS", watch=1, urgent=3, critical=5
        )
        await create_threshold_for_test(
            db_session, score_type="NEWS2", watch=1, urgent=3, critical=5
        )

        # Mock WebSocket client subscribed to MPI-WS-SUB only
        manager = WebSocketManager()
        set_websocket_manager(manager)
        mock_ws = _make_mock_websocket()
        await manager.connect(mock_ws)
        await manager.subscribe(mock_ws, "MPI-WS-SUB")

        # Ingest for the subscribed patient (high vitals -> alert)
        vitals_high = {
            "mpi_id": "MPI-WS-SUB",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "heart_rate": 140,
            "systolic_bp": 80,
            "respiratory_rate": 30,
            "temperature": 39.0,
            "avpu": "V",
            "spo2": 88,
            "supplemental_o2": True,
        }
        resp1 = await client.post("/api/v1/vitals", json=vitals_high)
        assert resp1.status_code in (200, 201)

        # Should have received alerts for MPI-WS-SUB
        sub_count_before = mock_ws.send_json.call_count
        assert sub_count_before >= 1

        # Reset counter
        mock_ws.send_json.reset_mock()

        # Ingest for the OTHER patient (high vitals -> alert)
        vitals_other = {
            "mpi_id": "MPI-WS-OTHER",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "heart_rate": 140,
            "systolic_bp": 80,
            "respiratory_rate": 30,
            "temperature": 39.0,
            "avpu": "V",
            "spo2": 88,
            "supplemental_o2": True,
        }
        resp2 = await client.post("/api/v1/vitals", json=vitals_other)
        assert resp2.status_code in (200, 201)

        # Since client only subscribed to MPI-WS-SUB, should NOT receive
        # alerts for MPI-WS-OTHER
        assert mock_ws.send_json.call_count == 0, (
            f"Expected 0 alerts for unsubscribed patient, got "
            f"{mock_ws.send_json.call_count}"
        )

        # Cleanup
        manager.disconnect(mock_ws)
        reset_websocket_manager()


class TestSingletonFunctions:
    """Tests for WebSocket manager singleton functions."""

    def test_get_websocket_manager_returns_same_instance(self):
        """get_websocket_manager should return the same singleton instance."""
        reset_websocket_manager()
        m1 = get_websocket_manager()
        m2 = get_websocket_manager()
        assert m1 is m2
        reset_websocket_manager()

    def test_set_websocket_manager_replaces_instance(self):
        """set_websocket_manager should replace the singleton."""
        reset_websocket_manager()
        custom = WebSocketManager()
        set_websocket_manager(custom)
        assert get_websocket_manager() is custom
        reset_websocket_manager()

    def test_reset_websocket_manager_clears_instance(self):
        """reset_websocket_manager should clear the singleton."""
        reset_websocket_manager()
        _ = get_websocket_manager()  # creates one
        assert get_websocket_manager() is not None
        reset_websocket_manager()
        # After reset, a new instance should be created
        new_mgr = get_websocket_manager()
        assert new_mgr is not None
        reset_websocket_manager()


# ── Test helpers ────────────────────────────────────────────────────────────

def _make_alert(
    mpi_id: str = "MPI-TEST",
    severity: str = "urgent",
    alert_id: int = 1,
) -> dict:
    """Create a test alert dictionary matching the broadcast format."""
    return {
        "type": "alert",
        "id": alert_id,
        "mpi_id": mpi_id,
        "severity": severity,
        "status": "active",
        "title": f"Test Alert for {mpi_id}",
        "body": "Test alert body",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
