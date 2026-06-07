from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("better-telegram-mcp")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = ["__version__"]
