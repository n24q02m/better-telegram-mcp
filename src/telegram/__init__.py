from importlib.metadata import PackageNotFoundError, version

from .__main__ import _cli as main

try:
    __version__ = version("n24q02m-telegram")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = ["main", "__version__"]
