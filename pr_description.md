🔒 Sentinel: [HIGH] Fix SSRF validation bypass on DNS resolution failure

### 🚨 Severity
HIGH - Server-Side Request Forgery (SSRF) protection bypass.

### 💡 Vulnerability
The `validate_url` function in `src/better_telegram_mcp/backends/security.py` relies on DNS resolution (`socket.getaddrinfo`) to check if a provided hostname resolves to an internal or private IP address. However, if the DNS resolution failed (raising an `OSError`), the function caught the exception and silently passed (`pass`). This "fail-open" behavior allowed attackers to bypass the SSRF protection entirely by providing hostnames that deliberately fail to resolve at the time of validation but might resolve later, or by exploiting differences in how the validation function and the underlying connection library handle malformed URLs/hostnames.

### 🎯 Impact
An attacker could bypass the internal network IP checks and potentially force the application to make HTTP requests to unauthorized internal services or local endpoints, leading to information disclosure or further exploitation within the internal network.

### 🔧 Fix
Modified the `try...except OSError` block in `validate_url` to fail closed. Now, if DNS resolution fails, it explicitly raises a `SecurityError("Failed to resolve hostname...")`, completely preventing the validation from passing.

### ✅ Verification
- Wrote a new unit test `test_dns_resolution_failure_blocks` in `tests/test_backends/test_security.py` that mocks `socket.getaddrinfo` to raise an `OSError` and asserts that `validate_url` correctly raises a `SecurityError`.
- Ran the full test suite (`uv run pytest`) and confirmed all tests pass.
- Ensured formatting (`uv run ruff format .`) and linting (`uv run ruff check .`) pass.
