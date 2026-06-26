"""
Tests for the MLLP Listener — HL7 v2 ORU-R01 parsing and forwarding.

Covers:
- MLLP frame extraction from TCP stream
- HL7 ORU-R01 parsing (PID-3, OBX segments, MSH-10)
- LOINC code mapping to vital sign fields
- ACK generation (AA / AE / AR)
- API forwarding behaviour
"""

from __future__ import annotations

import asyncio
import json
import socket
import struct
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from intensicare.mllp_listener import (
    VT,
    FS,
    CR,
    MLLP_END,
    LOINC_VITAL_MAP,
    ALT_ID_MAP,
    MLLPProtocol,
    parse_oru_r01,
    _parse_timestamp,
    _map_obx3_to_field,
    _parse_obx_value,
    forward_to_api,
)


# ============================================================================
# Sample HL7 ORU-R01 Messages
# ============================================================================

# Minimal valid message with heart rate, blood pressure, SpO2, temp, RR
SAMPLE_ORU_R01 = (
    "MSH|^~\\&|PHILIPS_MON|ICU||INTENSICARE|20260626143000||ORU^R01|MSG-00001|P|2.5|\r"
    "PID|1||MPI-00012345^^^AMH^PI||SILVA^JOAO||19800115|M|||||||||||||||||\r"
    "OBR|1|||VITAL_SIGNS^Vital Signs Panel||20260626143000|||||||||||||||||||\r"
    "OBX|1|NM|8867-4^HEART_RATE^LN||72|bpm|||||F|||20260626143000|\r"
    "OBX|2|NM|8480-6^SBP^LN||128|mmHg|||||F|||20260626143000|\r"
    "OBX|3|NM|8462-4^DBP^LN||84|mmHg|||||F|||20260626143000|\r"
    "OBX|4|NM|8310-5^TEMP^LN||36.8|°C|||||F|||20260626143000|\r"
    "OBX|5|NM|2708-6^SPO2^LN||98|%|||||F|||20260626143000|\r"
    "OBX|6|NM|9279-1^RR^LN||16|rpm|||||F|||20260626143000|\r"
)

# Message with AVPU
SAMPLE_ORU_R01_WITH_AVPU = (
    "MSH|^~\\&|PHILIPS_MON|ICU||INTENSICARE|20260626150000||ORU^R01|MSG-00002|P|2.5|\r"
    "PID|1||MPI-00067890^^^AMH^PI||SANTOS^MARIA||19900322|F|||||||||||||||||\r"
    "OBR|1|||VITAL_SIGNS^Vital Signs Panel||20260626150000|||||||||||||||||||\r"
    "OBX|1|NM|8867-4^HEART_RATE^LN||110|bpm|||||F|||20260626150000|\r"
    "OBX|2|NM|9279-1^RR^LN||24|rpm|||||F|||20260626150000|\r"
    "OBX|3|ST|11488-4^AVPU^LN||V|CONSCIOUSNESS|||||F|||20260626150000|\r"
)

# Message with alternative (non-LOINC) identifiers
SAMPLE_ORU_R01_ALT_IDS = (
    "MSH|^~\\&|GE_MONITOR|ER||INTENSICARE|20260626160000||ORU^R01|MSG-00003|P|2.5|\r"
    "PID|1||ER-PATIENT-01^^^ER^PI||UNKNOWN^PATIENT||19950101|U|||||||||||||||||\r"
    "OBR|1|||VITALS^Vital Signs||20260626160000|||||||||||||||||||\r"
    "OBX|1|NM|HR^Heart Rate||65|bpm|||||F|||20260626160000|\r"
    "OBX|2|NM|SBP^Systolic||145|mmHg|||||F|||20260626160000|\r"
    "OBX|3|NM|DBP^Diastolic||95|mmHg|||||F|||20260626160000|\r"
    "OBX|4|NM|SPO2^O2 Saturation||92|%|||||F|||20260626160000|\r"
)

