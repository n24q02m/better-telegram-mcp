"""Tests for multi-user HTTP transport endpoints."""

from __future__ import annotations

import asyncio
import json
from contextlib import suppress
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from better_telegram_mcp.auth.telegram_auth_provider import TelegramBearerRuntime
from better_telegram_mcp.config import Settings
from better_telegram_mcp.events.sse_fanout_hub import SSEFanoutHub
from better_telegram_mcp.transports.http_multi_user import create_app


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture
def app(data_dir: Path):
    return create_app(
        data_dir=data_dir,
        public_url="https://test.example.com",
        dcr_secret="test-dcr-secret",
        api_id=12345,
        api_hash="test_api_hash",
    )


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


def _make_app(data_dir: Path, relay_settings: Settings | None = None):
    return create_app(
        data_dir=data_dir,
        public_url="https://test.example.com",
        dcr_secret="test-dcr-secret",
        api_id=12345,
        api_hash="test_api_hash",
        relay_settings=relay_settings,
    )


def _register_runtime(app, bearer: str = "test-bearer"):
    provider = app.state.auth_provider
    backend = MagicMock()
    runtime = TelegramBearerRuntime(
        backend=backend,
        hub=SSEFanoutHub(provider._sse_subscriber_queue_size),
        mode="user",
        session_name="user-session",
    )
    provider._runtimes[bearer] = runtime
    provider.active_clients[bearer] = backend
    return provider, runtime


def _make_event(event_id: str) -> dict[str, object]:
    return {
        "event_id": event_id,
        "event_type": "UpdateNewMessage",
        "mode": "user",
        "account": {
            "telegram_id": 100,
            "session_name": "user-session",
            "mode": "user",
        },
        "update": {
            "_": "UpdateNewMessage",
            "message": {"id": 1, "message": "hello"},
        },
    }


def _read_sse_message(lines) -> list[str]:
    message: list[str] = []
    for line in lines:
        if line == "":
            if message:
                return message
            continue
        message.append(line)
    return message


async def _publish_when_connected(hub: SSEFanoutHub, event: dict[str, object]) -> bool:
    for _ in range(50):
        if hub.publish(event):
            return True
        await asyncio.sleep(0.01)
    return False


class _ASGIStreamHandle:
    def __init__(
        self,
        *,
        response_start: dict[str, object],
        messages: asyncio.Queue[dict[str, object]],
        task: asyncio.Task[None],
        disconnect: asyncio.Event,
    ) -> None:
        self.status_code = int(cast(int, response_start["status"]))
        headers = cast(list[tuple[bytes, bytes]], response_start.get("headers", []))
        self.headers = {
            key.decode("utf-8").lower(): value.decode("utf-8") for key, value in headers
        }
        self._messages = messages
        self._task = task
        self._disconnect = disconnect
        self._buffer = bytearray()

    async def read_message(self) -> list[str]:
        while True:
            if b"\n\n" in self._buffer:
                raw_message, remainder = self._buffer.split(b"\n\n", 1)
                self._buffer = bytearray(remainder)
                text = raw_message.decode("utf-8")
                return [line for line in text.split("\n") if line]

            message = await asyncio.wait_for(self._messages.get(), timeout=2)
            if message["type"] != "http.response.body":
                continue

            self._buffer.extend(cast(bytes, message.get("body", b"")))

            if not message.get("more_body", False) and not self._buffer:
                return []

    async def close(self) -> None:
        self._disconnect.set()
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task


async def _open_sse_stream(
    app,
    *,
    bearer: str,
    extra_headers: dict[str, str] | None = None,
) -> _ASGIStreamHandle:
    messages: asyncio.Queue[dict[str, object]] = asyncio.Queue()
    disconnect = asyncio.Event()
    request_sent = False

    headers = [(b"authorization", f"Bearer {bearer}".encode())]
    if extra_headers is not None:
        headers.extend(
            (key.lower().encode("utf-8"), value.encode("utf-8"))
            for key, value in extra_headers.items()
        )

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/events/telegram",
        "raw_path": b"/events/telegram",
        "query_string": b"",
        "headers": headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "state": {},
        "app": app,
        "extensions": {},
    }

    async def receive() -> dict[str, object]:
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": b"", "more_body": False}

        await disconnect.wait()
        return {"type": "http.disconnect"}

    async def send(message: dict[str, object]) -> None:
        await messages.put(message)

    task = asyncio.create_task(app(scope, receive, send))
    response_start = await asyncio.wait_for(messages.get(), timeout=2)
    assert response_start["type"] == "http.response.start"
    return _ASGIStreamHandle(
        response_start=response_start,
        messages=messages,
        task=task,
        disconnect=disconnect,
    )


