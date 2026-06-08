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
    # Make the mock_client callable so await client(...) works
    client.side_effect = AsyncMock()
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


class TestUserBackendFull:
    @pytest.fixture
    def backend(self, tmp_path):
        return UserBackend(_make_settings(tmp_path))

    async def test_clear_cache(self, backend, mock_client, mock_client_class):
        await backend.connect()
        mock_client.session.save = MagicMock()
        await backend.clear_cache()
        mock_client.session.save.assert_called_once()

    async def test_send_message(self, backend, mock_client, mock_client_class):
        await backend.connect()
        mock_msg = MagicMock()
        mock_msg.id = 100
        mock_msg.text = "sent"
        mock_client.send_message = AsyncMock(return_value=mock_msg)

        result = await backend.send_message("chat", "text")
        assert result["message_id"] == 100
        mock_client.send_message.assert_awaited_once()

    async def test_edit_message(self, backend, mock_client, mock_client_class):
        await backend.connect()
        mock_msg = MagicMock()
        mock_msg.id = 100
        mock_client.edit_message = AsyncMock(return_value=mock_msg)

        await backend.edit_message("chat", 100, "new text")
        mock_client.edit_message.assert_awaited_once()

    async def test_delete_message(self, backend, mock_client, mock_client_class):
        await backend.connect()
        mock_res = [MagicMock()]
        mock_res[0].pts = 1
        mock_client.delete_messages = AsyncMock(return_value=mock_res)

        assert await backend.delete_message("chat", 100) is True
        mock_client.delete_messages.assert_awaited_once()

    async def test_forward_message(self, backend, mock_client, mock_client_class):
        await backend.connect()
        mock_msg = MagicMock()
        mock_msg.id = 101
        mock_client.forward_messages = AsyncMock(return_value=[mock_msg])

        result = await backend.forward_message("from", "to", 100)
        assert result["message_id"] == 101

    async def test_pin_message(self, backend, mock_client, mock_client_class):
        await backend.connect()
        mock_client.pin_message = AsyncMock(return_value=True)
        assert await backend.pin_message("chat", 100) is True

    async def test_react_to_message(self, backend, mock_client, mock_client_class):
        await backend.connect()
        mock_client.side_effect = AsyncMock(return_value=None)
        assert await backend.react_to_message("chat", 100, "👍") is True

    async def test_search_messages(self, backend, mock_client, mock_client_class):
        await backend.connect()

        async def mock_iter(*args, **kwargs):
            m = MagicMock()
            m.id = 1
            yield m

        mock_client.iter_messages.return_value = mock_iter()

        results = await backend.search_messages("query")
        assert len(results) == 1

    async def test_get_history(self, backend, mock_client, mock_client_class):
        await backend.connect()

        async def mock_iter(*args, **kwargs):
            yield MagicMock()

        mock_client.iter_messages.return_value = mock_iter()

        results = await backend.get_history("chat")
        assert len(results) == 1

    async def test_list_chats(self, backend, mock_client, mock_client_class):
        await backend.connect()
        mock_client.get_dialogs = AsyncMock(return_value=[MagicMock()])
        results = await backend.list_chats()
        assert len(results) == 1

    async def test_get_chat_info(self, backend, mock_client, mock_client_class):
        await backend.connect()
        mock_client.get_entity = AsyncMock(return_value=MagicMock())
        result = await backend.get_chat_info("chat")
        assert "id" in result

    async def test_create_chat(self, backend, mock_client, mock_client_class):
        await backend.connect()
        mock_res = MagicMock()
        mock_res.chats = [MagicMock()]
        mock_client.side_effect = AsyncMock(return_value=mock_res)
        result = await backend.create_chat("title")
        assert "title" in result

    async def test_join_chat(self, backend, mock_client, mock_client_class):
        await backend.connect()
        mock_client.side_effect = AsyncMock(return_value=None)
        assert await backend.join_chat("link") is True

    async def test_leave_chat(self, backend, mock_client, mock_client_class):
        await backend.connect()
        mock_client.get_entity = AsyncMock(return_value=MagicMock())
        mock_client.get_me = AsyncMock(return_value=MagicMock())
        mock_client.side_effect = AsyncMock(return_value=None)
        assert await backend.leave_chat("chat") is True

    async def test_get_members(self, backend, mock_client, mock_client_class):
        await backend.connect()

        async def mock_iter(*args, **kwargs):
            yield MagicMock()

        mock_client.iter_participants.return_value = mock_iter()
        results = await backend.get_members("chat")
        assert len(results) == 1

    async def test_promote_admin(self, backend, mock_client, mock_client_class):
        await backend.connect()
        mock_client.side_effect = AsyncMock(return_value=None)
        assert await backend.promote_admin("chat", 123) is True

    async def test_update_chat_settings(self, backend, mock_client, mock_client_class):
        await backend.connect()
        mock_client.side_effect = AsyncMock(return_value=None)
        assert await backend.update_chat_settings("chat", title="new") is True

    async def test_send_media(self, backend, mock_client, mock_client_class):
        await backend.connect()
        mock_client.send_file = AsyncMock(return_value=MagicMock())
        with patch(
            "better_telegram_mcp.backends.user_backend.validate_file_path",
            return_value=Path("/tmp/fake"),
        ):
            result = await backend.send_media("chat", "photo", "/path/to/file")
            assert "message_id" in result

    async def test_download_media(self, backend, mock_client, mock_client_class):
        await backend.connect()
        mock_msg = MagicMock()
        mock_msg.media = MagicMock()
        mock_client.get_messages = AsyncMock(return_value=[mock_msg])
        mock_client.download_media = AsyncMock(return_value="/tmp/file")

        result = await backend.download_media("chat", 100)
        assert result == "/tmp/file"

    async def test_list_contacts(self, backend, mock_client, mock_client_class):
        await backend.connect()
        mock_res = MagicMock()
        mock_res.users = [MagicMock()]
        mock_client.side_effect = AsyncMock(return_value=mock_res)
        results = await backend.list_contacts()
        assert len(results) == 1

    async def test_search_contacts(self, backend, mock_client, mock_client_class):
        await backend.connect()
        mock_res = MagicMock()
        mock_res.users = [MagicMock()]
        mock_client.side_effect = AsyncMock(return_value=mock_res)
        results = await backend.search_contacts("query")
        assert len(results) == 1

    async def test_add_contact(self, backend, mock_client, mock_client_class):
        await backend.connect()
        mock_client.side_effect = AsyncMock(return_value=MagicMock())
        assert await backend.add_contact("phone", "first") is True

    async def test_block_user(self, backend, mock_client, mock_client_class):
        await backend.connect()
        mock_client.side_effect = AsyncMock(return_value=None)
        assert await backend.block_user(123) is True
