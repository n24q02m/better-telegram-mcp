from __future__ import annotations

import asyncio
import os
from typing import Annotated

import typer
from loguru import logger

from .config import Settings

app = typer.Typer(help="Better Telegram MCP CLI")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    transport: Annotated[
        str | None, typer.Option(help="Transport mode (stdio or http)")
    ] = None,
) -> None:
    """Better Telegram MCP CLI. Runs the server by default."""
    if ctx.invoked_subcommand is None:
        # Default action: run server
        from .server import mcp

        transport = transport or os.environ.get("TRANSPORT_MODE", "stdio")
        if transport == "http":
            from .transports.http import start_http

            start_http(Settings())
        else:
            mcp.run(transport="stdio")


@app.command()
def run(
    transport: Annotated[
        str | None, typer.Option(help="Transport mode (stdio or http)")
    ] = None,
) -> None:
    """Run the MCP server."""
    from .server import mcp

    transport = transport or os.environ.get("TRANSPORT_MODE", "stdio")
    if transport == "http":
        from .transports.http import start_http

        start_http(Settings())
    else:
        mcp.run(transport="stdio")


@app.command()
def auth(
    phone: Annotated[str | None, typer.Option(help="Phone number")] = None,
) -> None:
    """Interactive Telegram authentication in the terminal."""

    async def _auth():
        from .backends.user_backend import UserBackend

        settings = Settings()
        if phone:
            settings.phone = phone

        backend = UserBackend(settings)
        await backend.connect()

        if await backend.is_authorized():
            typer.echo("Already authorized.")
            await backend.disconnect()
            return

        target_phone = settings.phone
        if not target_phone:
            target_phone = typer.prompt("Enter your phone number (e.g. +1234567890)")

        logger.info("Sending OTP code to {}...", target_phone)
        try:
            await backend.send_code(target_phone)
        except Exception as e:
            typer.echo(f"Error sending code: {e}", err=True)
            await backend.disconnect()
            raise typer.Exit(1) from e

        code = typer.prompt("Enter the OTP code sent to your Telegram app")
        try:
            result = await backend.sign_in(target_phone, code.strip())
            typer.echo(
                f"Successfully authenticated as {result.get('authenticated_as')}"
            )
        except Exception as e:
            error_msg = str(e)
            # Check for 2FA requirement
            if any(
                kw in error_msg.lower()
                for kw in ("password", "2fa", "two-factor", "srp")
            ):
                password = typer.prompt("2FA password required", hide_input=True)
                try:
                    result = await backend.sign_in(
                        target_phone, code.strip(), password=password
                    )
                    typer.echo(
                        f"Successfully authenticated as {result.get('authenticated_as')}"
                    )
                except Exception as e2:
                    typer.echo(f"Authentication failed: {e2}", err=True)
                    await backend.disconnect()
                    raise typer.Exit(1) from e2
            else:
                typer.echo(f"Authentication failed: {e}", err=True)
                await backend.disconnect()
                raise typer.Exit(1) from e
        finally:
            await backend.disconnect()

    asyncio.run(_auth())


@app.command()
def auth_relay() -> None:
    """Authenticate via remote relay bridge."""

    async def _auth_relay():
        from .auth_client import AuthClient
        from .backends.user_backend import UserBackend

        settings = Settings()
        backend = UserBackend(settings)
        # We need to connect backend first to have it ready for commands
        await backend.connect()

        client = AuthClient(backend, settings)
        try:
            url = await client.create_session()
            typer.echo(
                f"\nRelay auth required. Open this URL in your browser:\n{url}\n"
            )

            # Try to open browser
            import webbrowser

            webbrowser.open(url)

            logger.info("Waiting for authentication to complete via relay...")
            # Run poll_and_execute in background
            poll_task = asyncio.create_task(client.poll_and_execute())
            await client.wait_for_auth()
            poll_task.cancel()
            typer.echo("Authentication complete!")
        except Exception as e:
            typer.echo(f"Relay auth failed: {e}", err=True)
            raise typer.Exit(1) from e
        finally:
            await client.close()
            await backend.disconnect()

    asyncio.run(_auth_relay())


if __name__ == "__main__":
    app()