class TestHealthEndpoint:
    def test_health_returns_ok(self, client: TestClient) -> None:
        """Health endpoint should return status ok."""
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["mode"] == "multi-user"
        assert "active_sessions" in body
        assert body["relay_enabled"] is False
        assert "timestamp" in body

    def test_health_reports_relay_enabled_without_leaking_url(
        self, data_dir: Path
    ) -> None:
        app = create_app(
            data_dir=data_dir,
            public_url="https://test.example.com",
            dcr_secret="test-dcr-secret",
            api_id=12345,
            api_hash="test_api_hash",
            relay_settings=Settings(relay_endpoint_url="https://example.com/events"),
        )
        client = TestClient(app)

        resp = client.get("/health")

        assert resp.status_code == 200
        body = resp.json()
        assert body["relay_enabled"] is True
        assert "relay_endpoint_url" not in body
        assert "example.com" not in resp.text


class TestDCREndpoint:
    def test_register_success(self, client: TestClient) -> None:
        """Should register client and return credentials."""
        resp = client.post(
            "/auth/register",
            json={
                "redirect_uris": ["http://localhost/callback"],
                "client_name": "TestApp",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "client_id" in body
        assert "client_secret" in body
        assert body["client_name"] == "TestApp"
        assert body["redirect_uris"] == ["http://localhost/callback"]

    def test_register_deterministic(self, client: TestClient) -> None:
        """Same input should produce same credentials."""
        payload = {
            "redirect_uris": ["http://localhost/callback"],
            "client_name": "TestApp",
        }
        resp1 = client.post("/auth/register", json=payload)
        resp2 = client.post("/auth/register", json=payload)

        assert resp1.json()["client_id"] == resp2.json()["client_id"]
        assert resp1.json()["client_secret"] == resp2.json()["client_secret"]

    def test_register_invalid_json(self, client: TestClient) -> None:
        """Should return 400 for invalid JSON."""
        resp = client.post(
            "/auth/register",
            content=b"not json",
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 400

    def test_register_invalid_uris_type(self, client: TestClient) -> None:
        """Should return 400 when redirect_uris is not a list."""
        resp = client.post(
            "/auth/register",
            json={"redirect_uris": "not-a-list"},
        )
        assert resp.status_code == 400

    def test_register_empty_body(self, client: TestClient) -> None:
        """Should accept empty body with defaults."""
        resp = client.post("/auth/register", json={})
        assert resp.status_code == 201
        body = resp.json()
        assert body["redirect_uris"] == []
        assert body["client_name"] is None


class TestBotAuthEndpoint:
    def test_bot_auth_success(self, client: TestClient) -> None:
        """Should validate bot token and return bearer."""
        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.BotBackend"
        ) as MockBot:
            mock_instance = MockBot.return_value
            mock_instance.connect = AsyncMock()
            mock_instance.disconnect = AsyncMock()

            resp = client.post(
                "/auth/bot",
                json={"bot_token": "123456:ABC-DEF"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "bearer_token" in body
        assert body["token_type"] == "Bearer"
        assert body["mode"] == "bot"

    def test_bot_auth_invalid_token(self, client: TestClient) -> None:
        """Should return 401 for invalid bot token."""
        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.BotBackend"
        ) as MockBot:
            mock_instance = MockBot.return_value
            mock_instance.connect = AsyncMock(side_effect=Exception("Unauthorized"))
            mock_instance.disconnect = AsyncMock()

            resp = client.post(
                "/auth/bot",
                json={"bot_token": "invalid"},
            )

        assert resp.status_code == 401

    def test_bot_auth_missing_token(self, client: TestClient) -> None:
        """Should return 400 when bot_token is missing."""
        resp = client.post("/auth/bot", json={})
        assert resp.status_code == 400

    def test_bot_auth_empty_token(self, client: TestClient) -> None:
        """Should return 400 when bot_token is empty string."""
        resp = client.post("/auth/bot", json={"bot_token": ""})
        assert resp.status_code == 400


class TestUserAuthEndpoints:
    def test_send_code_success(self, client: TestClient) -> None:
        """Should send code and return bearer + phone_code_hash."""
        mock_telethon_client = MagicMock()
        mock_sent_code = MagicMock()
        mock_sent_code.phone_code_hash = "hash123"
        mock_telethon_client.send_code_request = AsyncMock(return_value=mock_sent_code)

        mock_backend = MagicMock()
        mock_backend.connect = AsyncMock()
        mock_backend.disconnect = AsyncMock()
        mock_backend._ensure_client = MagicMock(return_value=mock_telethon_client)

        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.UserBackend",
            return_value=mock_backend,
        ):
            resp = client.post(
                "/auth/user/send-code",
                json={"phone": "+84912345678"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "bearer_token" in body
        assert body["phone_code_hash"] == "hash123"

    def test_send_code_missing_phone(self, client: TestClient) -> None:
        """Should return 400 when phone is missing."""
        resp = client.post("/auth/user/send-code", json={})
        assert resp.status_code == 400

    def test_verify_success(self, client: TestClient) -> None:
        """Should complete auth and return bearer + user info."""
        mock_telethon_client = MagicMock()
        mock_sent_code = MagicMock()
        mock_sent_code.phone_code_hash = "hash123"
        mock_telethon_client.send_code_request = AsyncMock(return_value=mock_sent_code)

        mock_backend = MagicMock()
        mock_backend.connect = AsyncMock()
        mock_backend.disconnect = AsyncMock()
        mock_backend._ensure_client = MagicMock(return_value=mock_telethon_client)
        mock_backend.sign_in = AsyncMock(
            return_value={
                "authenticated_as": "Test User",
                "username": "testuser",
            }
        )

        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.UserBackend",
            return_value=mock_backend,
        ):
            # Step 1: send code
            resp1 = client.post(
                "/auth/user/send-code",
                json={"phone": "+84912345678"},
            )
            bearer = resp1.json()["bearer_token"]

            # Step 2: verify
            resp2 = client.post(
                "/auth/user/verify",
                json={"code": "12345"},
                headers={"Authorization": f"Bearer {bearer}"},
            )

        assert resp2.status_code == 200
        body = resp2.json()
        assert body["bearer_token"] == bearer
        assert body["mode"] == "user"
        assert body["authenticated_as"] == "Test User"

    def test_verify_missing_bearer(self, client: TestClient) -> None:
        """Should return 401 when bearer is missing."""
        resp = client.post(
            "/auth/user/verify",
            json={"code": "12345"},
        )
        assert resp.status_code == 401

    def test_verify_missing_code(self, client: TestClient) -> None:
        """Should return 400 when code is missing."""
        resp = client.post(
            "/auth/user/verify",
            json={},
            headers={"Authorization": "Bearer some-token"},
        )
        assert resp.status_code == 400

    def test_verify_unknown_bearer(self, client: TestClient) -> None:
        """Should return 400 for unknown bearer token."""
        resp = client.post(
            "/auth/user/verify",
            json={"code": "12345"},
            headers={"Authorization": "Bearer unknown-bearer"},
        )
        assert resp.status_code == 400


class TestMCPEndpoint:
    def test_mcp_requires_bearer(self, client: TestClient) -> None:
        """Should return error when no bearer token."""
        resp = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "initialize", "id": 1},
        )
        assert resp.status_code == 403

    def test_mcp_invalid_bearer(self, client: TestClient) -> None:
        """Should return error for invalid/expired bearer."""
        resp = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "initialize", "id": 1},
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert resp.status_code == 403

    def test_mcp_rejects_get_and_delete(self, client: TestClient) -> None:
        """/mcp should remain the action endpoint, not a stream endpoint."""
        get_resp = client.get("/mcp")
        delete_resp = client.delete("/mcp")

        assert get_resp.status_code == 405
        assert delete_resp.status_code == 405


