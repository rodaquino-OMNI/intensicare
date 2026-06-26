"""
MLLP Listener — Async TCP server that receives HL7 v2 ORU-R01 messages.

Listens on port 2575, handles MLLP framing (VT=0x0B start, FS=0x1C+CR=0x0D end),
parses HL7 with hl7apy, extracts vital signs from OBR/OBX segments, and forwards
them as JSON to the Intensicare API.

Usage:
    python -m intensicare.mllp_listener [--host 0.0.0.0] [--port 2575] \
        [--api-url http://api:8000/api/v1]

MLLP framing:
    <VT> HL7 message <FS><CR>
    VT  = 0x0B (vertical tab)
    FS  = 0x1C (file separator)
    CR  = 0x0D (carriage return)

Idempotency is guaranteed via X-Idempotency-Key header using MSH-10
(Message Control ID).
"""

from __future__ import annotations

import asyncio
import logging
import struct
from datetime import datetime, timezone
from typing import Any

import httpx
import hl7apy  # type: ignore[import-untyped]
from hl7apy.core import Message  # type: ignore[import-untyped]

# ---------------------------------------------------------------------------
# MLLP Protocol Constants
# ---------------------------------------------------------------------------
VT: bytes = b"\x0b"  # Vertical Tab — message start
FS: bytes = b"\x1c"  # File Separator — segment/frame end
CR: bytes = b"\x0d"  # Carriage Return — final frame terminator
MLLP_END: bytes = FS + CR  # MLLP frame terminator

# ---------------------------------------------------------------------------
# HL7 Segment / Field Constants
# ---------------------------------------------------------------------------
SEG_MSH = "MSH"
SEG_PID = "PID"
SEG_OBR = "OBR"
SEG_OBX = "OBX"

# ---------------------------------------------------------------------------
# LOINC → Vital Sign Field Mapping
# ---------------------------------------------------------------------------
LOINC_VITAL_MAP: dict[str, str] = {
    "8867-4": "heart_rate",        # Heart rate (bpm)
    "8480-6": "systolic_bp",       # Systolic blood pressure (mmHg)
    "8462-4": "diastolic_bp",      # Diastolic blood pressure (mmHg)
    "8310-5": "temperature",       # Body temperature (°C)
    "2708-6": "spo2",              # Oxygen saturation (%)
    "59408-5": "spo2",             # Oxygen saturation in arterial blood (%)
    "9279-1": "respiratory_rate",  # Respiratory rate (rpm)
    "11488-4": "avpu",             # AVPU level of consciousness
}

