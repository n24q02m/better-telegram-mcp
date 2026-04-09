from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .base import TelegramBackend
from .security import validate_file_path, validate_url

API_BASE = "https://api.telegram.org/bot{}/"


class TelegramAPIError(Exception):
    def __init__(self, description: str, error_code: int = 0):
        super().__init__(description)
        self.error_code = error_code


class BotBackend(TelegramBackend):
    def __init__(self, bot_token: str):
        super().__init__("bot")
        self._token = bot_token
        self._base_url = API_BASE.format(bot_token)
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=30.0)
        self._connected = False
        self._bot_info: dict[str, Any] = {}

    async def _call(self, method: str, **params: Any) -> Any:
        data = {k: v for k, v in params.items() if v is not None}
        resp = await self._client.post(method, json=data)
        body = resp.json()
        if not body.get("ok"):
            desc = body.get("description", "Unknown error")
            raise TelegramAPIError(desc, body.get("error_code", resp.status_code))
        return body.get("result")

    async def _call_form(self, method: str, files: dict, **params: Any) -> Any:
        data = {k: str(v) for k, v in params.items() if v is not None}
        resp = await self._client.post(method, data=data, files=files)
        body = resp.json()
        if not body.get("ok"):
            raise TelegramAPIError(body.get("description", "Unknown error"))
        return body.get("result")

    # --- Connection ---
    async def connect(self) -> None:
        try:
            self._bot_info = await self._call("getMe")
            self._connected = True
        except TelegramAPIError as e:
            if "Unauthorized" in str(e):
                msg = (
                    "Invalid bot token. Get a new one from @BotFather: "
                    "https://t.me/BotFather"
                )
                raise TelegramAPIError(msg) from e
            raise ConnectionError(f"Failed to connect to Bot API: {e}") from e

    async def disconnect(self) -> None:
        await self._client.aclose()
        self._connected = False

    async def is_connected(self) -> bool:
        return self._connected

    async def is_authorized(self) -> bool:
        return self._connected

    async def send_code(self, phone: str) -> None:
        pass  # Bot is always authorized

    async def sign_in(
        self, phone: str, code: str, *, password: str | None = None
    ) -> dict[str, Any]:
        return {"message": "Bot mode does not require sign-in."}

    async def clear_cache(self) -> None:
        pass  # Bot API is stateless, no cache to clear

    # --- Messages ---
    async def send_message(
        self,
        chat_id: str | int,
        text: str,
        *,
        reply_to: int | None = None,
        parse_mode: str | None = None,
    ) -> dict[str, Any]:
        return await self._call(
            "sendMessage",
            chat_id=chat_id,
            text=text,
            reply_to_message_id=reply_to,
            parse_mode=parse_mode,
        )

    async def edit_message(
        self,
        chat_id: str | int,
        message_id: int,
        text: str,
        *,
        parse_mode: str | None = None,
    ) -> dict[str, Any]:
        return await self._call(
            "editMessageText",
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode=parse_mode,
        )

    async def delete_message(self, chat_id: str | int, message_id: int) -> bool:
        return await self._call("deleteMessage", chat_id=chat_id, message_id=message_id)

    async def forward_message(
        self, from_chat: str | int, to_chat: str | int, message_id: int
    ) -> dict[str, Any]:
        return await self._call(
            "forwardMessage",
            chat_id=to_chat,
            from_chat_id=from_chat,
            message_id=message_id,
        )

    async def pin_message(self, chat_id: str | int, message_id: int) -> bool:
        return await self._call(
            "pinChatMessage", chat_id=chat_id, message_id=message_id
        )

    async def react_to_message(
        self, chat_id: str | int, message_id: int, emoji: str
    ) -> bool:
        return await self._call(
            "setMessageReaction",
            chat_id=chat_id,
            message_id=message_id,
            reaction=[{"type": "emoji", "emoji": emoji}],
        )

    async def search_messages(
        self,
        query: str,
        *,
        chat_id: str | int | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        self.ensure_mode("user")

    async def get_history(
        self,
        chat_id: str | int,
        *,
        limit: int = 20,
        offset_id: int | None = None,
    ) -> list[dict[str, Any]]:
        return []  # Bot API cannot read arbitrary chat history

    async def get_updates(
        self,
        offset: int | None = None,
        timeout: int = 30,
        allowed_updates: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        result = await self._call(
            "getUpdates",
            offset=offset,
            timeout=timeout,
            allowed_updates=allowed_updates,
        )
        return result if isinstance(result, list) else []

    # --- Chats ---
    async def list_chats(self, *, limit: int = 50) -> list[dict[str, Any]]:
        self.ensure_mode("user")

    async def get_chat_info(self, chat_id: str | int) -> dict[str, Any]:
        return await self._call("getChat", chat_id=chat_id)

    async def create_chat(
        self, title: str, *, is_channel: bool = False
    ) -> dict[str, Any]:
        self.ensure_mode("user")

    async def join_chat(self, link_or_hash: str) -> bool:
        self.ensure_mode("user")

    async def leave_chat(self, chat_id: str | int) -> bool:
        return await self._call("leaveChat", chat_id=chat_id)

    async def get_members(
        self, chat_id: str | int, *, limit: int = 50
    ) -> list[dict[str, Any]]:
        result = await self._call("getChatAdministrators", chat_id=chat_id)
        return result if isinstance(result, list) else []

    async def promote_admin(
        self, chat_id: str | int, user_id: int, *, demote: bool = False
    ) -> bool:
        perms = not demote
        return await self._call(
            "promoteChatMember",
            chat_id=chat_id,
            user_id=user_id,
            can_manage_chat=perms,
            can_post_messages=perms,
            can_edit_messages=perms,
            can_delete_messages=perms,
        )

    async def update_chat_settings(self, chat_id: str | int, **kwargs: Any) -> bool:
        if "title" in kwargs:
            await self._call("setChatTitle", chat_id=chat_id, title=kwargs["title"])
        if "description" in kwargs:
            await self._call(
                "setChatDescription",
                chat_id=chat_id,
                description=kwargs["description"],
            )
        return True

    async def manage_topics(
        self, chat_id: str | int, action: str, **kwargs: Any
    ) -> dict[str, Any]:
        match action:
            case "list":
                return {
                    "error": "Bot API does not support listing forum topics. "
                    "Use user mode for full topic access."
                }
            case "create":
                return await self._call(
                    "createForumTopic",
                    chat_id=chat_id,
                    name=kwargs.get("name", "Topic"),
                )
            case "close":
                await self._call(
                    "closeForumTopic",
                    chat_id=chat_id,
                    message_thread_id=kwargs["topic_id"],
                )
                return {"closed": True}
            case _:
                return {"error": f"Unknown topic action: {action}"}

    # --- Media ---
    async def send_media(
        self,
        chat_id: str | int,
        media_type: str,
        file_path_or_url: str,
        *,
        caption: str | None = None,
    ) -> dict[str, Any]:
        method_map = {
            "photo": "sendPhoto",
            "document": "sendDocument",
            "voice": "sendVoice",
            "video": "sendVideo",
        }
        method = method_map.get(media_type, "sendDocument")

        if file_path_or_url.startswith(("http://", "https://")):
            validate_url(file_path_or_url)
            field = media_type if media_type != "document" else "document"
            return await self._call(
                method,
                chat_id=chat_id,
                **{field: file_path_or_url},
                caption=caption,
            )

        path = validate_file_path(file_path_or_url)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path_or_url}")
        field = media_type if media_type != "document" else "document"
        # ⚡ Bolt: Read file asynchronously to prevent blocking the event loop
        file_content = await asyncio.to_thread(path.read_bytes)
        return await self._call_form(
            method,
            files={field: (path.name, file_content)},
            chat_id=chat_id,
            caption=caption,
        )

    async def download_media(
        self,
        chat_id: str | int,
        message_id: int,
        *,
        output_dir: str | None = None,
    ) -> str:
        raise NotImplementedError(
            "Bot API download requires file_id. "
            "Use get_history to get message with file info first."
        )

    # --- Contacts (user-only) ---
    async def list_contacts(self) -> list[dict[str, Any]]:
        self.ensure_mode("user")

    async def search_contacts(self, query: str) -> list[dict[str, Any]]:
        self.ensure_mode("user")

    async def add_contact(
        self, phone: str, first_name: str, *, last_name: str | None = None
    ) -> bool:
        self.ensure_mode("user")

    async def block_user(self, user_id: int, *, unblock: bool = False) -> bool:
        self.ensure_mode("user")
