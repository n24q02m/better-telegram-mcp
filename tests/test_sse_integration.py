"""Integration coverage for unified Telegram SSE flows."""

from __future__ import annotations

import asyncio
import json
import time
from contextlib import suppress
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest

from better_telegram_mcp.auth.per_user_session_store import SessionInfo
from better_telegram_mcp.auth.telegram_auth_provider import TelegramAuthProvider
from better_telegram_mcp.backends.bot_backend import BotBackend
from better_telegram_mcp.config import Settings
from better_telegram_mcp.events import build_event_envelope
from better_telegram_mcp.transports.http_multi_user import create_app


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "data"
    directory.mkdir()
    return directory


def _make_app(data_dir: Path, runtime_settings: Settings | None = None):
    return create_app(
        data_dir=data_dir,
        public_url="https://test.example.com",
        dcr_secret="test-dcr-secret",
        api_id=12345,
        api_hash="test_api_hash",
        runtime_settings=runtime_settings,
    )


class _JSONResponseHandle:
    def __init__(self, status_code: int, headers: dict[str, str], body: bytes) -> None:
        self.status_code = status_code
        self.headers = headers
        self.body = body

    def json(self) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(self.body.decode("utf-8")))


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


async def _request_json(
    app,
    *,
    method: str,
    path: str,
    json_body: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> _JSONResponseHandle:
    response_start: dict[str, object] | None = None
    response_body = bytearray()
    request_sent = False
    encoded_body = b""
    request_headers: list[tuple[bytes, bytes]] = []

    if json_body is not None:
        encoded_body = json.dumps(json_body).encode("utf-8")
        request_headers.append((b"content-type", b"application/json"))

    if headers is not None:
        request_headers.extend(
            (key.lower().encode("utf-8"), value.encode("utf-8"))
            for key, value in headers.items()
        )

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": request_headers,
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
            return {
                "type": "http.request",
                "body": encoded_body,
                "more_body": False,
            }
        return {"type": "http.disconnect"}

    async def send(message: dict[str, object]) -> None:
        nonlocal response_start
        if message["type"] == "http.response.start":
            response_start = message
            return
        if message["type"] == "http.response.body":
            response_body.extend(cast(bytes, message.get("body", b"")))

    await app(scope, receive, send)
    assert response_start is not None
    raw_headers = cast(list[tuple[bytes, bytes]], response_start.get("headers", []))
    decoded_headers = {
        key.decode("utf-8").lower(): value.decode("utf-8") for key, value in raw_headers
    }
    return _JSONResponseHandle(
        status_code=int(cast(int, response_start["status"])),
        headers=decoded_headers,
        body=bytes(response_body),
    )


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


async def _emit_user_update_when_connected(
    backend: FakeUserBackend, update: dict[str, Any]
) -> bool:
    for _ in range(50):
        if await backend.emit_update(update):
            return True
        await asyncio.sleep(0.01)
    return False


class FakeUserBackend:
    instances: list[FakeUserBackend] = []

    def __init__(self, settings: Settings, event_dispatcher: Any | None = None) -> None:
        self._settings = settings
        self._event_dispatcher = event_dispatcher
        self._enabled = False
        self._connected = False
        self._client = self
        self.phone_code_hash = "hash123"
        FakeUserBackend.instances.append(self)

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    def _ensure_client(self) -> FakeUserBackend:
        return self

    async def send_code_request(self, phone: str) -> object:
        class SentCode:
            phone_code_hash = "hash123"

        return SentCode()

    async def sign_in(
        self, phone: str, code: str, *, password: str | None = None
    ) -> dict[str, Any]:
        return {"authenticated_as": "Fake User", "username": "fakeuser"}

    def set_event_dispatcher(self, event_dispatcher: Any | None) -> None:
        self._event_dispatcher = event_dispatcher

    async def enable_event_capture(self) -> None:
        self._enabled = True

    async def emit_update(self, update: dict[str, Any]) -> bool:
        if not self._enabled or self._event_dispatcher is None:
            return False

        envelope = build_event_envelope(
            {
                "telegram_id": 100,
                "session_name": self._settings.session_name,
                "username": "fakeuser",
                "mode": "user",
            },
            update,
        )

        if hasattr(self._event_dispatcher, "publish"):
            return bool(self._event_dispatcher.publish(envelope))
        if hasattr(self._event_dispatcher, "enqueue"):
            self._event_dispatcher.enqueue(envelope)
            return True
        return False


class FakeBotBackend(BotBackend):
    scenarios: dict[str, dict[str, Any]] = {}
    instances: dict[str, FakeBotBackend] = {}

    @classmethod
    def configure(
        cls,
        bot_token: str,
        *,
        bot_id: int,
        username: str | None = None,
        backlog: list[dict[str, Any]] | None = None,
        webhook_url: str = "",
    ) -> None:
        cls.scenarios[bot_token] = {
            "bot_id": bot_id,
            "username": username,
            "backlog": list(backlog or []),
            "webhook_url": webhook_url,
        }

    @classmethod
    def reset(cls) -> None:
        cls.scenarios.clear()
        cls.instances.clear()

    def __init__(self, bot_token: str) -> None:
        # Skip BotBackend.__init__ to avoid creating a real httpx client
        scenario = self.scenarios.get(bot_token)
        if scenario is None:
            msg = f"No fake bot scenario configured for {bot_token}"
            raise AssertionError(msg)

        self._token = bot_token
        self._bot_info = {"id": scenario["bot_id"]}
        if scenario["username"] is not None:
            self._bot_info["username"] = scenario["username"]

        self._webhook_url = cast(str, scenario["webhook_url"])
        self._backlog: list[dict[str, Any]] = list(
            cast(list[dict[str, Any]], scenario["backlog"])
        )
        self._live_batches: asyncio.Queue[list[dict[str, Any]] | Exception] = (
            asyncio.Queue()
        )
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._connected = False
        FakeBotBackend.instances[bot_token] = self

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    @property
    def bot_info(self) -> dict[str, Any]:
        return self._bot_info

    async def call_api(self, method: str, **params: Any) -> Any:
        return await self._call(method, **params)

    async def _call(self, method: str, **params: Any) -> Any:
        self.calls.append((method, params))
        if method == "getWebhookInfo":
            return {"url": self._webhook_url}
        msg = f"Unexpected Bot API method: {method}"
        raise AssertionError(msg)

    async def get_updates(
        self,
        offset: int | None = None,
        timeout: int = 30,
        allowed_updates: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append(
            (
                "get_updates",
                {
                    "offset": offset,
                    "timeout": timeout,
                    "allowed_updates": allowed_updates,
                },
            )
        )
        if offset is None and timeout == 0:
            backlog = list(self._backlog)
            self._backlog.clear()
            return backlog

        try:
            result = await asyncio.wait_for(self._live_batches.get(), timeout=0.05)
        except TimeoutError:
            return []

        if isinstance(result, Exception):
            raise result
        return result

    async def push_live_updates(self, *updates: dict[str, Any]) -> None:
        await self._live_batches.put(list(updates))


def _make_bot_update(update_id: int, text: str) -> dict[str, Any]:
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "text": text,
            "chat": {"id": 1, "type": "private"},
        },
    }


