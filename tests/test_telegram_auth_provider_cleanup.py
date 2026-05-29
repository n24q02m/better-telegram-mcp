from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from loguru import logger

from better_telegram_mcp.auth.telegram_auth_provider import TelegramAuthProvider


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture
def provider(data_dir: Path) -> TelegramAuthProvider:
    return TelegramAuthProvider(data_dir, api_id=12345, api_hash="test_hash")


async def test_shutdown_logs_pending_otp_disconnect_error(
    provider: TelegramAuthProvider, caplog: pytest.LogCaptureFixture
) -> None:
    """Should log a warning if a pending OTP backend fails to disconnect during shutdown."""
    # Propagate loguru to caplog
    handler_id = logger.add(caplog.handler, format="{message}", level="WARNING")

    try:
        mock_backend = AsyncMock()
        mock_backend.disconnect.side_effect = Exception("Disconnect failed")

        provider._pending_otps["test-bearer"] = {
            "bearer": "test-bearer",
            "backend": mock_backend,
            "phone": "+1234567890",
            "phone_code_hash": "hash",
            "session_name": "test-session",
            "created_at": time.time(),
        }

        await provider.shutdown()

        assert mock_backend.disconnect.called
        assert "test-bearer" not in provider._pending_otps

        # Verify that the warning was logged
        assert "Error disconnecting pending OTP backend test-bea" in caplog.text
    finally:
        logger.remove(handler_id)


async def test_cleanup_expired_concurrently(
    provider: TelegramAuthProvider,
) -> None:
    """Disconnects should run in parallel (asyncio.gather), not serially."""
    import asyncio
    import time

    N = 5
    delay = 0.1  # seconds per disconnect

    # Register N pending OTPs with a slow mock disconnect
    disconnects: list[AsyncMock] = []

    for i in range(N):
        mock_backend = AsyncMock()

        async def slow_disconnect() -> None:
            await asyncio.sleep(delay)

        mock_backend.disconnect = AsyncMock(side_effect=slow_disconnect)
        disconnects.append(mock_backend.disconnect)

        provider._pending_otps[f"stale-{i}"] = {
            "bearer": f"stale-{i}",
            "backend": mock_backend,
            "phone": "+1234567890",
            "phone_code_hash": "hash",
            "session_name": f"test-session-{i}",
            "created_at": time.time() - 301,  # Expired
        }

    assert len(provider._pending_otps) == N

    start = time.perf_counter()
    await provider.cleanup_expired()
    elapsed = time.perf_counter() - start

    # All disconnect() were awaited.
    assert all(d.called for d in disconnects)

    # Concurrent: must be substantially less than N * delay.
    assert elapsed < N * delay * 0.7, (
        f"cleanup_expired took {elapsed:.3f}s for {N}x{delay:.3f}s tasks -- "
        "looks like disconnects ran serially instead of via asyncio.gather"
    )
    assert len(provider._pending_otps) == 0
