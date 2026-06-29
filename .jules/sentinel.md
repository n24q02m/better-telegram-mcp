## 2025-02-27 - Fix DoS via memory exhaustion in fetch_url_safely
**Vulnerability:** fetch_url_safely used httpx.AsyncClient.get which loads the entire response into memory at once, creating a risk for Denial of Service (DoS) via Out-Of-Memory (OOM) attacks if a malicious or large file is fetched.
**Learning:** External URLs should be fetched with size limits and streaming to prevent memory exhaustion, as even validated internal IPs/URLs can return massive payloads.
**Prevention:** Always use httpx.stream and iterate over chunks (`aiter_bytes`) while enforcing a strict `max_size` limit on the accumulated data and checking the Content-Length header.
## 2025-02-24 - Cryptographically secure token generation
**Vulnerability:** Use of `os.urandom(32).hex()` for secret token generation.
**Learning:** While `os.urandom` is cryptographically secure, using the explicit `secrets` module (e.g. `secrets.token_hex(32)`) conveys a clearer security intent, is less prone to misuse, and aligns with modern Python security best practices.
**Prevention:** Use `secrets.token_hex()` or `secrets.token_urlsafe()` instead of raw `os.urandom` where appropriate.

## $(date +%Y-%m-%d) - Weak Master Secret Generation Fix
**Vulnerability:** The master encryption secret was generated using raw bytes from `urandom` (via `secrets.token_hex(32)`) and stored directly, which is a weaker pattern than using a Key Derivation Function (KDF) with high iteration counts to harden the secret against offline brute-force attacks if the storage medium is compromised.
**Learning:** Using raw entropy for persistent master keys misses the "work factor" benefits provided by KDFs like PBKDF2. A direct hex storage also makes it harder to rotate or update algorithms without breaking existing deployments.
**Prevention:** Always use a standard KDF (e.g., PBKDF2-HMAC-SHA256 with >=600,000 iterations) to derive operational secrets from a high-entropy seed and a unique salt. Implement version-prefixed storage formats (e.g., `v2:...`) from the start to allow for graceful migrations and backward compatibility.
