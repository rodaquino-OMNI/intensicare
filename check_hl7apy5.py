import hl7apy.parser

msg_str = "MSH|^~\\&|PHILIPS_MON|ICU||INTENSICARE|20260626143000||ORU^R01|MSG-00001|P|2.5|\rPID|1||MPI-00012345^^^AMH^PI||SILVA^JOAO||19800115|M\rOBR|1|||VITAL_SIGNS||20260626143000|\rOBX|1|NM|8867-4^HR^LN||72|bpm|\rOBX|2|NM|9279-1^RR^LN||16|rpm|"

segs = hl7apy.parser.parse_segments(msg_str)

for seg in segs:
    print(f"Segment: {seg.name}")
    for child in seg.children:
        print(f"  {child.name}: {child.value} type={child.classname}")
        # Print sub-components if any
        if hasattr(child, 'children') and child.children:
            for sub in child.children:
                print(f"    {sub.name}: {sub.value}")

# Now access specific fields
pid = [s for s in segs if s.name == 'PID'][0]
print("\nPID-3:", pid.PID_3.value)
print("  PID-3.1:", pid.PID_3.PID_3_1.value)
print("  PID-3.4:", pid.PID_3.PID_3_4.value)

# OBX
obx_list = [s for s in segs if s.name == 'OBX']
for obx in obx_list:
    print(f"\nOBX-3:", obx.OBX_3.value)
    print("  OBX-3.1:", obx.OBX_3.OBX_3_1.value)
    print("  OBX-3.2:", obx.OBX_3.OBX_3_2.value)
    print("OBX-5:", obx.OBX_5.value)
    print("  OBX-5.1:", obx.OBX_5.OBX_5_1.value)
