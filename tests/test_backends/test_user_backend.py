from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from better_telegram_mcp.config import Settings


def _make_settings(tmp_path: Path) -> Settings:
    """Create Settings for user mode with a temp data dir."""
    return Settings(
        api_id=12345,
        api_hash="test_hash",
        phone="+84912345678",
        data_dir=tmp_path,
        session_name="test_session",
    )


def _mock_message(
    msg_id: int = 1,
    text: str = "hello",
    date: str = "2026-01-01",
    sender_id: int = 100,
) -> MagicMock:
    msg = MagicMock()
    msg.id = msg_id
    msg.text = text
    msg.date = date
    msg.sender_id = sender_id
    msg.media = None
    return msg


def _mock_dialog(
    dialog_id: int = 1, title: str = "Test Chat", unread: int = 0
) -> MagicMock:
    d = MagicMock()
    d.id = dialog_id
    d.title = title
    d.name = title
    d.unread_count = unread
    return d


def _mock_user(
    user_id: int = 100,
    first_name: str = "Test",
    last_name: str = "User",
    username: str = "testuser",
    phone: str = "+84912345678",
) -> MagicMock:
    u = MagicMock()
    u.id = user_id
    u.first_name = first_name
    u.last_name = last_name
    u.username = username
    u.phone = phone
    return u


@pytest.fixture
def mock_client():
    """Create a fully mocked TelegramClient."""
    client = AsyncMock()
    # is_connected is sync in Telethon, so use MagicMock
    client.is_connected = MagicMock(return_value=True)
    client.is_user_authorized = AsyncMock(return_value=True)
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    return client


@pytest.fixture
def mock_client_class(mock_client):
    """Patch TelegramClient constructor to return mock_client."""
    with patch(
        "better_telegram_mcp.backends.user_backend.TelegramClient",
        return_value=mock_client,
    ) as cls:
        yield cls


class TestConnect:
    async def test_connect_authorized(self, tmp_path, mock_client, mock_client_class):
        from better_telegram_mcp.backends.user_backend import UserBackend

        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)

        await backend.connect()

        mock_client_class.assert_called_once()
        mock_client.connect.assert_awaited_once()
        mock_client.is_user_authorized.assert_awaited_once()
        assert await backend.is_connected() is True

    async def test_connect_unauthorized_raises(self, tmp_path, mock_client, mock_client_class):
        from better_telegram_mcp.backends.user_backend import UserBackend

        mock_client.is_user_authorized = AsyncMock(return_value=False)
        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)

        with pytest.raises(ConnectionError, match="Run: uvx better-telegram-mcp auth"):
            await backend.connect()

        mock_client.disconnect.assert_awaited_once()


class TestDisconnect:
    async def test_disconnect(self, tmp_path, mock_client, mock_client_class):
        from better_telegram_mcp.backends.user_backend import UserBackend

        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)
        await backend.connect()

        await backend.disconnect()

        mock_client.disconnect.assert_awaited()
        assert backend._client is None

    async def test_disconnect_when_not_connected(self, tmp_path):
        from better_telegram_mcp.backends.user_backend import UserBackend

        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)

        # Should not raise
        await backend.disconnect()


class TestSendMessage:
    async def test_send_message(self, tmp_path, mock_client, mock_client_class):
        from better_telegram_mcp.backends.user_backend import UserBackend

        mock_client.send_message = AsyncMock(return_value=_mock_message())
        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)
        await backend.connect()

        result = await backend.send_message(123, "hello", reply_to=5, parse_mode="html")

        mock_client.send_message.assert_awaited_once_with(
            123, "hello", reply_to=5, parse_mode="html"
        )
        assert result["message_id"] == 1
        assert result["text"] == "hello"

    async def test_send_message_not_connected(self, tmp_path):
        from better_telegram_mcp.backends.user_backend import UserBackend

        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)

        with pytest.raises(RuntimeError, match="Not connected"):
            await backend.send_message(123, "hello")


class TestSearchMessages:
    async def test_search_global(self, tmp_path, mock_client, mock_client_class):
        from better_telegram_mcp.backends.user_backend import UserBackend

        msgs = [_mock_message(msg_id=i, text=f"msg{i}") for i in range(3)]

        async def mock_iter(*args, **kwargs):
            for m in msgs:
                yield m

        mock_client.iter_messages = mock_iter

        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)
        await backend.connect()

        result = await backend.search_messages("test", limit=10)

        assert len(result) == 3
        assert result[0]["message_id"] == 0

    async def test_search_per_chat(self, tmp_path, mock_client, mock_client_class):
        from better_telegram_mcp.backends.user_backend import UserBackend

        msgs = [_mock_message(msg_id=1, text="found")]

        async def mock_iter(*args, **kwargs):
            for m in msgs:
                yield m

        mock_client.iter_messages = mock_iter

        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)
        await backend.connect()

        result = await backend.search_messages("test", chat_id=456, limit=5)

        assert len(result) == 1
        assert result[0]["text"] == "found"


