from __future__ import annotations

import json

import pytest

from better_telegram_mcp.backends.base import ModeError
from better_telegram_mcp.tools.contacts import ContactRequest, handle_contacts


@pytest.mark.asyncio
async def test_list(mock_backend):
    result = json.loads(
        await handle_contacts(mock_backend, ContactRequest(action="list"))
    )
    assert result["contacts"] == []
    assert result["count"] == 0


@pytest.mark.asyncio
async def test_search(mock_backend):
    result = json.loads(
        await handle_contacts(
            mock_backend, ContactRequest(action="search", query="John")
        )
    )
    assert result["contacts"] == []
    assert result["count"] == 0


@pytest.mark.asyncio
async def test_search_missing_params(mock_backend):
    result = json.loads(
        await handle_contacts(mock_backend, ContactRequest(action="search"))
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_add(mock_backend):
    result = json.loads(
        await handle_contacts(
            mock_backend,
            ContactRequest(
                action="add",
                phone="+1234567890",
                first_name="John",
                last_name="Doe",
            ),
        )
    )
    assert result["added"] is True
    mock_backend.add_contact.assert_awaited_once_with(
        "+1234567890", "John", last_name="Doe"
    )


@pytest.mark.asyncio
async def test_add_missing_params(mock_backend):
    result = json.loads(
        await handle_contacts(mock_backend, ContactRequest(action="add", phone="+123"))
    )
    assert "error" in result

    result = json.loads(
        await handle_contacts(
            mock_backend, ContactRequest(action="add", first_name="John")
        )
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_block(mock_backend):
    result = json.loads(
        await handle_contacts(mock_backend, ContactRequest(action="block", user_id=123))
    )
    assert result["blocked"] is True


@pytest.mark.asyncio
async def test_unblock(mock_backend):
    result = json.loads(
        await handle_contacts(
            mock_backend,
            ContactRequest(action="block", user_id=123, unblock=True),
        )
    )
    assert result["unblocked"] is True


@pytest.mark.asyncio
async def test_block_missing_params(mock_backend):
    result = json.loads(
        await handle_contacts(mock_backend, ContactRequest(action="block"))
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_unknown_action(mock_backend):
    result = json.loads(
        await handle_contacts(mock_backend, ContactRequest(action="unknown"))
    )
    assert "error" in result
    assert "Unknown action" in result["error"]


@pytest.mark.asyncio
async def test_mode_error(mock_backend):
    mock_backend.list_contacts.side_effect = ModeError("user")
    result = json.loads(
        await handle_contacts(mock_backend, ContactRequest(action="list"))
    )
    assert "error" in result
    assert "user mode" in result["error"]


@pytest.mark.asyncio
async def test_general_exception(mock_backend):
    mock_backend.add_contact.side_effect = RuntimeError("network error")
    result = json.loads(
        await handle_contacts(
            mock_backend,
            ContactRequest(action="add", phone="+1", first_name="X"),
        )
    )
    assert "error" in result
    assert "RuntimeError" in result["error"]
