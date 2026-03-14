from importlib.metadata import version

from .__main__ import _cli as main
from .server import mcp

__version__ = version("better-telegram-mcp")
__all__ = ["mcp", "main", "__version__"]
