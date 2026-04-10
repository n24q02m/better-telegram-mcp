"""Main entry point for better-telegram-mcp."""

from __future__ import annotations


def _cli() -> None:
    """Run the Typer CLI."""
    from .cli import app

    app()


if __name__ == "__main__":
    _cli()
