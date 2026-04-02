from __future__ import annotations

import socket

import pytest

from better_telegram_mcp.auth_server import _find_free_port


def test_find_free_port_error(monkeypatch):
    """Test that _find_free_port raises RuntimeError when socket.bind fails."""

    class MockSocket:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def bind(self, addr):
            raise OSError("mock bind error")

        def setsockopt(self, *args, **kwargs):
            pass

        def getsockname(self):
            return ("127.0.0.1", 0)

        def close(self):
            pass

    monkeypatch.setattr(socket, "socket", MockSocket)

    with pytest.raises(RuntimeError, match="Could not find a free port"):
        _find_free_port()


def test_find_free_port_success(monkeypatch):
    """Test that _find_free_port returns the port number on success."""

    class MockSocket:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def bind(self, addr):
            pass

        def setsockopt(self, *args, **kwargs):
            pass

        def getsockname(self):
            return ("127.0.0.1", 8888)

        def close(self):
            pass

    monkeypatch.setattr(socket, "socket", MockSocket)

    assert _find_free_port() == 8888
