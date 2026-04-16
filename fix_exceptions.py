import re

with open('src/better_telegram_mcp/credential_state.py', 'r') as f:
    content = f.read()

# Fix reset_state config deletion
content = re.sub(
    r'(delete_config\(SERVER_NAME\)\n\s+)except Exception:\n\s+pass',
    r'\1except Exception as e:\n        logger.debug("Failed to delete config during reset: {}", e)',
    content
)

# Fix backend disconnects
content = re.sub(
    r'(await _step_backend\.disconnect\(\)\n\s+)except Exception:\n\s+pass',
    r'\1except Exception as e:\n            logger.debug("Failed to disconnect backend: {}", e)',
    content
)

with open('src/better_telegram_mcp/credential_state.py', 'w') as f:
    f.write(content)
