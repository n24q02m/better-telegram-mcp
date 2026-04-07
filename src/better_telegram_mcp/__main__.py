from __future__ import annotations


def _cli() -> None:
    from .cli import _cli as cli_main

    cli_main()


if __name__ == "__main__":
    _cli()
