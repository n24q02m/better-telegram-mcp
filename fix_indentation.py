import re

with open('src/better_telegram_mcp/credential_state.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    new_lines.append(line)
    if 'except Exception as e:' in line and i + 1 < len(lines):
        next_line = lines[i+1]
        if 'logger.debug' in next_line and not next_line.startswith('            '):
            # Calculate required indentation
            indent = line[:line.find('except')] + '    '
            new_lines[-1] = line
            lines[i+1] = indent + next_line.lstrip()

with open('src/better_telegram_mcp/credential_state.py', 'w') as f:
    f.writelines(new_lines)