class TestTelegramSSEEndpoint:
    def test_events_telegram_requires_bearer(self, client: TestClient) -> None:
        resp = client.get("/events/telegram")

        assert resp.status_code == 401

    def test_events_telegram_invalid_bearer(self, client: TestClient) -> None:
        resp = client.get(
            "/events/telegram",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert resp.status_code == 401

    async def test_events_telegram_streams_framed_event(self, data_dir: Path) -> None:
        app = _make_app(data_dir)
        _provider, runtime = _register_runtime(app)

        stream = await _open_sse_stream(app, bearer="test-bearer")
        try:
            assert stream.status_code == 200
            assert stream.headers["content-type"].startswith("text/event-stream")

            assert (
                await _publish_when_connected(runtime.hub, _make_event("evt-1")) is True
            )

            message = await stream.read_message()
        finally:
            await stream.close()

        assert message[0] == "id: evt-1"
        assert message[1] == "event: UpdateNewMessage"
        assert json.loads(message[2].removeprefix("data: ")) == _make_event("evt-1")

    async def test_events_telegram_sends_heartbeat_event(self, data_dir: Path) -> None:
        app = _make_app(data_dir, relay_settings=Settings(sse_heartbeat_seconds=1))
        _provider, _runtime = _register_runtime(app)

        stream = await _open_sse_stream(app, bearer="test-bearer")
        try:
            message = await stream.read_message()
        finally:
            await stream.close()

        assert message[0] == "event: heartbeat"
        assert json.loads(message[1].removeprefix("data: ")) == {}

    async def test_second_connection_replaces_first(self, data_dir: Path) -> None:
        app = _make_app(data_dir)
        _provider, runtime = _register_runtime(app)

        first_stream = await _open_sse_stream(app, bearer="test-bearer")
        second_stream = await _open_sse_stream(app, bearer="test-bearer")
        try:
            first_message = await first_stream.read_message()
            assert first_message[0] == "event: error"
            assert json.loads(first_message[1].removeprefix("data: ")) == {
                "reason": "connection_replaced"
            }

            assert (
                await _publish_when_connected(runtime.hub, _make_event("evt-2")) is True
            )
            second_message = await second_stream.read_message()
        finally:
            await first_stream.close()
            await second_stream.close()

        assert second_message[0] == "id: evt-2"
        assert second_message[1] == "event: UpdateNewMessage"

    async def test_overflow_emits_error_and_closes(self, data_dir: Path) -> None:
        app = _make_app(data_dir, relay_settings=Settings(sse_subscriber_queue_size=1))
        _provider, runtime = _register_runtime(app)

        stream = await _open_sse_stream(app, bearer="test-bearer")
        try:
            assert (
                await _publish_when_connected(runtime.hub, _make_event("evt-1")) is True
            )
            assert runtime.hub.publish(_make_event("evt-2")) is False

            message = await stream.read_message()
        finally:
            await stream.close()

        assert message[0] == "event: error"
        assert json.loads(message[1].removeprefix("data: ")) == {"reason": "overflow"}

    async def test_runtime_stop_emits_error_and_closes(self, data_dir: Path) -> None:
        app = _make_app(data_dir)
        _provider, runtime = _register_runtime(app)

        stream = await _open_sse_stream(app, bearer="test-bearer")
        try:
            await runtime.hub.close("runtime_stopped")
            message = await stream.read_message()
        finally:
            await stream.close()

        assert message[0] == "event: error"
        assert json.loads(message[1].removeprefix("data: ")) == {
            "reason": "runtime_stopped"
        }

    async def test_last_event_id_is_ignored(self, data_dir: Path) -> None:
        app = _make_app(data_dir)
        _provider, runtime = _register_runtime(app)

        stream = await _open_sse_stream(
            app,
            bearer="test-bearer",
            extra_headers={"Last-Event-ID": "evt-old"},
        )
        try:
            assert (
                await _publish_when_connected(runtime.hub, _make_event("evt-live"))
                is True
            )
            message = await stream.read_message()
        finally:
            await stream.close()

        assert message[0] == "id: evt-live"

    async def test_disconnect_clears_active_subscriber(self, data_dir: Path) -> None:
        app = _make_app(data_dir)
        _provider, runtime = _register_runtime(app)

        stream = await _open_sse_stream(app, bearer="test-bearer")
        assert await _publish_when_connected(runtime.hub, _make_event("evt-1")) is True
        await stream.close()

        assert runtime.hub.publish(_make_event("evt-2")) is False


class TestBackwardCompatibility:
    def test_stdio_mode_unchanged(self) -> None:
        """Server module-level _backend should still work in stdio mode."""
        from better_telegram_mcp import server

        # In non-multi-user mode, get_backend should raise if no backend
        server._multi_user_mode = False
        server._backend = None
        with pytest.raises(RuntimeError, match="Backend not initialized"):
            server.get_backend()

    def test_multi_user_mode_flag(self) -> None:
        """create_http_mcp_server should set _multi_user_mode flag."""
        from better_telegram_mcp.server import create_http_mcp_server

        mcp = create_http_mcp_server()
        assert mcp is not None

        from better_telegram_mcp import server

        assert server._multi_user_mode is True
        # Reset for other tests
        server._multi_user_mode = False

    def test_get_backend_prefers_context_var_in_multi_user(self) -> None:
        """In multi-user mode, get_backend should check ContextVar first."""
        from better_telegram_mcp import server
        from better_telegram_mcp.transports.http import _current_backend

        server._multi_user_mode = True
        server._backend = MagicMock()

        mock_ctx_backend = MagicMock()
        token = _current_backend.set(mock_ctx_backend)
        try:
            result = server.get_backend()
            assert result is mock_ctx_backend
        finally:
            _current_backend.reset(token)
            server._multi_user_mode = False
            server._backend = None

    def test_get_backend_falls_back_to_global_in_multi_user(self) -> None:
        """In multi-user mode with no ContextVar, falls back to global."""
        from better_telegram_mcp import server

        server._multi_user_mode = True
        mock_global = MagicMock()
        server._backend = mock_global
        try:
            result = server.get_backend()
            assert result is mock_global
        finally:
            server._multi_user_mode = False
            server._backend = None
