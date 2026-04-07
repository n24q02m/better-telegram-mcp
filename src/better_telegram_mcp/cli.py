"""CLI entry point for better-telegram-mcp."""

from __future__ import annotations

import asyncio
import os
from typing import Annotated

import typer

from .config import Settings

app = typer.Typer(
    name="better-telegram-mcp",
    help="Better Telegram MCP Server CLI",
    no_args_is_help=False,
)


def _sanitize_error(msg: str) -> str:
    """Simplify internal error messages to user-friendly text."""
    import re

    _CAUSED_BY_RE = re.compile(r"\s*\(caused by \w+\)\s*$", re.IGNORECASE)
    _ERROR_SIMPLIFICATIONS: list[tuple[re.Pattern[str], str]] = [
        (
            re.compile(r".*password.*required.*", re.IGNORECASE),
            "Two-factor authentication password is required.",
        ),
        (
            re.compile(r".*password.*invalid.*|.*invalid.*password.*", re.IGNORECASE),
            "Incorrect 2FA password. Please try again.",
        ),
        (
            re.compile(r".*phone.*code.*invalid.*|.*invalid.*code.*", re.IGNORECASE),
            "Invalid OTP code. Please check and try again.",
        ),
        (
            re.compile(r".*phone.*code.*expired.*|.*code.*expired.*", re.IGNORECASE),
            "OTP code has expired. Please request a new one.",
        ),
        (
            re.compile(r".*flood.*wait.*|.*too many.*", re.IGNORECASE),
            "Too many attempts. Please wait a moment and try again.",
        ),
    ]
    cleaned = _CAUSED_BY_RE.sub("", msg).strip()
    for pattern, friendly in _ERROR_SIMPLIFICATIONS:
        if pattern.match(cleaned):
            return friendly
    return cleaned


async def _run_auth() -> None:
    """Run interactive terminal authentication."""
    settings = Settings()
    if settings.mode != "user":
        typer.echo("Error: Interactive auth is only for user mode (MTProto).")
        typer.echo("Set TELEGRAM_PHONE to your phone number.")
        raise typer.Exit(code=1)

    from .backends.user_backend import UserBackend

    backend = UserBackend(settings)
    await backend.connect()

    try:
        if await backend.is_authorized():
            typer.echo("Already authorized!")
            return

        phone = settings.phone
        if not phone:
            typer.echo("Error: TELEGRAM_PHONE is not set.")
            raise typer.Exit(code=1)

        typer.echo(f"Sending OTP code to {phone}...")
        try:
            await backend.send_code(phone)
        except Exception as e:
            typer.echo(f"Failed to send code: {_sanitize_error(str(e))}")
            raise typer.Exit(code=1) from e

        code = typer.prompt("Enter the OTP code sent to your Telegram app")
        try:
            result = await backend.sign_in(phone, code.strip())
            typer.echo(
                f"Successfully authenticated as {result.get('authenticated_as', 'User')}!"
            )
        except Exception as e:
            error_msg = str(e)
            needs_password = any(
                kw in error_msg.lower()
                for kw in ("password", "2fa", "two-factor", "srp")
            )
            if needs_password:
                password = typer.prompt(
                    "Your account has 2FA enabled. Enter your password", hide_input=True
                )
                try:
                    result = await backend.sign_in(
                        phone, code.strip(), password=password
                    )
                    typer.echo(
                        f"Successfully authenticated as {result.get('authenticated_as', 'User')}!"
                    )
                except Exception as e2:
                    typer.echo(f"Authentication failed: {_sanitize_error(str(e2))}")
                    raise typer.Exit(code=1) from e2
            else:
                typer.echo(f"Authentication failed: {_sanitize_error(error_msg)}")
                raise typer.Exit(code=1) from e

    finally:
        await backend.disconnect()


@app.command()
def auth() -> None:
    """Authenticate Telegram user account interactively."""
    asyncio.run(_run_auth())


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    transport: Annotated[
        str | None,
        typer.Option(help="Transport mode (stdio or http)"),
    ] = None,
) -> None:
    """Start the Better Telegram MCP server (default)."""
    if ctx.invoked_subcommand is not None:
        return

    from .server import main as server_main

    if transport:
        os.environ["TRANSPORT_MODE"] = transport

    server_main()


def _cli() -> None:
    """Entry point for project.scripts."""
    app()


if __name__ == "__main__":
    _cli()
