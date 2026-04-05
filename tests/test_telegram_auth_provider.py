"""Tests for TelegramAuthProvider (per-user authentication)."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from better_telegram_mcp.auth.per_user_session_store import SessionInfo
from better_telegram_mcp.auth.telegram_auth_provider import (
    _SESSION_TTL,
    TelegramAuthProvider,
)


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture
def provider(data_dir: Path) -> TelegramAuthProvider:
    return TelegramAuthProvider(data_dir, api_id=12345, api_hash="test_hash")


class TestRegisterBot:
    async def test_register_bot_success(self, provider: TelegramAuthProvider) -> None:
        """Should register bot and return bearer token."""
        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.BotBackend"
        ) as MockBot:
            mock_instance = MockBot.return_value
            mock_instance.connect = AsyncMock()
            mock_instance.disconnect = AsyncMock()

            bearer = await provider.register_bot("", "123:ABC")

        assert isinstance(bearer, str)
        assert len(bearer) > 0
        assert bearer in provider.active_clients

    async def test_register_bot_invalid_token(
        self, provider: TelegramAuthProvider
    ) -> None:
        """Should raise ValueError for invalid bot token."""
        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.BotBackend"
        ) as MockBot:
            mock_instance = MockBot.return_value
            mock_instance.connect = AsyncMock(side_effect=Exception("Unauthorized"))
            mock_instance.disconnect = AsyncMock()

            with pytest.raises(ValueError, match="Invalid bot token"):
                await provider.register_bot("", "invalid-token")

    async def test_register_bot_with_custom_bearer(
        self, provider: TelegramAuthProvider
    ) -> None:
        """Should use provided bearer when non-empty."""
        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.BotBackend"
        ) as MockBot:
            mock_instance = MockBot.return_value
            mock_instance.connect = AsyncMock()

            bearer = await provider.register_bot("custom-bearer", "123:ABC")

        assert bearer == "custom-bearer"

    async def test_register_bot_persists(self, provider: TelegramAuthProvider) -> None:
        """Registered bot should be persisted to session store."""
        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.BotBackend"
        ) as MockBot:
            mock_instance = MockBot.return_value
            mock_instance.connect = AsyncMock()

            bearer = await provider.register_bot("", "123:ABC")

        info = await provider._store.load(bearer)
        assert info is not None
        assert info.mode == "bot"
        assert info.bot_token == "123:ABC"


class TestResolveBackend:
    async def test_resolve_existing_backend(
        self, provider: TelegramAuthProvider
    ) -> None:
        """Should return backend for registered bearer."""
        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.BotBackend"
        ) as MockBot:
            mock_instance = MockBot.return_value
            mock_instance.connect = AsyncMock()

            bearer = await provider.register_bot("", "123:ABC")

        backend = provider.resolve_backend(bearer)
        assert backend is not None

    def test_resolve_unknown_bearer(self, provider: TelegramAuthProvider) -> None:
        """Should return None for unknown bearer."""
        assert provider.resolve_backend("unknown-bearer") is None


class TestStartUserAuth:
    async def test_start_user_auth_success(
        self, provider: TelegramAuthProvider
    ) -> None:
        """Should send code and return bearer + phone_code_hash."""
        mock_telethon_client = MagicMock()
        mock_sent_code = MagicMock()
        mock_sent_code.phone_code_hash = "hash123"
        mock_telethon_client.send_code_request = AsyncMock(return_value=mock_sent_code)

        mock_backend = MagicMock()
        mock_backend.connect = AsyncMock()
        mock_backend.disconnect = AsyncMock()
        mock_backend._ensure_client = MagicMock(return_value=mock_telethon_client)
        mock_backend._client = mock_telethon_client

        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.UserBackend",
            return_value=mock_backend,
        ):
            result = await provider.start_user_auth("", "+84912345678")

        assert "bearer" in result
        assert result["phone_code_hash"] == "hash123"

    async def test_start_user_auth_no_api_creds(self, data_dir: Path) -> None:
        """Should raise ValueError when api_id/api_hash not set."""
        provider = TelegramAuthProvider(data_dir, api_id=0, api_hash="")
        with pytest.raises(ValueError, match="TELEGRAM_API_ID"):
            await provider.start_user_auth("", "+84912345678")

    async def test_start_user_auth_send_code_fails(
        self, provider: TelegramAuthProvider
    ) -> None:
        """Should raise ValueError when send_code fails."""
        mock_telethon_client = MagicMock()
        mock_telethon_client.send_code_request = AsyncMock(
            side_effect=Exception("Phone invalid")
        )

        mock_backend = MagicMock()
        mock_backend.connect = AsyncMock()
        mock_backend.disconnect = AsyncMock()
        mock_backend._ensure_client = MagicMock(return_value=mock_telethon_client)

        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.UserBackend",
            return_value=mock_backend,
        ):
            with pytest.raises(ValueError, match="Failed to send code"):
                await provider.start_user_auth("", "+84912345678")


class TestCompleteUserAuth:
    async def test_complete_user_auth_success(
        self, provider: TelegramAuthProvider
    ) -> None:
        """Should sign in and activate backend."""
        mock_telethon_client = MagicMock()
        mock_sent_code = MagicMock()
        mock_sent_code.phone_code_hash = "hash123"
        mock_telethon_client.send_code_request = AsyncMock(return_value=mock_sent_code)

        mock_backend = MagicMock()
        mock_backend.connect = AsyncMock()
        mock_backend.disconnect = AsyncMock()
        mock_backend._ensure_client = MagicMock(return_value=mock_telethon_client)
        mock_backend.sign_in = AsyncMock(
            return_value={"authenticated_as": "Test", "username": "test"}
        )

        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.UserBackend",
            return_value=mock_backend,
        ):
            result = await provider.start_user_auth("", "+84912345678")
            bearer = result["bearer"]

            auth_result = await provider.complete_user_auth(bearer, "12345")

        assert auth_result["authenticated_as"] == "Test"
        assert bearer in provider.active_clients

    async def test_complete_user_auth_no_pending(
        self, provider: TelegramAuthProvider
    ) -> None:
        """Should raise ValueError when no pending OTP."""
        with pytest.raises(ValueError, match="No pending authentication"):
            await provider.complete_user_auth("unknown-bearer", "12345")

    async def test_complete_user_auth_wrong_code(
        self, provider: TelegramAuthProvider
    ) -> None:
        """Should raise ValueError on sign-in failure but keep pending state."""
        mock_telethon_client = MagicMock()
        mock_sent_code = MagicMock()
        mock_sent_code.phone_code_hash = "hash123"
        mock_telethon_client.send_code_request = AsyncMock(return_value=mock_sent_code)

        mock_backend = MagicMock()
        mock_backend.connect = AsyncMock()
        mock_backend.disconnect = AsyncMock()
        mock_backend._ensure_client = MagicMock(return_value=mock_telethon_client)
        mock_backend.sign_in = AsyncMock(side_effect=Exception("Invalid code"))

        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.UserBackend",
            return_value=mock_backend,
        ):
            result = await provider.start_user_auth("", "+84912345678")
            bearer = result["bearer"]

            with pytest.raises(ValueError, match="Sign-in failed"):
                await provider.complete_user_auth(bearer, "wrong")

        # Pending should still exist (allow retry)
        assert bearer in provider._pending_otps


class TestRevokeSession:
    async def test_revoke_existing_session(
        self, provider: TelegramAuthProvider
    ) -> None:
        """Should disconnect backend and remove from stores."""
        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.BotBackend"
        ) as MockBot:
            mock_instance = MockBot.return_value
            mock_instance.connect = AsyncMock()
            mock_instance.disconnect = AsyncMock()

            bearer = await provider.register_bot("", "123:ABC")

        assert bearer in provider.active_clients

        result = await provider.revoke_session(bearer)
        assert result is True
        assert bearer not in provider.active_clients

    async def test_revoke_nonexistent_session(
        self, provider: TelegramAuthProvider
    ) -> None:
        """Should return False for nonexistent session."""
        result = await provider.revoke_session("nonexistent")
        assert result is False

    async def test_revoke_cleans_session_owners(
        self, provider: TelegramAuthProvider
    ) -> None:
        """Should clean up session ownership mappings."""
        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.BotBackend"
        ) as MockBot:
            mock_instance = MockBot.return_value
            mock_instance.connect = AsyncMock()
            mock_instance.disconnect = AsyncMock()

            bearer = await provider.register_bot("", "123:ABC")

        provider.session_owners["session-1"] = bearer
        provider.session_owners["session-2"] = bearer
        provider.session_owners["session-3"] = "other-bearer"

        await provider.revoke_session(bearer)

        assert "session-1" not in provider.session_owners
        assert "session-2" not in provider.session_owners
        assert "session-3" in provider.session_owners


class TestSessionOwnership:
    async def test_cross_user_hijack_prevention(
        self, provider: TelegramAuthProvider
    ) -> None:
        """Different users cannot access each other's sessions."""
        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.BotBackend"
        ) as MockBot:
            mock_instance = MockBot.return_value
            mock_instance.connect = AsyncMock()

            bearer1 = await provider.register_bot("", "token1")
            bearer2 = await provider.register_bot("", "token2")

        # Assign session ownership
        provider.session_owners["session-A"] = bearer1

        # User 1 should access their session
        assert provider.session_owners.get("session-A") == bearer1

        # User 2 should not match
        assert provider.session_owners.get("session-A") != bearer2

        # Unknown session returns None
        assert provider.session_owners.get("session-X") is None


