"""Tests for credential_state module -- state machine, resolve, trigger_relay_setup."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from better_telegram_mcp.credential_state import (
    CredentialState,
    get_setup_url,
    get_state,
    reset_state,
    resolve_credential_state,
    set_state,
    trigger_relay_setup,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_credential_state():
    """Reset module-level state before/after each test."""
    import better_telegram_mcp.credential_state as cs

    old_state = cs._state
    old_url = cs._setup_url
    cs._state = CredentialState.AWAITING_SETUP
    cs._setup_url = None
    yield
    cs._state = old_state
    cs._setup_url = old_url


# ---------------------------------------------------------------------------
# CredentialState enum
# ---------------------------------------------------------------------------


def test_credential_state_values():
    assert CredentialState.AWAITING_SETUP.value == "awaiting_setup"
    assert CredentialState.SETUP_IN_PROGRESS.value == "setup_in_progress"
    assert CredentialState.CONFIGURED.value == "configured"


# ---------------------------------------------------------------------------
# get_state / get_setup_url / set_state / reset_state
# ---------------------------------------------------------------------------


def test_get_state_default():
    assert get_state() == CredentialState.AWAITING_SETUP


def test_get_setup_url_default():
    assert get_setup_url() is None


def test_set_state():
    set_state(CredentialState.CONFIGURED)
    assert get_state() == CredentialState.CONFIGURED


def test_set_state_setup_in_progress():
    set_state(CredentialState.SETUP_IN_PROGRESS)
    assert get_state() == CredentialState.SETUP_IN_PROGRESS


def test_reset_state():
    import better_telegram_mcp.credential_state as cs

    cs._state = CredentialState.CONFIGURED
    cs._setup_url = "https://example.com/setup"

    with patch("mcp_relay_core.storage.config_file.delete_config") as mock_delete:
        reset_state()

    assert get_state() == CredentialState.AWAITING_SETUP
    assert get_setup_url() is None
    mock_delete.assert_called_once_with("better-telegram-mcp")


def test_reset_state_delete_config_error():
    """reset_state swallows delete_config errors."""
    import better_telegram_mcp.credential_state as cs

    cs._state = CredentialState.CONFIGURED
    cs._setup_url = "https://example.com/setup"

    with patch(
        "mcp_relay_core.storage.config_file.delete_config",
        side_effect=Exception("disk error"),
    ):
        reset_state()

    assert get_state() == CredentialState.AWAITING_SETUP
    assert get_setup_url() is None


# ---------------------------------------------------------------------------
# resolve_credential_state
# ---------------------------------------------------------------------------


def test_resolve_bot_token_from_env():
    # Clean env of any existing telegram vars, then set only TELEGRAM_BOT_TOKEN
    with patch.dict(
        os.environ,
        {"TELEGRAM_BOT_TOKEN": "fake:token", "TELEGRAM_PHONE": ""},
    ):
        # Clear TELEGRAM_PHONE so the bot token path is hit
        os.environ.pop("TELEGRAM_PHONE", None)
        state = resolve_credential_state()
    assert state == CredentialState.CONFIGURED


def test_resolve_phone_from_env():
    with patch.dict(
        os.environ,
        {"TELEGRAM_PHONE": "+84912345678"},
    ):
        # Ensure no bot token
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        state = resolve_credential_state()
    assert state == CredentialState.CONFIGURED


def test_resolve_from_config_file_bot():
    """Config file has bot token -> CONFIGURED, env var applied."""
    saved = {"TELEGRAM_BOT_TOKEN": "token_from_file"}

    with patch.dict(os.environ, {}, clear=False):
        # Remove keys that would short-circuit
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        os.environ.pop("TELEGRAM_PHONE", None)

        with patch(
            "mcp_relay_core.storage.config_file.read_config", return_value=saved
        ):
            state = resolve_credential_state()

        assert state == CredentialState.CONFIGURED
        assert os.environ.get("TELEGRAM_BOT_TOKEN") == "token_from_file"

    # Cleanup in case patch.dict didn't restore
    os.environ.pop("TELEGRAM_BOT_TOKEN", None)


def test_resolve_from_config_file_user():
    """Config file has phone -> CONFIGURED."""
    saved = {"TELEGRAM_PHONE": "+84912345678"}

    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        os.environ.pop("TELEGRAM_PHONE", None)

        with patch(
            "mcp_relay_core.storage.config_file.read_config", return_value=saved
        ):
            state = resolve_credential_state()

        assert state == CredentialState.CONFIGURED

    os.environ.pop("TELEGRAM_PHONE", None)


def test_resolve_from_config_file_does_not_overwrite_existing_env():
    """Config file values should not overwrite existing env vars."""
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "from_env"}, clear=False):
        # Bot token already in env -> hits env check first, never reads config
        state = resolve_credential_state()

    assert state == CredentialState.CONFIGURED


def test_resolve_config_file_empty():
    """Config file exists but has no credential keys."""
    saved = {"SOME_OTHER_KEY": "value"}

    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        os.environ.pop("TELEGRAM_PHONE", None)

        with (
            patch("mcp_relay_core.storage.config_file.read_config", return_value=saved),
            patch(
                "better_telegram_mcp.credential_state.check_saved_sessions",
                return_value=False,
            ),
        ):
            state = resolve_credential_state()

    assert state == CredentialState.AWAITING_SETUP


def test_resolve_config_file_none():
    """Config file returns None (doesn't exist)."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        os.environ.pop("TELEGRAM_PHONE", None)

        with (
            patch("mcp_relay_core.storage.config_file.read_config", return_value=None),
            patch(
                "better_telegram_mcp.credential_state.check_saved_sessions",
                return_value=False,
            ),
        ):
            state = resolve_credential_state()

    assert state == CredentialState.AWAITING_SETUP


def test_resolve_config_file_read_error():
    """read_config raises -> skip to next check."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        os.environ.pop("TELEGRAM_PHONE", None)

        with (
            patch(
                "mcp_relay_core.storage.config_file.read_config",
                side_effect=Exception("decryption failed"),
            ),
            patch(
                "better_telegram_mcp.credential_state.check_saved_sessions",
                return_value=False,
            ),
        ):
            state = resolve_credential_state()

    assert state == CredentialState.AWAITING_SETUP


def test_resolve_saved_sessions_found():
    """Saved session files found -> stays AWAITING_SETUP (soft signal)."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        os.environ.pop("TELEGRAM_PHONE", None)

        with (
            patch("mcp_relay_core.storage.config_file.read_config", return_value=None),
            patch(
                "better_telegram_mcp.credential_state.check_saved_sessions",
                return_value=True,
            ),
        ):
            state = resolve_credential_state()

    assert state == CredentialState.AWAITING_SETUP


def test_resolve_nothing_found():
    """No env vars, no config file, no sessions -> AWAITING_SETUP."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        os.environ.pop("TELEGRAM_PHONE", None)

        with (
            patch("mcp_relay_core.storage.config_file.read_config", return_value=None),
            patch(
                "better_telegram_mcp.credential_state.check_saved_sessions",
                return_value=False,
            ),
        ):
            state = resolve_credential_state()

    assert state == CredentialState.AWAITING_SETUP


# ---------------------------------------------------------------------------
# trigger_relay_setup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trigger_relay_not_awaiting():
    """When state is not AWAITING_SETUP (and not forced), returns existing URL."""
    import better_telegram_mcp.credential_state as cs

    cs._state = CredentialState.CONFIGURED
    cs._setup_url = "https://relay.example.com/existing"

    result = await trigger_relay_setup()
    assert result == "https://relay.example.com/existing"
    assert cs._state == CredentialState.CONFIGURED


@pytest.mark.asyncio
async def test_trigger_relay_setup_in_progress_no_force():
    """When state is SETUP_IN_PROGRESS (and not forced), returns existing URL."""
    import better_telegram_mcp.credential_state as cs

    cs._state = CredentialState.SETUP_IN_PROGRESS
    cs._setup_url = "https://relay.example.com/in-progress"

    result = await trigger_relay_setup()
    assert result == "https://relay.example.com/in-progress"


@pytest.mark.asyncio
async def test_trigger_relay_reuses_existing_session():
    """Existing session lock -> reuse URL."""
    mock_session_info = MagicMock()
    mock_session_info.relay_url = "https://relay.example.com/reused"

    with patch(
        "mcp_relay_core.acquire_session_lock",
        new_callable=AsyncMock,
        return_value=mock_session_info,
    ):
        result = await trigger_relay_setup()

    assert result == "https://relay.example.com/reused"
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

    with patch(
        "mcp_relay_core.acquire_session_lock",
        new_callable=AsyncMock,
        return_value=mock_session_info,
    ):
        result = await trigger_relay_setup(force=True)

    assert result == "https://relay.example.com/forced"
    assert cs._state == CredentialState.SETUP_IN_PROGRESS


@pytest.mark.asyncio
async def test_trigger_relay_exception_returns_none():
    """Relay setup failure -> returns None, state back to AWAITING_SETUP."""
    with patch(
        "mcp_relay_core.acquire_session_lock",
        new_callable=AsyncMock,
        side_effect=Exception("network error"),
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
    mock_session.session_id = "sess-456"
    config = {"TELEGRAM_BOT_TOKEN": "bot:token123"}

    with (
        patch.dict(os.environ, {}, clear=False),
        patch(
            "mcp_relay_core.relay.client.poll_for_result",
            new_callable=AsyncMock,
            return_value=config,
        ),
        patch("mcp_relay_core.storage.config_file.write_config") as mock_write,
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
        ) as mock_release,
    ):
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        await _poll_relay_background("https://relay", mock_session, None)

        assert cs._state == CredentialState.CONFIGURED
        mock_write.assert_called_once_with("better-telegram-mcp", config)
        mock_send.assert_awaited_once()
        mock_release.assert_awaited_once()
        assert os.environ.get("TELEGRAM_BOT_TOKEN") == "bot:token123"


@pytest.mark.asyncio
async def test_poll_relay_background_user_mode():
    """User mode config -> calls _handle_user_mode_auth."""
    import better_telegram_mcp.credential_state as cs
    from better_telegram_mcp.credential_state import _poll_relay_background

    cs._state = CredentialState.SETUP_IN_PROGRESS

    mock_session = MagicMock()
    mock_session.session_id = "sess-789"
    config = {"TELEGRAM_PHONE": "+84912345678"}

    with (
        patch.dict(os.environ, {}, clear=False),
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
        os.environ.pop("TELEGRAM_PHONE", None)
        await _poll_relay_background("https://relay", mock_session, 60.0)

    assert cs._state == CredentialState.CONFIGURED
    mock_auth.assert_awaited_once()

    # Cleanup
    os.environ.pop("TELEGRAM_PHONE", None)


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
        patch.dict(os.environ, {}, clear=False),
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
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        await _poll_relay_background("https://relay", mock_session, None)

    assert cs._state == CredentialState.CONFIGURED

    # Cleanup
    os.environ.pop("TELEGRAM_BOT_TOKEN", None)


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
        patch.dict(os.environ, {}, clear=False),
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
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        await _poll_relay_background("https://relay", mock_session, 120.0)

    mock_poll.assert_awaited_once()
    call_kwargs = mock_poll.call_args
    assert call_kwargs.kwargs["timeout_s"] == 120.0

    # Cleanup
    os.environ.pop("TELEGRAM_BOT_TOKEN", None)


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
