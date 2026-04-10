with open("src/better_telegram_mcp/backends/security.py", "r") as f:
    data = f.read()

# Add macOS equivalents to _blocked_prefixes
data = data.replace(
    '"/etc/",',
    '"/etc/",\n        "/private/etc/",'
).replace(
    '"/var/run/",',
    '"/var/run/",\n        "/private/var/run/",'
).replace(
    '"/var/log/",',
    '"/var/log/",\n        "/private/var/log/",'
).replace(
    '"/var/spool/",',
    '"/var/spool/",\n        "/private/var/spool/",'
)

with open("src/better_telegram_mcp/backends/security.py", "w") as f:
    f.write(data)
