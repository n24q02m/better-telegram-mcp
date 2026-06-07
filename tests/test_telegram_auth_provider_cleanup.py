from __future__ import annotations

import asyncio
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


async def test_cleanup_expired_sessions_concurrently(
    provider: TelegramAuthProvider,
) -> None:
    """Should remove multiple expired sessions concurrently."""
    from better_telegram_mcp.auth.per_user_session_store import SessionInfo
    from better_telegram_mcp.auth.telegram_auth_provider import _SESSION_TTL

    # Store multiple expired sessions
    now = time.time()
    for i in range(5):
        provider._store.store(
            f"expired-{i}",
            SessionInfo(
                session_name=f"old-{i}",
                mode="bot",
                bot_token=f"t{i}",
                created_at=now - _SESSION_TTL - 1,
            ),
        )

    # Store a valid session
    provider._store.store(
        "valid",
        SessionInfo(
            session_name="new",
            mode="bot",
            bot_token="t-valid",
            created_at=now,
        ),
    )

    removed = await provider.cleanup_expired()
    assert removed == 5
    for i in range(5):
        assert provider._store.load(f"expired-{i}") is None
    assert provider._store.load("valid") is not None


async def test_cleanup_expired_sessions_gather_called(
    provider: TelegramAuthProvider,
) -> None:
    """Verify that asyncio.gather is used for revoking sessions."""
    from unittest.mock import patch

    from better_telegram_mcp.auth.per_user_session_store import SessionInfo
    from better_telegram_mcp.auth.telegram_auth_provider import _SESSION_TTL

    now = time.time()
    for i in range(3):
        provider._store.store(
            f"expired-{i}",
            SessionInfo(
                session_name=f"old-{i}",
                mode="bot",
                bot_token=f"t{i}",
                created_at=now - _SESSION_TTL - 1,
            ),
        )

    with patch("asyncio.gather", wraps=asyncio.gather) as mock_gather:
        removed = await provider.cleanup_expired()
        assert removed == 3
        assert mock_gather.called
