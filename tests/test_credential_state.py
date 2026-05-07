"""Tests for credential_state module -- state machine, resolve, save_credentials."""

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
    set_setup_url,
    set_state,
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


def test_set_setup_url():
    set_setup_url("http://localhost/setup")
    assert get_setup_url() == "http://localhost/setup"


def test_current_sub_contextvar():
    """Verify _current_sub contextvar isolation."""
    import asyncio
    from better_telegram_mcp.credential_state import _current_sub

    async def check_sub(val):
        _current_sub.set(val)
        await asyncio.sleep(0.01)
        return _current_sub.get()

    async def run_test():
        results = await asyncio.gather(check_sub("sub1"), check_sub("sub2"))
        assert results == ["sub1", "sub2"]

    asyncio.run(run_test())


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
        result = await save_credentials(
            {"TELEGRAM_BOT_TOKEN": "123:abc"}, {"sub": "test-sub"}
        )
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
        result = await save_credentials(
            {"TELEGRAM_PHONE": "+1234567890"}, {"sub": "test-sub"}
        )

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
        result = await save_credentials(
            {"TELEGRAM_PHONE": "+1234567890"}, {"sub": "test-sub"}
        )

    assert result is not None
    assert result["type"] == "error"
    assert "Failed to send OTP" in result["text"]

    os.environ.pop("TELEGRAM_PHONE", None)


async def test_on_step_submitted_no_session_returns_error():
    """Without active session, /otp submission returns error."""
    from better_telegram_mcp.credential_state import on_step_submitted

    result = await on_step_submitted({"otp_code": "12345"}, {"sub": "test-sub"})
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

    result = await cs.on_step_submitted({"otp_code": "12345"}, {"sub": "test-sub"})
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

    result = await cs.on_step_submitted({"otp_code": "12345"}, {"sub": "test-sub"})
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

    result = await cs.on_step_submitted({"otp_code": "00000"}, {"sub": "test-sub"})
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

    result = await cs.on_step_submitted({"password": "secret"}, {"sub": "test-sub"})
    assert result is None
    assert cs._state == cs.CredentialState.CONFIGURED


async def test_on_step_submitted_password_no_otp_returns_error():
    """Password submission without prior OTP should error (restart needed)."""
    import better_telegram_mcp.credential_state as cs

    mock_backend = MagicMock()
    cs._step_backend = mock_backend
    cs._step_phone = "+1234567890"
    cs._step_otp_code = None

    result = await cs.on_step_submitted({"password": "secret"}, {"sub": "test-sub"})
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

    result = await cs.on_step_submitted({"password": "wrong"}, {"sub": "test-sub"})
    assert result is not None
    assert result["type"] == "error"
    assert "2FA failed" in result["text"]
    assert cs._step_backend is None
    mock_backend.disconnect.assert_awaited_once()


async def test_on_step_submitted_unexpected_input_returns_error():
    """Unknown keys in step_data -> error."""
    import better_telegram_mcp.credential_state as cs

    cs._step_backend = MagicMock()

    result = await cs.on_step_submitted({"random_key": "value"}, {"sub": "test-sub"})
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
        result = await save_credentials(
            {"TELEGRAM_BOT_TOKEN": "cb:token"}, {"sub": "test-sub"}
        )

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
        result = await save_credentials(
            {"TELEGRAM_BOT_TOKEN": "cb-fail:token"}, {"sub": "test-sub"}
        )

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

    result = await cs.on_step_submitted({"otp_code": "00000"}, {"sub": "test-sub"})

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

    result = await cs.on_step_submitted({"password": "wrong"}, {"sub": "test-sub"})

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


# ---------------------------------------------------------------------------
# Multi-user branch (per-JWT-sub via TelegramAuthProvider)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_credentials_multiuser_bot_success():
    """Multi-user bot mode: register backend on the per-sub provider."""
    from better_telegram_mcp.credential_state import save_credentials

    provider = MagicMock()
    provider.register_bot = AsyncMock(return_value="sub-abc")

    with patch(
        "better_telegram_mcp.auth.telegram_auth_provider.get_global_provider",
        return_value=provider,
    ):
        result = await save_credentials(
            {"TELEGRAM_BOT_TOKEN": "123:abc"},
            {"sub": "sub-uuid-abc"},
        )

    assert result is None
    provider.register_bot.assert_awaited_once_with("sub-uuid-abc", "123:abc")
    assert get_state() == CredentialState.CONFIGURED


