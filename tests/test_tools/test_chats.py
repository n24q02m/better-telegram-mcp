from __future__ import annotations

import json

import pytest

from better_telegram_mcp.backends.base import ModeError
from better_telegram_mcp.tools.chats import handle_chats


@pytest.mark.asyncio
async def test_list(mock_backend):
    result = json.loads(await handle_chats(mock_backend, "list", limit=10))
    assert result["chats"] == []
    assert result["count"] == 0


@pytest.mark.asyncio
async def test_info(mock_backend):
    mock_backend.get_chat_info.return_value = {"id": 123, "title": "Test"}
    result = json.loads(await handle_chats(mock_backend, "info", chat_id=123))
    assert result["id"] == 123


@pytest.mark.asyncio
async def test_info_missing_params(mock_backend):
    result = json.loads(await handle_chats(mock_backend, "info"))
    assert "error" in result


@pytest.mark.asyncio
async def test_create(mock_backend):
    mock_backend.create_chat.return_value = {"id": 456, "title": "New"}
    result = json.loads(
        await handle_chats(mock_backend, "create", title="New", is_channel=True)
    )
    assert result["id"] == 456


@pytest.mark.asyncio
async def test_create_missing_params(mock_backend):
    result = json.loads(await handle_chats(mock_backend, "create"))
    assert "error" in result


@pytest.mark.asyncio
async def test_join(mock_backend):
    result = json.loads(
        await handle_chats(mock_backend, "join", link_or_hash="abc123")
    )
    assert result["joined"] is True


@pytest.mark.asyncio
async def test_join_missing_params(mock_backend):
    result = json.loads(await handle_chats(mock_backend, "join"))
    assert "error" in result


@pytest.mark.asyncio
async def test_leave(mock_backend):
    result = json.loads(
        await handle_chats(mock_backend, "leave", chat_id=123)
    )
    assert result["left"] is True


@pytest.mark.asyncio
async def test_leave_missing_params(mock_backend):
    result = json.loads(await handle_chats(mock_backend, "leave"))
    assert "error" in result


@pytest.mark.asyncio
async def test_members(mock_backend):
    result = json.loads(
        await handle_chats(mock_backend, "members", chat_id=123, limit=10)
    )
    assert result["members"] == []
    assert result["count"] == 0


@pytest.mark.asyncio
async def test_members_missing_params(mock_backend):
    result = json.loads(await handle_chats(mock_backend, "members"))
    assert "error" in result


@pytest.mark.asyncio
async def test_admin_promote(mock_backend):
    result = json.loads(
        await handle_chats(mock_backend, "admin", chat_id=123, user_id=456)
    )
    assert result["promoted"] is True


@pytest.mark.asyncio
async def test_admin_demote(mock_backend):
    result = json.loads(
        await handle_chats(
            mock_backend, "admin", chat_id=123, user_id=456, demote=True
        )
    )
    assert result["demoted"] is True


@pytest.mark.asyncio
async def test_admin_missing_params(mock_backend):
    result = json.loads(
        await handle_chats(mock_backend, "admin", chat_id=123)
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_settings(mock_backend):
    result = json.loads(
        await handle_chats(
            mock_backend, "settings", chat_id=123,
            title="New Title", description="New Desc",
        )
    )
    assert result["updated"] is True


@pytest.mark.asyncio
async def test_settings_missing_chat_id(mock_backend):
    result = json.loads(
        await handle_chats(mock_backend, "settings", title="X")
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_settings_no_fields(mock_backend):
    result = json.loads(
        await handle_chats(mock_backend, "settings", chat_id=123)
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_topics(mock_backend):
    mock_backend.manage_topics.return_value = {"topics": []}
    result = json.loads(
        await handle_chats(
            mock_backend, "topics", chat_id=123, topic_action="list"
        )
    )
    assert "topics" in result


@pytest.mark.asyncio
async def test_topics_create(mock_backend):
    mock_backend.manage_topics.return_value = {"topic_id": 1}
    result = json.loads(
        await handle_chats(
            mock_backend, "topics", chat_id=123,
            topic_action="create", topic_name="General",
        )
    )
    assert result["topic_id"] == 1


@pytest.mark.asyncio
async def test_topics_missing_chat_id(mock_backend):
    result = json.loads(
        await handle_chats(mock_backend, "topics", topic_action="list")
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_topics_missing_action(mock_backend):
    result = json.loads(
        await handle_chats(mock_backend, "topics", chat_id=123)
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_unknown_action(mock_backend):
    result = json.loads(await handle_chats(mock_backend, "unknown"))
    assert "error" in result
    assert "Unknown action" in result["error"]


@pytest.mark.asyncio
async def test_mode_error(mock_backend):
    mock_backend.list_chats.side_effect = ModeError("user")
    result = json.loads(await handle_chats(mock_backend, "list"))
    assert "error" in result
    assert "user mode" in result["error"]


@pytest.mark.asyncio
async def test_general_exception(mock_backend):
    mock_backend.get_chat_info.side_effect = RuntimeError("fail")
    result = json.loads(
        await handle_chats(mock_backend, "info", chat_id=123)
    )
    assert "error" in result
    assert "RuntimeError" in result["error"]
