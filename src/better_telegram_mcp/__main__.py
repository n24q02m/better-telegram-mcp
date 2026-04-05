from __future__ import annotations


def _cli() -> None:
    from .cli import app

    app()


if __name__ == "__main__":
    _cli()
