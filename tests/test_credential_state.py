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
    old_handle = cs._active_handle
    cs._state = CredentialState.AWAITING_SETUP
    cs._setup_url = None
    cs._active_handle = None
    cs._step_backend = None
    cs._step_phone = ""
    cs._step_otp_code = None
    yield
    cs._state = old_state
    cs._setup_url = old_url
    cs._active_handle = old_handle
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
    cs._setup_url = "http://127.0.0.1:1/setup"

    with patch("mcp_core.storage.config_file.delete_config") as mock_delete:
        reset_state()

    assert get_state() == CredentialState.AWAITING_SETUP
    assert get_setup_url() is None
    mock_delete.assert_called_once_with("better-telegram-mcp")


def test_reset_state_delete_config_error():
    """reset_state logs delete_config errors."""
    import better_telegram_mcp.credential_state as cs

    cs._state = CredentialState.CONFIGURED
    cs._setup_url = "http://127.0.0.1:1/setup"

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
    with patch.dict(
        os.environ,
        {"TELEGRAM_BOT_TOKEN": "fake:token", "TELEGRAM_PHONE": ""},
    ):
        os.environ.pop("TELEGRAM_PHONE", None)
        state = resolve_credential_state()
    assert state == CredentialState.CONFIGURED


def test_resolve_phone_from_env():
    with patch.dict(
        os.environ,
        {"TELEGRAM_PHONE": "+84912345678"},
    ):
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        state = resolve_credential_state()
    assert state == CredentialState.CONFIGURED


def test_resolve_from_config_file_bot():
    """Config file has bot token -> CONFIGURED, env var applied."""
    saved = {"TELEGRAM_BOT_TOKEN": "token_from_file"}

    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        os.environ.pop("TELEGRAM_PHONE", None)

        with patch("mcp_core.storage.config_file.read_config", return_value=saved):
            state = resolve_credential_state()

        assert state == CredentialState.CONFIGURED
        assert os.environ.get("TELEGRAM_BOT_TOKEN") == "token_from_file"

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
# trigger_relay_setup -- local HTTP fallback (no remote relay)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trigger_relay_not_awaiting():
    """When state is not AWAITING_SETUP (and not forced), returns existing URL."""
    import better_telegram_mcp.credential_state as cs

    cs._state = CredentialState.CONFIGURED
    cs._setup_url = "http://127.0.0.1:51000/"

    result = await trigger_relay_setup()
    assert result == "http://127.0.0.1:51000/"
    assert cs._state == CredentialState.CONFIGURED


@pytest.mark.asyncio
async def test_trigger_relay_setup_in_progress_no_force():
    """SETUP_IN_PROGRESS (not forced) -> return existing URL."""
    import better_telegram_mcp.credential_state as cs

    cs._state = CredentialState.SETUP_IN_PROGRESS
    cs._setup_url = "http://127.0.0.1:51001/"

    result = await trigger_relay_setup()
    assert result == "http://127.0.0.1:51001/"


@pytest.mark.asyncio
async def test_trigger_relay_spawns_local_form():
    """AWAITING_SETUP -> spawn local credential form, return URL, open browser."""
    mock_handle = MagicMock()
    mock_handle.host = "127.0.0.1"
    mock_handle.port = 51234

    with (
        patch(
            "mcp_core.start_local_server_background",
            new_callable=AsyncMock,
            return_value=mock_handle,
            create=True,
        ) as mock_start,
        patch("mcp_core.try_open_browser") as mock_browser,
    ):
        result = await trigger_relay_setup()

    assert result == "http://127.0.0.1:51234/"
    assert get_state() == CredentialState.SETUP_IN_PROGRESS
    mock_start.assert_awaited_once()
    # Verify callbacks are the local save_credentials / on_step_submitted.
    call_kwargs = mock_start.await_args.kwargs
    assert call_kwargs["server_name"] == "better-telegram-mcp"
    assert call_kwargs["host"] == "127.0.0.1"
    assert call_kwargs["port"] == 0
    assert callable(call_kwargs["on_credentials_saved"])
    assert callable(call_kwargs["on_step_submitted"])
    mock_browser.assert_called_once_with("http://127.0.0.1:51234/")


@pytest.mark.asyncio
async def test_trigger_relay_reuses_active_handle():
    """If an active handle already exists, reuse its URL instead of re-spawning."""
    import better_telegram_mcp.credential_state as cs

    cs._state = CredentialState.AWAITING_SETUP
    cs._active_handle = MagicMock()
    cs._setup_url = "http://127.0.0.1:51111/"

    with patch(
        "mcp_core.start_local_server_background",
        new_callable=AsyncMock,
        create=True,
    ) as mock_start:
        result = await trigger_relay_setup()

    assert result == "http://127.0.0.1:51111/"
    mock_start.assert_not_awaited()


@pytest.mark.asyncio
async def test_trigger_relay_exception_returns_none():
    """Spawn failure -> returns None, state back to AWAITING_SETUP."""
    with patch(
        "mcp_core.start_local_server_background",
        new_callable=AsyncMock,
        side_effect=RuntimeError("bind failed"),
        create=True,
    ):
        result = await trigger_relay_setup()

    assert result is None
    assert get_state() == CredentialState.AWAITING_SETUP


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
    assert cs._step_backend is None
    mock_backend.disconnect.assert_awaited_once()


