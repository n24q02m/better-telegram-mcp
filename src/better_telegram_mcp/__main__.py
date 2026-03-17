from __future__ import annotations


def _cli() -> None:
    from .server import main

    main()


if __name__ == "__main__":
    _cli()
