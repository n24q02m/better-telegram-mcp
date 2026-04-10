from pathlib import Path
print(Path("/etc/passwd").resolve())
print(Path("/etc/cron.d").resolve())
