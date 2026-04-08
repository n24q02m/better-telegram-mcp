from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

# Import E2E pytest_addoption hooks so --setup/--browser/--backend are registered
from conftest_e2e import pytest_addoption as _e2e_addoption  # noqa: F401

from better_telegram_mcp.backends.base import TelegramBackend


def pytest_addoption(parser):
    """Register E2E CLI options + backend option."""
    _e2e_addoption(parser)
    try:
        parser.addoption(
            "--backend",
            choices=["bot", "user"],
            default="bot",
            help="Telegram backend mode: bot (Bot API) or user (MTProto)",
        )
    except ValueError:
        pass  # Already added


class MockBackend(TelegramBackend):
    # Provide concrete implementations to satisfy ABC
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def is_connected(self) -> bool:
        return True

    async def is_authorized(self) -> bool:
        return True

    async def send_code(self, phone: str) -> None: ...
    async def sign_in(
        self, phone: str, code: str, *, password: str | None = None
    ) -> dict[str, Any]:
        return {"authenticated_as": "Test", "username": "testuser"}

    async def send_message(
        self,
        chat_id: str | int,
        text: str,
        *,
        reply_to: int | None = None,
        parse_mode: str | None = None,
    ) -> dict[str, Any]: ...
    async def edit_message(
        self,
        chat_id: str | int,
        message_id: int,
        text: str,
        *,
        parse_mode: str | None = None,
    ) -> dict[str, Any]: ...
    async def delete_message(self, chat_id: str | int, message_id: int) -> bool: ...
    async def forward_message(
        self, from_chat: str | int, to_chat: str | int, message_id: int
    ) -> dict[str, Any]: ...
    async def pin_message(self, chat_id: str | int, message_id: int) -> bool: ...
    async def react_to_message(
        self, chat_id: str | int, message_id: int, emoji: str
    ) -> bool: ...
    async def search_messages(
        self, query: str, *, chat_id: str | int | None = None, limit: int = 20
    ) -> list[dict[str, Any]]: ...
    async def get_history(
        self, chat_id: str | int, *, limit: int = 20, offset_id: int | None = None
    ) -> list[dict[str, Any]]: ...
    async def list_chats(self, *, limit: int = 50) -> list[dict[str, Any]]: ...
    async def get_chat_info(self, chat_id: str | int) -> dict[str, Any]: ...
    async def create_chat(
        self, title: str, *, is_channel: bool = False
    ) -> dict[str, Any]: ...
    async def join_chat(self, link_or_hash: str) -> bool: ...
    async def leave_chat(self, chat_id: str | int) -> bool: ...
    async def get_members(
        self, chat_id: str | int, *, limit: int = 50
    ) -> list[dict[str, Any]]: ...
    async def promote_admin(
        self, chat_id: str | int, user_id: int, *, demote: bool = False
    ) -> bool: ...
    async def update_chat_settings(self, chat_id: str | int, **kwargs: Any) -> bool: ...
    async def manage_topics(
        self, chat_id: str | int, action: str, **kwargs: Any
    ) -> dict[str, Any]: ...
    async def send_media(
        self,
        chat_id: str | int,
        media_type: str,
        file_path_or_url: str,
        *,
        caption: str | None = None,
    ) -> dict[str, Any]: ...
    async def download_media(
        self, chat_id: str | int, message_id: int, *, output_dir: str | None = None
    ) -> str: ...
    async def list_contacts(self) -> list[dict[str, Any]]: ...
    async def search_contacts(self, query: str) -> list[dict[str, Any]]: ...
    async def add_contact(
        self, phone: str, first_name: str, *, last_name: str | None = None
    ) -> bool: ...
    async def block_user(self, user_id: int, *, unblock: bool = False) -> bool: ...
    async def clear_cache(self) -> None: ...

    def __init__(self, mode: str = "bot"):
        super().__init__(mode)
        # Override with AsyncMock for call tracking
        self.send_message = AsyncMock(return_value={"message_id": 1})
        self.edit_message = AsyncMock(return_value={"message_id": 1})
        self.delete_message = AsyncMock(return_value=True)
        self.forward_message = AsyncMock(return_value={"message_id": 2})
        self.pin_message = AsyncMock(return_value=True)
        self.react_to_message = AsyncMock(return_value=True)
        self.search_messages = AsyncMock(return_value=[])
        self.get_history = AsyncMock(return_value=[])
        self.list_chats = AsyncMock(return_value=[])
        self.get_chat_info = AsyncMock(return_value={})
        self.create_chat = AsyncMock(return_value={})
        self.join_chat = AsyncMock(return_value=True)
        self.leave_chat = AsyncMock(return_value=True)
        self.get_members = AsyncMock(return_value=[])
        self.promote_admin = AsyncMock(return_value=True)
        self.update_chat_settings = AsyncMock(return_value=True)
        self.manage_topics = AsyncMock(return_value={})
        self.send_media = AsyncMock(return_value={"message_id": 3})
        self.download_media = AsyncMock(return_value="/tmp/file.jpg")
        self.list_contacts = AsyncMock(return_value=[])
        self.search_contacts = AsyncMock(return_value=[])
        self.add_contact = AsyncMock(return_value=True)
        self.block_user = AsyncMock(return_value=True)
        self.clear_cache = AsyncMock()
        self.connect = AsyncMock()
        self.disconnect = AsyncMock()
        self.is_connected = AsyncMock(return_value=True)
        self.is_authorized = AsyncMock(return_value=True)
        self.send_code = AsyncMock()
        self.sign_in = AsyncMock(
            return_value={"authenticated_as": "Test", "username": "testuser"}
        )


@pytest.fixture
def mock_backend():
    return MockBackend("bot")


@pytest.fixture
def mock_user_backend():
    return MockBackend("user")


@pytest.fixture(autouse=True)
def mock_browser_open(monkeypatch):
    """Mock webbrowser.open and try_open_browser globally to prevent CI timeouts."""
    monkeypatch.setattr("webbrowser.open", lambda *args, **kwargs: True)
    try:
        monkeypatch.setattr("mcp_relay_core.try_open_browser", lambda *args, **kwargs: True)
    except AttributeError:
        pass
