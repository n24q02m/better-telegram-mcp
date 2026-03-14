from __future__ import annotations

import json

import httpx
import pytest

from better_telegram_mcp.backends.base import ModeError
from better_telegram_mcp.backends.bot_backend import (
    BotBackend,
    TelegramAPIError,
)


def _make_transport(result: dict | list | bool, ok: bool = True):
    """Create a MockTransport that returns a Telegram-style JSON response."""
    body = {"ok": ok, "result": result}
    if not ok:
        body = {"ok": False, "description": result if isinstance(result, str) else "Error", "error_code": 400}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200 if ok else 400, json=body)

    return httpx.MockTransport(handler)


def _make_bot(result: dict | list | bool = True, ok: bool = True) -> BotBackend:
    """Create a BotBackend with mocked HTTP transport."""
    bot = BotBackend("123456:ABC-DEF")
    bot._client = httpx.AsyncClient(
        transport=_make_transport(result, ok),
        base_url=bot._base_url,
    )
    return bot


# --- Connection ---


async def test_connect_success():
    bot = BotBackend("123456:ABC-DEF")
    bot._client = httpx.AsyncClient(
        transport=_make_transport(
            {"id": 123, "is_bot": True, "first_name": "TestBot"}
        ),
        base_url=bot._base_url,
    )
    await bot.connect()
    assert await bot.is_connected()
    assert bot._bot_info["id"] == 123


async def test_connect_invalid_token():
    body = {"ok": False, "description": "Unauthorized", "error_code": 401}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json=body)

    bot = BotBackend("invalid-token")
    bot._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url=bot._base_url,
    )
    with pytest.raises(TelegramAPIError, match="Invalid bot token"):
        await bot.connect()


async def test_disconnect():
    bot = _make_bot({"id": 123, "is_bot": True, "first_name": "TestBot"})
    await bot.connect()
    assert await bot.is_connected()
    await bot.disconnect()
    assert not await bot.is_connected()


# --- Messages ---


async def test_send_message():
    msg = {"message_id": 42, "text": "hello", "chat": {"id": 1}}
    bot = _make_bot(msg)
    result = await bot.send_message(123, "hello")
    assert result["message_id"] == 42


async def test_send_message_with_reply():
    msg = {"message_id": 43, "text": "reply"}
    bot = _make_bot(msg)
    result = await bot.send_message(123, "reply", reply_to=42)
    assert result["message_id"] == 43


async def test_edit_message():
    msg = {"message_id": 42, "text": "edited"}
    bot = _make_bot(msg)
    result = await bot.edit_message(123, 42, "edited")
    assert result["text"] == "edited"


async def test_delete_message():
    bot = _make_bot(True)
    result = await bot.delete_message(123, 42)
    assert result is True


async def test_forward_message():
    msg = {"message_id": 99, "forward_date": 12345}
    bot = _make_bot(msg)
    result = await bot.forward_message(123, 456, 42)
    assert result["message_id"] == 99


async def test_pin_message():
    bot = _make_bot(True)
    result = await bot.pin_message(123, 42)
    assert result is True


async def test_react_to_message():
    bot = _make_bot(True)
    result = await bot.react_to_message(123, 42, "👍")
    assert result is True


# --- User-only methods raise ModeError ---


async def test_search_messages_raises_mode_error():
    bot = _make_bot()
    with pytest.raises(ModeError, match="requires user mode"):
        await bot.search_messages("test")


async def test_list_chats_raises_mode_error():
    bot = _make_bot()
    with pytest.raises(ModeError, match="requires user mode"):
        await bot.list_chats()


async def test_create_chat_raises_mode_error():
    bot = _make_bot()
    with pytest.raises(ModeError, match="requires user mode"):
        await bot.create_chat("Test Group")


async def test_join_chat_raises_mode_error():
    bot = _make_bot()
    with pytest.raises(ModeError, match="requires user mode"):
        await bot.join_chat("https://t.me/+abc")


async def test_list_contacts_raises_mode_error():
    bot = _make_bot()
    with pytest.raises(ModeError, match="requires user mode"):
        await bot.list_contacts()


async def test_search_contacts_raises_mode_error():
    bot = _make_bot()
    with pytest.raises(ModeError, match="requires user mode"):
        await bot.search_contacts("John")


async def test_add_contact_raises_mode_error():
    bot = _make_bot()
    with pytest.raises(ModeError, match="requires user mode"):
        await bot.add_contact("+1234567890", "John")


