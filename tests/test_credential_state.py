"""Tests for non-blocking credential state management."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from better_telegram_mcp.credential_state import (
    CredentialState,
    get_state,
    reset_state,
    set_on_configured,
    trigger_relay_setup,
)


@pytest.fixture(autouse=True)
def _reset_module_state():
    """Ensure state is clean before each test."""
    import better_telegram_mcp.credential_state as cs

    cs._state = CredentialState.AWAITING_SETUP
    cs._setup_url = None
    cs._on_configured_callback = None
    yield


def test_get_state_default():
    assert get_state() == CredentialState.AWAITING_SETUP


def test_reset_state():
    import better_telegram_mcp.credential_state as cs

    cs._state = CredentialState.CONFIGURED
    cs._setup_url = "https://relay"
    reset_state()
    assert cs._state == CredentialState.AWAITING_SETUP
    assert cs._setup_url is None


@pytest.mark.asyncio
async def test_on_configured_registration():
    import better_telegram_mcp.credential_state as cs

    callback = AsyncMock()
    set_on_configured(callback)
    assert cs._on_configured_callback == callback


# ---------------------------------------------------------------------------
# trigger_relay_setup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trigger_relay_already_in_progress():
    """If setup is in progress, return existing setup URL without re-triggering."""
    import better_telegram_mcp.credential_state as cs

    cs._state = CredentialState.SETUP_IN_PROGRESS
    cs._setup_url = "https://relay.example.com/existing"

    with patch("mcp_relay_core.acquire_session_lock") as mock_lock:
        result = await trigger_relay_setup()

    assert result == "https://relay.example.com/existing"
    mock_lock.assert_not_called()


@pytest.mark.asyncio
async def test_trigger_relay_already_configured():
    """If configured, return None (no setup needed)."""
    import better_telegram_mcp.credential_state as cs

    cs._state = CredentialState.CONFIGURED

    with patch("mcp_relay_core.acquire_session_lock") as mock_lock:
        result = await trigger_relay_setup()

    assert result is None
    mock_lock.assert_not_called()


@pytest.mark.asyncio
async def test_trigger_relay_uses_existing_session():
    """If another process already has a session lock, reuse it."""
    mock_session_info = MagicMock()
    mock_session_info.relay_url = "https://relay.example.com/locked"

    with patch(
        "mcp_relay_core.acquire_session_lock",
        new_callable=AsyncMock,
        return_value=mock_session_info,
    ):
        result = await trigger_relay_setup()

    assert result == "https://relay.example.com/locked"
    assert get_state() == CredentialState.SETUP_IN_PROGRESS


@pytest.mark.asyncio
async def test_trigger_relay_creates_new_session():
    """No existing lock -> create new session, save lock, open browser."""
    mock_session = MagicMock()
    mock_session.session_id = "sess-123"
    mock_session.relay_url = "https://relay.example.com/new"

    with (
        patch(
            "mcp_relay_core.acquire_session_lock",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "mcp_relay_core.relay.client.create_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ),
        patch(
            "mcp_relay_core.write_session_lock",
            new_callable=AsyncMock,
        ) as mock_write_lock,
        patch("mcp_relay_core.try_open_browser") as mock_browser,
        patch(
            "better_telegram_mcp.credential_state._poll_relay_background",
            new_callable=MagicMock,
        ),
        patch("asyncio.create_task") as mock_create_task,
    ):
        result = await trigger_relay_setup()

    assert result == "https://relay.example.com/new"
    assert get_state() == CredentialState.SETUP_IN_PROGRESS
    mock_write_lock.assert_awaited_once()
    mock_browser.assert_called_once_with("https://relay.example.com/new")
    mock_create_task.assert_called_once()


@pytest.mark.asyncio
async def test_trigger_relay_force_reconfigures():
    """force=True triggers relay even when state is CONFIGURED."""
    import better_telegram_mcp.credential_state as cs

    cs._state = CredentialState.CONFIGURED

    mock_session_info = MagicMock()
    mock_session_info.relay_url = "https://relay.example.com/forced"

    with (
        patch(
            "mcp_relay_core.acquire_session_lock",
            new_callable=AsyncMock,
            return_value=mock_session_info,
        ),
        patch("mcp_relay_core.try_open_browser"),
        patch(
            "better_telegram_mcp.credential_state._poll_relay_background",
            new_callable=MagicMock,
        ),
        patch("asyncio.create_task") as mock_create_task,
    ):
        result = await trigger_relay_setup(force=True)

    assert result == "https://relay.example.com/forced"
    assert cs._state == CredentialState.SETUP_IN_PROGRESS
    # Reusing existing session lock if force=True and it exists is expected
    mock_create_task.assert_not_called()


@pytest.mark.asyncio
async def test_trigger_relay_exception_returns_none():
    """Relay setup failure -> returns None, state back to AWAITING_SETUP."""
    with (
        patch(
            "mcp_relay_core.acquire_session_lock",
            new_callable=AsyncMock,
            side_effect=Exception("network error"),
        ),
        patch("asyncio.create_task"),
    ):
        result = await trigger_relay_setup()

    assert result is None
    assert get_state() == CredentialState.AWAITING_SETUP


# ---------------------------------------------------------------------------
# _poll_relay_background
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_poll_relay_background_bot_mode():
    """Bot mode config -> save + apply env + notify complete."""
    import better_telegram_mcp.credential_state as cs
    from better_telegram_mcp.credential_state import _poll_relay_background

    cs._state = CredentialState.SETUP_IN_PROGRESS

    mock_session = MagicMock()
    mock_session.session_id = "sess-bot"
    config = {"TELEGRAM_BOT_TOKEN": "bot:token123"}

    mock_callback = AsyncMock()
    cs._on_configured_callback = mock_callback

    # We need to ensure TELEGRAM_BOT_TOKEN is NOT in env before the call
    with (
        patch.dict(os.environ, {}, clear=True),
        patch(
            "mcp_relay_core.relay.client.poll_for_result",
            new_callable=AsyncMock,
            return_value=config,
        ),
        patch("mcp_relay_core.storage.config_file.write_config"),
        patch(
            "better_telegram_mcp.relay_setup._is_user_mode_config",
            return_value=False,
        ),
        patch(
            "mcp_relay_core.relay.client.send_message",
            new_callable=AsyncMock,
        ) as mock_send,
        patch(
            "mcp_relay_core.release_session_lock",
            new_callable=AsyncMock,
        ),
    ):
        await _poll_relay_background("https://relay", mock_session, None)

        assert cs._state == CredentialState.CONFIGURED
        assert os.environ.get("TELEGRAM_BOT_TOKEN") == "bot:token123"
        mock_callback.assert_awaited_once()
        # Should send complete message
        mock_send.assert_awaited()
        last_call = mock_send.call_args
        assert last_call.args[2]["type"] == "complete"


@pytest.mark.asyncio
async def test_poll_relay_background_user_mode():
    """User mode config -> save + call _handle_user_mode_auth."""
    import better_telegram_mcp.credential_state as cs
    from better_telegram_mcp.credential_state import _poll_relay_background

    cs._state = CredentialState.SETUP_IN_PROGRESS

    mock_session = MagicMock()
    mock_session.session_id = "sess-user"
    config = {"TELEGRAM_PHONE": "+84912345678"}

    with (
        patch.dict(os.environ, {}, clear=True),
        patch(
            "mcp_relay_core.relay.client.poll_for_result",
            new_callable=AsyncMock,
            return_value=config,
        ),
        patch("mcp_relay_core.storage.config_file.write_config"),
        patch(
            "better_telegram_mcp.relay_setup._is_user_mode_config",
            return_value=True,
        ),
        patch(
            "better_telegram_mcp.credential_state._handle_user_mode_auth",
            new_callable=AsyncMock,
        ) as mock_auth,
        patch(
            "mcp_relay_core.release_session_lock",
            new_callable=AsyncMock,
        ),
    ):
        await _poll_relay_background("https://relay", mock_session, 60.0)

    assert cs._state == CredentialState.CONFIGURED
    mock_auth.assert_awaited_once()


@pytest.mark.asyncio
async def test_poll_relay_background_relay_skipped():
    """RELAY_SKIPPED error -> state back to AWAITING_SETUP."""
    import better_telegram_mcp.credential_state as cs
    from better_telegram_mcp.credential_state import _poll_relay_background

    cs._state = CredentialState.SETUP_IN_PROGRESS

    mock_session = MagicMock()

    with patch(
        "mcp_relay_core.relay.client.poll_for_result",
        new_callable=AsyncMock,
        side_effect=RuntimeError("RELAY_SKIPPED by user"),
    ):
        await _poll_relay_background("https://relay", mock_session, None)

    assert cs._state == CredentialState.AWAITING_SETUP


@pytest.mark.asyncio
async def test_poll_relay_background_runtime_error():
    """Non-RELAY_SKIPPED RuntimeError -> state back to AWAITING_SETUP."""
    import better_telegram_mcp.credential_state as cs
    from better_telegram_mcp.credential_state import _poll_relay_background

    cs._state = CredentialState.SETUP_IN_PROGRESS

    mock_session = MagicMock()

    with patch(
        "mcp_relay_core.relay.client.poll_for_result",
        new_callable=AsyncMock,
        side_effect=RuntimeError("connection reset"),
    ):
        await _poll_relay_background("https://relay", mock_session, None)

    assert cs._state == CredentialState.AWAITING_SETUP


@pytest.mark.asyncio
async def test_poll_relay_background_generic_exception():
    """Generic exception -> state back to AWAITING_SETUP."""
    import better_telegram_mcp.credential_state as cs
    from better_telegram_mcp.credential_state import _poll_relay_background

    cs._state = CredentialState.SETUP_IN_PROGRESS

    mock_session = MagicMock()

    with patch(
        "mcp_relay_core.relay.client.poll_for_result",
        new_callable=AsyncMock,
        side_effect=ValueError("bad data"),
    ):
        await _poll_relay_background("https://relay", mock_session, None)

    assert cs._state == CredentialState.AWAITING_SETUP


@pytest.mark.asyncio
async def test_poll_relay_background_bot_send_message_error():
    """Bot mode: send_message failure is swallowed, state still CONFIGURED."""
    import better_telegram_mcp.credential_state as cs
    from better_telegram_mcp.credential_state import _poll_relay_background

    cs._state = CredentialState.SETUP_IN_PROGRESS

    mock_session = MagicMock()
    mock_session.session_id = "sess-err"
    config = {"TELEGRAM_BOT_TOKEN": "bot:errtoken"}

    with (
        patch.dict(os.environ, {}, clear=True),
        patch(
            "mcp_relay_core.relay.client.poll_for_result",
            new_callable=AsyncMock,
            return_value=config,
        ),
        patch("mcp_relay_core.storage.config_file.write_config"),
        patch(
            "better_telegram_mcp.relay_setup._is_user_mode_config",
            return_value=False,
        ),
        patch(
            "mcp_relay_core.relay.client.send_message",
            new_callable=AsyncMock,
            side_effect=Exception("send failed"),
        ),
        patch(
            "mcp_relay_core.release_session_lock",
            new_callable=AsyncMock,
        ),
    ):
        await _poll_relay_background("https://relay", mock_session, None)

    assert cs._state == CredentialState.CONFIGURED


@pytest.mark.asyncio
async def test_poll_relay_background_custom_timeout():
    """Custom timeout is passed through to poll_for_result."""
    import better_telegram_mcp.credential_state as cs
    from better_telegram_mcp.credential_state import _poll_relay_background

    cs._state = CredentialState.SETUP_IN_PROGRESS

    mock_session = MagicMock()
    mock_session.session_id = "sess-timeout"
    config = {"TELEGRAM_BOT_TOKEN": "bot:timeout"}

    with (
        patch.dict(os.environ, {}, clear=True),
        patch(
            "mcp_relay_core.relay.client.poll_for_result",
            new_callable=AsyncMock,
            return_value=config,
        ) as mock_poll,
        patch("mcp_relay_core.storage.config_file.write_config"),
        patch(
            "better_telegram_mcp.relay_setup._is_user_mode_config",
            return_value=False,
        ),
        patch(
            "mcp_relay_core.relay.client.send_message",
            new_callable=AsyncMock,
        ),
        patch(
            "mcp_relay_core.release_session_lock",
            new_callable=AsyncMock,
        ),
    ):
        await _poll_relay_background("https://relay", mock_session, 120.0)

    mock_poll.assert_awaited_once()
    call_kwargs = mock_poll.call_args
    assert call_kwargs.kwargs["timeout_s"] == 120.0


# ---------------------------------------------------------------------------
# _handle_user_mode_auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_user_mode_auth_already_authorized():
    """User is already authorized -> send complete message."""
    from better_telegram_mcp.credential_state import _handle_user_mode_auth

    config = {"TELEGRAM_PHONE": "+84912345678"}

    mock_backend = AsyncMock()
    mock_backend.is_authorized = AsyncMock(return_value=True)

    mock_session = MagicMock()
    mock_session.session_id = "sess-auth"

    mock_settings = MagicMock()

    with (
        patch(
            "better_telegram_mcp.config.Settings.from_relay_config",
            return_value=mock_settings,
        ),
        patch(
            "better_telegram_mcp.backends.user_backend.UserBackend",
            return_value=mock_backend,
        ),
        patch(
            "mcp_relay_core.relay.client.send_message",
            new_callable=AsyncMock,
        ) as mock_send,
    ):
        await _handle_user_mode_auth("https://relay", mock_session, config)

    mock_backend.connect.assert_awaited_once()
    mock_backend.disconnect.assert_awaited_once()
    # Should send "already authorized" complete message
    mock_send.assert_awaited()
    last_call = mock_send.call_args
    assert last_call.args[2]["type"] == "complete"


@pytest.mark.asyncio
async def test_handle_user_mode_auth_needs_auth():
    """User not authorized -> calls _relay_telethon_auth."""
    from better_telegram_mcp.credential_state import _handle_user_mode_auth

    config = {"TELEGRAM_PHONE": "+84912345678"}

    mock_backend = AsyncMock()
    mock_backend.is_authorized = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.session_id = "sess-unauth"

    mock_settings = MagicMock()

    with (
        patch(
            "better_telegram_mcp.config.Settings.from_relay_config",
            return_value=mock_settings,
        ),
        patch(
            "better_telegram_mcp.backends.user_backend.UserBackend",
            return_value=mock_backend,
        ),
        patch(
            "mcp_relay_core.relay.client.send_message",
            new_callable=AsyncMock,
        ),
        patch(
            "better_telegram_mcp.relay_setup._relay_telethon_auth",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_auth,
    ):
        await _handle_user_mode_auth("https://relay", mock_session, config)

    mock_auth.assert_awaited_once()
    mock_backend.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_user_mode_auth_auth_fails():
    """User auth fails -> logs warning, disconnect still called."""
    from better_telegram_mcp.credential_state import _handle_user_mode_auth

    config = {"TELEGRAM_PHONE": "+84912345678"}

    mock_backend = AsyncMock()
    mock_backend.is_authorized = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.session_id = "sess-fail"

    mock_settings = MagicMock()

    with (
        patch(
            "better_telegram_mcp.config.Settings.from_relay_config",
            return_value=mock_settings,
        ),
        patch(
            "better_telegram_mcp.backends.user_backend.UserBackend",
            return_value=mock_backend,
        ),
        patch(
            "mcp_relay_core.relay.client.send_message",
            new_callable=AsyncMock,
        ),
        patch(
            "better_telegram_mcp.relay_setup._relay_telethon_auth",
            new_callable=AsyncMock,
            return_value=False,
        ),
    ):
        await _handle_user_mode_auth("https://relay", mock_session, config)

    # disconnect called even on failure (via finally)
    mock_backend.disconnect.assert_awaited_once()


# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------


def test_credential_keys():
    from better_telegram_mcp.credential_state import (
        CREDENTIAL_KEYS_BOT,
        CREDENTIAL_KEYS_USER,
    )

    assert "TELEGRAM_BOT_TOKEN" in CREDENTIAL_KEYS_BOT
    assert "TELEGRAM_PHONE" in CREDENTIAL_KEYS_USER
