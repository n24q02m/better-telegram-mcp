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


async def test_cleanup_expired_concurrent(provider: TelegramAuthProvider) -> None:
    """Should clean up multiple expired sessions and OTPs concurrently."""
    from better_telegram_mcp.auth.per_user_session_store import SessionInfo
    from better_telegram_mcp.auth.telegram_auth_provider import _SESSION_TTL

    now = time.time()
    # 2 expired sessions
    provider._store.store(
        "exp1",
        SessionInfo(
            session_name="s1",
            mode="bot",
            bot_token="t1",
            created_at=now - _SESSION_TTL - 10,
        ),
    )
    provider._store.store(
        "exp2",
        SessionInfo(
            session_name="s2",
            mode="bot",
            bot_token="t2",
            created_at=now - _SESSION_TTL - 20,
        ),
    )
    # 1 valid session
    provider._store.store(
        "valid",
        SessionInfo(
            session_name="s3",
            mode="bot",
            bot_token="t3",
            created_at=now,
        ),
    )

    # 2 stale OTPs
    mock_backend1 = AsyncMock()
    mock_backend2 = AsyncMock()
    provider._pending_otps["otp1"] = {
        "bearer": "otp1",
        "backend": mock_backend1,
        "phone": "+1",
        "phone_code_hash": "h1",
        "session_name": "o1",
        "created_at": now - 600,
    }
    provider._pending_otps["otp2"] = {
        "bearer": "otp2",
        "backend": mock_backend2,
        "phone": "+2",
        "phone_code_hash": "h2",
        "session_name": "o2",
        "created_at": now - 700,
    }

    removed = await provider.cleanup_expired()
    assert removed == 4
    assert provider._store.load("exp1") is None
    assert provider._store.load("exp2") is None
    assert provider._store.load("valid") is not None
    assert "otp1" not in provider._pending_otps
    assert "otp2" not in provider._pending_otps
    mock_backend1.disconnect.assert_called_once()
    mock_backend2.disconnect.assert_called_once()


async def test_cleanup_expired_handles_exceptions(
    provider: TelegramAuthProvider, caplog: pytest.LogCaptureFixture
) -> None:
    """Should handle and log exceptions during cleanup without crashing."""
    from better_telegram_mcp.auth.per_user_session_store import SessionInfo
    from better_telegram_mcp.auth.telegram_auth_provider import _SESSION_TTL

    handler_id = logger.add(caplog.handler, format="{message}", level="WARNING")

    try:
        now = time.time()
        # Mock revoke_session to raise an error for one bearer
        original_revoke = provider.revoke_session

        async def mock_revoke(bearer: str) -> bool:
            if bearer == "fail":
                raise Exception("Revocation failed")
            return await original_revoke(bearer)

        provider.revoke_session = mock_revoke

        provider._store.store(
            "fail",
            SessionInfo(
                session_name="sf",
                mode="bot",
                bot_token="tf",
                created_at=now - _SESSION_TTL - 10,
            ),
        )
        provider._store.store(
            "ok",
            SessionInfo(
                session_name="so",
                mode="bot",
                bot_token="to",
                created_at=now - _SESSION_TTL - 20,
            ),
        )

        # Stale OTP that fails to disconnect
        mock_backend = AsyncMock()
        mock_backend.disconnect.side_effect = Exception("Disconnect failed")
        provider._pending_otps["otp_fail"] = {
            "bearer": "otp_fail",
            "backend": mock_backend,
            "phone": "+1",
            "phone_code_hash": "h1",
            "session_name": "of",
            "created_at": now - 600,
        }

        removed = await provider.cleanup_expired()

        # 'ok' session removed = 1
        # 'otp_fail' removed from dict = 1
        # Total = 2
        assert removed == 2
        assert "Error during session revocation: Revocation failed" in caplog.text
        assert (
            "Error disconnecting stale OTP backend otp_fail: Disconnect failed"
            in caplog.text
        )
    finally:
        logger.remove(handler_id)
