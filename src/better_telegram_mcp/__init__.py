from importlib.metadata import PackageNotFoundError, version

from .__main__ import _cli as main

try:
    __version__ = version("better-telegram-mcp")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"

__all__ = ["main", "__version__"]
