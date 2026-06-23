from __future__ import annotations

from typing import Any

import pytest

from better_telegram_mcp.backends.base import ModeError, TelegramBackend


class SimpleBackend(TelegramBackend):
    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def is_connected(self) -> bool:
        return True

    async def is_authorized(self) -> bool:
        return True

    async def send_code(self, phone: str) -> None:
        pass

    async def sign_in(
        self, phone: str, code: str, *, password: str | None = None
    ) -> dict[str, Any]:
        return {}

    async def clear_cache(self) -> None:
        pass

    async def send_message(
        self, chat_id: str | int, text: str, **kwargs
    ) -> dict[str, Any]:
        return {}

    async def edit_message(
        self, chat_id: str | int, message_id: int, text: str, **kwargs
    ) -> dict[str, Any]:
        return {}

    async def delete_message(self, chat_id: str | int, message_id: int) -> bool:
        return True

    async def forward_message(
        self, from_chat: str | int, to_chat: str | int, message_id: int
    ) -> dict[str, Any]:
        return {}

    async def pin_message(self, chat_id: str | int, message_id: int) -> bool:
        return True

    async def react_to_message(
        self, chat_id: str | int, message_id: int, emoji: str
    ) -> bool:
        return True

    async def search_messages(self, query: str, **kwargs) -> list[dict[str, Any]]:
        return []

    async def get_history(self, chat_id: str | int, **kwargs) -> list[dict[str, Any]]:
        return []

    async def list_chats(self, **kwargs) -> list[dict[str, Any]]:
        return []

    async def get_chat_info(self, chat_id: str | int) -> dict[str, Any]:
        return {}

    async def create_chat(self, title: str, **kwargs) -> dict[str, Any]:
        return {}

    async def join_chat(self, link_or_hash: str) -> bool:
        return True

    async def leave_chat(self, chat_id: str | int) -> bool:
        return True

    async def get_members(self, chat_id: str | int, **kwargs) -> list[dict[str, Any]]:
        return []

    async def promote_admin(self, chat_id: str | int, user_id: int, **kwargs) -> bool:
        return True

    async def update_chat_settings(self, chat_id: str | int, **kwargs) -> bool:
        return True

    async def manage_topics(
        self, chat_id: str | int, action: str, **kwargs
    ) -> dict[str, Any]:
        return {}

    async def send_media(
        self, chat_id: str | int, media_type: str, file_path_or_url: str, **kwargs
    ) -> dict[str, Any]:
        return {}

    async def download_media(
        self, chat_id: str | int, message_id: int, **kwargs
    ) -> str:
        return ""

    async def list_contacts(self) -> list[dict[str, Any]]:
        return []

    async def search_contacts(self, query: str) -> list[dict[str, Any]]:
        return []

    async def add_contact(self, phone: str, first_name: str, **kwargs) -> bool:
        return True

    async def block_user(self, user_id: int, **kwargs) -> bool:
        return True


def test_ensure_mode_passes_correct_mode():
    backend = SimpleBackend("bot")
    backend.ensure_mode("bot")


def test_ensure_mode_fails_wrong_mode():
    backend = SimpleBackend("bot")
    with pytest.raises(
        ModeError, match="requires user mode, but server is in bot mode. Set"
    ):
        backend.ensure_mode("user")

    with pytest.raises(ValueError):
        backend.ensure_mode("user")


def test_mode_error_message_user():
    err = ModeError("user", "bot")
    assert "requires user mode, but server is in bot mode. Set" in str(err)


def test_mode_error_non_user():
    err = ModeError("bot", "user")
    assert "requires bot mode, but server is in user mode" in str(err)


def test_mode_error_backward_compatibility():
    err = ModeError("bot")
    assert str(err) == "This action requires bot mode."

    err = ModeError("user")
    assert str(err).startswith("This action requires user mode. Set")


def test_mode_error_user_with_dot_trigger():
    # msg starts as "This action requires user mode." because no current_mode
    # it ends with dot.
    err = ModeError("user")
    assert str(err).count("..") == 0
