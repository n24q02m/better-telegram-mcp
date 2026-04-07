"""CLI entry point for better-telegram-mcp."""

from __future__ import annotations

import asyncio
import os

import typer

from .config import Settings

app = typer.Typer(
    name="better-telegram-mcp",
    help="Production-grade MCP server for Telegram",
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def callback(
    ctx: typer.Context,
    transport: str = typer.Option(
        "stdio", "--transport", "-t", help="Transport mode (stdio, http)"
    ),
):
    """Run the MCP server (default)."""
    if ctx.invoked_subcommand is None:
        # Run the server
        os.environ["TRANSPORT_MODE"] = transport
        from .server import main as server_main

        server_main()


@app.command()
def run(
    transport: str = typer.Option(
        "stdio", "--transport", "-t", help="Transport mode (stdio, http)"
    ),
):
    """Start the MCP server."""
    os.environ["TRANSPORT_MODE"] = transport
    from .server import main as server_main

    server_main()


@app.command()
def auth(
    phone: str | None = typer.Option(None, "--phone", "-p", help="Phone number"),
):
    """Authenticate Telegram account (Terminal OTP)."""
    asyncio.run(_auth_flow(phone))


async def _auth_flow(phone: str | None):
    settings = Settings()
    if phone:
        settings.phone = phone

    if not settings.phone:
        settings.phone = typer.prompt("Enter your phone number (e.g. +123456789)")

    from .backends.user_backend import UserBackend

    backend = UserBackend(settings)
    await backend.connect()

    try:
        if await backend.is_authorized():
            typer.echo(f"Already authorized as {settings.phone}")
            return

        typer.echo(f"Sending OTP to {settings.phone}...")
        await backend.send_code(settings.phone)

        code = typer.prompt("Enter the OTP code")

        try:
            result = await backend.sign_in(settings.phone, code)
            typer.echo(f"Successfully authenticated as {result['authenticated_as']}")
        except Exception as e:
            msg = str(e).lower()
            if any(kw in msg for kw in ("password", "2fa", "two-factor", "srp")):
                password = typer.prompt("Enter your 2FA password", hide_input=True)
                result = await backend.sign_in(settings.phone, code, password=password)
                typer.echo(
                    f"Successfully authenticated as {result['authenticated_as']}"
                )
            else:
                typer.secho(f"Authentication failed: {e}", fg=typer.colors.RED)
                raise typer.Exit(code=1) from e
    finally:
        await backend.disconnect()


def _cli_entry():
    app()
