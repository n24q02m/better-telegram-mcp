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
    cs._step_backend = None
    cs._step_phone = ""
    cs._step_otp_code = None
    yield
    cs._state = old_state
    cs._setup_url = old_url
    cs._step_backend = None
    cs._step_phone = ""
    cs._step_otp_code = None


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

    with patch("mcp_core.storage.config_file.delete_config") as mock_delete:
        reset_state()

    assert get_state() == CredentialState.AWAITING_SETUP
    assert get_setup_url() is None
    mock_delete.assert_called_once_with("better-telegram-mcp")


def test_reset_state_delete_config_error():
    """reset_state logs delete_config errors."""
    import better_telegram_mcp.credential_state as cs

    cs._state = CredentialState.CONFIGURED
    cs._setup_url = "https://example.com/setup"

    with (
        patch(
            "mcp_core.storage.config_file.delete_config",
            side_effect=Exception("disk error"),
        ),
        patch("better_telegram_mcp.credential_state.logger") as mock_logger,
    ):
        reset_state()
    mock_logger.warning.assert_called_once()

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

        with patch("mcp_core.storage.config_file.read_config", return_value=saved):
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

        with patch("mcp_core.storage.config_file.read_config", return_value=saved):
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
            patch("mcp_core.storage.config_file.read_config", return_value=saved),
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
            patch("mcp_core.storage.config_file.read_config", return_value=None),
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
                "mcp_core.storage.config_file.read_config",
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
            patch("mcp_core.storage.config_file.read_config", return_value=None),
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
            patch("mcp_core.storage.config_file.read_config", return_value=None),
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
        "mcp_core.acquire_session_lock",
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
            "mcp_core.acquire_session_lock",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "mcp_core.relay.client.create_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ),
        patch(
            "mcp_core.write_session_lock",
            new_callable=AsyncMock,
        ) as mock_write_lock,
        patch("mcp_core.try_open_browser") as mock_browser,
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
            "mcp_core.acquire_session_lock",
            new_callable=AsyncMock,
            return_value=mock_session_info,
        ),
        patch("mcp_core.try_open_browser"),
        patch("asyncio.create_task", return_value=MagicMock()),
    ):
        result = await trigger_relay_setup(force=True)

    assert result == "https://relay.example.com/forced"
    assert cs._state == CredentialState.SETUP_IN_PROGRESS


