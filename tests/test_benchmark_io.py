import asyncio
import time
from pathlib import Path

import pytest


def create_large_file(path: Path, size_mb: int):
    # Create a dummy large file (e.g., 50MB)
    with open(path, "wb") as f:
        f.write(b"0" * (size_mb * 1024 * 1024))


async def simulate_concurrent_requests(
    path: Path, use_async: bool, num_requests: int = 10
):
    async def read_file():
        if use_async:
            return await asyncio.to_thread(path.read_bytes)
        else:
            with open(path, "rb") as f:
                return f.read()

    start = time.perf_counter()
    # Run requests concurrently
    tasks = [read_file() for _ in range(num_requests)]
    await asyncio.gather(*tasks)
    return time.perf_counter() - start


@pytest.mark.asyncio
async def test_io_benchmark(tmp_path):
    # 50 MB file
    test_file = tmp_path / "large_test_file.bin"
    create_large_file(test_file, 50)

    # Warmup
    await simulate_concurrent_requests(test_file, use_async=False, num_requests=1)
    await simulate_concurrent_requests(test_file, use_async=True, num_requests=1)

    print("\n--- Benchmark: Reading 50MB file 20 times concurrently ---")

    sync_time = await simulate_concurrent_requests(
        test_file, use_async=False, num_requests=20
    )
    print(f"Sync (blocking) read time: {sync_time:.4f} seconds")

    async_time = await simulate_concurrent_requests(
        test_file, use_async=True, num_requests=20
    )
    print(f"Async (to_thread) read time: {async_time:.4f} seconds")

    print(f"Speedup: {sync_time / async_time:.2f}x")
