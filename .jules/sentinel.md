## 2025-02-27 - Fix DoS via memory exhaustion in fetch_url_safely
**Vulnerability:** fetch_url_safely used httpx.AsyncClient.get which loads the entire response into memory at once, creating a risk for Denial of Service (DoS) via Out-Of-Memory (OOM) attacks if a malicious or large file is fetched.
**Learning:** External URLs should be fetched with size limits and streaming to prevent memory exhaustion, as even validated internal IPs/URLs can return massive payloads.
**Prevention:** Always use httpx.stream and iterate over chunks (`aiter_bytes`) while enforcing a strict `max_size` limit on the accumulated data and checking the Content-Length header.
## 2025-02-24 - Cryptographically secure token generation
**Vulnerability:** Use of `os.urandom(32).hex()` for secret token generation.
**Learning:** While `os.urandom` is cryptographically secure, using the explicit `secrets` module (e.g. `secrets.token_hex(32)`) conveys a clearer security intent, is less prone to misuse, and aligns with modern Python security best practices.
**Prevention:** Use `secrets.token_hex()` or `secrets.token_urlsafe()` instead of raw `os.urandom` where appropriate.

## 2024-05-18 - SSRF via IPv6 Unspecified Address (::)
**Vulnerability:** The URL validation logic correctly blocked the IPv4 unspecified address `0.0.0.0` but failed to block its IPv6 equivalent `::`. This allowed SSRF requests to bypass the filter and target `localhost` on systems with IPv6 enabled.
**Learning:** Hardcoded string checks (like `hostname in {"0.0.0.0"}`) and IPv4-only IP network blocks are insufficient when IPv6 is available, as attackers can use IPv6 variants (like `::`) to achieve the same routing behavior.
**Prevention:** Always include the IPv6 equivalent `::/128` (unspecified) in blocked internal networks alongside `0.0.0.0/8`, and ensure string-based early filters catch `::`.
## 2025-02-28 - Fix DoS via memory exhaustion in bot_backend download_media
**Vulnerability:** `BotBackend.download_media` used `httpx.AsyncClient.get` which loads the entire response into memory at once. If a bot is tricked into downloading a massive file, this could lead to Out-Of-Memory (OOM) Denial of Service (DoS).
**Learning:** Even internal API wrappers (like Telegram Bot API wrappers) must treat large file downloads securely, especially if the input `file_id` is passed by users (e.g. from an MCP query).
**Prevention:** Always stream media downloads using `httpx.stream`, check `Content-Length`, enforce a `max_size` limit, and iterate over the response chunks using `aiter_bytes()`. Avoid using `asyncio.to_thread` for every small chunk, relying instead on OS-level buffering to minimize overhead.
