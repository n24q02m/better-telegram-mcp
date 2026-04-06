content = open('src/better_telegram_mcp/credential_state.py').read()
content = content.replace("  # ty: ignore[invalid-argument-type]", "")
content = content.replace("  # ty: ignore[union-attr]", "")
open('src/better_telegram_mcp/credential_state.py', 'w').write(content)