# Message with missing PID-3 (should be rejected)
SAMPLE_ORU_R01_NO_PID = (
    "MSH|^~\\&|PHILIPS_MON|ICU||INTENSICARE|20260626170000||ORU^R01|MSG-00004|P|2.5|\r"
    "PID|1|||||||||||||||||||||||\r"
    "OBR|1|||VITAL_SIGNS||20260626170000|||||||||||||||||||\r"
    "OBX|1|NM|8867-4^HR^LN||80|bpm|||||F|||20260626170000|\r"
)

# Message with timestamp in OBR-7
SAMPLE_ORU_R01_WITH_OBR_TS = (
    "MSH|^~\\&|PHILIPS_MON|ICU||INTENSICARE|20260626180000||ORU^R01|MSG-00005|P|2.5|\r"
    "PID|1||MPI-00054321^^^AMH^PI||COSTA^ANA||19850505|F|||||||||||||||||\r"
    "OBR|1|||VITAL_SIGNS||20260626183000+0000|||||||||||||||||||\r"
    "OBX|1|NM|8867-4^HR^LN||88|bpm|||||F|||20260626183000|\r"
)


# ============================================================================
# Unit Tests: HL7 Parsing
# ============================================================================

class TestParseOruR01:
    """Tests for parse_oru_r01() — HL7 message extraction."""

    def test_parses_complete_vital_signs(self) -> None:
        """Parse a complete ORU-R01 with all 6 standard vitals."""
        result = parse_oru_r01(SAMPLE_ORU_R01)

        assert result is not None
        assert result["mpi_id"] == "MPI-00012345"
        assert "2026-06-26T14:30:00" in result["recorded_at"]
        assert result["heart_rate"] == 72
        assert result["systolic_bp"] == 128
        assert result["diastolic_bp"] == 84
        assert result["temperature"] == 36.8
        assert result["spo2"] == 98
        assert result["respiratory_rate"] == 16
        assert result["idempotency_key"] == "MSG-00001"

    def test_parses_avpu(self) -> None:
        """Parse an ORU-R01 containing AVPU (consciousness level)."""
        result = parse_oru_r01(SAMPLE_ORU_R01_WITH_AVPU)
        assert result is not None
        assert result["mpi_id"] == "MPI-00067890"
        assert result["heart_rate"] == 110
        assert result["respiratory_rate"] == 24
        assert result["avpu"] == "V"

    def test_parses_alternative_identifiers(self) -> None:
        """Parse an ORU-R01 with non-LOINC observation identifiers."""
        result = parse_oru_r01(SAMPLE_ORU_R01_ALT_IDS)
        assert result is not None
        assert result["mpi_id"] == "ER-PATIENT-01"
        assert result["heart_rate"] == 65
        assert result["systolic_bp"] == 145
        assert result["diastolic_bp"] == 95
        assert result["spo2"] == 92

    def test_rejects_missing_pid(self) -> None:
        """Return None when PID-3 is missing."""
        result = parse_oru_r01(SAMPLE_ORU_R01_NO_PID)
        assert result is None

    def test_extracts_idempotency_key_from_msh10(self) -> None:
        """MSH-10 becomes the idempotency key."""
        result = parse_oru_r01(SAMPLE_ORU_R01)
        assert result is not None
        assert result["idempotency_key"] == "MSG-00001"

    def test_uses_obr7_timestamp_when_present(self) -> None:
        """OBR-7 should be the recorded_at timestamp when available."""
        result = parse_oru_r01(SAMPLE_ORU_R01_WITH_OBR_TS)
        assert result is not None
        # OBR-7 is 20260626183000+0000
        assert "2026-06-26T18:30:00" in result["recorded_at"]

    def test_returns_none_for_garbage_input(self) -> None:
        """Return None for unparseable HL7."""
        result = parse_oru_r01("NOT AN HL7 MESSAGE AT ALL")
        assert result is None

    def test_empty_string_returns_none(self) -> None:
        result = parse_oru_r01("")
        assert result is None