@pytest.mark.asyncio
async def test_save_credentials_multiuser_bot_invalid_token():
    """Multi-user bot mode surfaces validation errors via 'error' result."""
    from better_telegram_mcp.credential_state import save_credentials

    provider = MagicMock()
    provider.register_bot = AsyncMock(side_effect=ValueError("Invalid bot token"))

    with patch(
        "better_telegram_mcp.auth.telegram_auth_provider.get_global_provider",
        return_value=provider,
    ):
        result = await save_credentials(
            {"TELEGRAM_BOT_TOKEN": "bad"},
            {"sub": "sub-uuid"},
        )

    assert result is not None
    assert result["type"] == "error"
    assert "bot token" in result["text"].lower()


@pytest.mark.asyncio
async def test_save_credentials_multiuser_bot_missing_token():
    """Multi-user mode with neither bot token nor phone returns error."""
    from better_telegram_mcp.credential_state import save_credentials

    provider = MagicMock()

    with patch(
        "better_telegram_mcp.auth.telegram_auth_provider.get_global_provider",
        return_value=provider,
    ):
        result = await save_credentials({}, {"sub": "sub-uuid"})

    assert result is not None
    assert result["type"] == "error"


@pytest.mark.asyncio
async def test_save_credentials_multiuser_user_mode_starts_otp():
    """Multi-user user mode: drive the per-sub OTP flow via the provider."""
    from better_telegram_mcp.credential_state import save_credentials

    provider = MagicMock()
    provider.start_user_auth = AsyncMock(
        return_value={"bearer": "sub-x", "phone_code_hash": "hash"}
    )

    with patch(
        "better_telegram_mcp.auth.telegram_auth_provider.get_global_provider",
        return_value=provider,
    ):
        result = await save_credentials(
            {"TELEGRAM_PHONE": "+84912345678"},
            {"sub": "sub-uuid"},
        )

    assert result is not None
    assert result["type"] == "otp_required"
    assert result["field"] == "otp_code"
    provider.start_user_auth.assert_awaited_once_with("sub-uuid", "+84912345678")
    assert get_state() == CredentialState.SETUP_IN_PROGRESS


@pytest.mark.asyncio
async def test_save_credentials_multiuser_user_mode_send_code_failure():
    """Multi-user user mode handles upstream Telethon failure with error result."""
    from better_telegram_mcp.credential_state import save_credentials

    provider = MagicMock()
    provider.start_user_auth = AsyncMock(side_effect=ValueError("Telethon: limit"))

    with patch(
        "better_telegram_mcp.auth.telegram_auth_provider.get_global_provider",
        return_value=provider,
    ):
        result = await save_credentials(
            {"TELEGRAM_PHONE": "+84912345678"},
            {"sub": "sub-uuid"},
        )

    assert result is not None
    assert result["type"] == "error"


@pytest.mark.asyncio
async def test_on_step_submitted_multiuser_otp_success():
    """Multi-user OTP path: provider.complete_user_auth marks CONFIGURED."""
    from better_telegram_mcp.credential_state import on_step_submitted

    provider = MagicMock()
    provider.complete_user_auth = AsyncMock(return_value={"user_id": 1})

    with patch(
        "better_telegram_mcp.auth.telegram_auth_provider.get_global_provider",
        return_value=provider,
    ):
        result = await on_step_submitted({"otp_code": "12345"}, {"sub": "sub-uuid"})

    assert result is None
    provider.complete_user_auth.assert_awaited_once_with("sub-uuid", "12345")
    assert get_state() == CredentialState.CONFIGURED


