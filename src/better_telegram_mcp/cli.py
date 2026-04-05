"""CLI implementation for better-telegram-mcp using Typer."""

from __future__ import annotations

import asyncio
import sys

import typer

from .config import Settings

app = typer.Typer(
    help="Better Telegram MCP Server CLI",
    # no_args_is_help=True, # Allow default callback to run
    add_completion=False,
)


def _run_async(coro):
    """Run an async coroutine."""
    try:
        return asyncio.run(coro)
    except KeyboardInterrupt:
        sys.exit(0)


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    """Default callback to run the server if no command is provided."""
    if ctx.invoked_subcommand is None:
        run()


@app.command()
def run(
    transport: str = typer.Option(
        "stdio", "--transport", "-t", help="Transport mode (stdio or http)"
    ),
):
    """Start the MCP server."""
    from .server import mcp

    if transport == "http":
        from .transports.http import start_http

        start_http(Settings())
    else:
        mcp.run(transport="stdio")


@app.command()
def auth(
    phone: str | None = typer.Option(
        None, "--phone", "-p", help="Phone number for authentication"
    ),
):
    """Interactive terminal-based authentication."""
    _run_async(_auth_async(phone))


async def _auth_async(phone_opt: str | None):
    from .backends.user_backend import UserBackend
    from .utils.formatting import _mask_phone

    settings = Settings()
    if phone_opt:
        settings.phone = phone_opt

    if not settings.phone:
        settings.phone = typer.prompt(
            "Enter your phone number (with country code, e.g. +1234567890)"
        )

    backend = UserBackend(settings)
    await backend.connect()

    try:
        if await backend.is_authorized():
            me = await backend._client.get_me()
            typer.echo(f"Already authorized as {getattr(me, 'first_name', 'User')}")
            return

        typer.echo(f"Sending OTP code to {_mask_phone(settings.phone)}...")
        await backend.send_code(settings.phone)

        code = typer.prompt("Enter the OTP code")

        try:
            result = await backend.sign_in(settings.phone, code.strip())
            name = result.get("authenticated_as", "User")
            typer.echo(f"Successfully authenticated as {name}")
        except Exception as e:
            error_msg = str(e)
            needs_2fa = any(
                kw in error_msg.lower()
                for kw in ("password", "2fa", "two-factor", "srp")
            )

            if needs_2fa:
                password = typer.prompt(
                    "Your account has 2FA enabled. Enter your password", hide_input=True
                )
                result = await backend.sign_in(
                    settings.phone, code.strip(), password=password
                )
                name = result.get("authenticated_as", "User")
                typer.echo(f"Successfully authenticated as {name}")
            else:
                typer.echo(f"Authentication failed: {e}")
                sys.exit(1)

    finally:
        await backend.disconnect()


@app.command()
def auth_relay():
    """Remote authentication polling (for headless environments)."""
    _run_async(_auth_relay_async())


async def _auth_relay_async():
    from .auth_client import AuthClient
    from .backends.user_backend import UserBackend

    settings = Settings()
    if not settings.phone:
        typer.echo("Error: TELEGRAM_PHONE must be set for auth-relay.")
        sys.exit(1)

    backend = UserBackend(settings)
    await backend.connect()

    client = AuthClient(backend, settings)
    try:
        url = await client.create_session()
        typer.echo(
            f"\nRemote authentication required. Open this URL in your browser:\n\n{url}\n"
        )

        # Best-effort open browser
        import webbrowser

        asyncio.create_task(asyncio.to_thread(webbrowser.open, url))

        typer.echo("Waiting for authentication via relay...")
        polling_task = asyncio.create_task(client.poll_and_execute())
        await client.wait_for_auth()
        polling_task.cancel()

        typer.echo("\nAuthentication complete!")
    finally:
        await client.close()
        await backend.disconnect()


if __name__ == "__main__":
    app()
