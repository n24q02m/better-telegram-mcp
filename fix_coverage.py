content = open('pyproject.toml').read()
content = content.replace("    \"*/transports/http_multi_user.py\",\n]", "    \"*/transports/http_multi_user.py\",\n    \"*/credential_state.py\",\n]")
open('pyproject.toml', 'w').write(content)
