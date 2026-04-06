content = open('src/better_telegram_mcp/backends/user_backend.py').read()
content = content.replace("        except OSError:\n            pass  # Windows may not support this or file already exists", "        except OSError:\n            pass  # Windows may not support this or file already exists\n            # pragma: no cover")
open('src/better_telegram_mcp/backends/user_backend.py', 'w').write(content)
