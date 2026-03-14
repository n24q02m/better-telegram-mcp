from importlib.metadata import version

from .__main__ import _cli as main

__version__ = version("better-telegram-mcp")
__all__ = ["main", "__version__"]