@pytest.mark.asyncio
async def test_on_step_submitted_multiuser_otp_triggers_2fa():
    """Multi-user OTP failure with 2FA hint triggers password_required step."""
    import better_telegram_mcp.credential_state as cs
    from better_telegram_mcp.credential_state import on_step_submitted

    provider = MagicMock()
    provider.complete_user_auth = AsyncMock(
        side_effect=ValueError(
            "Two-step verification is enabled and a password is required"
        )
    )

    with patch(
        "better_telegram_mcp.auth.telegram_auth_provider.get_global_provider",
        return_value=provider,
    ):
        result = await on_step_submitted({"otp_code": "12345"}, {"sub": "sub-pw"})

    assert result is not None
    assert result["type"] == "password_required"
    assert cs._per_sub_steps["sub-pw"][2] == "12345"
    cs._per_sub_steps.pop("sub-pw", None)


@pytest.mark.asyncio
async def test_on_step_submitted_multiuser_otp_other_failure():
    """Non-2FA OTP failure returns generic error and clears stash."""
    import better_telegram_mcp.credential_state as cs
    from better_telegram_mcp.credential_state import on_step_submitted

    cs._per_sub_steps["sub-bad"] = (None, "+84", None)
    provider = MagicMock()
    provider.complete_user_auth = AsyncMock(
        side_effect=ValueError("PHONE_CODE_INVALID")
    )

    with patch(
        "better_telegram_mcp.auth.telegram_auth_provider.get_global_provider",
        return_value=provider,
    ):
        result = await on_step_submitted({"otp_code": "00000"}, {"sub": "sub-bad"})

    assert result is not None
    assert result["type"] == "error"
    assert "sub-bad" not in cs._per_sub_steps


@pytest.mark.asyncio
async def test_on_step_submitted_multiuser_password_success():
    """Multi-user 2FA password completes auth using the stashed OTP."""
    import better_telegram_mcp.credential_state as cs
    from better_telegram_mcp.credential_state import on_step_submitted

    cs._per_sub_steps["sub-2fa"] = (None, "+84", "67890")
    provider = MagicMock()
    provider.complete_user_auth = AsyncMock(return_value={"user_id": 2})

    with patch(
        "better_telegram_mcp.auth.telegram_auth_provider.get_global_provider",
        return_value=provider,
    ):
        result = await on_step_submitted({"password": "p4ss"}, {"sub": "sub-2fa"})

    assert result is None
    provider.complete_user_auth.assert_awaited_once_with(
        "sub-2fa", "67890", password="p4ss"
    )
    assert get_state() == CredentialState.CONFIGURED
    assert "sub-2fa" not in cs._per_sub_steps


@pytest.mark.asyncio
async def test_on_step_submitted_multiuser_password_no_otp_stash():
    """Submitting password without an OTP-stash returns error."""
    import better_telegram_mcp.credential_state as cs
    from better_telegram_mcp.credential_state import on_step_submitted

    cs._per_sub_steps.pop("sub-orphan", None)
    provider = MagicMock()

    with patch(
        "better_telegram_mcp.auth.telegram_auth_provider.get_global_provider",
        return_value=provider,
    ):
        result = await on_step_submitted({"password": "p"}, {"sub": "sub-orphan"})

    assert result is not None
    assert result["type"] == "error"


@pytest.mark.asyncio
async def test_on_step_submitted_multiuser_password_failure():
    """Multi-user 2FA password failure returns error and clears stash."""
    import better_telegram_mcp.credential_state as cs
    from better_telegram_mcp.credential_state import on_step_submitted

    cs._per_sub_steps["sub-pwfail"] = (None, "+84", "11111")
    provider = MagicMock()
    provider.complete_user_auth = AsyncMock(
        side_effect=ValueError("PASSWORD_HASH_INVALID")
    )

    with patch(
        "better_telegram_mcp.auth.telegram_auth_provider.get_global_provider",
        return_value=provider,
    ):
        result = await on_step_submitted({"password": "wrong"}, {"sub": "sub-pwfail"})

    assert result is not None
    assert result["type"] == "error"
    assert "sub-pwfail" not in cs._per_sub_steps


@pytest.mark.asyncio
async def test_on_step_submitted_multiuser_unexpected_input():
    """Multi-user path with neither otp_code nor password returns error."""
    from better_telegram_mcp.credential_state import on_step_submitted

    provider = MagicMock()

    with patch(
        "better_telegram_mcp.auth.telegram_auth_provider.get_global_provider",
        return_value=provider,
    ):
        result = await on_step_submitted({}, {"sub": "sub-x"})

    assert result is not None
    assert result["type"] == "error"
