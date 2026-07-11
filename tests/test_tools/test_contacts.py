from __future__ import annotations

from better_telegram_mcp.backends.base import ModeError
from better_telegram_mcp.backends.security import SecurityError
from better_telegram_mcp.tools.contacts import ContactsOptions, handle_contacts


async def test_list(mock_backend):
    mock_backend.list_contacts.return_value = [{"user_id": 123, "first_name": "John"}]
    result = await handle_contacts(mock_backend, "list")
    assert result["contacts"] == [{"user_id": 123, "first_name": "John"}]
    assert result["count"] == 1
    mock_backend.list_contacts.assert_awaited_once_with()


async def test_search(mock_backend):
    mock_backend.search_contacts.return_value = [{"user_id": 123, "first_name": "John"}]
    result = await handle_contacts(
        mock_backend, "search", ContactsOptions(query="John")
    )
    assert result["contacts"] == [{"user_id": 123, "first_name": "John"}]
    assert result["count"] == 1
    mock_backend.search_contacts.assert_awaited_once_with("John")


async def test_search_missing_params(mock_backend):
    result = await handle_contacts(mock_backend, "search")
    assert "error" in result


async def test_add(mock_backend):
    result = await handle_contacts(
        mock_backend,
        "add",
        ContactsOptions(
            phone="+1234567890",
            first_name="John",
            last_name="Doe",
        ),
    )
    assert result["added"] is True
    mock_backend.add_contact.assert_awaited_once_with(
        "+1234567890", "John", last_name="Doe"
    )


async def test_add_no_last_name(mock_backend):
    result = await handle_contacts(
        mock_backend,
        "add",
        ContactsOptions(
            phone="+1234567890",
            first_name="John",
        ),
    )
    assert result["added"] is True
    mock_backend.add_contact.assert_awaited_once_with(
        "+1234567890", "John", last_name=None
    )


async def test_add_failure(mock_backend):
    mock_backend.add_contact.return_value = False
    result = await handle_contacts(
        mock_backend,
        "add",
        ContactsOptions(
            phone="+1234567890",
            first_name="John",
        ),
    )
    assert result["added"] is False


async def test_add_missing_params(mock_backend):
    result = await handle_contacts(mock_backend, "add", ContactsOptions(phone="+123"))
    assert "error" in result

    result = await handle_contacts(
        mock_backend, "add", ContactsOptions(first_name="John")
    )
    assert "error" in result


async def test_block(mock_backend):
    result = await handle_contacts(mock_backend, "block", ContactsOptions(user_id=123))
    assert result["blocked"] is True
    mock_backend.block_user.assert_awaited_once_with(123, unblock=False)


async def test_block_explicit_false(mock_backend):
    result = await handle_contacts(
        mock_backend, "block", ContactsOptions(user_id=123, unblock=False)
    )
    assert result["blocked"] is True
    mock_backend.block_user.assert_awaited_once_with(123, unblock=False)


async def test_unblock(mock_backend):
    result = await handle_contacts(
        mock_backend, "block", ContactsOptions(user_id=123, unblock=True)
    )
    assert result["unblocked"] is True
    mock_backend.block_user.assert_awaited_once_with(123, unblock=True)


async def test_block_missing_params(mock_backend):
    result = await handle_contacts(mock_backend, "block")
    assert "error" in result


async def test_unknown_action(mock_backend):
    result = await handle_contacts(mock_backend, "unknown")
    assert "error" in result
    assert "Unknown action" in result["error"]


async def test_mode_error(mock_backend):
    mock_backend.list_contacts.side_effect = ModeError("user")
    result = await handle_contacts(mock_backend, "list")
    assert "error" in result
    assert "user mode" in result["error"]


async def test_general_exception(mock_backend):
    mock_backend.add_contact.side_effect = RuntimeError("network error")
    result = await handle_contacts(
        mock_backend, "add", ContactsOptions(phone="+1", first_name="X")
    )
    assert "error" in result
    assert "RuntimeError" in result["error"]


async def test_unknown_action_suggestion(mock_backend):
    result = await handle_contacts(mock_backend, "lisst")
    assert "error" in result
    assert "Did you mean 'list'?" in result["error"]


async def test_security_error(mock_backend):
    mock_backend.list_contacts.side_effect = SecurityError("Blocked")
    result = await handle_contacts(mock_backend, "list")
    assert "error" in result
    assert "Blocked" in result["error"]