class TestUnifiedSSEIntegration:
    async def test_user_auth_to_sse_stream_end_to_end(self, data_dir: Path) -> None:
        app = _make_app(data_dir)
        provider = cast(TelegramAuthProvider, app.state.auth_provider)

        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.UserBackend",
            FakeUserBackend,
        ):
            send_code = await _request_json(
                app,
                method="POST",
                path="/auth/user/send-code",
                json_body={"phone": "+84912345678"},
            )
            bearer = send_code.json()["bearer_token"]

            verify = await _request_json(
                app,
                method="POST",
                path="/auth/user/verify",
                json_body={"code": "12345"},
                headers={"Authorization": f"Bearer {bearer}"},
            )

            stream = await _open_sse_stream(app, bearer=bearer)
            try:
                # Skip retry hint
                await stream.read_message()

                runtime = provider.resolve_runtime(bearer)
                assert runtime is not None
                backend = cast(FakeUserBackend, runtime.backend)
                delivered = await _emit_user_update_when_connected(
                    backend,
                    {
                        "_": "UpdateNewMessage",
                        "message": {"id": 1, "message": "hello from user"},
                    },
                )
                message = await stream.read_message() if delivered else []
            finally:
                await stream.close()
                await provider.shutdown()

        assert send_code.status_code == 200
        assert verify.status_code == 200
        assert delivered is True
        assert message[1] == "event: UpdateNewMessage"
        payload = json.loads(message[2].removeprefix("data: "))
        assert payload["mode"] == "user"
        assert payload["account"]["telegram_id"] == 100

    async def test_bot_auth_to_sse_stream_is_live_only(self, data_dir: Path) -> None:
        settings = Settings(
            bot_poll_timeout_seconds=1,
            bot_poll_backoff_initial_ms=10,
            bot_poll_backoff_max_ms=20,
        )
        app = _make_app(data_dir, runtime_settings=settings)
        provider = cast(TelegramAuthProvider, app.state.auth_provider)
        FakeBotBackend.reset()
        FakeBotBackend.configure(
            "123:ABC",
            bot_id=200,
            username="testbot",
            backlog=[_make_bot_update(10, "stale backlog")],
        )

        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.BotBackend",
            FakeBotBackend,
        ):
            auth = await _request_json(
                app,
                method="POST",
                path="/auth/bot",
                json_body={"bot_token": "123:ABC"},
            )
            bearer = auth.json()["bearer_token"]
            stream = await _open_sse_stream(app, bearer=bearer)
            try:
                # Skip retry hint
                await stream.read_message()

                backend = FakeBotBackend.instances["123:ABC"]
                await backend.push_live_updates(_make_bot_update(11, "live update"))
                message = await stream.read_message()
            finally:
                await stream.close()
                await provider.shutdown()
                FakeBotBackend.reset()

        assert auth.status_code == 200
        payload = json.loads(message[2].removeprefix("data: "))
        assert payload["mode"] == "bot"
        assert payload["update"]["update_id"] == 11
        assert payload["update"]["message"]["text"] == "live update"
        assert payload["update"]["message"]["text"] != "stale backlog"

    async def test_unrelated_bearer_does_not_receive_events(
        self, data_dir: Path
    ) -> None:
        settings = Settings(bot_poll_timeout_seconds=1)
        app = _make_app(data_dir, runtime_settings=settings)
        provider = cast(TelegramAuthProvider, app.state.auth_provider)
        FakeBotBackend.reset()
        FakeBotBackend.configure("token-a", bot_id=201, username="bota")
        FakeBotBackend.configure("token-b", bot_id=202, username="botb")

        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.BotBackend",
            FakeBotBackend,
        ):
            auth_a = await _request_json(
                app,
                method="POST",
                path="/auth/bot",
                json_body={"bot_token": "token-a"},
            )
            auth_b = await _request_json(
                app,
                method="POST",
                path="/auth/bot",
                json_body={"bot_token": "token-b"},
            )
            bearer_a = auth_a.json()["bearer_token"]
            bearer_b = auth_b.json()["bearer_token"]

            stream_a = await _open_sse_stream(app, bearer=bearer_a)
            stream_b = await _open_sse_stream(app, bearer=bearer_b)
            try:
                # Skip retry hints
                await stream_a.read_message()
                await stream_b.read_message()

                await FakeBotBackend.instances["token-a"].push_live_updates(
                    _make_bot_update(20, "only for A")
                )
                message_a = await stream_a.read_message()
                with pytest.raises(TimeoutError):
                    await asyncio.wait_for(stream_b.read_message(), timeout=0.2)
            finally:
                await stream_a.close()
                await stream_b.close()
                await provider.shutdown()
                FakeBotBackend.reset()

        payload_a = json.loads(message_a[2].removeprefix("data: "))
        assert payload_a["update"]["update_id"] == 20

    async def test_revoke_session_closes_stream_end_to_end(
        self, data_dir: Path
    ) -> None:
        settings = Settings(bot_poll_timeout_seconds=1)
        app = _make_app(data_dir, runtime_settings=settings)
        provider = cast(TelegramAuthProvider, app.state.auth_provider)
        FakeBotBackend.reset()
        FakeBotBackend.configure("token-revoke", bot_id=210, username="revoker")

        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.BotBackend",
            FakeBotBackend,
        ):
            auth = await _request_json(
                app,
                method="POST",
                path="/auth/bot",
                json_body={"bot_token": "token-revoke"},
            )
            bearer = auth.json()["bearer_token"]

            stream = await _open_sse_stream(app, bearer=bearer)
            try:
                # Skip retry hint
                await stream.read_message()

                revoked = await provider.revoke_session(bearer)
                message = await stream.read_message()
            finally:
                await stream.close()
                await provider.shutdown()
                FakeBotBackend.reset()

        assert revoked is True
        assert message[0] == "event: error"
        assert json.loads(message[1].removeprefix("data: ")) == {
            "reason": "runtime_stopped"
        }

    async def test_shutdown_closes_active_streams_end_to_end(
        self, data_dir: Path
    ) -> None:
        settings = Settings(bot_poll_timeout_seconds=1)
        app = _make_app(data_dir, runtime_settings=settings)
        provider = cast(TelegramAuthProvider, app.state.auth_provider)
        FakeBotBackend.reset()
        FakeBotBackend.configure("token-shutdown", bot_id=211, username="shutdown")

        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.BotBackend",
            FakeBotBackend,
        ):
            auth = await _request_json(
                app,
                method="POST",
                path="/auth/bot",
                json_body={"bot_token": "token-shutdown"},
            )
            bearer = auth.json()["bearer_token"]

            stream = await _open_sse_stream(app, bearer=bearer)
            try:
                # Skip retry hint
                await stream.read_message()

                await provider.shutdown()
                message = await stream.read_message()
            finally:
                await stream.close()
                FakeBotBackend.reset()

        assert message[0] == "event: error"
        assert json.loads(message[1].removeprefix("data: ")) == {
            "reason": "runtime_stopped"
        }

    async def test_duplicate_bot_token_replaces_session_end_to_end(
        self, data_dir: Path
    ) -> None:
        app = _make_app(data_dir, runtime_settings=Settings(bot_poll_timeout_seconds=1))
        provider = cast(TelegramAuthProvider, app.state.auth_provider)
        FakeBotBackend.reset()
        FakeBotBackend.configure("token-dup", bot_id=212, username="dupbot")

        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.BotBackend",
            FakeBotBackend,
        ):
            first = await _request_json(
                app,
                method="POST",
                path="/auth/bot",
                json_body={"bot_token": "token-dup"},
            )
            second = await _request_json(
                app,
                method="POST",
                path="/auth/bot",
                json_body={"bot_token": "token-dup"},
            )
            await provider.shutdown()
            FakeBotBackend.reset()

        assert first.status_code == 200
        assert second.status_code == 200
        # Second registration got a new bearer (old one was revoked)
        assert first.json()["bearer_token"] != second.json()["bearer_token"]

    async def test_restored_bot_resumes_from_persisted_offset(
        self, data_dir: Path
    ) -> None:
        settings = Settings(bot_poll_timeout_seconds=1)
        app = _make_app(data_dir, runtime_settings=settings)
        provider = cast(TelegramAuthProvider, app.state.auth_provider)
        provider._store.store(
            "restored-bearer",
            SessionInfo(
                session_name="restored-session",
                mode="bot",
                bot_token="token-restored",
                bot_offset=41,
                created_at=time.time(),
            ),
        )
        FakeBotBackend.reset()
        FakeBotBackend.configure("token-restored", bot_id=220, username="restored")

        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.BotBackend",
            FakeBotBackend,
        ):
            restored = await provider.restore_sessions()
            stream = await _open_sse_stream(app, bearer="restored-bearer")
            try:
                # Skip retry hint
                await stream.read_message()

                backend = FakeBotBackend.instances["token-restored"]
                await backend.push_live_updates(
                    _make_bot_update(41, "old"),
                    _make_bot_update(42, "new"),
                )
                message = await stream.read_message()
                # Allow async offset flush to complete
                await asyncio.sleep(0.1)
                stored = provider._store.load("restored-bearer")
            finally:
                await stream.close()
                await provider.shutdown()
                FakeBotBackend.reset()

        assert restored == 1
        payload = json.loads(message[2].removeprefix("data: "))
        assert payload["update"]["update_id"] == 42
        assert stored is not None
        assert stored.bot_offset == 42