class TestRestoreSessions:
    async def test_restore_bot_sessions(self, provider: TelegramAuthProvider) -> None:
        """Should restore bot sessions from store on startup."""
        # Store a session directly
        await provider._store.store(
            "stored-bearer",
            SessionInfo(
                session_name="test",
                mode="bot",
                bot_token="123:ABC",
                created_at=time.time(),
            ),
        )

        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.BotBackend"
        ) as MockBot:
            mock_instance = MockBot.return_value
            mock_instance.connect = AsyncMock()

            restored = await provider.restore_sessions()

        assert restored == 1
        assert "stored-bearer" in provider.active_clients

    async def test_restore_expired_sessions_removed(
        self, provider: TelegramAuthProvider
    ) -> None:
        """Should remove expired sessions during restore."""
        await provider._store.store(
            "expired-bearer",
            SessionInfo(
                session_name="old",
                mode="bot",
                bot_token="123:ABC",
                created_at=time.time() - _SESSION_TTL - 1,
            ),
        )

        restored = await provider.restore_sessions()
        assert restored == 0
        assert "expired-bearer" not in provider.active_clients

    async def test_restore_failed_session_removed(
        self, provider: TelegramAuthProvider
    ) -> None:
        """Should remove sessions that fail to reconnect."""
        await provider._store.store(
            "broken-bearer",
            SessionInfo(
                session_name="broken",
                mode="bot",
                bot_token="invalid",
                created_at=time.time(),
            ),
        )

        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.BotBackend"
        ) as MockBot:
            mock_instance = MockBot.return_value
            mock_instance.connect = AsyncMock(
                side_effect=Exception("Connection failed")
            )

            restored = await provider.restore_sessions()

        assert restored == 0
        assert await provider._store.load("broken-bearer") is None


