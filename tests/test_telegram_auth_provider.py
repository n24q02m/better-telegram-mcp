"""Tests for TelegramAuthProvider (per-user authentication)."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from better_telegram_mcp.auth.per_user_session_store import SessionInfo
from better_telegram_mcp.auth.telegram_auth_provider import (
    _SESSION_TTL,
    TelegramAuthProvider,
    TelegramBearerRuntime,
    _RuntimeEventSink,
)
from better_telegram_mcp.config import Settings
from better_telegram_mcp.events.sse_fanout_hub import SSEFanoutHub


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

        info = provider._store.load(bearer)
        assert info is not None
        assert info.mode == "bot"
        assert info.bot_token == "123:ABC"

    async def test_register_bot_starts_polling_producer(
        self, provider: TelegramAuthProvider
    ) -> None:
        mock_backend = AsyncMock()
        mock_backend.connect = AsyncMock()
        mock_backend.disconnect = AsyncMock()
        mock_producer = AsyncMock()

        with (
            patch(
                "better_telegram_mcp.auth.telegram_auth_provider.BotBackend",
                return_value=mock_backend,
            ),
            patch(
                "better_telegram_mcp.auth.telegram_auth_provider.BotUpdateProducer",
                return_value=mock_producer,
            ) as MockProducer,
        ):
            bearer = await provider.register_bot("bearer-1", "123:ABC")

        runtime = provider.resolve_runtime(bearer)
        assert runtime is not None
        assert runtime.bot_producer is mock_producer
        MockProducer.assert_called_once()
        assert MockProducer.call_args.kwargs["backend"] is mock_backend
        assert MockProducer.call_args.kwargs["session_store"] is provider._store
        assert MockProducer.call_args.kwargs["bearer"] == bearer
        assert MockProducer.call_args.kwargs["event_sink"] is runtime.hub
        mock_producer.start.assert_awaited_once()

    async def test_register_bot_rolls_back_when_producer_start_fails(
        self, provider: TelegramAuthProvider
    ) -> None:
        mock_backend = AsyncMock()
        mock_backend.connect = AsyncMock()
        mock_backend.disconnect = AsyncMock()
        mock_producer = AsyncMock()
        mock_producer.start = AsyncMock(side_effect=ValueError("webhook configured"))

        with (
            patch(
                "better_telegram_mcp.auth.telegram_auth_provider.BotBackend",
                return_value=mock_backend,
            ),
            patch(
                "better_telegram_mcp.auth.telegram_auth_provider.BotUpdateProducer",
                return_value=mock_producer,
            ),
        ):
            with pytest.raises(ValueError, match="webhook configured"):
                await provider.register_bot("bearer-1", "123:ABC")

        assert provider.resolve_runtime("bearer-1") is None
        assert provider.resolve_backend("bearer-1") is None
        assert provider._store.load("bearer-1") is None
        mock_backend.disconnect.assert_awaited_once()

    async def test_register_bot_rejects_duplicate_token_under_concurrency(
        self, provider: TelegramAuthProvider
    ) -> None:
        first_backend = AsyncMock()
        first_backend.disconnect = AsyncMock()
        second_backend = AsyncMock()
        second_backend.disconnect = AsyncMock()
        producer_one = AsyncMock()
        producer_one.start = AsyncMock()
        producer_two = AsyncMock()
        producer_two.start = AsyncMock()

        async def slow_connect() -> None:
            await asyncio.sleep(0.05)

        first_backend.connect = AsyncMock(side_effect=slow_connect)
        second_backend.connect = AsyncMock(side_effect=slow_connect)

        with (
            patch(
                "better_telegram_mcp.auth.telegram_auth_provider.BotBackend",
                side_effect=[first_backend, second_backend],
            ),
            patch(
                "better_telegram_mcp.auth.telegram_auth_provider.BotUpdateProducer",
                side_effect=[producer_one, producer_two],
            ),
        ):
            results = await asyncio.gather(
                provider.register_bot("bearer-1", "shared-token"),
                provider.register_bot("bearer-2", "shared-token"),
                return_exceptions=True,
            )

        successes = [result for result in results if isinstance(result, str)]
        failures = [result for result in results if isinstance(result, Exception)]

        assert successes == ["bearer-1"]
        assert len(failures) == 1
        assert isinstance(failures[0], ValueError)
        assert "already active" in str(failures[0])
        assert provider.resolve_runtime("bearer-1") is not None
        assert provider.resolve_runtime("bearer-2") is None
        assert provider._store.load("bearer-1") is not None
        assert provider._store.load("bearer-2") is None
        second_backend.connect.assert_not_awaited()
        second_backend.disconnect.assert_not_awaited()


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


class TestBearerRuntimes:
    async def test_register_bot_creates_isolated_runtime_per_bearer(
        self, provider: TelegramAuthProvider
    ) -> None:
        first_backend = AsyncMock()
        first_backend.connect = AsyncMock()
        first_backend.disconnect = AsyncMock()

        second_backend = AsyncMock()
        second_backend.connect = AsyncMock()
        second_backend.disconnect = AsyncMock()

        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.BotBackend",
            side_effect=[first_backend, second_backend],
        ):
            first_bearer = await provider.register_bot("bearer-1", "token-1")
            second_bearer = await provider.register_bot("bearer-2", "token-2")

        first_runtime = provider.resolve_runtime(first_bearer)
        second_runtime = provider.resolve_runtime(second_bearer)

        assert first_runtime is not None
        assert second_runtime is not None
        assert first_runtime is not second_runtime
        assert first_runtime.backend is first_backend
        assert second_runtime.backend is second_backend
        assert first_runtime.hub is not second_runtime.hub
        assert provider.resolve_sse_hub(first_bearer) is first_runtime.hub
        assert provider.resolve_sse_hub(second_bearer) is second_runtime.hub
        assert provider.resolve_backend(first_bearer) is first_backend
        assert provider.resolve_backend(second_bearer) is second_backend

    async def test_register_bot_rejects_duplicate_active_bot_token(
        self, provider: TelegramAuthProvider
    ) -> None:
        first_backend = AsyncMock()
        first_backend.connect = AsyncMock()
        first_backend.disconnect = AsyncMock()

        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.BotBackend",
            return_value=first_backend,
        ):
            await provider.register_bot("bearer-1", "shared-token")

            with pytest.raises(ValueError, match="already active"):
                await provider.register_bot("bearer-2", "shared-token")

        assert provider.resolve_runtime("bearer-1") is not None
        assert provider.resolve_runtime("bearer-2") is None


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

    async def test_start_user_auth_does_not_inject_relay_into_pending_backend(
        self, data_dir: Path
    ) -> None:
        relay_settings = Settings(relay_endpoint_url="https://example.com/events")
        provider = TelegramAuthProvider(
            data_dir,
            api_id=12345,
            api_hash="test_hash",
            relay_settings=relay_settings,
        )

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
        ) as MockUserBackend:
            await provider.start_user_auth("", "+84912345678")

        assert MockUserBackend.call_args.kwargs["event_dispatcher"] is None

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

    async def test_complete_user_auth_injects_shared_relay(
        self, data_dir: Path
    ) -> None:
        relay_settings = Settings(relay_endpoint_url="https://example.com/events")
        provider = TelegramAuthProvider(
            data_dir,
            api_id=12345,
            api_hash="test_hash",
            relay_settings=relay_settings,
        )

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
        mock_backend.set_event_dispatcher = MagicMock()
        mock_backend.enable_event_capture = AsyncMock()

        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.UserBackend",
            return_value=mock_backend,
        ):
            result = await provider.start_user_auth("", "+84912345678")
            bearer = result["bearer"]

            await provider.complete_user_auth(bearer, "12345")

        mock_backend.set_event_dispatcher.assert_called_once()
        final_dispatcher = mock_backend.set_event_dispatcher.call_args.args[0]

        assert isinstance(final_dispatcher, _RuntimeEventSink)
        assert final_dispatcher.relay_dispatcher is provider._event_dispatcher
        runtime = provider.resolve_runtime(bearer)
        assert runtime is not None
        assert final_dispatcher.hub is runtime.hub
        mock_backend.enable_event_capture.assert_awaited_once()
        assert provider._event_dispatcher is not None

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

    async def test_revoke_stops_producer_before_hub_and_backend(
        self, provider: TelegramAuthProvider
    ) -> None:
        order: list[str] = []

        class RecordingProducer:
            async def stop(self) -> None:
                order.append("producer")

        backend = AsyncMock()

        async def disconnect() -> None:
            order.append("backend")

        backend.disconnect = AsyncMock(side_effect=disconnect)
        hub = SSEFanoutHub(subscriber_queue_size=1)

        async def close(reason: str) -> None:
            assert reason == "runtime_stopped"
            order.append("hub")

        hub.close = close  # type: ignore[method-assign]
        provider._store.store(
            "bearer-1",
            SessionInfo(session_name="bot", mode="bot", bot_token="123:ABC"),
        )
        provider._runtimes["bearer-1"] = TelegramBearerRuntime(
            backend=backend,
            hub=hub,
            mode="bot",
            session_name="bot",
            bot_token="123:ABC",
            bot_producer=RecordingProducer(),
        )
        provider.active_clients["bearer-1"] = backend

        await provider.revoke_session("bearer-1")

        assert order == ["producer", "hub", "backend"]


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
        provider._store.store(
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

    async def test_restore_bot_sessions_start_polling_from_persisted_offset(
        self, provider: TelegramAuthProvider
    ) -> None:
        provider._store.store(
            "stored-bearer",
            SessionInfo(
                session_name="test",
                mode="bot",
                bot_token="123:ABC",
                bot_offset=41,
                created_at=time.time(),
            ),
        )

        mock_backend = AsyncMock()
        mock_backend.connect = AsyncMock()
        mock_backend.disconnect = AsyncMock()
        mock_producer = AsyncMock()

        with (
            patch(
                "better_telegram_mcp.auth.telegram_auth_provider.BotBackend",
                return_value=mock_backend,
            ),
            patch(
                "better_telegram_mcp.auth.telegram_auth_provider.BotUpdateProducer",
                return_value=mock_producer,
            ) as MockProducer,
        ):
            restored = await provider.restore_sessions()

        runtime = provider.resolve_runtime("stored-bearer")
        assert restored == 1
        assert runtime is not None
        assert runtime.bot_producer is mock_producer
        assert MockProducer.call_args.kwargs["bearer"] == "stored-bearer"
        assert MockProducer.call_args.kwargs["event_sink"] is runtime.hub
        mock_producer.start.assert_awaited_once()

    async def test_restore_bot_session_rolls_back_when_producer_start_fails(
        self, provider: TelegramAuthProvider
    ) -> None:
        provider._store.store(
            "stored-bearer",
            SessionInfo(
                session_name="test",
                mode="bot",
                bot_token="123:ABC",
                created_at=time.time(),
            ),
        )

        mock_backend = AsyncMock()
        mock_backend.connect = AsyncMock()
        mock_backend.disconnect = AsyncMock()
        mock_producer = AsyncMock()
        mock_producer.start = AsyncMock(side_effect=ValueError("webhook configured"))

        with (
            patch(
                "better_telegram_mcp.auth.telegram_auth_provider.BotBackend",
                return_value=mock_backend,
            ),
            patch(
                "better_telegram_mcp.auth.telegram_auth_provider.BotUpdateProducer",
                return_value=mock_producer,
            ),
        ):
            restored = await provider.restore_sessions()

        assert restored == 0
        assert provider.resolve_runtime("stored-bearer") is None
        assert provider.resolve_backend("stored-bearer") is None
        assert provider._store.load("stored-bearer") is None
        mock_backend.disconnect.assert_awaited_once()

    async def test_restore_user_sessions_publish_to_sse_hub_after_restore_sse(
        self, data_dir: Path
    ) -> None:
        relay_settings = Settings(relay_endpoint_url="https://example.com/events")
        provider = TelegramAuthProvider(
            data_dir,
            api_id=12345,
            api_hash="test_hash",
            relay_settings=relay_settings,
        )
        provider._store.store(
            "stored-user",
            SessionInfo(
                session_name="user-session",
                mode="user",
                api_id=12345,
                api_hash="test_hash",
                phone="+84912345678",
                created_at=time.time(),
            ),
        )

        class RestoredUserBackend:
            def __init__(
                self, settings: Settings, event_dispatcher: Any | None = None
            ) -> None:
                self.settings = settings
                self.event_dispatcher = event_dispatcher
                self.enable_event_capture = AsyncMock(side_effect=self._enable_capture)
                self.set_event_dispatcher = MagicMock(side_effect=self._set_dispatcher)
                self.connect = AsyncMock()

            def _set_dispatcher(self, event_dispatcher: Any | None) -> None:
                self.event_dispatcher = event_dispatcher

            async def _enable_capture(self) -> None:
                return None

            def emit_event(self, event: dict[str, object]) -> bool:
                assert self.event_dispatcher is not None
                publish = getattr(self.event_dispatcher, "publish", None)
                assert callable(publish)
                return bool(publish(event))

        restored_backend: RestoredUserBackend | None = None

        def build_backend(
            settings: Settings, event_dispatcher: Any | None = None
        ) -> RestoredUserBackend:
            nonlocal restored_backend
            restored_backend = RestoredUserBackend(settings, event_dispatcher)
            return restored_backend

        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.UserBackend"
        ) as MockUserBackend:
            MockUserBackend.side_effect = build_backend

            restored = await provider.restore_sessions()

        assert restored_backend is not None
        assert restored == 1
        assert provider._event_dispatcher is not None
        assert MockUserBackend.call_args.kwargs["event_dispatcher"] is None

        runtime = provider.resolve_runtime("stored-user")
        assert runtime is not None

        restored_backend.set_event_dispatcher.assert_called_once()
        installed_sink = restored_backend.set_event_dispatcher.call_args.args[0]
        assert isinstance(installed_sink, _RuntimeEventSink)
        assert installed_sink.hub is runtime.hub
        assert installed_sink.relay_dispatcher is provider._event_dispatcher
        restored_backend.enable_event_capture.assert_awaited_once()

        subscriber = runtime.hub.subscribe()
        event = {
            "event_id": "restore-event",
            "event_type": "UpdateNewMessage",
            "occurred_at": "2026-04-09T00:00:00+00:00",
            "mode": "user",
            "account": {
                "telegram_id": 123,
                "session_name": "user-session",
                "username": "restored-user",
                "mode": "user",
            },
            "update": {"_": "UpdateNewMessage", "message": {"id": 1}},
        }

        assert restored_backend.emit_event(event) is True
        item = await subscriber.next_item()
        assert item.kind == "event"
        assert item.event == event


class TestRelayShutdown:
    async def test_shutdown_stops_shared_relay_dispatcher(self, data_dir: Path) -> None:
        relay_settings = Settings(relay_endpoint_url="https://example.com/events")
        provider = TelegramAuthProvider(
            data_dir,
            api_id=12345,
            api_hash="test_hash",
            relay_settings=relay_settings,
        )

        dispatcher = AsyncMock()
        provider._event_dispatcher = dispatcher
        provider.active_clients["bearer"] = AsyncMock(disconnect=AsyncMock())

        await provider.shutdown()

        dispatcher.stop.assert_awaited_once()

    async def test_restore_expired_sessions_removed(
        self, provider: TelegramAuthProvider
    ) -> None:
        """Should remove expired sessions during restore."""
        provider._store.store(
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
        provider._store.store(
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
        assert provider._store.load("broken-bearer") is None


class TestCleanupExpired:
    async def test_cleanup_expired_sessions(
        self, provider: TelegramAuthProvider
    ) -> None:
        """Should remove expired sessions."""
        # Store an expired session
        provider._store.store(
            "expired",
            SessionInfo(
                session_name="old",
                mode="bot",
                bot_token="t1",
                created_at=time.time() - _SESSION_TTL - 1,
            ),
        )
        # Store a valid session
        provider._store.store(
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
        assert provider._store.load("expired") is None
        assert provider._store.load("valid") is not None

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

    async def test_shutdown_stops_producers_before_hubs_and_backends(
        self, provider: TelegramAuthProvider
    ) -> None:
        order: list[str] = []

        class RecordingProducer:
            def __init__(self, name: str) -> None:
                self.name = name

            async def stop(self) -> None:
                order.append(f"producer:{self.name}")

        def make_backend(name: str) -> AsyncMock:
            backend = AsyncMock()

            async def disconnect() -> None:
                order.append(f"backend:{name}")

            backend.disconnect = AsyncMock(side_effect=disconnect)
            return backend

        def make_hub(name: str) -> SSEFanoutHub:
            hub = SSEFanoutHub(subscriber_queue_size=1)

            async def close(reason: str) -> None:
                assert reason == "runtime_stopped"
                order.append(f"hub:{name}")

            hub.close = close  # type: ignore[method-assign]
            return hub

        first_backend = make_backend("one")
        second_backend = make_backend("two")

        provider._runtimes["b1"] = TelegramBearerRuntime(
            backend=first_backend,
            hub=make_hub("one"),
            mode="bot",
            session_name="one",
            bot_token="token-1",
            bot_producer=RecordingProducer("one"),
        )
        provider._runtimes["b2"] = TelegramBearerRuntime(
            backend=second_backend,
            hub=make_hub("two"),
            mode="bot",
            session_name="two",
            bot_token="token-2",
            bot_producer=RecordingProducer("two"),
        )
        provider.active_clients["b1"] = first_backend
        provider.active_clients["b2"] = second_backend

        await provider.shutdown()

        assert order == [
            "producer:one",
            "hub:one",
            "backend:one",
            "producer:two",
            "hub:two",
            "backend:two",
        ]
