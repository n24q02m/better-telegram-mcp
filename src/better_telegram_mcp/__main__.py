from __future__ import annotations

import sys


def _cli() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "auth":
        from .cli import run_auth

        run_auth()
    else:
        from .server import main

        main()


if __name__ == "__main__":
    _cli()
