from __future__ import annotations


def _cli() -> None:
    from .cli import _cli_entry

    _cli_entry()


if __name__ == "__main__":
    _cli()
