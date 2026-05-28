from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from loguru import logger

from better_telegram_mcp.auth.per_user_session_store import SessionInfo
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


async def test_cleanup_expired_sessions_and_otps(
    provider: TelegramAuthProvider,
) -> None:
    """Verify that cleanup_expired correctly identifies and removes expired sessions and stale OTPs."""
    now = time.time()

    # 1. Setup expired and non-expired sessions
    expired_info = SessionInfo(
        session_name="expired",
        mode="user",
        phone="+111",
        created_at=now - (40 * 24 * 60 * 60),
    )
    valid_info = SessionInfo(
        session_name="valid", mode="user", phone="+222", created_at=now
    )

    provider._store.load_all = MagicMock(
        return_value={"expired-bearer": expired_info, "valid-bearer": valid_info}
    )

    # Mock revoke_session
    provider.revoke_session = AsyncMock(return_value=True)

    # 2. Setup stale and non-stale pending OTPs
    stale_backend = AsyncMock()
    valid_backend = AsyncMock()

    provider._pending_otps["stale-otp"] = {
        "bearer": "stale-otp",
        "backend": stale_backend,
        "phone": "+333",
        "phone_code_hash": "hash1",
        "session_name": "s1",
        "created_at": now - 600,  # 10 min ago
    }
    provider._pending_otps["valid-otp"] = {
        "bearer": "valid-otp",
        "backend": valid_backend,
        "phone": "+444",
        "phone_code_hash": "hash2",
        "session_name": "s2",
        "created_at": now,
    }

    # 3. Run cleanup
    removed_count = await provider.cleanup_expired()

    # 4. Verify results
    # 1 expired session + 1 stale OTP
    assert removed_count == 2
    provider.revoke_session.assert_called_once_with("expired-bearer")
    stale_backend.disconnect.assert_called_once()
    valid_backend.disconnect.assert_not_called()

    assert "stale-otp" not in provider._pending_otps
    assert "valid-otp" in provider._pending_otps
