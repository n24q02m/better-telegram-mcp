## 2025-02-28 - Fix SSRF Bypass via IPv6 Unspecified Address (`::`)
**Vulnerability:** URL validation for SSRF protection failed to block the IPv6 unspecified address (`::`), which many systems route to `localhost`, potentially bypassing IPv4-only loopback checks (`127.0.0.1`, `0.0.0.0`).
**Learning:** Checking for `0.0.0.0` or `127.0.0.0/8` is insufficient because systems with IPv6 enabled may resolve `::` locally, allowing an attacker to reach internal services.
**Prevention:** Always explicitly block `::/128` in IP network blocklists and `"::"` in static hostname bypass checks alongside `0.0.0.0` and `localhost`.

## 2025-02-27 - Fix DoS via memory exhaustion in fetch_url_safely
**Vulnerability:** fetch_url_safely used httpx.AsyncClient.get which loads the entire response into memory at once, creating a risk for Denial of Service (DoS) via Out-Of-Memory (OOM) attacks if a malicious or large file is fetched.
**Learning:** External URLs should be fetched with size limits and streaming to prevent memory exhaustion, as even validated internal IPs/URLs can return massive payloads.
**Prevention:** Always use httpx.stream and iterate over chunks (`aiter_bytes`) while enforcing a strict `max_size` limit on the accumulated data and checking the Content-Length header.
## 2025-02-24 - Cryptographically secure token generation
**Vulnerability:** Use of `os.urandom(32).hex()` for secret token generation.
**Learning:** While `os.urandom` is cryptographically secure, using the explicit `secrets` module (e.g. `secrets.token_hex(32)`) conveys a clearer security intent, is less prone to misuse, and aligns with modern Python security best practices.
**Prevention:** Use `secrets.token_hex()` or `secrets.token_urlsafe()` instead of raw `os.urandom` where appropriate.
