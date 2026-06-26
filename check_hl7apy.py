import hl7apy
print(dir(hl7apy))
print("---")
# Check if there's a parser module
import hl7apy.parser
print(dir(hl7apy.parser))
print("---")
# Check core
from hl7apy import core
print(dir(core))
