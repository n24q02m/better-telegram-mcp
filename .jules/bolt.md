## 2025-05-22 - DNS Cache for SSRF Validation
**Learning:** `socket.getaddrinfo` is a blocking network operation that can introduce significant latency and overhead when called frequently (e.g., during media downloads or API hits). Caching DNS results locally with a short TTL (e.g., 60s) prevents repeated network roundtrips while still allowing for IP changes.
**Action:** Implement a thread-safe (or event-loop safe) DNS cache for security-critical URL validations. Ensure the cache can be cleared manually via backend management tools.
