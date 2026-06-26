import hl7apy.parser

# Original message with actual carriage returns
msg_str = "MSH|^~\\&|PHILIPS_MON|ICU||INTENSICARE|20260626143000||ORU^R01|MSG-00001|P|2.5|\rPID|1||MPI-00012345^^^AMH^PI||SILVA^JOAO||19800115|M\rOBR|1|||VITAL_SIGNS||20260626143000|\rOBX|1|NM|8867-4^HR^LN||72|bpm|\rOBX|2|NM|9279-1^RR^LN||16|rpm|"

msg = hl7apy.parser.parse_message(msg_str)
print("type:", type(msg))
print("MSH:", msg.MSH)
print("MSH[10]:", msg.MSH.MSH_10)
print("message control id value:", msg.MSH.MSH_10.value)

# PID
pid = msg.PID
print("PID:", pid)
for i, child in enumerate(pid.children):
    print(f"  PID.{i+1}: {child.value}")

# PID-3
pid3 = pid.PID_3
print("PID-3:", pid3)
for j, sub in enumerate(pid3.children):
    print(f"  PID-3.{j+1}: {sub.value}")

# OBX
obx_list = msg.OBX
print("OBX count:", len(obx_list))
for i, obx in enumerate(obx_list):
    print(f"  OBX[{i}].OBX_3: {obx.OBX_3.value}")
    print(f"    OBX_3.1: {obx.OBX_3.OBX_3_1.value}")
    print(f"    OBX_3.2: {obx.OBX_3.OBX_3_2.value}")
    print(f"  OBX[{i}].OBX_5: {obx.OBX_5.value}")
    print(f"    OBX_5.1: {obx.OBX_5.OBX_5_1.value}")