# Alternative identifier mappings (used when OBX-3 doesn't carry LOINC)
ALT_ID_MAP: dict[str, str] = {
    "PULSE": "heart_rate",
    "PULS": "heart_rate",
    "HR": "heart_rate",
    "HEART_RATE": "heart_rate",
    "SBP": "systolic_bp",
    "SYS": "systolic_bp",
    "SYSTOLIC": "systolic_bp",
    "DBP": "diastolic_bp",
    "DIA": "diastolic_bp",
    "DIASTOLIC": "diastolic_bp",
    "TEMP": "temperature",
    "TEMPERATURE": "temperature",
    "SPO2": "spo2",
    "O2SAT": "spo2",
    "O2_SAT": "spo2",
    "SAT": "spo2",
    "RR": "respiratory_rate",
    "RESP": "respiratory_rate",
    "RESP_RATE": "respiratory_rate",
    "RESPIRATORY_RATE": "respiratory_rate",
    "AVPU": "avpu",
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("intensicare.mllp_listener")
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


# ---------------------------------------------------------------------------
# HL7 Parsing Utilities
# ---------------------------------------------------------------------------

def _safe_get_segment(msg: Message, segment_name: str, index: int = 0) -> Any:
    """Safely retrieve a segment from an hl7apy Message.

    Returns the segment object or None if not present.
    """
    try:
        segments = getattr(msg, segment_name)
        if isinstance(segments, list):
            if index < len(segments):
                return segments[index]
            return None
        return segments
    except AttributeError:
        return None


def _safe_field(segment: Any, field_idx: int, sub_idx: int = 1) -> str | None:
    """Safely extract a field value from an hl7apy segment."""
    if segment is None:
        return None
    try:
        val = str(segment.children[field_idx - 1].children[sub_idx - 1].value)
        val = val.strip()
        return val if val else None
    except (IndexError, AttributeError):
        return None


def _parse_timestamp(raw: str | None) -> datetime | None:
    """Parse an HL7 timestamp (YYYYMMDDHHMMSS[.SSSS][+/-ZZZZ]) to UTC datetime."""
    if raw is None or len(raw) < 8:
        return None

    import re

    # Strip timezone offset for naive parsing; we'll reapply if present.
    tz_match = re.search(r"([+\-]\d{4})$", raw)
    tz_offset: int = 0
    clean = raw
    if tz_match:
        tz_str = tz_match.group(0)
        clean = raw[: tz_match.start()]
        sign = 1 if tz_str[0] == "+" else -1
        tz_offset = sign * (int(tz_str[1:3]) * 3600 + int(tz_str[3:5]) * 60)

    # Parse the body
    formats = [
        "%Y%m%d%H%M%S.%f",
        "%Y%m%d%H%M%S",
        "%Y%m%d%H%M",
        "%Y%m%d%H",
        "%Y%m%d",
    ]
    dt: datetime | None = None
    for fmt in formats:
        try:
            dt = datetime.strptime(clean, fmt)
            break
        except ValueError:
            continue

    if dt is None:
        return None

    # Apply timezone
    from datetime import timedelta

    return dt.replace(tzinfo=timezone.utc) - timedelta(seconds=tz_offset)


def _parse_obx_value(raw: str | None, field_name: str) -> Any:
    """Parse an OBX-5 observation value into the appropriate Python type."""
    if raw is None or raw == "":
        return None

    int_fields = {"heart_rate", "systolic_bp", "diastolic_bp", "spo2", "respiratory_rate"}
    float_fields = {"temperature"}
    str_fields = {"avpu"}

    if field_name in int_fields:
        try:
            return int(float(raw))
        except (ValueError, TypeError):
            logger.warning("Failed to parse int value %r for field %s", raw, field_name)
            return None

    if field_name in float_fields:
        try:
            return float(raw)
        except (ValueError, TypeError):
            logger.warning("Failed to parse float value %r for field %s", raw, field_name)
            return None

    if field_name in str_fields:
        val = raw.strip().upper()
        if val in ("A", "V", "P", "U"):
            return val
        return None

    return raw


def _map_obx3_to_field(identifier: str, text: str | None = None) -> str | None:
    """Map an OBX-3 observation identifier + optional text to a vital sign field name."""
    # 1. Exact LOINC code match
    if identifier in LOINC_VITAL_MAP:
        return LOINC_VITAL_MAP[identifier]

    # 2. Alternative identifier match (case-insensitive)
    upper_id = identifier.upper().strip()
    if upper_id in ALT_ID_MAP:
        return ALT_ID_MAP[upper_id]

    # 3. Try text field
    if text:
        upper_text = text.upper().strip()
        if upper_text in ALT_ID_MAP:
            return ALT_ID_MAP[upper_text]

    return None


def parse_oru_r01(message_str: str) -> dict[str, Any] | None:
    """Parse an HL7 ORU-R01 message and extract patient ID + vital signs.

    Args:
        message_str: Raw HL7 message string (with \r or \r\n segment separators).

    Returns:
        A dict with 'mpi_id', 'recorded_at', and vital sign fields,
        or None if parsing fails.
    """
    try:
        msg = hl7apy.loads(message_str.replace("\\r", "\r"))
    except Exception as exc:
        logger.error("Failed to parse HL7 message: %s", exc)
        return None

    # --- Extract MSH-10 (Message Control ID → Idempotency Key) ---
    msh = _safe_get_segment(msg, SEG_MSH)
    idempotency_key = _safe_field(msh, 10)  # MSH-10
    if idempotency_key is None:
        logger.warning("MSH-10 (Message Control ID) is missing; cannot guarantee idempotency")

    # --- Extract MSH-7 (Message DateTime) as fallback ---
    msh_timestamp = _safe_field(msh, 7)

    # --- Extract PID-3 (Patient ID) ---
    pid = _safe_get_segment(msg, SEG_PID)
    mpi_id = _safe_field(pid, 3)  # PID-3 first component (patient identifier)
    if mpi_id is None:
        logger.error("PID-3 (Patient Identifier) is missing; cannot process message")
        return None

    # --- Extract OBR-7 (Observation DateTime) for recorded_at ---
    obr = _safe_get_segment(msg, SEG_OBR, 0)
    obr_timestamp = _safe_field(obr, 7)  # OBR-7

    # Use OBR-7, fall back to MSH-7
    recorded_at_raw = obr_timestamp or msh_timestamp
    recorded_at = _parse_timestamp(recorded_at_raw)
    if recorded_at is None:
        logger.warning("No valid observation datetime found; using current UTC time")
        recorded_at = datetime.now(timezone.utc)

    # --- Extract vital signs from OBX segments ---
    vitals: dict[str, Any] = {}

    obx_segments = []
    try:
        if hasattr(msg, SEG_OBX):
            raw_obx = msg.OBX
            obx_segments = raw_obx if isinstance(raw_obx, list) else [raw_obx]
    except AttributeError:
        pass

    for idx, obx in enumerate(obx_segments):
        # OBX-3: Observation Identifier
        obx3_id = _safe_field(obx, 3)  # OBX-3.1 (identifier)
        obx3_text = _safe_field(obx, 3, 2)  # OBX-3.2 (text)

        if obx3_id is None:
            logger.debug("OBX[%d] has no identifier (OBX-3); skipping", idx)
            continue

        # OBX-5: Observation Value
        obx5_value = _safe_field(obx, 5)  # OBX-5.1

        field_name = _map_obx3_to_field(obx3_id, obx3_text)
        if field_name is None:
            logger.debug(
                "OBX[%d]: unmapped identifier %r (text=%r); skipping",
                idx,
                obx3_id,
                obx3_text,
            )
            continue

        parsed_value = _parse_obx_value(obx5_value, field_name)
        if parsed_value is not None:
            vitals[field_name] = parsed_value
            logger.debug(
                "OBX[%d]: mapped %r → %s = %s",
                idx,
                obx3_id,
                field_name,
                parsed_value,
            )
        else:
            logger.debug(
                "OBX[%d]: could not parse value %r for field %s",
                idx,
                obx5_value,
                field_name,
            )

    if not vitals:
        logger.warning("No vital signs extracted from message (mpi_id=%s)", mpi_id)
        return None

    # Build result
    result: dict[str, Any] = {
        "mpi_id": mpi_id,
        "recorded_at": recorded_at.isoformat(),
        "idempotency_key": idempotency_key or f"msh10-missing-{mpi_id}",
        **vitals,
    }

    return result


# ---------------------------------------------------------------------------
# API Forwarder
# ---------------------------------------------------------------------------
async def forward_to_api(
    client: httpx.AsyncClient,
    api_url: str,
    vitals_data: dict[str, Any],
    idempotency_key: str,
) -> bool:
    """POST vital signs to the Intensicare API.

    Args:
        client: httpx AsyncClient instance.
        api_url: Base API URL (e.g., http://api:8000/api/v1).
        vitals_data: Dict with mpi_id, recorded_at, and vital sign fields.
        idempotency_key: MSH-10 message control ID for idempotency.

    Returns:
        True on success (HTTP 200/201/409), False on failure.
    """
    # Remove idempotency_key from vitals_data (it's a header, not body)
    body = {k: v for k, v in vitals_data.items() if k != "idempotency_key"}

    headers = {
        "Content-Type": "application/json",
        "X-Idempotency-Key": idempotency_key,
    }

    url = f"{api_url.rstrip('/')}/vitals"

    try:
        response = await client.post(url, json=body, headers=headers, timeout=15.0)
        if response.status_code in (200, 201):
            resp_json = response.json()
            logger.info(
                "Vitals forwarded successfully: mpi_id=%s, vital_id=%s, mews=%s",
                resp_json.get("mpi_id"),
                resp_json.get("id"),
                resp_json.get("mews_score"),
            )
            return True
        elif response.status_code == 409:
            logger.warning(
                "Conflict forwarding vitals for mpi_id=%s: %s",
                vitals_data.get("mpi_id"),
                response.text,
            )
            return False
        else:
            logger.error(
                "API returned %d forwarding vitals for mpi_id=%s: %s",
                response.status_code,
                vitals_data.get("mpi_id"),
                response.text,
            )
            return False
    except httpx.TimeoutException:
        logger.error("Timeout forwarding vitals for mpi_id=%s", vitals_data.get("mpi_id"))
        return False
    except httpx.ConnectError:
        logger.error("Connection refused to API at %s", url)
        return False
    except Exception as exc:
        logger.error(
            "Unexpected error forwarding vitals for mpi_id=%s: %s",
            vitals_data.get("mpi_id"),
            exc,
        )
        return False


# ---------------------------------------------------------------------------
# MLLP TCP Server
# ---------------------------------------------------------------------------

class MLLPProtocol(asyncio.Protocol):
    """Async protocol handler for MLLP-framed HL7 messages."""

    def __init__(
        self,
        api_url: str,
        httpx_client: httpx.AsyncClient,
    ) -> None:
        super().__init__()
        self.api_url = api_url
        self.http_client = httpx_client
        self.buffer: bytearray = bytearray()

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport: asyncio.Transport = transport  # type: ignore[assignment]
        peer = transport.get_extra_info("peername")
        logger.info("MLLP connection from %s:%s", *peer)

    def data_received(self, data: bytes) -> None:
        """Buffer incoming data and extract complete MLLP frames."""
        self.buffer.extend(data)

        while True:
            # Look for MLLP frame delimiters
            vt_idx = self.buffer.find(VT)
            if vt_idx == -1:
                # No start marker found; discard junk before next VT
                self.buffer.clear()
                return

            end_idx = self.buffer.find(MLLP_END, vt_idx + 1)
            if end_idx == -1:
                # Frame not complete yet; wait for more data
                return

            # Extract complete frame
            frame_start = vt_idx + 1
            frame_end = end_idx
            hl7_bytes = bytes(self.buffer[frame_start:frame_end])

            # Remove processed data from buffer (including delimiters)
            del self.buffer[: end_idx + len(MLLP_END)]

            # Schedule message processing (non-blocking)
            hl7_str = hl7_bytes.decode("utf-8", errors="replace").strip()
            asyncio.ensure_future(self._process_message(hl7_str))

    async def _process_message(self, message_str: str) -> None:
        """Parse and forward an HL7 message."""
        logger.debug("Received HL7 message (%d chars)", len(message_str))

        # Parse
        vitals_data = parse_oru_r01(message_str)
        if vitals_data is None:
            logger.warning("Could not extract vitals from message; sending NAK")
            self._send_ack("AR")  # Application Reject
            return

        idempotency_key = vitals_data.get("idempotency_key", "no-key")

        # Forward to API
        logger.info(
            "Forwarding vitals: mpi_id=%s, fields=%s",
            vitals_data.get("mpi_id"),
            [k for k in vitals_data if k not in ("mpi_id", "recorded_at", "idempotency_key")],
        )
        success = await forward_to_api(
            self.http_client,
            self.api_url,
            vitals_data,
            idempotency_key,
        )

        if success:
            self._send_ack("AA")  # Application Accept
        else:
            self._send_ack("AE")  # Application Error

    def _send_ack(self, ack_code: str) -> None:
        """Send an MLLP-framed HL7 ACK message back to the client."""
        # Build a minimal ACK response
        ack_msg = (
            "MSH|^~\\&|||||20260626000000||ACK^ACK|ACK-0001|P|2.5|\r"
            f"MSA|{ack_code}|ACK-0001|Intensicare MLLP Listener ACK\r"
        )
        mllp_frame = VT + ack_msg.encode("ascii") + MLLP_END
        if hasattr(self, "transport") and self.transport is not None:
            self.transport.write(mllp_frame)

    def connection_lost(self, exc: Exception | None) -> None:
        if exc is not None:
            logger.error("MLLP connection lost with error: %s", exc)
        else:
            logger.info("MLLP connection closed cleanly")
        # Clear buffer to free memory
        self.buffer.clear()


async def run_mllp_listener(
    host: str = "0.0.0.0",
    port: int = 2575,
    api_url: str = "http://api:8000/api/v1",
) -> None:
    """Start the MLLP TCP listener.

    Args:
        host: Bind address.
        port: TCP port (default: 2575 — standard HL7 MLLP port).
        api_url: Intensicare API base URL for forwarding.
    """
    logger.info(
        "Starting MLLP listener on %s:%d, forwarding to %s",
        host,
        port,
        api_url,
    )

    async with httpx.AsyncClient() as http_client:
        loop = asyncio.get_running_loop()

        def protocol_factory() -> MLLPProtocol:
            return MLLPProtocol(api_url=api_url, httpx_client=http_client)

        server = await loop.create_server(
            protocol_factory,
            host=host,
            port=port,
            backlog=128,
        )

        logger.info("MLLP listener is ready and accepting connections")
        try:
            async with server:
                await server.serve_forever()
        except asyncio.CancelledError:
            logger.info("MLLP listener shutting down")
        finally:
            server.close()
            await server.wait_closed()
            logger.info("MLLP listener stopped")


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Intensicare MLLP Listener — receive HL7 v2 ORU-R01 messages",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Bind address (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=2575,
        help="TCP port (default: 2575 — standard HL7 MLLP port)",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:8000/api/v1",
        help="Intensicare API base URL (default: http://localhost:8000/api/v1)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(run_mllp_listener(args.host, args.port, args.api_url))
    except KeyboardInterrupt:
        logger.info("MLLP listener terminated by user")
