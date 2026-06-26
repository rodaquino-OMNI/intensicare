"""Quick smoke test for MLLP listener module."""
import sys
sys.path.insert(0, 'src')

from intensicare.mllp_listener import (
    parse_oru_r01, _parse_timestamp, _map_obx3_to_field, _parse_obx_value,
    VT, FS, CR, MLLP_END,
)

# --- Test sample message ---
msg = (
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

result = parse_oru_r01(msg)
assert result is not None
assert result["mpi_id"] == "MPI-00012345"
assert result["heart_rate"] == 72
assert result["systolic_bp"] == 128
assert result["diastolic_bp"] == 84
assert result["temperature"] == 36.8
assert result["spo2"] == 98
assert result["respiratory_rate"] == 16
assert result["idempotency_key"] == "MSG-00001"
print("PASS: Full vital signs parsed correctly")

# --- Test AVPU ---
msg2 = (
    "MSH|^~\\&|PHILIPS_MON|ICU||INTENSICARE|20260626150000||ORU^R01|MSG-00002|P|2.5|\r"
    "PID|1||MPI-00067890^^^AMH^PI||SANTOS^MARIA||19900322|F\r"
    "OBR|1|||VITAL_SIGNS||20260626150000|\r"
    "OBX|1|ST|11488-4^AVPU^LN||V|CONSCIOUSNESS|\r"
)
result2 = parse_oru_r01(msg2)
assert result2 is not None
assert result2["avpu"] == "V"
print("PASS: AVPU parsed correctly")

# --- Test alt IDs ---
msg3 = (
    "MSH|^~\\&|GE_MONITOR|ER||INTENSICARE|20260626160000||ORU^R01|MSG-00003|P|2.5|\r"
    "PID|1||ER-PATIENT-01^^^ER^PI||UNKNOWN^PATIENT||19950101|U\r"
    "OBR|1|||VITALS||20260626160000|\r"
    "OBX|1|NM|HR^Heart Rate||65|bpm|\r"
    "OBX|2|NM|SBP^Systolic||145|mmHg|\r"
)
result3 = parse_oru_r01(msg3)
assert result3 is not None
assert result3["heart_rate"] == 65
assert result3["systolic_bp"] == 145
print("PASS: Alternative identifiers mapped correctly")

# --- Test missing PID ---
msg4 = (
    "MSH|^~\\&|PHILIPS_MON|ICU||INTENSICARE|20260626170000||ORU^R01|MSG-00004|P|2.5|\r"
    "PID|1|\r"
    "OBR|1|||VITAL_SIGNS||20260626170000|\r"
    "OBX|1|NM|8867-4^HR^LN||80|\r"
)
result4 = parse_oru_r01(msg4)
assert result4 is None
print("PASS: Missing PID returns None")

# --- Test constants ---
assert VT == b"\x0b"
assert FS == b"\x1c"
assert CR == b"\x0d"
assert MLLP_END == b"\x1c\x0d"
print("PASS: MLLP constants correct")

# --- Test timestamp ---
dt = _parse_timestamp("20260626143000+0000")
assert dt is not None
assert dt.year == 2026 and dt.month == 6 and dt.day == 26
assert dt.hour == 14 and dt.minute == 30
print("PASS: Timestamp parsing works")

# --- Test mappings ---
assert _map_obx3_to_field("8867-4") == "heart_rate"
assert _map_obx3_to_field("HR") == "heart_rate"
assert _map_obx3_to_field("AVPU") == "avpu"
assert _map_obx3_to_field("UNKNOWN") is None
print("PASS: OBX-3 mappings correct")

# --- Test value parsing ---
assert _parse_obx_value("72", "heart_rate") == 72
assert _parse_obx_value("36.8", "temperature") == 36.8
assert _parse_obx_value("A", "avpu") == "A"
assert _parse_obx_value("X", "avpu") is None
assert _parse_obx_value("", "heart_rate") is None
print("PASS: OBX-5 value parsing correct")

print()
print("ALL SMOKE TESTS PASSED!")
