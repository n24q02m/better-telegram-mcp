from __future__ import annotations

import json

import pytest

from better_telegram_mcp.backends.base import ModeError
from better_telegram_mcp.backends.security import SecurityError
from better_telegram_mcp.tools.contacts import ContactsOptions, handle_contacts


@pytest.mark.asyncio
async def test_list(mock_backend):
    result = json.loads(await handle_contacts(mock_backend, "list"))
    assert result["contacts"] == []
    assert result["count"] == 0


@pytest.mark.asyncio
async def test_search(mock_backend):
    result = json.loads(
        await handle_contacts(mock_backend, "search", ContactsOptions(query="John"))
    )
    assert result["contacts"] == []
    assert result["count"] == 0


@pytest.mark.asyncio
async def test_search_missing_params(mock_backend):
    result = json.loads(await handle_contacts(mock_backend, "search"))
    assert result.get("status") == "error" and "message" in result


@pytest.mark.asyncio
async def test_add(mock_backend):
    result = json.loads(
        await handle_contacts(
            mock_backend,
            "add",
            ContactsOptions(
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
        await handle_contacts(mock_backend, "add", ContactsOptions(phone="+123"))
    )
    assert result.get("status") == "error" and "message" in result

    result = json.loads(
        await handle_contacts(mock_backend, "add", ContactsOptions(first_name="John"))
    )
    assert result.get("status") == "error" and "message" in result


@pytest.mark.asyncio
async def test_block(mock_backend):
    result = json.loads(
        await handle_contacts(mock_backend, "block", ContactsOptions(user_id=123))
    )
    assert result["blocked"] is True


@pytest.mark.asyncio
async def test_unblock(mock_backend):
    result = json.loads(
        await handle_contacts(
            mock_backend, "block", ContactsOptions(user_id=123, unblock=True)
        )
    )
    assert result["unblocked"] is True


@pytest.mark.asyncio
async def test_block_missing_params(mock_backend):
    result = json.loads(await handle_contacts(mock_backend, "block"))
    assert result.get("status") == "error" and "message" in result


@pytest.mark.asyncio
async def test_unknown_action(mock_backend):
    result = json.loads(await handle_contacts(mock_backend, "unknown"))
    assert result.get("status") == "error" and "message" in result
    assert "Unknown action" in result["message"]


@pytest.mark.asyncio
async def test_mode_error(mock_backend):
    mock_backend.list_contacts.side_effect = ModeError("user")
    result = json.loads(await handle_contacts(mock_backend, "list"))
    assert result.get("status") == "error" and "message" in result
    assert "user mode" in result["message"]


@pytest.mark.asyncio
async def test_general_exception(mock_backend):
    mock_backend.add_contact.side_effect = RuntimeError("network error")
    result = json.loads(
        await handle_contacts(
            mock_backend, "add", ContactsOptions(phone="+1", first_name="X")
        )
    )
    assert result.get("status") == "error" and "message" in result
    assert "RuntimeError" in result["message"]


@pytest.mark.asyncio
async def test_unknown_action_suggestion(mock_backend):
    result = json.loads(await handle_contacts(mock_backend, "lisst"))
    assert result.get("status") == "error" and "message" in result
    assert "Did you mean 'list'?" in result["message"]


@pytest.mark.asyncio
async def test_security_error(mock_backend):
    mock_backend.list_contacts.side_effect = SecurityError("Blocked")
    result = json.loads(await handle_contacts(mock_backend, "list"))
    assert result.get("status") == "error" and "message" in result
    assert "Blocked" in result["message"]