class TestCleanupExpired:
    async def test_cleanup_expired_sessions(
        self, provider: TelegramAuthProvider
    ) -> None:
        """Should remove expired sessions."""
        # Store an expired session
        await provider._store.store(
            "expired",
            SessionInfo(
                session_name="old",
                mode="bot",
                bot_token="t1",
                created_at=time.time() - _SESSION_TTL - 1,
            ),
        )
        # Store a valid session
        await provider._store.store(
            "valid",
            SessionInfo(
                session_name="new",
                mode="bot",
                bot_token="t2",
                created_at=time.time(),
            ),
        )

        removed = await provider.cleanup_expired()
        assert removed == 1
        assert await provider._store.load("expired") is None
        assert await provider._store.load("valid") is not None

    async def test_cleanup_stale_otps(self, provider: TelegramAuthProvider) -> None:
        """Should clean up pending OTPs older than 5 minutes."""
        mock_backend = AsyncMock()
        provider._pending_otps["stale"] = {
            "bearer": "stale",
            "backend": mock_backend,
            "phone": "+84912345678",
            "phone_code_hash": "hash",
            "session_name": "s1",
            "created_at": time.time() - 301,
        }

        removed = await provider.cleanup_expired()
        assert removed == 1
        assert "stale" not in provider._pending_otps
        mock_backend.disconnect.assert_called_once()


class TestShutdown:
    async def test_shutdown_disconnects_all(
        self, provider: TelegramAuthProvider
    ) -> None:
        """Should disconnect all active backends on shutdown."""
        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.BotBackend"
        ) as MockBot:
            mock_instance = MockBot.return_value
            mock_instance.connect = AsyncMock()
            mock_instance.disconnect = AsyncMock()

            await provider.register_bot("b1", "token1")
            await provider.register_bot("b2", "token2")

        assert len(provider.active_clients) == 2

        await provider.shutdown()

        assert len(provider.active_clients) == 0
        assert len(provider.session_owners) == 0
