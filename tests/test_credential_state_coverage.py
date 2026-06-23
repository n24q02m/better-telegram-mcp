from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from better_telegram_mcp.credential_state import (
    CredentialState,
    _per_sub_steps,
    on_step_submitted,
)


@pytest.fixture(autouse=True)
def clean_state():
    import better_telegram_mcp.credential_state as cs

    cs._state = CredentialState.AWAITING_SETUP
    cs._per_sub_steps.clear()
    yield
    cs._state = CredentialState.AWAITING_SETUP
    cs._per_sub_steps.clear()


@pytest.mark.asyncio
async def test_on_step_submitted_multi_user_2fa_flow_coverage():
    """Cover multi-user 2FA branches in on_step_submitted."""
    mock_provider = MagicMock()
    mock_provider.complete_user_auth = AsyncMock()

    # Mock _needs_2fa_password to return True for the specific error
    with (
        patch(
            "better_telegram_mcp.auth.telegram_auth_provider.get_global_provider",
            return_value=mock_provider,
        ),
        patch(
            "better_telegram_mcp.credential_state._needs_2fa_password",
            return_value=True,
        ),
    ):
        # 1. OTP submission triggers 2FA required
        mock_provider.complete_user_auth.side_effect = ValueError(
            "SESSION_PASSWORD_NEEDED"
        )

        step_data = {"otp_code": "12345"}
        context = {"sub": "user1"}

        res = await on_step_submitted(step_data, context)

        assert res is not None
        assert res["type"] == "password_required"
        assert "user1" in _per_sub_steps
        assert _per_sub_steps["user1"][2] == "12345"

        # 2. Password submission success
        mock_provider.complete_user_auth.side_effect = None  # Reset side effect
        mock_provider.complete_user_auth.return_value = None

        step_data = {"password": "mypassword"}
        res = await on_step_submitted(step_data, context)

        assert res is None
        assert "user1" not in _per_sub_steps


@pytest.mark.asyncio
async def test_on_step_submitted_multi_user_otp_failure_not_2fa():
    """Cover multi-user OTP failure that is NOT 2FA."""
    mock_provider = MagicMock()
    mock_provider.complete_user_auth = AsyncMock(side_effect=ValueError("OTHER_ERROR"))

    with (
        patch(
            "better_telegram_mcp.auth.telegram_auth_provider.get_global_provider",
            return_value=mock_provider,
        ),
        patch(
            "better_telegram_mcp.credential_state._needs_2fa_password",
            return_value=False,
        ),
    ):
        step_data = {"otp_code": "12345"}
        context = {"sub": "user1"}

        res = await on_step_submitted(step_data, context)
        assert res is not None
        assert res["type"] == "error"
        assert "Authentication failed" in res["text"]
        assert "user1" not in _per_sub_steps


@pytest.mark.asyncio
async def test_on_step_submitted_multi_user_password_failure():
    """Cover multi-user password failure."""
    mock_provider = MagicMock()
    mock_provider.complete_user_auth = AsyncMock()

    _per_sub_steps["user1"] = (None, "", "12345")

    with patch(
        "better_telegram_mcp.auth.telegram_auth_provider.get_global_provider",
        return_value=mock_provider,
    ):
        mock_provider.complete_user_auth.side_effect = ValueError("WRONG_PASSWORD")

        step_data = {"password": "wrong"}
        context = {"sub": "user1"}

        res = await on_step_submitted(step_data, context)
        assert res is not None
        assert res["type"] == "error"
        assert "2FA failed" in res["text"]
        assert "user1" not in _per_sub_steps


@pytest.mark.asyncio
async def test_on_step_submitted_multi_user_password_missing_stash():
    """Cover multi-user password submission when stash is missing."""
    mock_provider = MagicMock()

    with patch(
        "better_telegram_mcp.auth.telegram_auth_provider.get_global_provider",
        return_value=mock_provider,
    ):
        step_data = {"password": "mypassword"}
        context = {"sub": "user1"}

        res = await on_step_submitted(step_data, context)
        assert res is not None
        assert res["type"] == "error"
        assert "OTP code missing" in res["text"]


@pytest.mark.asyncio
async def test_on_step_submitted_unexpected_input():
    """Cover unexpected input branch."""
    mock_provider = MagicMock()

    with patch(
        "better_telegram_mcp.auth.telegram_auth_provider.get_global_provider",
        return_value=mock_provider,
    ):
        step_data = {"wrong_field": "some_value"}
        context = {"sub": "user1"}

        res = await on_step_submitted(step_data, context)
        assert res is not None
        assert res["type"] == "error"
        assert "Unexpected input" in res["text"]


@pytest.mark.asyncio
async def test_on_step_submitted_multi_user_otp_needs_2fa_with_stash():
    """Cover multi-user OTP failure with stash already present."""
    mock_provider = MagicMock()
    mock_provider.complete_user_auth = AsyncMock(
        side_effect=ValueError("SESSION_PASSWORD_NEEDED")
    )

    _per_sub_steps["user1"] = ("mock_backend", "mock_phone", None)

    with (
        patch(
            "better_telegram_mcp.auth.telegram_auth_provider.get_global_provider",
            return_value=mock_provider,
        ),
        patch(
            "better_telegram_mcp.credential_state._needs_2fa_password",
            return_value=True,
        ),
    ):
        step_data = {"otp_code": "12345"}
        context = {"sub": "user1"}

        res = await on_step_submitted(step_data, context)
        assert res is not None
        assert res["type"] == "password_required"
        assert _per_sub_steps["user1"] == ("mock_backend", "mock_phone", "12345")
