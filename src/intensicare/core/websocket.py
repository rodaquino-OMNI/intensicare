"""WebSocket manager for real-time alert broadcasting.

Provides:
- Connection lifecycle management (connect/disconnect)
- Patient-specific subscription filtering
- Broadcast alerts to connected clients
"""

from __future__ import annotations

import json
import logging
from typing import Any

from starlette.websockets import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and broadcasts alerts in real time.

    Supports per-connection patient_id subscription filtering so that
    clients only receive alerts for the patients they care about.
    """

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._subscriptions: dict[WebSocket, set[str]] = {}

    @property
    def active_connections(self) -> int:
        """Number of currently active WebSocket connections."""
        return len(self._connections)

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection and register it."""
        await websocket.accept()
        self._connections.append(websocket)
        self._subscriptions[websocket] = set()
        logger.info(
            "WebSocket client connected (total: %d)", len(self._connections)
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection and its subscriptions."""
        if websocket in self._connections:
            self._connections.remove(websocket)
        self._subscriptions.pop(websocket, None)
        logger.info(
            "WebSocket client disconnected (total: %d)", len(self._connections)
        )

    async def subscribe(self, websocket: WebSocket, patient_id: str) -> None:
        """Subscribe a connection to alerts for a specific patient."""
        if websocket in self._subscriptions:
            self._subscriptions[websocket].add(patient_id)
            logger.debug("WebSocket subscribed to patient %s", patient_id)

    async def unsubscribe(self, websocket: WebSocket, patient_id: str) -> None:
        """Unsubscribe a connection from alerts for a specific patient."""
        if websocket in self._subscriptions:
            self._subscriptions[websocket].discard(patient_id)
            logger.debug("WebSocket unsubscribed from patient %s", patient_id)

    async def broadcast_alert(self, alert_data: dict[str, Any]) -> None:
        """Broadcast an alert to relevant connected clients.

        If a client has no patient_id subscriptions, it receives all alerts.
        If a client has subscriptions, it only receives alerts matching
        those patient_ids.
        """
        disconnected: list[WebSocket] = []

        for ws in self._connections:
            try:
                subscribed_ids = self._subscriptions.get(ws, set())
                mpi_id = alert_data.get("mpi_id")

                # If no subscriptions defined, broadcast all.
                # If subscriptions exist, only send to matching patients.
                if not subscribed_ids or mpi_id in subscribed_ids:
                    await ws.send_json(alert_data)
            except Exception:
                disconnected.append(ws)

        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws)

    async def send_error(
        self, websocket: WebSocket, message: str
    ) -> None:
        """Send an error message to a specific WebSocket client."""
        try:
            await websocket.send_json({"type": "error", "message": message})
        except Exception:
            self.disconnect(websocket)


# Module-level singleton — matches the Redis/engine pattern
_manager: WebSocketManager | None = None


def get_websocket_manager() -> WebSocketManager:
    """Get or create the global WebSocket manager singleton."""
    global _manager
    if _manager is None:
        _manager = WebSocketManager()
    return _manager


def set_websocket_manager(manager: WebSocketManager) -> None:
    """Set a specific WebSocket manager instance (useful for testing)."""
    global _manager
    _manager = manager


def reset_websocket_manager() -> None:
    """Reset the WebSocket manager (useful for testing)."""
    global _manager
    _manager = None
