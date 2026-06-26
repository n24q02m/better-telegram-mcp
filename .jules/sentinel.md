## 2025-02-27 - Fix DoS via memory exhaustion in fetch_url_safely
**Vulnerability:** fetch_url_safely used httpx.AsyncClient.get which loads the entire response into memory at once, creating a risk for Denial of Service (DoS) via Out-Of-Memory (OOM) attacks if a malicious or large file is fetched.
**Learning:** External URLs should be fetched with size limits and streaming to prevent memory exhaustion, as even validated internal IPs/URLs can return massive payloads.
**Prevention:** Always use httpx.stream and iterate over chunks (`aiter_bytes`) while enforcing a strict `max_size` limit on the accumulated data and checking the Content-Length header.
## 2025-02-27 - Use secrets module for cryptographically secure random values
**Vulnerability:** `os.urandom().hex()` was used to generate a master server secret. While technically secure via OS entropy, it lacks explicit semantic meaning for security operations and is not the recommended standard.
**Learning:** Python's `secrets` module is the official library for generating cryptographically strong random numbers suitable for managing data such as passwords, account authentication, security tokens, and related secrets.
**Prevention:** Always use `secrets.token_hex()` or similar functions from the `secrets` module instead of `os.urandom()` directly when generating secure credentials or tokens to explicitly convey security intent and conform to best practices.