@pytest.mark.asyncio
async def test_trigger_relay_exception_returns_none():
    """Relay setup failure -> returns None, state back to AWAITING_SETUP."""
    with (
        patch(
            "mcp_core.acquire_session_lock",
            new_callable=AsyncMock,
            side_effect=Exception("network error"),
        ),
        patch("asyncio.create_task", return_value=MagicMock()),
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
            "mcp_core.relay.client.poll_for_result",
            new_callable=AsyncMock,
            return_value=config,
        ),
        patch("mcp_core.storage.config_file.write_config") as mock_write,
        patch(
            "better_telegram_mcp.relay_setup._is_user_mode_config",
            return_value=False,
        ),
        patch(
            "mcp_core.relay.client.send_message",
            new_callable=AsyncMock,
        ) as mock_send,
        patch(
            "mcp_core.release_session_lock",
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
async def test_poll_relay_background_user_mode_runs_otp_flow():
    """User mode: relay drives full OTP multi-step via input_required messages.

    Flow: poll_for_result returns phone -> save_credentials triggers Telethon
    send_code -> server pushes input_required for OTP via send_message ->
    poll_for_responses gets OTP -> on_step_submitted verifies with Telethon ->
    server pushes 'complete' message. No 2FA in this test case.
    """
    import better_telegram_mcp.credential_state as cs
    from better_telegram_mcp.credential_state import _poll_relay_background

    cs._state = CredentialState.SETUP_IN_PROGRESS

    mock_session = MagicMock()
    mock_session.session_id = "sess-789"
    config = {"TELEGRAM_PHONE": "+84912345678"}

    with (
        patch.dict(os.environ, {}, clear=False),
        patch(
            "mcp_core.relay.client.poll_for_result",
            new_callable=AsyncMock,
            return_value=config,
        ),
        patch("mcp_core.storage.config_file.write_config"),
        patch(
            "better_telegram_mcp.credential_state.save_credentials",
            new_callable=AsyncMock,
            return_value={
                "type": "otp_required",
                "text": "Enter OTP",
                "field": "otp_code",
                "input_type": "text",
            },
        ) as mock_save,
        patch(
            "better_telegram_mcp.credential_state.on_step_submitted",
            new_callable=AsyncMock,
            return_value=None,
        ) as mock_step,
        patch(
            "mcp_core.relay.client.send_message",
            new_callable=AsyncMock,
            return_value="msg-otp-1",
        ) as mock_send,
        patch(
            "mcp_core.relay.client.poll_for_responses",
            new_callable=AsyncMock,
            return_value="12345",
        ) as mock_poll_resp,
        patch(
            "mcp_core.release_session_lock",
            new_callable=AsyncMock,
        ),
    ):
        os.environ.pop("TELEGRAM_PHONE", None)
        await _poll_relay_background("https://relay", mock_session, 60.0)

    mock_save.assert_awaited_once_with(config)
    mock_poll_resp.assert_awaited_once()
    mock_step.assert_awaited_once_with({"otp_code": "12345"})
    # send_message called at least twice: once for input_required, once for complete
    assert mock_send.await_count >= 2
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
        "mcp_core.relay.client.poll_for_result",
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
        "mcp_core.relay.client.poll_for_result",
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
        "mcp_core.relay.client.poll_for_result",
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
            "mcp_core.relay.client.poll_for_result",
            new_callable=AsyncMock,
            return_value=config,
        ),
        patch("mcp_core.storage.config_file.write_config"),
        patch(
            "better_telegram_mcp.relay_setup._is_user_mode_config",
            return_value=False,
        ),
        patch(
            "mcp_core.relay.client.send_message",
            new_callable=AsyncMock,
            side_effect=Exception("send failed"),
        ),
        patch(
            "mcp_core.release_session_lock",
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
            "mcp_core.relay.client.poll_for_result",
            new_callable=AsyncMock,
            return_value=config,
        ) as mock_poll,
        patch("mcp_core.storage.config_file.write_config"),
        patch(
            "better_telegram_mcp.relay_setup._is_user_mode_config",
            return_value=False,
        ),
        patch(
            "mcp_core.relay.client.send_message",
            new_callable=AsyncMock,
        ),
        patch(
            "mcp_core.release_session_lock",
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
# Module constants
# ---------------------------------------------------------------------------


def test_credential_keys():
    from better_telegram_mcp.credential_state import (
        CREDENTIAL_KEYS_BOT,
        CREDENTIAL_KEYS_USER,
    )

    assert "TELEGRAM_BOT_TOKEN" in CREDENTIAL_KEYS_BOT
    assert "TELEGRAM_PHONE" in CREDENTIAL_KEYS_USER


# ---------------------------------------------------------------------------
# save_credentials + multi-step OTP via /otp endpoint
# ---------------------------------------------------------------------------


async def test_save_credentials_bot_mode_returns_none():
    """Bot mode (token only) should complete immediately."""
    from better_telegram_mcp.credential_state import save_credentials

    with patch("mcp_core.storage.config_file.write_config"):
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        result = await save_credentials({"TELEGRAM_BOT_TOKEN": "123:abc"})
    assert result is None

    # Cleanup
    os.environ.pop("TELEGRAM_BOT_TOKEN", None)


async def test_save_credentials_user_mode_returns_otp_required():
    """User mode (phone only) should return otp_required next_step."""
    from better_telegram_mcp.credential_state import save_credentials

    mock_backend = MagicMock()
    mock_backend.connect = AsyncMock()
    mock_backend.send_code = AsyncMock()

    with (
        patch("mcp_core.storage.config_file.write_config"),
        patch(
            "better_telegram_mcp.backends.user_backend.UserBackend",
            return_value=mock_backend,
        ),
    ):
        os.environ.pop("TELEGRAM_PHONE", None)
        result = await save_credentials({"TELEGRAM_PHONE": "+1234567890"})

    assert result is not None
    assert result["type"] == "otp_required"
    assert result["field"] == "otp_code"
    assert result["input_type"] == "text"

    # Cleanup
    os.environ.pop("TELEGRAM_PHONE", None)


async def test_save_credentials_user_mode_telethon_failure_returns_error():
    """If UserBackend import/construction fails, return error dict."""
    from better_telegram_mcp.credential_state import save_credentials

    with (
        patch("mcp_core.storage.config_file.write_config"),
        patch(
            "better_telegram_mcp.config.Settings.from_relay_config",
            side_effect=RuntimeError("bad settings"),
        ),
    ):
        os.environ.pop("TELEGRAM_PHONE", None)
        result = await save_credentials({"TELEGRAM_PHONE": "+1234567890"})

    assert result is not None
    assert result["type"] == "error"
    assert "Failed to send OTP" in result["text"]

    # Cleanup
    os.environ.pop("TELEGRAM_PHONE", None)


async def test_on_step_submitted_no_session_returns_error():
    """Without active session, /otp submission returns error."""
    from better_telegram_mcp.credential_state import on_step_submitted

    result = await on_step_submitted({"otp_code": "12345"})
    assert result is not None
    assert result["type"] == "error"


async def test_on_step_submitted_otp_success_returns_none():
    """OTP success should finalize auth and return None."""
    import better_telegram_mcp.credential_state as cs

    mock_backend = MagicMock()
    mock_backend.sign_in = AsyncMock(return_value={"authenticated_as": "User"})
    mock_backend.disconnect = AsyncMock()
    cs._step_backend = mock_backend
    cs._step_phone = "+1234567890"

    result = await cs.on_step_submitted({"otp_code": "12345"})
    assert result is None
    assert cs._state == cs.CredentialState.CONFIGURED


async def test_on_step_submitted_needs_2fa_returns_password_required():
    """When Telethon indicates 2FA needed, return password_required."""
    import better_telegram_mcp.credential_state as cs

    mock_backend = MagicMock()
    mock_backend.sign_in = AsyncMock(
        side_effect=Exception("SessionPasswordNeededError: password required")
    )
    cs._step_backend = mock_backend
    cs._step_phone = "+1234567890"

    result = await cs.on_step_submitted({"otp_code": "12345"})
    assert result is not None
    assert result["type"] == "password_required"
    assert result["field"] == "password"
    assert result["input_type"] == "password"
    # 2FA path: backend must be kept for password submission.
    assert cs._step_backend is mock_backend


async def test_on_step_submitted_otp_invalid_returns_error():
    """When OTP is invalid (non-2FA error), return error and clean up."""
    import better_telegram_mcp.credential_state as cs

    mock_backend = MagicMock()
    mock_backend.sign_in = AsyncMock(side_effect=Exception("phone code invalid"))
    mock_backend.disconnect = AsyncMock()
    cs._step_backend = mock_backend
    cs._step_phone = "+1234567890"

    result = await cs.on_step_submitted({"otp_code": "00000"})
    assert result is not None
    assert result["type"] == "error"
    assert "Authentication failed" in result["text"]
    # Terminal failure cleans up backend so retry starts fresh.
    assert cs._step_backend is None
    mock_backend.disconnect.assert_awaited_once()


async def test_on_step_submitted_password_success_returns_none():
    """2FA password success should finalize."""
    import better_telegram_mcp.credential_state as cs

    mock_backend = MagicMock()
    mock_backend.sign_in = AsyncMock(return_value={"authenticated_as": "User"})
    mock_backend.disconnect = AsyncMock()
    cs._step_backend = mock_backend
    cs._step_phone = "+1234567890"
    cs._step_otp_code = "12345"

    result = await cs.on_step_submitted({"password": "secret"})
    assert result is None
    assert cs._state == cs.CredentialState.CONFIGURED


async def test_on_step_submitted_password_no_otp_returns_error():
    """Password submission without prior OTP should error (restart needed)."""
    import better_telegram_mcp.credential_state as cs

    mock_backend = MagicMock()
    cs._step_backend = mock_backend
    cs._step_phone = "+1234567890"
    cs._step_otp_code = None

    result = await cs.on_step_submitted({"password": "secret"})
    assert result is not None
    assert result["type"] == "error"


async def test_on_step_submitted_password_failure_returns_error():
    """2FA password failure returns error and cleans up backend."""
    import better_telegram_mcp.credential_state as cs

    mock_backend = MagicMock()
    mock_backend.sign_in = AsyncMock(side_effect=Exception("wrong password"))
    mock_backend.disconnect = AsyncMock()
    cs._step_backend = mock_backend
    cs._step_phone = "+1234567890"
    cs._step_otp_code = "12345"

    result = await cs.on_step_submitted({"password": "wrong"})
    assert result is not None
    assert result["type"] == "error"
    assert "2FA failed" in result["text"]
    # Terminal failure cleans up.
    assert cs._step_backend is None
    mock_backend.disconnect.assert_awaited_once()


async def test_on_step_submitted_unexpected_input_returns_error():
    """Unknown keys in step_data -> error."""
    import better_telegram_mcp.credential_state as cs

    cs._step_backend = MagicMock()

    result = await cs.on_step_submitted({"random_key": "value"})
    assert result is not None
    assert result["type"] == "error"
