content = open('src/better_telegram_mcp/backends/user_backend.py').read()
content = content.replace("            try:\n                os.chmod(session_file, 0o600)\n            except OSError:\n                pass  # pragma: no cover", "            try:\n                os.chmod(session_file, 0o600)\n            except OSError:\n                pass")
open('src/better_telegram_mcp/backends/user_backend.py', 'w').write(content)
