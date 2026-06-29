## 2025-02-27 - Fix DoS via memory exhaustion in fetch_url_safely
**Vulnerability:** fetch_url_safely used httpx.AsyncClient.get which loads the entire response into memory at once, creating a risk for Denial of Service (DoS) via Out-Of-Memory (OOM) attacks if a malicious or large file is fetched.
**Learning:** External URLs should be fetched with size limits and streaming to prevent memory exhaustion, as even validated internal IPs/URLs can return massive payloads.
**Prevention:** Always use httpx.stream and iterate over chunks (`aiter_bytes`) while enforcing a strict `max_size` limit on the accumulated data and checking the Content-Length header.
## 2025-02-24 - Cryptographically secure token generation
**Vulnerability:** Use of `os.urandom(32).hex()` for secret token generation.
**Learning:** While `os.urandom` is cryptographically secure, using the explicit `secrets` module (e.g. `secrets.token_hex(32)`) conveys a clearer security intent, is less prone to misuse, and aligns with modern Python security best practices.
**Prevention:** Use `secrets.token_hex()` or `secrets.token_urlsafe()` instead of raw `os.urandom` where appropriate.
## 2026-06-29 - Improved Mode Validation Errors
**Vulnerability:** Weakly typed and uninformative mode validation errors in the base backend.
**Learning:** Inheriting custom exceptions from standard types like `ValueError` makes them more interoperable with generic error handlers while maintaining domain-specific semantics. Including context (like the current state vs. the required state) in error messages significantly reduces debugging time for users.
**Prevention:** Always provide the current state when raising mismatch errors, and ensure custom exceptions inherit from the most relevant standard library exception to respect common "catch-all" patterns.
