from __future__ import annotations

import asyncio

import typer

from .backends.user_backend import UserBackend
from .config import Settings

app = typer.Typer(help="Better Telegram MCP CLI")


@app.command()
def run() -> None:
    """Run the MCP server (default)."""
    from .server import main

    main()


@app.command()
def auth(
    phone: str | None = typer.Option(None, help="Telegram phone number (+84...)"),
) -> None:
    """Authenticate a Telegram user account interactively."""

    async def _auth() -> None:
        settings = Settings()
        if phone:
            settings.phone = phone

        if not settings.phone:
            typer.echo("Error: TELEGRAM_PHONE is not set and --phone was not provided.")
            raise typer.Exit(code=1)

        backend = UserBackend(settings)
        await backend.connect()

        try:
            if await backend.is_authorized():
                me = await backend._ensure_client().get_me()
                typer.echo(
                    f"Already authorized as {getattr(me, 'first_name', 'User')}!"
                )
                return

            typer.echo(f"Sending OTP code to {settings.phone}...")
            await backend.send_code(settings.phone)

            code = typer.prompt("Enter the OTP code you received")
            try:
                result = await backend.sign_in(settings.phone, code.strip())
                name = result.get("authenticated_as", "User")
                typer.echo(f"Successfully authenticated as {name}!")
            except Exception as e:
                error_msg = str(e)
                needs_password = any(
                    kw in error_msg.lower()
                    for kw in ("password", "2fa", "two-factor", "srp")
                )
                if needs_password:
                    password = typer.prompt(
                        "Two-factor authentication enabled. Enter your password",
                        hide_input=True,
                    )
                    result = await backend.sign_in(
                        settings.phone, code.strip(), password=password
                    )
                    name = result.get("authenticated_as", "User")
                    typer.echo(f"Successfully authenticated as {name}!")
                else:
                    typer.echo(f"Authentication failed: {e}")
                    raise typer.Exit(code=1) from e
        finally:
            await backend.disconnect()

    asyncio.run(_auth())


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Better Telegram MCP Server."""
    if ctx.invoked_subcommand is None:
        run()


if __name__ == "__main__":
    app()
