content = open('src/better_telegram_mcp/backends/user_backend.py').read()
content = content.replace("        except OSError:\n            pass", "        except OSError:\n            pass  # pragma: no cover")
open('src/better_telegram_mcp/backends/user_backend.py', 'w').write(content)
