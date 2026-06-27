## 2025-02-27 - Fix DoS via memory exhaustion in fetch_url_safely
**Vulnerability:** fetch_url_safely used httpx.AsyncClient.get which loads the entire response into memory at once, creating a risk for Denial of Service (DoS) via Out-Of-Memory (OOM) attacks if a malicious or large file is fetched.
**Learning:** External URLs should be fetched with size limits and streaming to prevent memory exhaustion, as even validated internal IPs/URLs can return massive payloads.
**Prevention:** Always use httpx.stream and iterate over chunks (`aiter_bytes`) while enforcing a strict `max_size` limit on the accumulated data and checking the Content-Length header.
## 2025-02-28 - Avoid os.urandom for secrets
**Vulnerability:** Use of `os.urandom(32).hex()` for cryptographic token generation instead of the modern Python `secrets` module.
**Learning:** While `os.urandom` is cryptographically secure, the standard library explicitly provides the `secrets` module (since Python 3.6) as the idiomatic and highly-auditable way to generate security-sensitive tokens, passwords, and API keys. Using `secrets` communicates security intent far better to code reviewers and static analysis tools.
**Prevention:** Whenever you need to generate secure random numbers or tokens (e.g. session keys, CSRF tokens, API tokens), import the `secrets` module and use `secrets.token_hex()`, `secrets.token_urlsafe()`, or `secrets.token_bytes()` instead of `os.urandom()` or `random()`.