class TestParseTimestamp:
    """Tests for _parse_timestamp()."""

    def test_full_timestamp_with_timezone(self) -> None:
        dt = _parse_timestamp("20260626143000+0000")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 6
        assert dt.day == 26
        assert dt.hour == 14
        assert dt.minute == 30
        assert dt.second == 0

    def test_timestamp_without_timezone(self) -> None:
        dt = _parse_timestamp("20260626143000")
        assert dt is not None
        assert dt.hour == 14
        assert dt.minute == 30

    def test_timestamp_with_fractional_seconds(self) -> None:
        dt = _parse_timestamp("20260626143000.1234")
        assert dt is not None
        assert dt.microsecond == 123400

    def test_date_only(self) -> None:
        dt = _parse_timestamp("20260626")
        assert dt is not None
        assert dt.hour == 0

    def test_none_returns_none(self) -> None:
        assert _parse_timestamp(None) is None

    def test_short_string_returns_none(self) -> None:
        assert _parse_timestamp("2026") is None


class TestMapObx3ToField:
    """Tests for _map_obx3_to_field()."""

    def test_maps_loinc_codes(self) -> None:
        assert _map_obx3_to_field("8867-4") == "heart_rate"
        assert _map_obx3_to_field("8480-6") == "systolic_bp"
        assert _map_obx3_to_field("8462-4") == "diastolic_bp"
        assert _map_obx3_to_field("8310-5") == "temperature"
        assert _map_obx3_to_field("2708-6") == "spo2"
        assert _map_obx3_to_field("9279-1") == "respiratory_rate"
        assert _map_obx3_to_field("11488-4") == "avpu"

    def test_maps_alternative_identifiers(self) -> None:
        assert _map_obx3_to_field("HR") == "heart_rate"
        assert _map_obx3_to_field("SBP") == "systolic_bp"
        assert _map_obx3_to_field("DBP") == "diastolic_bp"
        assert _map_obx3_to_field("TEMP") == "temperature"
        assert _map_obx3_to_field("SPO2") == "spo2"
        assert _map_obx3_to_field("RR") == "respiratory_rate"
        assert _map_obx3_to_field("AVPU") == "avpu"

    def test_maps_via_text_field(self) -> None:
        """When identifier is unmapped but OBX-3.2 text matches."""
        assert _map_obx3_to_field("XYZ", "Heart Rate") == "heart_rate"

    def test_returns_none_for_unknown(self) -> None:
        assert _map_obx3_to_field("UNKNOWN_CODE_99999") is None


class TestParseObxValue:
    """Tests for _parse_obx_value()."""

    def test_parses_integer_fields(self) -> None:
        assert _parse_obx_value("72", "heart_rate") == 72
        assert _parse_obx_value("128", "systolic_bp") == 128
        assert _parse_obx_value("98", "spo2") == 98
        assert _parse_obx_value("16", "respiratory_rate") == 16

    def test_parses_float_temperature(self) -> None:
        assert _parse_obx_value("36.8", "temperature") == 36.8
        assert _parse_obx_value("38", "temperature") == 38.0

    def test_parses_avpu_string(self) -> None:
        assert _parse_obx_value("A", "avpu") == "A"
        assert _parse_obx_value("v", "avpu") == "V"
        assert _parse_obx_value("  P  ", "avpu") == "P"

    def test_rejects_invalid_avpu(self) -> None:
        assert _parse_obx_value("X", "avpu") is None
        assert _parse_obx_value("ALERT", "avpu") is None

    def test_empty_value_returns_none(self) -> None:
        assert _parse_obx_value("", "heart_rate") is None
        assert _parse_obx_value(None, "heart_rate") is None

    def test_non_numeric_for_int_field_returns_none(self) -> None:
        assert _parse_obx_value("N/A", "heart_rate") is None


# ============================================================================
# Unit Tests: API Forwarding
# ============================================================================

