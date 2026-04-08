## 2024-04-08 - Prevent DNS Rebinding (TOCTOU) in SSRF Protection
**Vulnerability:** The `validate_url` function performed SSRF checks by resolving a hostname to its IP and verifying it, but the application then passed the original URL string to HTTP clients (`httpx`, `Telethon`). This exposed the application to a Time-of-Check to Time-of-Use (TOCTOU) / DNS Rebinding vulnerability where an attacker's DNS server could return a safe IP during the check and a private IP during the actual request.
**Learning:** Checking a domain name for SSRF without pinning the validated IP allows the underlying HTTP client to perform a second DNS resolution, effectively bypassing the security check.
**Prevention:** Always use IP pinning for SSRF protection. Resolve the hostname once, validate the resolved IP, and use the validated IP in the subsequent HTTP request while preserving the original hostname in the `Host` header.
## 2024-04-08 - Prevent Rate Limiting Bypass via IP Spoofing
**Vulnerability:** The `AuthServer` authentication endpoints relied on `cf-connecting-ip` and `x-forwarded-for` HTTP headers to identify the client IP. An attacker could trivially inject these headers to spoof their IP address, thereby bypassing rate limits on sensitive OTP requests.
**Learning:** Application-layer trust of reverse proxy headers without validating the connection is arriving from a trusted proxy allows arbitrary IP spoofing.
**Prevention:** Strictly extract the socket IP directly via `request.client.host` and ignore proxy headers unless a verified proxy topology is explicitly configured.
