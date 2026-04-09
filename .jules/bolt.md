## 2024-05-19 - Offload synchronous PerUserSessionStore operations to threads
**Learning:** Synchronous file I/O and CPU-intensive cryptographic operations (like AES-GCM/PBKDF2) in `PerUserSessionStore` and `CredentialStore` block the main event loop if called directly in an asynchronous context (e.g., Starlette or FastMCP request handlers).
**Action:** Always wrap `store.load`, `store.store`, `store.load_all`, and `store.delete` in `await asyncio.to_thread(...)` when invoked from `async def` functions to prevent blocking the async runtime.