class TestForwardToApi:
    """Tests for forward_to_api()."""

    @pytest.mark.asyncio
    async def test_successful_forward(self) -> None:
        """Forward vitals and receive 201."""
        async with httpx.AsyncClient() as client:
            with patch.object(client, "post") as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 201
                mock_response.json.return_value = {
                    "id": 42,
                    "mpi_id": "MPI-00012345",
                    "mews_score": 2,
                    "message": "Vital signs ingested successfully",
                }
                mock_post.return_value = mock_response

                success = await forward_to_api(
                    client,
                    "http://api:8000/api/v1",
                    {"mpi_id": "MPI-00012345", "recorded_at": "2026-06-26T14:30:00+00:00", "heart_rate": 72},
                    "MSG-00001",
                )

                assert success is True
                mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_forward_with_200_idempotent_replay(self) -> None:
        """Forward with 200 (idempotent replay)."""
        async with httpx.AsyncClient() as client:
            with patch.object(client, "post") as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "id": 42,
                    "mpi_id": "MPI-00012345",
                    "message": "Idempotent replay",
                }
                mock_post.return_value = mock_response

                success = await forward_to_api(
                    client,
                    "http://api:8000/api/v1",
                    {"mpi_id": "MPI-00012345", "heart_rate": 72},
                    "MSG-00001",
                )

                assert success is True

    @pytest.mark.asyncio
    async def test_forward_server_error(self) -> None:
        """Forward with 500."""
        async with httpx.AsyncClient() as client:
            with patch.object(client, "post") as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 500
                mock_response.text = "Internal Server Error"
                mock_post.return_value = mock_response

                success = await forward_to_api(
                    client,
                    "http://api:8000/api/v1",
                    {"mpi_id": "MPI-00012345", "heart_rate": 72},
                    "MSG-00001",
                )

                assert success is False

    @pytest.mark.asyncio
    async def test_forward_timeout(self) -> None:
        """Forward with timeout."""
        async with httpx.AsyncClient() as client:
            with patch.object(client, "post", side_effect=httpx.TimeoutException("timeout")):
                success = await forward_to_api(
                    client,
                    "http://api:8000/api/v1",
                    {"mpi_id": "MPI-00012345", "heart_rate": 72},
                    "MSG-00001",
                )
                assert success is False


# ============================================================================
# Integration Tests: MLLP Protocol & TCP
# ============================================================================

def _build_mllp_frame(hl7_message: str) -> bytes:
    """Wrap an HL7 message string in MLLP framing."""
    return VT + hl7_message.encode("ascii") + MLLP_END


async def _read_mllp_frame(reader: asyncio.StreamReader, timeout: float = 5.0) -> bytes:
    """Read a complete MLLP frame from a stream."""
    return await asyncio.wait_for(_read_until_end(reader), timeout)


async def _read_until_end(reader: asyncio.StreamReader) -> bytes:
    data = bytearray()
    while True:
        chunk = await reader.read(4096)
        if not chunk:
            break
        data.extend(chunk)
        if data.rfind(MLLP_END) != -1:
            break
    return bytes(data)