async def test_on_step_submitted_unexpected_input_returns_error():
    """Unknown keys in step_data -> error."""
    import better_telegram_mcp.credential_state as cs

    cs._step_backend = MagicMock()

    result = await cs.on_step_submitted({"random_key": "value"})
    assert result is not None
    assert result["type"] == "error"


# ---------------------------------------------------------------------------
# set_on_configured
# ---------------------------------------------------------------------------


def test_set_on_configured_registers_callback():
    """set_on_configured stores callback in module-level variable."""
    import better_telegram_mcp.credential_state as cs

    async def my_callback():
        pass

    cs.set_on_configured(my_callback)
    assert cs._on_configured_callback is my_callback
    cs._on_configured_callback = None


# ---------------------------------------------------------------------------
# save_credentials -- bot mode with on_configured_callback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_credentials_bot_mode_callback_invoked():
    """Bot mode: on_configured_callback is called after credentials saved."""
    import better_telegram_mcp.credential_state as cs
    from better_telegram_mcp.credential_state import save_credentials

    callback = AsyncMock()
    cs._on_configured_callback = callback

    with patch("mcp_core.storage.config_file.write_config"):
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        result = await save_credentials({"TELEGRAM_BOT_TOKEN": "cb:token"})

    assert result is None
    callback.assert_awaited_once()

    cs._on_configured_callback = None
    os.environ.pop("TELEGRAM_BOT_TOKEN", None)


@pytest.mark.asyncio
async def test_save_credentials_bot_mode_callback_raises():
    """Bot mode: on_configured_callback exception is swallowed, still returns None."""
    import better_telegram_mcp.credential_state as cs
    from better_telegram_mcp.credential_state import save_credentials

    cs._on_configured_callback = AsyncMock(side_effect=RuntimeError("reinit error"))

    with patch("mcp_core.storage.config_file.write_config"):
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        result = await save_credentials({"TELEGRAM_BOT_TOKEN": "cb-fail:token"})

    assert result is None

    cs._on_configured_callback = None
    os.environ.pop("TELEGRAM_BOT_TOKEN", None)


# ---------------------------------------------------------------------------
# on_step_submitted -- disconnect raises (best-effort paths)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_on_step_submitted_otp_invalid_disconnect_raises():
    """Non-2FA OTP error + disconnect raises -> still cleans up + returns error."""
    import better_telegram_mcp.credential_state as cs

    mock_backend = MagicMock()
    mock_backend.sign_in = AsyncMock(side_effect=Exception("phone code invalid"))
    mock_backend.disconnect = AsyncMock(side_effect=Exception("disconnect failed"))
    cs._step_backend = mock_backend
    cs._step_phone = "+1234567890"

    result = await cs.on_step_submitted({"otp_code": "00000"})

    assert result is not None
    assert result["type"] == "error"
    assert cs._step_backend is None


@pytest.mark.asyncio
async def test_on_step_submitted_password_failure_disconnect_raises():
    """2FA password failure + disconnect raises -> still cleans up + returns error."""
    import better_telegram_mcp.credential_state as cs

    mock_backend = MagicMock()
    mock_backend.sign_in = AsyncMock(side_effect=Exception("wrong password"))
    mock_backend.disconnect = AsyncMock(side_effect=Exception("disconnect failed"))
    cs._step_backend = mock_backend
    cs._step_phone = "+1234567890"
    cs._step_otp_code = "12345"

    result = await cs.on_step_submitted({"password": "wrong"})

    assert result is not None
    assert result["type"] == "error"
    assert cs._step_backend is None


# ---------------------------------------------------------------------------
# _finalize_auth -- disconnect raises + callback raises
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_finalize_auth_disconnect_raises():
    """_finalize_auth: disconnect failure is swallowed, state still CONFIGURED."""
    import better_telegram_mcp.credential_state as cs
    from better_telegram_mcp.credential_state import _finalize_auth

    mock_backend = MagicMock()
    mock_backend.disconnect = AsyncMock(side_effect=Exception("disconnect error"))
    cs._step_backend = mock_backend
    cs._step_phone = "+1234567890"
    cs._step_otp_code = "12345"
    cs._on_configured_callback = None

    await _finalize_auth()

    assert cs._state == CredentialState.CONFIGURED
    assert cs._step_backend is None
    assert cs._step_phone == ""
    assert cs._step_otp_code is None


@pytest.mark.asyncio
async def test_finalize_auth_callback_raises():
    """_finalize_auth: on_configured_callback exception is swallowed."""
    import better_telegram_mcp.credential_state as cs
    from better_telegram_mcp.credential_state import _finalize_auth

    cs._step_backend = None
    cs._on_configured_callback = AsyncMock(side_effect=RuntimeError("reinit error"))

    await _finalize_auth()

    assert cs._state == CredentialState.CONFIGURED

    cs._on_configured_callback = None


@pytest.mark.asyncio
async def test_finalize_auth_callback_invoked():
    """_finalize_auth: on_configured_callback is called on success."""
    import better_telegram_mcp.credential_state as cs
    from better_telegram_mcp.credential_state import _finalize_auth

    callback = AsyncMock()
    cs._step_backend = None
    cs._on_configured_callback = callback

    await _finalize_auth()

    callback.assert_awaited_once()
    assert cs._state == CredentialState.CONFIGURED

    cs._on_configured_callback = None
