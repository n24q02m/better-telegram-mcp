from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telethon import TelegramClient

from better_telegram_mcp.backends.user_backend import UserBackend
from better_telegram_mcp.config import Settings


def _make_settings(tmp_path: Path) -> Settings:
    return Settings(
        api_id=12345,
        api_hash="abcde",
        phone="+84912345678",
        data_dir=tmp_path,
    )


@pytest.fixture
def mock_client():
    client = MagicMock(spec=TelegramClient)
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.is_connected = MagicMock(return_value=True)
    client.is_user_authorized = AsyncMock(return_value=True)
    client.session = MagicMock()
    return client


@pytest.fixture
def mock_client_class(mock_client):
    with patch(
        "better_telegram_mcp.backends.user_backend.TelegramClient",
        return_value=mock_client,
    ) as mock:
        yield mock


class TestUserBackendBasics:
    async def test_ensure_client_raises_if_not_connected(self, tmp_path):
        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)
        with pytest.raises(RuntimeError, match="Not connected"):
            _ = backend.client

    async def test_connect_success(self, tmp_path, mock_client, mock_client_class):
        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)
        await backend.connect()

        mock_client_class.assert_called_once()
        mock_client.connect.assert_awaited_once()

    async def test_disconnect(self, tmp_path, mock_client, mock_client_class):
        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)
        await backend.connect()
        await backend.disconnect()

        mock_client.disconnect.assert_awaited_once()
        assert backend._client is None

    async def test_is_connected(self, tmp_path, mock_client, mock_client_class):
        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)

        assert await backend.is_connected() is False

        await backend.connect()
        assert await backend.is_connected() is True

    async def test_is_authorized(self, tmp_path, mock_client, mock_client_class):
        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)

        assert await backend.is_authorized() is False

        await backend.connect()
        assert await backend.is_authorized() is True


class TestSendCode:
    async def test_send_code(self, tmp_path, mock_client, mock_client_class):
        mock_client.send_code_request = AsyncMock()
        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)
        await backend.connect()

        await backend.send_code("+84912345678")

        mock_client.send_code_request.assert_awaited_once_with("+84912345678")


class TestSignIn:
    async def test_sign_in_success(self, tmp_path, mock_client, mock_client_class):
        mock_me = MagicMock()
        mock_me.first_name = "Test"
        mock_me.username = "testuser"
        mock_client.sign_in = AsyncMock()
        mock_client.get_me = AsyncMock(return_value=mock_me)

        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)
        await backend.connect()

        result = await backend.sign_in("+84912345678", "12345")

        mock_client.sign_in.assert_awaited_once_with("+84912345678", "12345")
        assert result["authenticated_as"] == "Test"
        assert result["username"] == "testuser"


class TestSerializeHelpers:
    def test_serialize_message(self):
        from better_telegram_mcp.backends.user_helpers import serialize_message

        msg = MagicMock()
        msg.id = 1
        msg.text = "Hello"
        msg.date = None
        msg.sender_id = 123

        result = serialize_message(msg)
        assert result["message_id"] == 1
        assert result["text"] == "Hello"
        assert result["sender_id"] == 123

    def test_serialize_dialog(self):
        from better_telegram_mcp.backends.user_helpers import serialize_dialog

        d = MagicMock()
        d.id = 1
        d.title = "Test Chat"
        d.unread_count = 5

        result = serialize_dialog(d)
        assert result["id"] == 1
        assert result["title"] == "Test Chat"
        assert result["unread_count"] == 5

    def test_serialize_user(self):
        from better_telegram_mcp.backends.user_helpers import serialize_user

        u = MagicMock()
        u.id = 1
        u.first_name = "John"
        u.last_name = "Doe"
        u.username = "johndoe"
        u.phone = "12345"

        result = serialize_user(u)
        assert result["id"] == 1
        assert result["first_name"] == "John"
        assert result["username"] == "johndoe"

    def test_serialize_entity(self):
        from telethon.tl.types import Channel, User

        from better_telegram_mcp.backends.user_helpers import serialize_entity

        u = MagicMock(spec=User)
        u.id = 1
        u.first_name = "John"
        u.last_name = "Doe"
        u.username = "johndoe"

        result = serialize_entity(u)
        assert result["id"] == 1
        assert result["first_name"] == "John"

        c = MagicMock(spec=Channel)
        c.id = 2
        c.title = "Channel"
        c.participants_count = 10

        result = serialize_entity(c)
        assert result["id"] == 2
        assert result["title"] == "Channel"


class TestUserBackendLogging:
    @pytest.fixture
    def mock_logger(self):
        with patch("better_telegram_mcp.backends.user_helpers.logger") as mock:
            yield mock

    async def test_connect_logging(
        self, tmp_path, mock_client, mock_client_class, mock_logger
    ):
        settings = _make_settings(tmp_path)
        # Force OSError in os.open
        with patch(
            "better_telegram_mcp.backends.user_helpers.os.open",
            side_effect=OSError("Permission denied"),
        ):
            backend = UserBackend(settings)
            await backend.connect()

        mock_logger.debug.assert_called()
        args, _ = mock_logger.debug.call_args
        assert "Could not pre-create session file" in args[0]

    async def test_sign_in_chmod_logging(
        self, tmp_path, mock_client, mock_client_class, mock_logger
    ):
        # Setup for sign_in
        mock_me = MagicMock()
        mock_me.first_name = "Test"
        mock_me.username = "testuser"
        mock_client.sign_in = AsyncMock()
        mock_client.get_me = AsyncMock(return_value=mock_me)

        settings = _make_settings(tmp_path)
        # Create session file
        session_file = (settings.data_dir / settings.session_name).with_suffix(
            ".session"
        )
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        session_file.write_text("fake session")

        backend = UserBackend(settings)
        await backend.connect()

        # Force OSError in os.chmod
        with patch(
            "better_telegram_mcp.backends.user_helpers.os.chmod",
            side_effect=OSError("Operation not permitted"),
        ):
            await backend.sign_in("+84912345678", "12345")

        mock_logger.debug.assert_called()
        args, _ = mock_logger.debug.call_args
        assert "Could not set session file permissions" in args[0]


class TestTopicManagement:
    async def test_manage_topics_dispatch(
        self, tmp_path, mock_client, mock_client_class
    ):
        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)
        await backend.connect()

        with patch.object(backend, "_list_topics", new_callable=AsyncMock) as mock_list:
            await backend.manage_topics(123, "list", limit=10)
            mock_list.assert_awaited_once_with(123, limit=10)

        with patch.object(
            backend, "_create_topic", new_callable=AsyncMock
        ) as mock_create:
            await backend.manage_topics(123, "create", name="New Topic")
            mock_create.assert_awaited_once_with(123, name="New Topic")

        with patch.object(
            backend, "_close_topic", new_callable=AsyncMock
        ) as mock_close:
            await backend.manage_topics(123, "close", topic_id=456)
            mock_close.assert_awaited_once_with(123, topic_id=456)

        result = await backend.manage_topics(123, "invalid")
        assert "error" in result
