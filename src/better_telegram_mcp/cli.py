"""Typer-based CLI for better-telegram-mcp."""

from __future__ import annotations

import asyncio
import os

import typer

from .config import Settings

app = typer.Typer(help="Better Telegram MCP Server CLI")


def _run_async(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    transport: str = typer.Option("stdio", help="Transport mode (stdio or http)"),
):
    """Start the MCP server (default)."""
    if ctx.invoked_subcommand is not None:
        return

    os.environ["TRANSPORT_MODE"] = transport
    from .server import main as server_main

    server_main()


@app.command()
def auth(
    phone: str | None = typer.Option(None, help="Telegram phone number"),
    session: str = typer.Option("default", help="Session name"),
):
    """Interactive terminal-based Telegram authentication."""
    settings = Settings(phone=phone, session_name=session)
    if not settings.phone:
        typer.echo("Error: TELEGRAM_PHONE is required for authentication.")
        raise typer.Exit(code=1)

    from .backends.user_backend import UserBackend

    backend = UserBackend(settings)

    async def _auth_flow():
        await backend.connect()
        try:
            if await backend.is_authorized():
                typer.echo(f"Already authorized as {settings.phone}")
                return

            typer.echo(f"Sending OTP to {settings.phone}...")
            await backend.send_code(settings.phone)

            code = typer.prompt("Enter the OTP code sent to your Telegram app")
            try:
                result = await backend.sign_in(settings.phone, code)
                name = result.get("authenticated_as", "User")
                typer.echo(f"Successfully authenticated as {name}")
            except Exception as e:
                error_msg = str(e)
                if any(
                    kw in error_msg.lower()
                    for kw in ("password", "2fa", "two-factor", "srp")
                ):
                    password = typer.prompt("2FA password required", hide_input=True)
                    result = await backend.sign_in(
                        settings.phone, code, password=password
                    )
                    name = result.get("authenticated_as", "User")
                    typer.echo(f"Successfully authenticated as {name}")
                else:
                    typer.echo(f"Authentication failed: {e}")
                    raise typer.Exit(code=1) from e
        finally:
            await backend.disconnect()

    _run_async(_auth_flow())


@app.command()
def auth_relay(
    phone: str | None = typer.Option(None, help="Telegram phone number"),
    url: str | None = typer.Option(None, help="Remote relay server URL"),
):
    """Poll a remote relay server for OTP commands."""
    settings = Settings(phone=phone)
    if url:
        settings.auth_url = url

    if not settings.phone:
        typer.echo("Error: TELEGRAM_PHONE is required.")
        raise typer.Exit(code=1)

    from .auth_client import AuthClient
    from .backends.user_backend import UserBackend

    backend = UserBackend(settings)
    client = AuthClient(backend, settings)

    async def _relay_flow():
        await backend.connect()
        try:
            auth_url = await client.create_session()
            typer.echo(f"Auth session created. Please visit: {auth_url}")
            typer.echo("Polling for commands...")

            # Start polling in background and wait for it
            await client.poll_and_execute()
            await client.wait_for_auth()
            typer.echo("Authentication complete!")
        finally:
            await client.close()
            await backend.disconnect()

    _run_async(_relay_flow())


if __name__ == "__main__":
    app()