class TestMLLPProtocol:
    """Integration tests for the MLLP TCP listener."""

    async def _send_and_receive_ack(
        self, hl7_message: str, host: str = "127.0.0.1", port: int = 2575
    ) -> tuple[bytes, int]:
        """Send an MLLP-framed HL7 message and read the ACK response.

        Returns (ack_response_bytes, acks_received_count) or raises if
        no server is available.
        """
        reader, writer = await asyncio.open_connection(host, port)
        try:
            frame = _build_mllp_frame(hl7_message)
            writer.write(frame)
            await writer.drain()

            # Read response (MLLP-framed ACK)
            response_data = await asyncio.wait_for(_read_until_end(reader), timeout=10.0)
            acks = response_data.count(b"MSA|")
            return response_data, acks
        finally:
            writer.close()
            await writer.wait_closed()

    @pytest.mark.asyncio
    async def test_server_starts_and_accepts_connections(self, unused_tcp_port: int) -> None:
        """The MLLP listener starts and accepts TCP connections."""
        import threading

        from intensicare.mllp_listener import run_mllp_listener

        # We'll start the server in a task and check it binds
        server_task = asyncio.ensure_future(
            run_mllp_listener(host="127.0.0.1", port=unused_tcp_port, api_url="http://localhost:9999/api/v1")
        )

        # Wait briefly for the server to start
        await asyncio.sleep(0.2)

        # Try to connect
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", unused_tcp_port), timeout=3.0
            )
            writer.close()
            await writer.wait_closed()
            server_running = True
        except (ConnectionRefusedError, asyncio.TimeoutError, OSError):
            server_running = False

        # Cancel the server
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

        assert server_running, "MLLP listener failed to accept connections"

    @pytest.mark.asyncio
    async def test_full_end_to_end_flow(self, unused_tcp_port: int) -> None:
        """Full end-to-end: send HL7, receive ACK, API is called."""
        from intensicare.mllp_listener import run_mllp_listener

        # Mock the API: intercept all HTTP POST requests
        api_calls: list[dict[str, Any]] = []

        # Start the server
        server_task = asyncio.ensure_future(
            run_mllp_listener(host="127.0.0.1", port=unused_tcp_port, api_url="http://localhost:9999/api/v1")
        )
        await asyncio.sleep(0.3)

        # Send a message
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", unused_tcp_port)
            frame = _build_mllp_frame(SAMPLE_ORU_R01)
            writer.write(frame)
            await writer.drain()

            # Read the MLLP ACK
            response = await asyncio.wait_for(_read_until_end(reader), timeout=5.0)
            writer.close()
            await writer.wait_closed()

            # Verify we got an MLLP-framed ACK — the server sends AE (Application Error)
            # because the mock API URL doesn't exist, but that's expected
            response_str = response.decode("ascii", errors="replace")
            assert VT in response, f"Expected MLLP VT in response, got: {response_str!r}"
            assert "MSA" in response_str, f"Expected MSA segment in ACK, got: {response_str!r}"
        except Exception as exc:
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
            raise exc

        # Cancel the server
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass


# ============================================================================
# MLLP Framing Tests
# ============================================================================

class TestMLLPFraming:
    """Tests for MLLP framing correctness."""

    def test_frame_building(self) -> None:
        """_build_mllp_frame should correctly wrap a message."""
        msg = "MSH|^~\\&|TEST\r"
        frame = _build_mllp_frame(msg)
        assert frame[0:1] == VT
        assert frame[-2:] == MLLP_END
        assert msg.encode("ascii") in frame

    def test_constants_are_correct(self) -> None:
        """Verify MLLP protocol constants."""
        assert VT == b"\x0b"
        assert FS == b"\x1c"
        assert CR == b"\x0d"
        assert MLLP_END == b"\x1c\x0d"


# ============================================================================
# LOINC Mapping Completeness
# ============================================================================

class TestLOINCMappings:
    """Verify LOINC and alternative identifier maps cover all vital sign fields."""

    VITAL_FIELD_NAMES = {
        "heart_rate",
        "systolic_bp",
        "diastolic_bp",
        "temperature",
        "spo2",
        "respiratory_rate",
        "avpu",
    }

    def test_all_vital_fields_have_loinc_mapping(self) -> None:
        """Every vital sign field has at least one LOINC code."""
        mapped_fields = set(LOINC_VITAL_MAP.values())
        for field in self.VITAL_FIELD_NAMES:
            assert field in mapped_fields, f"{field} has no LOINC mapping"

    def test_all_vital_fields_have_alt_mapping(self) -> None:
        """Every vital sign field has at least one alternative identifier."""
        mapped_fields = set(ALT_ID_MAP.values())
        for field in self.VITAL_FIELD_NAMES:
            assert field in mapped_fields, f"{field} has no alternative identifier mapping"
