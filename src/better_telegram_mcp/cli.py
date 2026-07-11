"""Console-script entry: mounts the shared mcp_core CLI builder.

Bare invocation and any leading-dash argv (e.g. --http) start the server
exactly as before; subcommands run one-shot operator actions. The
``login``/``logout`` subcommands are single-user / local-machine only:
they write the on-disk session and the encrypted single-user config, so
running them makes sense on the machine that hosts the stdio server.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys

from mcp_core import build_cli

_MARKER_PLUGIN = "telegram"
_MARKER_SUB_KEY = "tokens/app-identity"


def _serve(argv: list[str]) -> int | None:
    from better_telegram_mcp.server import main as server_main

    server_main()
    return 0


# --- login ---


def _configure_login(p: argparse.ArgumentParser) -> None:
    p.description = (
        "Authenticate this local machine (single-user). Bot mode validates "
        "the token; phone mode runs the interactive OTP/2FA flow and stores "
        "the Telethon session on disk."
    )
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--bot-token",
        default=None,
        help="Bot API token from @BotFather (bot mode)",
    )
    group.add_argument(
        "--phone",
        default=None,
        help="Phone number in +<country><number> form (user mode, interactive)",
    )


def _handle_login(args: argparse.Namespace) -> int:
    if args.bot_token:
        return _login_bot(args.bot_token)
    return _login_phone(args.phone)


def _login_bot(bot_token: str) -> int:
    try:
        asyncio.run(_verify_bot_token(bot_token))
    except Exception as e:
        from better_telegram_mcp.relay_setup import _sanitize_error

        print(f"Login failed: {_sanitize_error(str(e))}", file=sys.stderr)
        return 1

    from better_telegram_mcp.credential_state import _write_single_user_config

    _write_single_user_config({"TELEGRAM_BOT_TOKEN": bot_token})
    print("Logged in (bot mode). Credentials saved to the local config.")
    return 0


async def _verify_bot_token(bot_token: str) -> None:
    from better_telegram_mcp.backends.bot_backend import BotBackend

    backend = BotBackend(bot_token)
    try:
        await backend.connect()
    finally:
        await backend.disconnect()


def _login_phone(phone: str) -> int:
    if not sys.stdin.isatty():
        print(
            "login --phone requires an interactive terminal "
            "(the OTP code is prompted on stdin).",
            file=sys.stderr,
        )
        return 1

    try:
        result = asyncio.run(_run_phone_login(phone))
    except Exception as e:
        from better_telegram_mcp.relay_setup import _sanitize_error

        print(f"Login failed: {_sanitize_error(str(e))}", file=sys.stderr)
        return 1

    who = result.get("authenticated_as") or "user"
    print(f"Logged in as {who} (user mode). Session saved locally.")
    return 0


async def _run_phone_login(phone: str) -> dict:
    from better_telegram_mcp.backends.user_backend import UserBackend
    from better_telegram_mcp.config import Settings
    from better_telegram_mcp.relay_setup import _needs_2fa_password

    settings = Settings.from_relay_config({"TELEGRAM_PHONE": phone})
    backend = UserBackend(settings)
    await backend.connect()
    try:
        await backend.send_code(phone)
        code = _prompt_otp()
        try:
            result = await backend.sign_in(phone, code)
        except Exception as e:
            if not _needs_2fa_password(str(e)):
                raise
            password = _prompt_2fa_password()
            result = await backend.sign_in(phone, code, password=password)
        _persist_phone_identity(settings, phone)
        return result
    finally:
        await backend.disconnect()


def _prompt_otp() -> str:
    print(
        "Enter the OTP code sent to your Telegram app: ",
        end="",
        file=sys.stderr,
        flush=True,
    )
    return sys.stdin.readline().strip()


def _prompt_2fa_password() -> str:
    return getpass.getpass("Enter your 2FA password: ", stream=sys.stderr)


def _persist_phone_identity(settings, phone: str) -> None:
    from better_telegram_mcp.credential_state import _write_single_user_config

    _write_single_user_config({"TELEGRAM_PHONE": phone})
    _api_identity_store().save({"api_id": str(settings.api_id)})


# --- logout ---


def _handle_logout(args: argparse.Namespace) -> int:
    from better_telegram_mcp.config import Settings

    settings = Settings()
    session_path = settings.session_path
    actions: list[str] = []

    if session_path.exists():
        try:
            asyncio.run(_revoke_session(settings))
            actions.append("revoked Telegram session server-side")
        except Exception as e:
            from better_telegram_mcp.relay_setup import _sanitize_error

            print(
                "Warning: could not revoke session server-side: "
                f"{_sanitize_error(str(e))}",
                file=sys.stderr,
            )
        try:
            session_path.unlink()
            actions.append("deleted local session file")
        except FileNotFoundError:
            pass

    if _clear_single_user_config():
        actions.append("cleared saved credentials")
    if _clear_api_identity_marker():
        actions.append("cleared api identity marker")

    if not actions:
        print("Nothing to log out.")
        return 0

    for action in actions:
        print(f"- {action}")
    print("Logged out.")
    return 0


async def _revoke_session(settings) -> None:
    from better_telegram_mcp.backends.user_backend import UserBackend

    backend = UserBackend(settings)
    await backend.connect()
    try:
        await backend.log_out()
    finally:
        await backend.disconnect()


def _clear_single_user_config() -> bool:
    from better_telegram_mcp.credential_state import (
        _delete_single_user_config,
        _read_single_user_config,
    )

    existed = bool(_read_single_user_config())
    if existed:
        _delete_single_user_config()
    return existed


def _clear_api_identity_marker() -> bool:
    store = _api_identity_store()
    existed = bool(store.load())
    store.clear()
    return existed


def _api_identity_store():
    from mcp_core.storage.per_plugin_store import PerPluginStore

    return PerPluginStore(_MARKER_PLUGIN, sub_key=_MARKER_SUB_KEY)


# --- entry ---


def _extras() -> dict:
    return {
        "login": (_configure_login, _handle_login),
        "logout": _handle_logout,
    }


def _version() -> str:
    from better_telegram_mcp import __version__

    return __version__


def main() -> int:
    return build_cli(
        "better-telegram-mcp",
        serve=_serve,
        extra=_extras(),
        version=_version(),
    )(None)
