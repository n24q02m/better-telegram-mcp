import sys

with open('src/better_telegram_mcp/auth/telegram_auth_provider.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if 'logger.info("Registered user session: {}", info["session_name"][:8])' in line:
        line = line.replace('info["session_name"]', 'info.session_name')
    new_lines.append(line)

with open('src/better_telegram_mcp/auth/telegram_auth_provider.py', 'w') as f:
    f.writelines(new_lines)
