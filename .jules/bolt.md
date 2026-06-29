## 2025-06-29 - Parallelizing N+1 KV Store Queries
**Learning:** Sequential KV reads involving CPU-heavy PBKDF2 key derivations (600k iterations) are a major bottleneck in load_all operations. Parallelization via ThreadPoolExecutor effectively overlaps network I/O and utilizes multiple cores for cryptography.
**Action:** Always prefer parallelizing independent KV operations when bulk APIs are unavailable and cryptographic operations are involved.
