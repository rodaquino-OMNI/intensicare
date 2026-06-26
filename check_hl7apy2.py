import hl7apy.parser

msg_str = "MSH|^~\\&|PHILIPS_MON|ICU||INTENSICARE|20260626143000||ORU^R01|MSG-00001|P|2.5|\rPID|1||MPI-00012345^^^AMH^PI||SILVA^JOAO||19800115|M"

# Try parse_message
msg = hl7apy.parser.parse_message(msg_str.replace("\\r", "\r"))
print("type:", type(msg))
print("MSH:", msg.MSH)
print("MSH[10]:", msg.MSH.MSH_10)
print("PID:", msg.PID)

# Try accessing children by index
pid = msg.PID
print("PID children:", pid.children)
for i, child in enumerate(pid.children):
    print(f"  PID.{i+1}: {child.value}")

# Try getting PID-3
print("PID-3:", pid.PID_3)
print("PID-3 children:", pid.PID_3.children)
print("PID-3 component 1:", pid.PID_3.PID_3_1)
print("PID-3.1 value:", pid.PID_3.PID_3_1.value)
