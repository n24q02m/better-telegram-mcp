from __future__ import annotations

import json

import pytest

from better_telegram_mcp.backends.base import ModeError
from better_telegram_mcp.tools.messages import handle_messages


@pytest.mark.asyncio
async def test_send(mock_backend):
    result = json.loads(
        await handle_messages(mock_backend, "send", chat_id=123, text="hello")
    )
    assert result["message_id"] == 1
    mock_backend.send_message.assert_awaited_once_with(
        123, "hello", reply_to=None, parse_mode=None
    )


@pytest.mark.asyncio
async def test_send_with_reply_and_parse_mode(mock_backend):
    result = json.loads(
        await handle_messages(
            mock_backend,
            "send",
            chat_id=123,
            text="hi",
            reply_to=5,
            parse_mode="HTML",
        )
    )
    assert result["message_id"] == 1
    mock_backend.send_message.assert_awaited_once_with(
        123, "hi", reply_to=5, parse_mode="HTML"
    )


@pytest.mark.asyncio
async def test_send_missing_params(mock_backend):
    result = json.loads(await handle_messages(mock_backend, "send"))
    assert "error" in result

    result = json.loads(await handle_messages(mock_backend, "send", chat_id=123))
    assert "error" in result


@pytest.mark.asyncio
async def test_edit(mock_backend):
    result = json.loads(
        await handle_messages(
            mock_backend, "edit", chat_id=123, message_id=1, text="edited"
        )
    )
    assert result["message_id"] == 1
    mock_backend.edit_message.assert_awaited_once_with(
        123, 1, "edited", parse_mode=None
    )


@pytest.mark.asyncio
async def test_edit_missing_params(mock_backend):
    result = json.loads(
        await handle_messages(mock_backend, "edit", chat_id=123, text="x")
    )
    assert "error" in result

    result = json.loads(
        await handle_messages(mock_backend, "edit", chat_id=123, message_id=1)
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_delete(mock_backend):
    result = json.loads(
        await handle_messages(mock_backend, "delete", chat_id=123, message_id=1)
    )
    assert result["deleted"] is True


@pytest.mark.asyncio
async def test_delete_missing_params(mock_backend):
    result = json.loads(await handle_messages(mock_backend, "delete", chat_id=123))
    assert "error" in result


@pytest.mark.asyncio
async def test_forward(mock_backend):
    result = json.loads(
        await handle_messages(
            mock_backend,
            "forward",
            from_chat=1,
            to_chat=2,
            message_id=10,
        )
    )
    assert result["message_id"] == 2


@pytest.mark.asyncio
async def test_forward_missing_params(mock_backend):
    result = json.loads(
        await handle_messages(mock_backend, "forward", from_chat=1, to_chat=2)
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_pin(mock_backend):
    result = json.loads(
        await handle_messages(mock_backend, "pin", chat_id=123, message_id=1)
    )
    assert result["pinned"] is True


@pytest.mark.asyncio
async def test_pin_missing_params(mock_backend):
    result = json.loads(await handle_messages(mock_backend, "pin", chat_id=123))
    assert "error" in result


@pytest.mark.asyncio
async def test_react(mock_backend):
    result = json.loads(
        await handle_messages(
            mock_backend, "react", chat_id=123, message_id=1, emoji="👍"
        )
    )
    assert result["reacted"] is True


@pytest.mark.asyncio
async def test_react_missing_params(mock_backend):
    result = json.loads(
        await handle_messages(mock_backend, "react", chat_id=123, message_id=1)
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_search(mock_backend):
    result = json.loads(
        await handle_messages(mock_backend, "search", query="test", limit=10)
    )
    assert result["messages"] == []
    assert result["count"] == 0


@pytest.mark.asyncio
async def test_search_missing_params(mock_backend):
    result = json.loads(await handle_messages(mock_backend, "search"))
    assert "error" in result


@pytest.mark.asyncio
async def test_history(mock_backend):
    result = json.loads(
        await handle_messages(
            mock_backend, "history", chat_id=123, limit=5, offset_id=100
        )
    )
    assert result["messages"] == []
    assert result["count"] == 0


@pytest.mark.asyncio
async def test_history_missing_params(mock_backend):
    result = json.loads(await handle_messages(mock_backend, "history"))
    assert "error" in result


@pytest.mark.asyncio
async def test_unknown_action(mock_backend):
    result = json.loads(await handle_messages(mock_backend, "unknown"))
    assert "error" in result
    assert "Unknown action" in result["error"]


@pytest.mark.asyncio
async def test_mode_error(mock_backend):
    mock_backend.search_messages.side_effect = ModeError("user")
    result = json.loads(await handle_messages(mock_backend, "search", query="test"))
    assert "error" in result
    assert "user mode" in result["error"]


@pytest.mark.asyncio
async def test_general_exception(mock_backend):
    mock_backend.send_message.side_effect = RuntimeError("boom")
    result = json.loads(
        await handle_messages(mock_backend, "send", chat_id=1, text="x")
    )
    assert "error" in result
    assert "RuntimeError" in result["error"]