async def test_block_user_raises_mode_error():
    bot = _make_bot()
    with pytest.raises(ModeError, match="requires user mode"):
        await bot.block_user(123)


# --- NotImplementedError ---


async def test_get_history_raises_not_implemented():
    bot = _make_bot()
    with pytest.raises(NotImplementedError, match="Bot API does not support"):
        await bot.get_history(123)


async def test_download_media_raises_not_implemented():
    bot = _make_bot()
    with pytest.raises(NotImplementedError, match="Bot API download requires"):
        await bot.download_media(123, 42)


# --- Chat operations ---


async def test_get_chat_info():
    chat = {"id": 123, "type": "group", "title": "Test Group"}
    bot = _make_bot(chat)
    result = await bot.get_chat_info(123)
    assert result["title"] == "Test Group"


async def test_leave_chat():
    bot = _make_bot(True)
    result = await bot.leave_chat(123)
    assert result is True


async def test_get_members():
    members = [
        {"user": {"id": 1, "first_name": "Admin"}, "status": "creator"},
    ]
    bot = _make_bot(members)
    result = await bot.get_members(123)
    assert len(result) == 1
    assert result[0]["status"] == "creator"


async def test_promote_admin():
    bot = _make_bot(True)
    result = await bot.promote_admin(123, 456)
    assert result is True


async def test_promote_admin_demote():
    bot = _make_bot(True)
    result = await bot.promote_admin(123, 456, demote=True)
    assert result is True


async def test_update_chat_settings():
    bot = _make_bot(True)
    result = await bot.update_chat_settings(123, title="New Title")
    assert result is True


async def test_update_chat_settings_description():
    bot = _make_bot(True)
    result = await bot.update_chat_settings(123, description="New desc")
    assert result is True


async def test_manage_topics_list():
    bot = _make_bot()
    result = await bot.manage_topics(123, "list")
    assert result == {"topics": []}


async def test_manage_topics_create():
    topic = {"message_thread_id": 10, "name": "New Topic"}
    bot = _make_bot(topic)
    result = await bot.manage_topics(123, "create", name="New Topic")
    assert result["name"] == "New Topic"


async def test_manage_topics_close():
    bot = _make_bot(True)
    result = await bot.manage_topics(123, "close", topic_id=10)
    assert result == {"closed": True}


async def test_manage_topics_unknown():
    bot = _make_bot()
    result = await bot.manage_topics(123, "unknown")
    assert "error" in result


# --- Media ---


async def test_send_media_url():
    msg = {"message_id": 50}
    bot = _make_bot(msg)
    result = await bot.send_media(
        123, "photo", "https://example.com/photo.jpg", caption="Nice"
    )
    assert result["message_id"] == 50


async def test_send_media_file(tmp_path):
    f = tmp_path / "test.jpg"
    f.write_bytes(b"fake image data")
    msg = {"message_id": 51}
    bot = _make_bot(msg)
    result = await bot.send_media(123, "photo", str(f))
    assert result["message_id"] == 51


async def test_send_media_file_not_found():
    bot = _make_bot()
    with pytest.raises(FileNotFoundError, match="File not found"):
        await bot.send_media(123, "photo", "/nonexistent/file.jpg")


# --- API error handling ---


async def test_api_error_handling():
    bot = _make_bot("Bad Request: chat not found", ok=False)
    with pytest.raises(TelegramAPIError, match="Bad Request"):
        await bot.send_message(999, "test")


async def test_api_error_has_error_code():
    bot = _make_bot("Forbidden", ok=False)
    with pytest.raises(TelegramAPIError) as exc_info:
        await bot.send_message(999, "test")
    assert exc_info.value.error_code == 400


# --- Verify request body ---


async def test_send_message_request_body():
    """Verify the correct JSON body is sent to the Telegram API."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"ok": True, "result": {"message_id": 1}},
        )

    bot = BotBackend("123456:ABC-DEF")
    bot._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url=bot._base_url,
    )
    await bot.send_message(123, "hello", parse_mode="HTML")

    assert captured["url"].endswith("/sendMessage")
    assert captured["body"]["chat_id"] == 123
    assert captured["body"]["text"] == "hello"
    assert captured["body"]["parse_mode"] == "HTML"
    # None values should be filtered out
    assert "reply_to_message_id" not in captured["body"]
