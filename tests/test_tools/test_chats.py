from __future__ import annotations

import json

import pytest

from better_telegram_mcp.backends.base import ModeError
from better_telegram_mcp.tools.chats import ChatOptions, handle_chats


@pytest.mark.asyncio
async def test_list(mock_backend):
    result = json.loads(await handle_chats(mock_backend, "list", ChatOptions(limit=10)))
    assert result["chats"] == []
    assert result["count"] == 0


@pytest.mark.asyncio
async def test_info(mock_backend):
    mock_backend.get_chat_info.return_value = {"id": 123, "title": "Test"}
    result = json.loads(
        await handle_chats(mock_backend, "info", ChatOptions(chat_id=123))
    )
    assert result["id"] == 123


@pytest.mark.asyncio
async def test_info_missing_params(mock_backend):
    result = json.loads(await handle_chats(mock_backend, "info", ChatOptions()))
    assert "error" in result


@pytest.mark.asyncio
async def test_create(mock_backend):
    mock_backend.create_chat.return_value = {"id": 456, "title": "New"}
    result = json.loads(
        await handle_chats(
            mock_backend, "create", ChatOptions(title="New", is_channel=True)
        )
    )
    assert result["id"] == 456


@pytest.mark.asyncio
async def test_create_missing_params(mock_backend):
    result = json.loads(await handle_chats(mock_backend, "create", ChatOptions()))
    assert "error" in result


@pytest.mark.asyncio
async def test_join(mock_backend):
    result = json.loads(
        await handle_chats(mock_backend, "join", ChatOptions(link_or_hash="abc123"))
    )
    assert result["joined"] is True


@pytest.mark.asyncio
async def test_join_missing_params(mock_backend):
    result = json.loads(await handle_chats(mock_backend, "join", ChatOptions()))
    assert "error" in result


@pytest.mark.asyncio
async def test_leave(mock_backend):
    result = json.loads(
        await handle_chats(mock_backend, "leave", ChatOptions(chat_id=123))
    )
    assert result["left"] is True


@pytest.mark.asyncio
async def test_leave_missing_params(mock_backend):
    result = json.loads(await handle_chats(mock_backend, "leave", ChatOptions()))
    assert "error" in result


@pytest.mark.asyncio
async def test_members(mock_backend):
    result = json.loads(
        await handle_chats(mock_backend, "members", ChatOptions(chat_id=123, limit=10))
    )
    assert result["members"] == []
    assert result["count"] == 0


@pytest.mark.asyncio
async def test_members_missing_params(mock_backend):
    result = json.loads(await handle_chats(mock_backend, "members", ChatOptions()))
    assert "error" in result


@pytest.mark.asyncio
async def test_admin_promote(mock_backend):
    result = json.loads(
        await handle_chats(mock_backend, "admin", ChatOptions(chat_id=123, user_id=456))
    )
    assert result["promoted"] is True


@pytest.mark.asyncio
async def test_admin_demote(mock_backend):
    result = json.loads(
        await handle_chats(
            mock_backend, "admin", ChatOptions(chat_id=123, user_id=456, demote=True)
        )
    )
    assert result["demoted"] is True


@pytest.mark.asyncio
async def test_admin_missing_params(mock_backend):
    result = json.loads(
        await handle_chats(mock_backend, "admin", ChatOptions(chat_id=123))
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_settings(mock_backend):
    result = json.loads(
        await handle_chats(
            mock_backend,
            "settings",
            ChatOptions(
                chat_id=123,
                title="New Title",
                description="New Desc",
            ),
        )
    )
    assert result["updated"] is True


@pytest.mark.asyncio
async def test_settings_missing_chat_id(mock_backend):
    result = json.loads(
        await handle_chats(mock_backend, "settings", ChatOptions(title="X"))
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_settings_no_fields(mock_backend):
    result = json.loads(
        await handle_chats(mock_backend, "settings", ChatOptions(chat_id=123))
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_topics(mock_backend):
    mock_backend.manage_topics.return_value = {"topics": []}
    result = json.loads(
        await handle_chats(
            mock_backend, "topics", ChatOptions(chat_id=123, topic_action="list")
        )
    )
    assert "topics" in result


@pytest.mark.asyncio
async def test_topics_create(mock_backend):
    mock_backend.manage_topics.return_value = {"topic_id": 1}
    result = json.loads(
        await handle_chats(
            mock_backend,
            "topics",
            ChatOptions(
                chat_id=123,
                topic_action="create",
                topic_name="General",
            ),
        )
    )
    assert result["topic_id"] == 1


@pytest.mark.asyncio
async def test_topics_close_with_id(mock_backend):
    mock_backend.manage_topics.return_value = {"closed": True}
    result = json.loads(
        await handle_chats(
            mock_backend,
            "topics",
            ChatOptions(
                chat_id=123,
                topic_action="close",
                topic_id=42,
            ),
        )
    )
    assert result["closed"] is True
    mock_backend.manage_topics.assert_awaited_once_with(123, "close", topic_id=42)


@pytest.mark.asyncio
async def test_topics_missing_chat_id(mock_backend):
    result = json.loads(
        await handle_chats(mock_backend, "topics", ChatOptions(topic_action="list"))
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_topics_missing_action(mock_backend):
    result = json.loads(
        await handle_chats(mock_backend, "topics", ChatOptions(chat_id=123))
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_unknown_action(mock_backend):
    result = json.loads(await handle_chats(mock_backend, "unknown", ChatOptions()))
    assert "error" in result
    assert "Unknown action" in result["error"]


@pytest.mark.asyncio
async def test_mode_error(mock_backend):
    mock_backend.list_chats.side_effect = ModeError("user")
    result = json.loads(await handle_chats(mock_backend, "list", ChatOptions()))
    assert "error" in result
    assert "user mode" in result["error"]


@pytest.mark.asyncio
async def test_general_exception(mock_backend):
    mock_backend.get_chat_info.side_effect = RuntimeError("fail")
    result = json.loads(
        await handle_chats(mock_backend, "info", ChatOptions(chat_id=123))
    )
    assert "error" in result
    assert "RuntimeError" in result["error"]


@pytest.mark.asyncio
async def test_unknown_action_suggestion(mock_backend):
    result = json.loads(await handle_chats(mock_backend, "lisst", ChatOptions()))
    assert "error" in result
    assert "Did you mean 'list'?" in result["error"]


@pytest.mark.asyncio
async def test_settings_title_only(mock_backend):
    result = json.loads(
        await handle_chats(
            mock_backend,
            "settings",
            ChatOptions(chat_id=123, title="Only Title"),
        )
    )
    assert result["updated"] is True
    mock_backend.update_chat_settings.assert_awaited_once_with(123, title="Only Title")


@pytest.mark.asyncio
async def test_settings_description_only(mock_backend):
    result = json.loads(
        await handle_chats(
            mock_backend,
            "settings",
            ChatOptions(chat_id=123, description="Only Desc"),
        )
    )
    assert result["updated"] is True
    mock_backend.update_chat_settings.assert_awaited_once_with(
        123, description="Only Desc"
    )


@pytest.mark.asyncio
async def test_topics_complex(mock_backend):
    mock_backend.manage_topics.return_value = {"ok": True}
    result = json.loads(
        await handle_chats(
            mock_backend,
            "topics",
            ChatOptions(
                chat_id=123,
                topic_action="rename",
                topic_id=42,
                topic_name="New Name",
            ),
        )
    )
    assert result["ok"] is True
    mock_backend.manage_topics.assert_awaited_once_with(
        123, "rename", topic_id=42, name="New Name"
    )