class TestListChats:
    async def test_list_chats(self, tmp_path, mock_client, mock_client_class):
        from better_telegram_mcp.backends.user_backend import UserBackend

        dialogs = [_mock_dialog(i, f"Chat {i}") for i in range(3)]
        mock_client.get_dialogs = AsyncMock(return_value=dialogs)

        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)
        await backend.connect()

        result = await backend.list_chats(limit=10)

        assert len(result) == 3
        assert result[1]["title"] == "Chat 1"
        mock_client.get_dialogs.assert_awaited_once_with(limit=10)


class TestGetHistory:
    async def test_get_history(self, tmp_path, mock_client, mock_client_class):
        from better_telegram_mcp.backends.user_backend import UserBackend

        msgs = [_mock_message(msg_id=i) for i in range(5)]
        mock_client.get_messages = AsyncMock(return_value=msgs)

        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)
        await backend.connect()

        result = await backend.get_history(123, limit=5)

        assert len(result) == 5
        mock_client.get_messages.assert_awaited_once_with(123, limit=5)

    async def test_get_history_with_offset(self, tmp_path, mock_client, mock_client_class):
        from better_telegram_mcp.backends.user_backend import UserBackend

        mock_client.get_messages = AsyncMock(return_value=[])

        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)
        await backend.connect()

        await backend.get_history(123, limit=10, offset_id=50)

        mock_client.get_messages.assert_awaited_once_with(
            123, limit=10, offset_id=50
        )


class TestListContacts:
    async def test_list_contacts_returns_list(self, tmp_path, mock_client, mock_client_class):
        from better_telegram_mcp.backends.user_backend import UserBackend

        users = [_mock_user(user_id=i) for i in range(2)]
        mock_client.get_contacts = AsyncMock(return_value=users)

        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)
        await backend.connect()

        result = await backend.list_contacts()

        assert len(result) == 2
        assert result[0]["first_name"] == "Test"

    async def test_list_contacts_returns_object_with_users(self, tmp_path, mock_client, mock_client_class):
        from better_telegram_mcp.backends.user_backend import UserBackend

        contacts_obj = MagicMock()
        contacts_obj.users = [_mock_user()]
        mock_client.get_contacts = AsyncMock(return_value=contacts_obj)

        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)
        await backend.connect()

        result = await backend.list_contacts()

        assert len(result) == 1


class TestDownloadMedia:
    async def test_download_media(self, tmp_path, mock_client, mock_client_class):
        from better_telegram_mcp.backends.user_backend import UserBackend

        msg = _mock_message()
        msg.media = MagicMock()  # has media
        mock_client.get_messages = AsyncMock(return_value=msg)
        mock_client.download_media = AsyncMock(return_value="/tmp/photo.jpg")

        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)
        await backend.connect()

        result = await backend.download_media(123, 1)

        assert result == "/tmp/photo.jpg"

    async def test_download_media_no_media_raises(self, tmp_path, mock_client, mock_client_class):
        from better_telegram_mcp.backends.user_backend import UserBackend

        msg = _mock_message()
        msg.media = None
        mock_client.get_messages = AsyncMock(return_value=msg)

        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)
        await backend.connect()

        with pytest.raises(ValueError, match="no media"):
            await backend.download_media(123, 1)


class TestEditMessage:
    async def test_edit_message(self, tmp_path, mock_client, mock_client_class):
        from better_telegram_mcp.backends.user_backend import UserBackend

        mock_client.edit_message = AsyncMock(return_value=_mock_message(text="edited"))

        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)
        await backend.connect()

        result = await backend.edit_message(123, 1, "edited")

        assert result["text"] == "edited"


class TestDeleteMessage:
    async def test_delete_message(self, tmp_path, mock_client, mock_client_class):
        from better_telegram_mcp.backends.user_backend import UserBackend

        mock_client.delete_messages = AsyncMock(return_value=MagicMock())

        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)
        await backend.connect()

        result = await backend.delete_message(123, 1)

        assert result is True


class TestForwardMessage:
    async def test_forward_message(self, tmp_path, mock_client, mock_client_class):
        from better_telegram_mcp.backends.user_backend import UserBackend

        mock_client.forward_messages = AsyncMock(return_value=_mock_message(msg_id=2))

        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)
        await backend.connect()

        result = await backend.forward_message(100, 200, 1)

        assert result["message_id"] == 2


class TestBlockUser:
    async def test_block_user(self, tmp_path, mock_client, mock_client_class):
        from better_telegram_mcp.backends.user_backend import UserBackend

        mock_client.__call__ = AsyncMock()
        # Make the client callable (for TL requests)
        mock_client.return_value = None

        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)
        await backend.connect()

        result = await backend.block_user(123)

        assert result is True

    async def test_unblock_user(self, tmp_path, mock_client, mock_client_class):
        from better_telegram_mcp.backends.user_backend import UserBackend

        mock_client.return_value = None

        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)
        await backend.connect()

        result = await backend.block_user(123, unblock=True)

        assert result is True


class TestIsConnected:
    async def test_not_connected_without_client(self, tmp_path):
        from better_telegram_mcp.backends.user_backend import UserBackend

        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)

        assert await backend.is_connected() is False
