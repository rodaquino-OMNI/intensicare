import hl7apy.parser
import hl7apy.core

# Try the message class directly maybe
msg_str = "MSH|^~\\&|PHILIPS_MON|ICU||INTENSICARE|20260626143000||ORU^R01|MSG-00001|P|2.5|\rPID|1||MPI-00012345^^^AMH^PI||SILVA^JOAO||19800115|M\rOBR|1|||VITAL_SIGNS||20260626143000|\rOBX|1|NM|8867-4^HR^LN||72|bpm|"

# Try creating message with explicit segments
lines = msg_str.split("\r")
print("Lines:", lines)

# The parse function's approach
m = hl7apy.parser.parse_message(msg_str)
print("Message segments:", [s for s in dir(m) if not s.startswith('_')])
print("Has PID attr:", hasattr(m, 'PID'))

# Try iterating children
print("m.children:", m.children)
for seg in m.children:
    print(f"  {seg}: {seg.value}")

# Try parse_segments
segs = hl7apy.parser.parse_segments(msg_str)
print("parse_segments result:", segs)
for s in segs:
    print(f"  segment: {s}, value={s.value}")
    print(f"  children: {s.children}")
