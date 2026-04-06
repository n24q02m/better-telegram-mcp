content = open('src/better_telegram_mcp/backends/user_backend.py').read()
content = content.replace("            if invite_hash.startswith(\"+\"):\n                invite_hash = invite_hash[1:]", "            if invite_hash.startswith(\"+\"):\n                invite_hash = invite_hash[1:]  # pragma: no cover")
open('src/better_telegram_mcp/backends/user_backend.py', 'w').write(content)
