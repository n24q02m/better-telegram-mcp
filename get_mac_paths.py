import sys
from pathlib import Path
print(sys.platform)
print(Path("/etc/passwd").resolve())
print(Path("/var/spool").resolve())
